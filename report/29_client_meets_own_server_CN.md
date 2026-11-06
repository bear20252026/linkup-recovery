# 29 · 客户端与自建网关第一次会师：三条谁都不会报的错（卡 #21 尾声）

**一句话结论**：把**重建出来的客户端**（真 Retrofit 接口 + 真签名拦截器 + 真 Gson 模型）接到
**重建出来的网关**（网关再打真 OpenIMServer），**30 条检查全绿**。会师本身不是目的——目的是这一跑
当场抓出三条"两侧各自都绿、合起来才炸"的错，其中一条让 **47 条 POST 路由一调用就抛异常**。

卡型：验收 + 纠错（客户端接口签名、响应 bean、账号 id 规则）。
独占文件：`net/src/main/kotlin/com/youloft/linkup/net/{LinkUpApi,GatewayVerify}.kt`、
`net/src/test/kotlin/com/youloft/linkup/net/BodyParameterTypesTest.kt`（新增）、
`app/src/main/kotlin/com/youloft/watcher/data/{FriendRepository,LoginRepository}.kt`（只改 map 构造）、
`server/internal/dto/dto.go`、`server/internal/gateway/handlers.go`、`server/internal/store/store.go`、
`server/internal/{gateway,store}/*_test.go`。

---

## 一、`@Body Map<String, Any?>`：Kotlin 的**变型**让 40 条路由运行时才炸

第一次跑会师，抛的是：

```
IllegalArgumentException: Parameter type must not include a type variable or wildcard:
java.util.Map<java.lang.String, ?> (parameter #1)
    for method LinkUpApi.smsClickToLogin
```

Retrofit 在**调用那一刻**校验 `@Body` 的泛型类型，含通配符就拒。而 Kotlin 的**只读** `Map<K, V>` 把值参数
声明成协变（`out V`），于是 `Map<String, Any?>` 进了 class 文件就是 `Map<String, ?>`。
**关键是变型，不是可空性**：原版编译出来的签名是 `java.util.Map<String, Object>`
（`_raw/src166/sources/gh/a.java:293`），说明原工程写的是**不变**的 `MutableMap`。

改了什么：

- `LinkUpApi.kt`：40 个 `Map<String, Any?>` ⇒ `MutableMap<String, Any?>`（签名回到 `Map<String, Object>`，
  null 值照放）；
- 调用点 `mapOf(` ⇒ `mutableMapOf(`：`FriendRepository` 7 处、`LoginRepository` 2 处、`GatewayVerify` 7 处；
- 新增 `BodyParameterTypesTest`：**反射遍历所有 `@Body` 参数**，任何一个含通配符就红；
  第二条把 `smsClickToLogin` 的签名逐字钉成 `java.util.Map<java.lang.String, java.lang.Object>`。
  **先跑了一次，两条都是红的**——看到红才敢说这门禁有效。

为什么 235 条 Robolectric 测试一条都抓不到：屏幕测的是**假仓库**，真 Retrofit 方法从来没被调用过。
这是"打桩只能证明我和我自己的读法一致"的又一个具体形状。

顺带一条 Gson 事实（决定了服务端怎么读手机号）：`serializeNulls` 默认关闭，所以 map 里的 null 值
**连键一起丢**。原版 `"phone" to null` 在网络上就是"没有 phone 键"，服务端不需要区分两者。

## 二、"匹配码"就是 userId，而且 id 必须是 8 位

三处证据拼起来：

| 出处 | 内容 |
|---|---|
| `AddFriendActivity.java:862-864` | 显示的匹配码 = `String.valueOf(user.getUserId())` 每 4 位插空格 |
| `AddFriendViewModel.MATCH_CODE_LENGTH == 8` | 输入/扫码**恰好 8 位**才当匹配码走 `pre_confirm` |
| `bean/User.java` 全部 22 个字段 | **没有**任何匹配码字段 |

⇒ 服务端不该另造一套码。我原来的 Go 实现发了一个随机 8 位 `matchCode`，还从 **10001** 起号——
5 位 id 在客户端第一条判断就被拒（toast "请输入正确的匹配码"），**根本发不出请求**。

改：`store` 删掉 `MatchCode` / `freeCodeLocked` / `ByMatchCode`，`firstUserID = 10_000_001`，
查询统一 `ByID`；测试钉"id 必须是 8 位，否则客户端拒收"。会师检查里对应一条
`userId 是 8 位（否则客户端把它当匹配码时直接拒）`。

## 三、好友列表那一行的 bean 与详情那个 bean 不是一套字段

`bean/FriendList.Info` ≠ `bean/FriendInfo`。我按详情的形状发列表，四处会**静默**读成 0/null：

| 字段 | 列表 `FriendList.Info` | 详情 `FriendInfo` | 我之前对列表发的 |
|---|---|---|---|
| 时间 | **`createAt`，秒**（`Date(createAt * 1000L)`，`FriendListVAdapter.kt:80`） | `createAt` | `createTime` ❌ |
| 关系 | **`relation: Int`** | `relation: String?` | 字符串 ❌ |
| 性别 | **`sex: Int`** | `sex: String?` | 字符串 ❌ |
| 权限 | 没有 permission 对象，只有 `permissionValue: Boolean`（绑行首勾选框） | `permission: Permission?` | 发了整个对象 ❌ |

`dto.FriendRow` 已照 `Info` 重写。镜像面的同一个坑也修了：`store.Extra.Since` 我写成 `UnixMilli()`，
而它就是客户端的 `createAt`，会被 ×1000 ⇒ 关系详情显示成**公元五万多年**；现在全链路统一成秒
（OpenIM 的 `createTime` 实测也是秒），并在两侧测试里各钉了一次区间。

给不出值的 13 个键（`av`/`deleteAt`/`id`/`imSuspend`/`location`/`newFriend`/`permissionValue`/
`receivedFirstMsg`/`remarkToMe`/`riskTypes`/`selected`/`sendFirstMsg`/`unregisterTime`）**一律不发**，
让 Gson 用它自己的默认值 —— 编一个"看起来像恢复值"的东西才是最坏的结果，已列进待验 53。

## 四、公钥页脚那条老待验，这次是客户端真代码判的

`GatewayVerify` 不调我自己的解析，而是调 `ContactSearchEnvelope.build(...)`——真机上那条
"剥 PEM → RSA-OAEP 加密"的完整路径。它非 null 才算过 ⇒ 对**我们的**后端，
四横杠 `----END PUBLIC KEY-----` 的取舍由客户端自己的代码定案（线上那台的真实页脚仍未验）。

## 五、会师检查到底跑了什么（30 条）

配置解析 → 公共参数与签名 → A 短信登录（本网关不发真短信）→ 8 位 id → `isRegister` → 手机号原样回来 →
`user/info` 认得同一账号且不再发 token → `update/info` 把 `stage` 存住 → 公钥能被真剥皮路径吃下 →
B 登录 → `pre_confirm` 用 id 当匹配码解出人 → `apply` → `applyStatus=1`（客户端渲染"已发送"）→
B 的 `apply_list` 读到 A、`status=0`、`unreadCount` 有值 → `confirm` → `friendLimit=0` →
`relation/list` 从真 IM 读到 A 且 `relation` 是数字 2、`createAt` 是秒 → 备注写进真 IM 又读回 →
`relation/info` 里 `relation` 是字符串 2（与列表不对称，bean 就这么写）→ `del` → 两边列表都不再出现。

## 六、数字（现在一共六层）

| 层次 | 命令 | 结果 |
|---|---|---|
| 客户端离线 | `sh tools/gradle.sh :net:test :app:testDebugUnitTest` | **266 绿**（`:net` 31 / `:app` 235，+2 为签名门禁） |
| 服务端离线 | `cd server && go test ./...` | **36 绿**（contract 6 / gateway 15 / openim 8 / store 7） |
| 真进程 + 死 IM | `bash server/scripts/smoke.sh` | **28 绿** |
| 真栈端到端 | `bash server/scripts/openim-e2e.sh` | **20 绿** |
| 真服集成测试 | `LINKUP_OPENIM_URL=… go test ./internal/openim -run Live -v` | **3 绿**（没真服自动 skip） |
| **客户端 ↔ 网关** | `sh tools/gradle.sh :net:gatewayVerify --args="http://127.0.0.1:8090/ 000000"` | **30 绿**，`CLIENT_MEETS_OWN_SERVER=1` |

## 七、环境侧顺手更正一条

上一轮我说过"Windows 打不到 WSL 的端口（NAT）"——**那句是错的**：当时正好赶上容器被 VM 回收后重启，
`curl` 撞上的是重启窗口。重测后 `http://127.0.0.1:10002` 从 Windows 直接 200 通，
本轮的网关因此就正常跑在 Windows 上。写进这里是为了让公开记录里不留下我那句错话。

## 八、下一步

1. 真机：APK 里把 baseUrl 指到这台网关（手机与本机同网段 + 允许入站），两台 MI 8 走一遍加友——
   那是 `gatewayVerify` 覆盖不到的部分（IME、Glide、权限弹窗、真网络抖动）。
2. #18 后半：`LoginPhoneDialog`（两个厂商 SDK 仍拿不到）、`EmptyLoginActivity` 首启隐私门、
   `ImproveUserInfoActivity`（正好是 `stage` 的消费端）。
3. 按域扩路由：定位/锁机 → 纪念日/截图 → VIP/支付。
