# 28 · 真栈验收：把 OpenIM 跑在 D 盘，服务器当场纠正我四条（卡 #21 后半）

**一句话结论**：重建网关接**真的 OpenIMServer v3.8.3-patch.18** 跑通了——登录 → 申请 → 同意 →
两个申请列表 → 好友列表 → 详情 → 备注 → 双向删除，**20 条端到端用例全绿**，另有 **3 个在线集成测试**
（没真服时自动 skip）。这一轮最值钱的不是"跑通了"，而是**跑通过程中服务器把我四条写错的东西当面纠正了**，
其中一条会让整套关系功能 100% 不可用，而它在打桩测试里永远发现不了。

卡型：验收 + 纠错（不改客户端契约，只改服务端对 IM 的调用）。
独占文件：`server/internal/openim/**`、`server/internal/gateway/handlers.go`（`deleteFriend`）、
`server/internal/store/store.go`（`Since` 单位）、`server/scripts/openim-e2e.sh`（新增）、
`recovered/openim_live_evidence_2026-11-05/**`（新增留证）、`.gitattributes`。

**没碰的东西**：Docker Desktop 的磁盘与配置（C 盘一个字节没多占）、你的现有镜像、客户端 Kotlin 代码。

---

## 一、环境是怎么搭的（以及为什么不是"搬 Docker 的盘"）

你要的是"迁到 D 然后跑起来"。搬 Docker Desktop 的 `docker_data.vhdx` 要改它的私有配置，
弄坏会连累现有容器，所以我换了条路：**在 D 盘 import 一个独立 WSL 发行版，里面自己跑 dockerd**。

```
D:\linkup-im\rootfs\ext4.vhdx   ← Ubuntu 24.04 LTS 官方 WSL rootfs（sha256 校验后才 import）
    └─ dockerd (Ubuntu 29.1.3 + compose 2.40.3)
        └─ mongo / redis / etcd / kafka / minio / openim-server:v3.8.3-patch.18
```

C 盘：0 字节增量。要撤：`wsl --unregister linkup-im`。整套占用 5.7 GB，D 还剩 950 GB。

三条环境事实值得记（换台机器大概率还会撞）：

| # | 事实 | 症状 | 处理 |
|---|---|---|---|
| 1 | 这台机 WSL 是 **NAT 模式且没有 IPv6 路由**，而 DNS 只回 AAAA | `curl` **0 秒**失败，看着像"断网" | 在该发行版里 `net.ipv6.conf.*.disable_ipv6=1` |
| 2 | **Docker Hub 直连不通**（`registry-1.docker.io` 连不上） | 拉镜像全挂 | `docker.1ms.run` 匿名可拉；`docker.m.daocloud.io` 只放行 `library/*`，`openim/*` 回 403 |
| 3 | **WSL 会在空闲时回收 VM** | 分几次 `wsl -d …` 调用时容器反复 `Up 6 seconds`，10002 时通时断，验收莫名其妙红一片 | 起栈 + 等 healthy + 跑验收必须在**一次调用**里跑完（脚本先 `nohup sleep 7200 &` 顶住） |
| 4 | 这套 compose 的 `DATA_DIR=./`，数据是 **bind mount** 不是命名卷 | `docker compose down -v` 之后 IM 仍认得上一轮的账号与昵称，以为清干净了其实没清 | 真要干净基线得 `down && rm -rf components/mnt && up`；并且网关 store 与 IM 库必须一起对待（删 store 让 id 从 10001 重开、而 IM 还留着旧关系 ⇒ `add_friend` 被"已经是好友"拒——踩过一次） |

官方 compose 用的是 `openim-docker` tag `v3.8.3-patch.1`，里面 pin 的正是
`openim/openim-server:v3.8.3-patch.18`；我把 `.env` 的 `OPENIM_SECRET` 换成非默认值再跑——
网关在 `-dev` 之外会拒绝公开的 `openIM123`，这条守卫顺带被真跑了一次。

## 二、服务器纠正我的四条（打桩测试一条都抓不到）

| # | 我之前写的 | 真服的回答 | 后果 |
|---|---|---|---|
| 1 | `get_admin_token` 发 `"userID":["imAdmin"]` | `errCode 1001`：`json: cannot unmarshal array into Go struct field GetAdminTokenReq.userID of type string` | **每次 IM 调用都拿不到令牌**，申请/同意/列表/删除全废。而协议模块 `auth.GetAdminTokenReq.UserID` 本来就是 `string`——**是我读错，不是版本差异** |
| 2 | `is_friend` 请求发 `{ownerUserID,friendUserID}` | `ArgsError: userID1 is empty`（正确字段 **userID1/userID2**） | 这个调用必失败；客户端"已经是好友"分支拿不到答案 |
| 3 | `is_friend` 响应读 `{"isFriend":bool}` | 回 **`{"inUser1Friends":…,"inUser2Friends":…}`** ——两个方向各一个旗标 | 读不存在的键 ⇒ 恒 false，"已经是好友"的提示永远不会出现 |
| 4 | `delete_friend` 调一次就算删干净 | 删除是**单向**的：删 B→A 之后 A 侧 `inUser2Friends` 仍是 true | 一边删了另一边还留着 ⇒ **好友在另一台手机上复活**。现在两个方向都删，并有测试断言两次调用的 ownerUserID 分别是双方 |

第 1 条的错误消息里还带着 `/go/pkg/mod/github.com/openimsdk/tools@v0.0.50-alpha.122…`，
顺手确认了这个镜像的构建依赖版本。

另外两条不是"错"而是**只有真服才能给的口径**：

5. **`get_friend_apply_list` 不传 `handleResults` = 不过滤**：同意之后再查，`handleResult:1` 的行还在。
   ⇒ 未读数只能自己按 `handleResult==0` 数（网关就是这么实现的，现在有了实测依据）。传 `[0]` 才只回未处理。
6. **重复注册回 `errCode 1102 / RegisteredAlreadyError / "userID registered already"`**：
   我原来的 `IsAlreadyKnown` 只匹配 "exist" 子串，**接不住这条**——于是"登录时 IM 账号已存在"这种
   正常情况会被记成失败。现在按 1102 判，并且有一条负向断言：别的 errCode 不许被当成已存在。

## 三、顺带抓出的两个我自己的实现错（与 IM 无关）

1. **`Extra.Since` 我写成了 `time.Now().UnixMilli()`**，而它出去就是客户端的 `createAt`，客户端做
   `Date(createAt * 1000L)`（`FriendInfoActivity.kt:103`、`FriendListVAdapter.kt:80`）
   ⇒ 关系详情会显示成**公元五万多年**。OpenIM 自己的 `createTime` 也是秒 ⇒ 全链路统一成秒，
   并在 store 测试里钉住取值区间（`1.7e9 < Since < 1e10`）。
2. **我的验证脚本被 Python 文本模式写成了 CRLF**：bash 不报"语法错误"这种好话，只是
   `dirname "$BASH_SOURCE"` 带上一截 `\r`，于是 cd 到不存在的目录，在错误位置跑 `go build` 后失败。
   已把 `*.sh` 与 `*.go` 在 `.gitattributes` 钉成 LF（`*.go` 那条是因为 Windows 上 CRLF 会让
   `gofmt -l` 把 12 个文件**全部**报成待格式化，门禁变假警报），并把工作区两个脚本归一化。

还有一次差点收下的假绿：`wsl -d … -- bash -c '… pkill -f linkup-gateway …'` 把**我自己**的命令行匹配掉了，
整段输出为空；`[l]inkup-gateway` 括号法也不行，因为同一行里还有别处提到这个名字——改用 `pkill -x`（只比进程名）。

## 四、现在的验收矩阵

| 层次 | 命令 | 结果 |
|---|---|---|
| 离线单测 | `go test ./...` | **36 绿**（contract 6 / gateway 15 / openim 8 / store 7），Windows 与 Linux 各跑一遍 |
| 真进程 + 死 IM | `bash server/scripts/smoke.sh` | **28 绿**——证明不可达时报错而不是报空好友列表 |
| **真栈端到端** | `OPENIM_URL=… OPENIM_SECRET=… bash server/scripts/openim-e2e.sh` | **20 绿**，OpenIM 原始应答留证 |
| **在线集成测试** | `LINKUP_OPENIM_URL=… go test ./internal/openim -run Live -v` | **3 绿**；无真服时 skip，不拖红离线套件 |

留证文件（原样，不做加工）：`recovered/openim_live_evidence_2026-11-05/` 里四个 JSON——
`friendsInfo` / `FriendRequests` / `friendRequests` / `inUser1Friends+inUser2Friends` 的真实形状。

## 五、待验 47/48/49 划掉，还剩什么

`recovered/DESIGN_CN.md` 第九节的 47（网关↔真 OpenIM 闭环）、48（三个不规则 key 的拼法）、
49（`handleResults` 口径）三条已改为**已验**，出处就是本报告与留证。

仍然没验的：
- **待验 50**：三方登录 `isRegister` 该答 true 还是 false（要真客户端配合才知道原版行为）；
- 97 条里剩下的 80 条路由字段（要线上源码或对生产逐条打）；
- **待验 51**：生产网关 `link.tttick.com` 到底要不要补 Signature 校验（运维决定）；
- 客户端把 baseUrl 指到这台重建网关，用两台真机走一遍加友——那才是这条链的最后一环。

## 六、下一刀

1. 客户端 baseUrl 指向重建网关，真机跑加友（顺带把 50 判定掉）。
2. 按域扩路由：定位/锁机 → 纪念日/截图 → VIP/支付；`internal/store` 那一层随时可换成真库。
3. 会话与消息面接 OpenIM 的 msg/conversation 域——那部分 IM 是现成的，LinkUp 侧要补的是
   `SdkInitManager` 的登录/登出与 `AccountSideEffects.onSignedIn` 的实现（#11 遗留）。
4. 服务端源码（Jenkins job `desyb_always_guard.api`）继续追：现在它影响的是"我定的那些取值对不对"。
