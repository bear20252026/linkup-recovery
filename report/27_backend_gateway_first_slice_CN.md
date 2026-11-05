# 27 · 后端重建第一刀：Go 网关 + OpenIMServer 适配层（卡 #21）

**一句话结论**：`server/` 落下来了——17 条路由（登录 5 + 配置/公钥 2 + 关系域 10），照客户端的契约
一个字节不改；关系与好友状态交给 OpenIMServer，LinkUp 自有的东西（匹配码、关系类型、九项共享开关、
备注、验证码、配额）留在本地。**34 个 Go 测试 + 28 条真进程真 socket 用例全绿，全部离线可跑**。
唯一没跑的是真 OpenIM 容器本身——C 盘放不下那套镜像，这条留在待验 47，没算绿。

卡型：新增（后端第一刀，含一层三方服务适配）。独占文件：`server/**`、`tools/publish.sh`（改复制策略）、
`README.md`、`recovered/DESIGN_CN.md`（五点二十二 + 待验 47–52）。
**没碰任何 Kotlin 文件**，所以 `net`/`app` 的 264 条不受影响。

**安全边界**：这一刀**物理上发不出短信**（没有任何短信通道，`api/sms/send` 只把码写进 store 并打日志）；
不碰线上写接口；`-dev` 才允许用公开 demo 密钥；RSA 私钥与 store 文件已进 `.gitignore`。

---

## 一、为什么是 OpenIM，以及它接得住多少

按你的方向（找一个符合的开源项目接上）先把家底摆清楚：**97 条路由里，OpenIM 能直接顶掉的是
关系域那 10 条**（好友、申请、备注、是否好友）＋ 还没重建的消息/会话/对象存储面，约 **12–14 条**；
剩下 83 条是 LinkUp 自己的业务（定位轨迹、锁机、截图、纪念日、VIP/支付、风控、上报），
任何 IM 开源项目都不会替你实现它们。另外要说一句：现网的即时通信是**环信**（SaaS，appkey 在我方手里），
所以 OpenIM 不是"必须换"，是"我们重写服务端时可以选择自己掌控"——这个取舍我按你定的方向执行。

分工因此很清楚：

```
客户端 ──(原契约：路径/信封/AES 签名/JWT 全不变)──> Go 网关
                                                      ├─ internal/store  账号·匹配码·每方向 extras·验证码·配额
                                                      └─ internal/openim 好友关系·申请·（以后）会话与消息
```

网关用 **Go**：与线上那个丢失的服务同栈（源码线索是 `always_guard.api` + Go 中间件
`internal/middleware/signature.go`/`jwt.go`），本机 Go 1.27 现成，产物是一个静态二进制。

## 二、这一轮从代码里新核出来的四条（之前不知道）

| # | 事实 | 出处 |
|---|---|---|
| 1 | `api/relation/confirm` 的 `code` 在 **query**，body 里那份只是重复 | `LinkUpApi.kt:54` `@Query("code") code: Long, @Body payload` |
| 2 | `api/user/update/info` 的 body 恰好四键：`avatar` / `nickname` / `sex` / **`stage`** | 1.6.6 `datasource/a.java:402`，键名分别来自 `ImproveUserInfoActivity.f65723w = "avatar"`（`:54`）、字面量 `"nickname"`、`com.baidu.mobads.sdk.api.ArticleInfo.USER_SEX = "sex"`（`:6`）、字面量 `"stage"` |
| 3 | `stage` 有真实语义：补资料向导走到第几步。`App.user.setStage()` 本地写，下次进屏 `getStage() > 0` 就从那一步继续 | 1.6.6 `ImproveUserInfoActivity.java:343, 411-412` |
| 4 | OpenIM 两个申请列表的响应键**大小写不一致**：`get_friend_apply_list` → `FriendRequests`，`get_self_friend_apply_list` → `friendRequests` | `openimsdk/protocol v0.0.73-alpha.12`：`relation/relation.pb.go:514` vs `:2083`（protojson 生成的 tag 就是这样） |

第 2/3 条直接影响可用性：上一版我把 `update/info` 只当 `{nickname, avatar, sex}`，**`stage` 会被服务端丢掉**，
于是每个中途退出补资料的人下次都被打回第一步——而且不报错。现在 `store.User` 有 `Stage`，
并且测试钉住"客户端没带的键不许清空已存值，而 `stage: 0` 必须真的生效"（`0` 在 stage 里是有意义的值）。

第 4 条是"反过来说服我别改"的：Go 的 `encoding/json` 有大小写不敏感兜底，所以一个解码器恰好能读两种拼法。
测试把 **两种大小写都写进打桩**，防止以后有人"顺手统一"把自发列表读成空。

## 三、我自己写出来的四个 bug（都在这轮被抓到并修）

1. **签名中间件在"跳过校验"分支里顺手没读 body。** 后果：`login`/`sms` 路径的 body 永远是空 map ⇒
   `typeId` 解析成 0 ⇒ **所有登录都被自己拒**。现象是 gateway 测试 9 条红，错误消息却是我自己写的
   "一键登录需要号码认证 SDK"——**一条误导性的拒绝话术把真因藏了一轮**。修：body 一律先读再决定校不校。
2. **`IssueCode(phone, ttl)` 收了 `ttl` 然后 `_ = ttl`。** 验证码永不过期。这类东西编译过、看着也对，
   只有真去断言过期才红。修：`Code.ExpiresAt` + `CheckCode` 里比对并清除，测试覆盖"过期/重发/一次性/尝试上限"。
3. **`ThirdAccount` 的 switch 有一条分支让返回指针保持 nil** → 测试当场 panic。更深的一层是：我原来给
   三方登录编了个账号键 `"wx"+platform+":"+unionId` 塞进 phone 列，于是**"微信绑过手机的人再用短信登录"
   会拿到第二个账号**。修：`User` 增加 `unionId`/`platform`，规则改成 union id 为主键、手机来就附上、
   只有手机已知时该账号收养 union id（前提它原来没有）。测试断言"一个人无论几个入口都只有一个账号"。
4. **`smoke.sh` 自己漏了 query**：签的是 `...?page=1&pageSize=20`，请求却打的裸路径 ⇒ 网关答 1001。
   我先怀疑网关，查了两轮才确认是脚本错。副作用是好的：这条现在是一对用例——
   签名与实际 query 不一致 ⇒ 拒；一致 ⇒ 过。

顺带记一条**发布链的坑**（同源教训）：`tools/publish.sh` 用 `git archive | tar -x` 叠加复制，
`rm -rf` 只列了当时存在的那几个目录名——本卡新增的 `server/` 不在列，**本地删掉的文件会在
公开仓里复活**。已改成整目录清空再解。

同一段还揪出**我自己写错的一条**：新写的目录表里我加了一行 `core-net/`，说它是 1.5.6 那套自研 HTTP 栈
（定位上报）。查磁盘才发现那只是个**空目录骨架**——`find` 出来 0 个文件、`settings.gradle.kts` 里
没有 `:core-net`、它从未进过 git 也从未进过公开仓。yftracker 旧链路的真实状态仍是待验第 3 行写的
"尚未接入重建工程"。空骨架已删、那一行已去掉。**教训**：写"目录 → 职责"这种表的时候，
要逐行对着 `git ls-files` 数一遍，不能照着印象写。

## 四、三分类：照客户端的 / 我定的 / 未知

完整表在 `server/README.md`。这里只列"如果换个人实现，最可能被悄悄改掉"的三条：

- **不可改**：RSA 公钥必须以**四个横杠**结尾 `----END PUBLIC KEY-----`。客户端就剥这个字面量，标准
  五横杠会残留一个 `-` → Base64 解不开 → 静默走 `status=10086`（连"匹配码无效"都不弹）。
  这轮不只是写进文档，是落成服务端代码 + **负向测试**（五横杠必须测出解析失败）。
- **不可改**：`Authorization` 是裸 JWT（无 `Bearer `）；`typeId`、`platform` 在 JSON 里是**字符串**；
  签名跳过规则只看路径分段有没有 `login`/`sms`（所以 `api/client/config` 是要签名的）。
- **我定的（全部是启动 flag，不写成"看起来像恢复值"的常量）**：`-friend-limit` 默认 `-1` 不配额；
  `-cut-login-type` 默认 `9` 不走一键登录（GY / FlyVerify 两个 SDK 拿不到，答 `1`/`3` 是骗客户端它有一条
  走不通的路）；"该用户不存在"用 `1002`；`api/client/config` 九个开关取客户端自己的 fallback 值、
  IM 群 id 留空；confirm 时两个方向各保留各人的选择。

**与线上现状一处刻意不同**：生产网关 `link.tttick.com` 实测不校验 Signature（不带签名也给你真配置，
见 DESIGN §七），重建版**默认校验**——这是安全取向的正向偏离，但要不要给线上补这道闸，得运维拍板（待验 51）。

## 五、验收数字，以及我**没**验收的

- `go vet` 干净、`gofmt` 干净；`go test ./...` **34 绿**：contract 6、gateway 15、openim 6、store 7，全离线。
- `bash server/scripts/smoke.sh` **28 绿**：真起 `cmd/server` 进程、真走 TCP、签名由 **openssl** 在 shell 里算。
  于是同一条 AES-128-CBC 契约在 **JVM 客户端 / Go / OpenSSL** 三个实现下对上了。
  （顺带：我一开始把 openssl 的 `-K` hex 里 `4b` 打成 `6b`，两家"不一致"其实是我的键错——这类
  "第三方工具看起来在反对你"的场合，先怀疑自己的输入。）
- 其它被 smoke 钉住的运行时事实：`-store=` 内存模式可用、私钥文件确实落盘且重启复用（不换 key）、
  空 JWT/空 IM 密钥在 `-dev` 下被顶替**并打进日志**、未知路径先被签名闸挡下（不会 404 泄漏路由表）。
- **没验收的**：真 OpenIM 容器一次都没起过。C 盘 7.2 GB（99% 满）而 Docker data-root 在 C，
  那套镜像（mongo:7.0.28 / redis:7.0.0 / bitnamilegacy kafka+minio+etcd / openim-server:v3.8.3-patch.18）
  解压 2.5–3.5 GB。所以 `internal/openim` 只有 httptest 打桩，**"网关 ↔ 真服"是待验 47，不是绿**。
  smoke 里甚至**故意**把 `-openim` 指到死端口，用来证明不可达时答 `status:500 服务暂时不可用`，
  而不是一个看起来像成功的空好友列表——这条是"绝不报假绿"在服务端侧的形状。
- **没做的真机验证**：客户端还没把 baseUrl 指到这台网关跑过（那是下一刀的第一件事）。
- 客户端侧同时复验没有倒退：`:net` **29 / 0**、`:app` **235 / 0**（合计 264，从 XML 报告逐条数出来的；
  本卡没碰任何 Kotlin 文件）。
- 一条差点被吞掉的验收事故：`sh tools/gradle.sh … | tail` 之后的 `$?` 是 **`tail` 的 0**。我第一次就是这么
  跑的，屏幕上"没有 FAILED"，实际那一次是 **BUILD FAILED**。真退出码必须从被测命令自己取。
- 一条顺带挖出的坏任务：`:fastkit:testDebugUnitTest` 现在跑不起来（AAPT 找不到 `colorPrimaryVariant` 等
  Material 属性——模块 res 引用了它们，测试变体类路径却没有 material 依赖），而 `fastkit/src` 只有 `main/`，
  **零测试源**。所以回归命令里不该出现它；将来给 :fastkit 补测试时要先补这个依赖。

## 六、下一刀切哪里

1. **把 Docker 磁盘迁到 D**，跑通待验 47–49（含三个不规则 key 与 `handleResults` 口径），把打桩换成真服。
2. 客户端 baseUrl 指过来，真机走一遍"两台设备加友"——那时 `isRegister` 到底该答什么（待验 50）会自己现形。
3. 按域扩路由：定位/锁机 → 纪念日/截图 → VIP/支付。每域一批测试，`store` 那一层随时可替换成真库。
4. 服务端源码（Jenkins job `desyb_always_guard.api`）仍要追：现在它影响的是"我定的那些取值对不对"，
   不再是"能不能上线"。
