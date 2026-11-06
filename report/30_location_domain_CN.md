# 30 · 定位域服务端：上报 → 按天 → 当天轨迹（卡 #22 前半）

**一句话结论**：定位的数据面做实了。网关新增 3 条路由（`api/location/report`、`api/location/days`、
`api/location/v2/tracks`），把设备上报的点存下来、按天索引、算回客户端轨迹页要的那三个数字与两种行；
**服务端 49 个测试全绿**，并且 `gatewayVerify` 从客户端一侧把它跑了一遍——**46 条全绿**，其中 16 条是定位链，
全部由客户端**真 bean** 解出来（不是手写的期望 JSON）。

卡型：新功能（服务端一个域 + 客户端契约验证）。
独占文件：`server/internal/location/**`（新增）、`server/internal/{store,gateway,dto}/**`、
`server/cmd/server/main.go`（3 个 flag）、`net/src/main/kotlin/com/youloft/linkup/api/dto/Dtos.kt`
（`TrackRecordBean.points/tracks` 的类型）、`net/src/main/kotlin/com/youloft/linkup/net/GatewayVerify.kt`。

**红线照旧**：这一刀没打线上任何接口；`gatewayVerify` 与 `smoke.sh` 的 `/api/sms/send`、
`/api/location/report` 都打在**重建网关**上，它没有任何短信通道，也不会长途外发。

---

## 一、为什么先做服务端而不是轨迹页

轨迹页与首页地图卡在同一个依赖上：`com.baidu.mapapi.map.MapView`（在
`recovered/missing_third_party_classes.txt` 里，Maven Central 没有，本机取不到）。界面等得起，
**数据契约等不起**——早一天把服务端形状钉死，界面接上来就只是插一层。

所以这一刀交付的是可独立验收的功能：手机上报位置 → 服务端存下并归日 → 轨迹页读某天时拿到
折线、事件行、三个汇总数字，并且**别人不能随便看**。

## 二、每个形状都有出处（不是设计出来的）

| 形状 | 依据 |
|---|---|
| `totalDistance` 米 | `TrackRecordFragment.java:181` 除以 1000 后拼 "km" |
| `totalStayTime` 秒 | `:164` 乘 1000 再格式化 |
| `timePeriod` epoch 秒 | `:280` `Date(timePeriod * 1000)` 格式化 "HH:mm" |
| `line.type` 1/2/3/4 | `:236-300` 的分支：1→`less_than_1m`、2→`less_than_200m`、3→"无法获取定位"图标、4→"没有新定位" |
| `track.type` 2=到达 3=离开 | `:484-500`：2 用停留图标 + `R.string.arrive`，3 用蓝点 + `R.string.leave` |
| 行只在 `lostType == 0` 时渲染 | 同段守卫 |
| `bean/Address` 六个键、**没有整串地址** | `bean/Address.java` ⇒ 整串由服务端拼，`placeOf` 按 parts 顺序拼 |
| `api/location/report` 的 body 是 `Location` bean 本身（10 键，含 `type`） | `gh/a.java:401`：`@Body Location`，不是 map |
| `TrackRecordBean.Point/Track/Line` 是嵌套 bean | `bean/TrackRecordBean.java`；`:net` 生成器把两个列表留在了 `List<JsonElement?>`，这一刀换成 `List<TrackRecordBean.Point?>?` / `…Track?>?` |

算法本身很朴素：**段距离 ≤ 1 米就是还在同一段停留**（阈值直接来自客户端那句 `less_than_1m`），
超过就是移动；事件行只在停留边界、数据缺口、无法定位时产生，纯移动的点是折线顶点而不是行。

## 三、三个服务端量做成了 flag，而不是藏进代码

`-stay-seconds`（停留多久算一个到达点，默认 120）、`-gap-seconds`（沉默多久算"没有新定位"，默认 1800）、
`-loc-timezone`（一天从哪个时区算，默认 `Asia/Shanghai`）。

前两个是原服务端算完就扔的中间量，客户端只看结果，APK 里没有依据；把它们写成"看起来像恢复值"的常量
是最坏的做法。测试里有一条 `TestLocationFlagsAreHonouredNotHardcoded`：把阈值改成 600 秒，
四分钟的停留就**不该**算到达点，但停留秒数仍然要记满 240 —— 证明是真参数。

时区那条还有个平台坑：Windows 上构建的 Go 没有内嵌 tzdb，`time.LoadLocation("Asia/Shanghai")` 会失败，
所以 `loadZone` 在失败时退回固定 +08:00 而不是让服务起不来。

## 四、谁能看谁的位置

自己永远可以；他人必须有任一方向的关系（确认过的好友）。拒绝时 **HTTP 200 + 信封 `status=403`**，
文案 "没有查看该设备位置的权限"——403 这个码是**我定的**（客户端只判 `status != 200` 并 toast `msg`，
原服务端的码不可观测），这一点在代码和 README 里都写明了。

`gatewayVerify` 里有一条时序性的断言：关系删除之后再读对方轨迹，必须被拒。这条只有两侧都真跑才测得出来。

## 五、两条路由故意没做（不是漏了）

- `api/location/batch/report`：接口在 `gh/a.java:255` 声明了，但 1.6.6 整棵树找不到调用点。
  body 的键名没有任何依据，**编一个键名只会让以后对线上时多一条假一致**（待验 58）。
- `api/widget/location` / `api/widget/track`：响应里的 `friendLocation`/`friendState` 需要先有
  "配对的另一人"模型和电量/屏幕态（属敏感事件域）。没有那两层就做，就是填字段（待验 59）。

## 六、数字

| 层次 | 命令 | 结果 |
|---|---|---|
| 定位算法 | `go test ./internal/location` | **9 绿** |
| 定位路由 | `go test ./internal/gateway -run Location` | **4 绿** |
| 服务端全量 | `go test ./...` | **49 绿**（contract 6 / gateway 19 / location 9 / openim 8 / store 7） |
| 客户端全量 | `sh tools/gradle.sh :net:test :app:testDebugUnitTest` | **266 绿** |
| 死 IM | `bash server/scripts/smoke.sh` | 28 绿 |
| 真 OpenIM | `bash server/scripts/openim-e2e.sh` | 20 绿 |
| **客户端 ↔ 网关** | `sh tools/gradle.sh :net:gatewayVerify --args="http://127.0.0.1:8090/ 000000"` | **46 绿** |

定位链在会师检查里长这样：上报一个带地址的 fix（body 是 `Location` bean）→ 服务端回显经纬度/
`timePeriod` 并分配 `id` → 同址 5 分钟 → `days` 里有今天且是 `yyyy-MM-dd` → `v2/tracks` 解出
`points`（2 个，类型是嵌套 bean）与 `tracks`（2 行，type 依次 2/3）、`totalDistance=0`、
`totalStayTime=300`、`arrivalPointCount=1`、`friendLocation` 带地点名、`permission` 非空 →
删关系后读对方轨迹被拒。

## 七、下一刀

1. 轨迹页的**地图面**：要么找到百度 Maps SDK 的离线件（含 `MapView`），要么先用
   非地图版面把这一页的列表/汇总卡跑起来（数据已经齐了）。
2. 敏感事件域（`api/sensitive/*`）→ 它补上 `FriendState`，桌面卡片两条路由才动得了。
3. 配对模型（守护人/被守护人），这是 widget 与"别人能不能看我位置"的真正依据。
