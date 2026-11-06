# 31 · 定位抽象层：一家接口，各家 SDK 与 API（卡 #23）

**一句话结论**：定位不再是"绑死百度"的代码，而是 `location/` 模块里的**一家接口 + 三家实现**：
系统 `LocationManager` 今天就能跑，百度实现用反射绑定（签名逐条对着 APK 反编译的行号），
测试假源让回归不碰任何 SDK。接口层零三方依赖，并由一条门禁测试把这件事钉住。
**`:location` 93 个测试全绿，客户端三层合计 367 全绿，0 skip。**

卡型：新功能（一层可替换的抽象 + 两家真实现 + 一条架构门禁）。
独占文件：`location/**`（新模块）、`settings.gradle.kts`、`app/build.gradle.kts`、
`app/src/main/kotlin/com/youloft/watcher/data/{LinkUpLocationGateway,LocationSources}.kt`、
`app/src/main/kotlin/com/youloft/watcher/data/local/{InstallChannel,StoredRemoteConfig}.kt`、
`app/src/main/kotlin/com/youloft/watcher/RecoveryProbeActivity.kt`、
`recovered/{geo_golden_156.txt,baidu_location_api_156.txt}`。

**红线照旧**：全离线。没打线上接口，没发过一条短信；`_raw/` 依旧不入库。

---

## 一、为什么是"单独一个模块的一家接口"

用户这轮的原话是：**"我要一个那种抽象的。定位。他可以兼容各家的 sdk。和 apI。把它单独儿变成一个接口。"**

背景很硬：`com.baidu.location.*` 与地图 View 都只活在两个 APK 里，公共仓库没有可拉的产物，
所以"照原版直接写百度调用"= 定位功能被一个拿不到的依赖按住。把这层抽出来之后，
"SDK 不在场"只是**其中一种实现**，功能今天就能往下走。

切分点不是我发明的：**1.6.6 原版自己已经找到了一半**。`_raw/src166/sources/dg/a.java` 里有一个不可变值类
`Snapshot(locationMode, scanSpan)`，`update()` 在配置没变时返回 null，调用方
（`manager/s0.java:769-774`）因此只在真变了才 `setLocOption`；`toOption()` 把另外**十三个**百度字段
写成常量。也就是说原版运行时已认定"会变通的只有模式与间隔"。`LocationRequest` 就带这两个（加
`needsPlace / needsPoi / allowCachedFixes / singleFixTimeoutMillis`），那十三个常量留在适配器里。

## 二、接口必须能表达原版真的做过的动作

| 接口成员 | 原版动作 | 证据 |
|---|---|---|
| `start(request, listener)` | 建 client + 选项 + 注册监听 + `start()` | `x0.java:677-699`、`s0.java:764-785` |
| `update(request)` | 休眠切档（前台 2000ms ↔ `locationScanMillsWhenDormancy`） | `x0.java:619-648`、`s0.java:810` |
| `singleFix(request)` | 单次定位 `setOnceLocation(true)` + `requestLocation()` | `s0.java:3031`（`reason=manual_request`） |
| `lastFix()` | `CacheUtils.S1(location)` 存的最近定位 | `x0.java:707-714` |
| `PlaceResolver` | 地址缺了才反查；地址→坐标 | `utils/j0.java:149-169`（源名 `GeoCodeUtils.kt`）、`x0.java:785-797` |
| `LocationGateway.report` | `POST api/location/report`，body 是 `Location` bean | `gh/a.java:401`、`bh/a.java:354` |
| `ReportKind`（bean 的 `type`） | 0 未判定 / 2 停留 / 3 离开 / 4 转发未变化 | `x0.java:304 / 251 / 203,211 / 1418` |

**逆地理为什么是独立一条缝**：原版的 `GeoCoder` 来自百度**地图搜索** SDK —— 另一个 artifact、
另一个初始化入口，也是全 app 唯一能把地址变回坐标的东西。把它挂在 provider 上，等于强迫每家 SDK
都长出一张它本来没有的脸。

**API 侧只抽象"写"**：`days` / `v2/tracks` 的响应形状在 `:net` 已被真 bean 钉死、并被 `gatewayVerify`
用真 Gson 解过。再在定位层建一套"中立读取模型"就是给同一份线上契约准备两份真相 —— 这种契约最不该这样。

## 三、坐标系：bean 里存的是 WGS84（这轮最容易做错的一条）

`x0.java:290` 每个回调都先 `h0.c(lat, lng)`，即 **bd09ll → gcj02 → wgs84**；要算距离时
`bean/Location.java:222 getLatLng09()` 再换回去。整条链上没有任何地方把 bd09 直接落库或上报。

于是：`GeoMath.kt` 是 `h0.java` 的逐字移植（含"中国范围外不偏移"的短路，以及 `wgs84→bd09`
范围外**仍然**加 bd09 偏移这个怪癖），并且新增一份证据文件
`recovered/geo_golden_156.txt` —— 把 `h0.java` 的纯算术抄成临时 Java，**用 JDK 真跑出来的 46 行**。
`GeoMathTest` 逐行复现全部 40 个数值断言。适配器的坐标系**从 `BDLocation.getCoorType()` 读**而不是假定，
高德/腾讯那种默认 gcj02 的厂商接进来才会被正确归一。

距离：原版 `DistanceUtil.getDistance(bd09, bd09)`，缺点时返回哨兵 `-1.0`（`x0.java:786` 专门判它）。
中立实现 `distanceMeters(a, b)` 用**可空**表达同一件事，不把 `-1` 当数字往下传。

## 四、测试当场抓出我五条错（全部已修）

这层的测试**跑的是生产反射代码**，SDK 只是签名一致的替身 —— 所以它有能力红，也就真红了：

1. **`Method.invoke` 对 void 方法返回 null**，我却拿返回值判成败 ⇒ `setLocOption` / `register` / `start`
   每一次成功都被当成失败，`BaiduLocationProvider.start()` 根本返回不了 true，`LocationClient.start()`
   一次都没被调到。
2. **嵌套枚举的二进制名只有一个 `$`**。我写出两个 ⇒ `Class.forName` 恒失败 ⇒
   `locationMode` 与 `firstLocType` 永远 null，而且 `setLocationMode(null)` 会被静默传给 SDK。
   现在 `buildOption` 对**任何**缺失成员直接返回失败并写 `missingReason`，不再"少配一项也照样出门"。
3. **我凭语义编了一个 SDK 方法**：`unregisterLocationListener`。两版 APK 的 `LocationClient`
   都只有两个 `register` 重载，**没有注销** —— 这同时解释了原版为什么全进程只建一个 client。
   `close()` 改成 stop + 丢弃，测试替身与证据文件一起去掉这个方法。
4. `SystemLocationProvider.singleFix` **成功后泄漏注册**：清理只挂在 `invokeOnCancellation` 上，
   正常返回那条路径没人摘，每个 enabled provider 留下一个 0ms 注册，`stop()/close()` 还看不见它。
5. `Location.getId()` 在 compileSdk 34 **不可见**，我写的 `providerId = id` 编译得过但恒为 `"system"`；
   改用 `location.provider`，现在能真的报 `gps` / `network`。

第 3、5 两条也说明：这类绑定**必须逐条对着反编译行号**，`recovered/baidu_location_api_156.txt`
存在的意义就在这里。

## 五、节律逐字移植，判定明确不搬

`x0.java:156-158`：`speed<=0 → maxInterval`，否则 `min(max(minUploadDistance/speed, minInterval), maxInterval)`；
放行条件 `cur.timePeriod - lastReported.timePeriod >= 上式`，速度取两点的较大值（`x0.java:191/221`）。
移植成 `LocationTuning.cadenceSeconds` + `ReportGate`，并被测试钉成数字表
（0→20s、1→20s、4→10s、8→5s、64→5s）。

单位是这里最容易悄悄错的：`x0.java:288` **只在 `locType==61`（GNSS）**时把百度的 km/h 除以 3.6，
其他类型一律写 0 —— 所以"静止"在原版是由厂商定位类型决定的，不是速度阈值。框架源本来就是 m/s，
不除。**弄错就是线上上报频率差 3.6 倍。**

`x0.java:164-265` 那套"停留点 / 潜在停留点 / 离开判定"状态机**本轮没搬**：它依赖三个进程内状态，
JADX 反编译里寄存器复用严重，硬抄会产出"看着像、数字不对"的实现。所以 `ReportGate` 只做节律放行、
`type` 一律发 0；服务端 `Summarise` 本来就按原始点算停留/离开，功能不断。

抄录时发现**原版自身一处可疑**：`x0.java:242` 判"潜在停留范围外"用的是 `stayDistanceThreshold`（200m），
而按键名语义应是 `potentialStayDistanceThreshold`（20m）。两种读法差 10 倍，直接决定轨迹密度 —— 进待验 62。

十七个定位远程配置键连同默认值全部入表（`manager/l.java:64-80`），`RemoteConfig` 新增 `number()`，
`LocationTuning.fromConfig` 按键覆盖、缺键保留原包兜底（`locationMaxInterval` 读成 0 就意味着每条都上报）。

## 六、真机上还差什么

`RecoveryProbeActivity` 多了一段只读检查：选到哪家 provider、各家的 `capabilities`、这台机器
权限状态、真实配置阈值、一次 `singleFix`、以及 `Geocoder` 到底能不能出地址。
只有手机能答的三条已进待验表：**62**（200m 还是 20m）、**64/65**（百度 AAR 从哪来 +
真 SDK 是否接受动态代理出来的监听器）、**66**（国内 ROM 上 `Geocoder` 是否可用 —— 它决定"无 SDK 版"
能不能真的产品化）。**63** 是一次只读 GET `configsys` 就能定的十七个键线上真值。

## 七、验收

| 命令 | 结果 |
|---|---|
| `sh tools/gradle.sh :location:testDebugUnitTest` | **93 绿**：Baidu 反射 23、坐标黄金样本 14、节律/采集 17、系统源 16、Geocoder 10、选择回退 7、架构门禁 6 |
| `sh tools/gradle.sh :net:test :app:testDebugUnitTest` | **274 绿**（:net 31 + :app 243；本轮新增 8 条：十键上报形状、WGS84 出网、type 0/2/3/4、配置阈值保留兜底） |
| `cd server && go test ./...` | 49 绿（服务端本轮未动；`smoke.sh` 与 `gatewayVerify` 同理没重跑，没把旧结果当本轮结论） |

## 八、下一张卡（不在本轮范围）

1. 上报前台服务（带 `ACCESS_BACKGROUND_LOCATION` / `FOREGROUND_SERVICE_LOCATION`，
   并把 `privacyAgreed` 接到真的隐私同意位）。
2. 停留/离开判定作为 `ReportPolicy` 的第二实现 —— 先把 242 行那个 200/20 定下来。
3. 轨迹页地图：`LocationProvider` 这条缝已经证明"厂商可以缺席"，地图 View 该照同一条缝做。
