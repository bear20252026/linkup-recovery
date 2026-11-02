# LinkUp 静态摸底报告 - Stage 1

> 第一阶段：基于 APK 元数据 / Manifest / 资源 / native 库的静态分析  
> 工具：androguard 4.1.3 + python-zipfile  
> 时间：2026-05-19  
> APK：`linkup_1.5.5.apk` (121MB, SHA256 `bd1f2095c0f281c75e41736ad241474649d4d79ef4105ff905f93bfbfe7b1270`)

---

## 一、基本信息

| 字段 | 值 |
|---|---|
| 包名 | `com.youloft.watcher` |
| App 名 | LinkUp |
| 版本 | 1.5.5 (versionCode=155) |
| min/target SDK | 26 / 34（Android 8.0 ~ Android 14） |
| 签名 | v1 + v2（**未启用 v3**），CN = `YL` |
| 主 Activity | `com.youloft.watcher.pages.SplashActivity` |
| 开发者 | 重庆可兰达科技 / 渝ICP备17001599号-29A |
| 隐私协议 | https://web-link.tttick.com/business/protocol/privacy.html |
| 加固检测 | **未发现常见加壳特征**（梆梆/360/腾讯加固/爱加密/娜迦的资产标志均未命中） |

## 二、APK 体积构成（121MB 的去向）

```
7 个 dex 文件，合计 ≈ 51.7MB （代码量极大）
   classes.dex   9.0 MB    classes2.dex  7.5 MB    classes3.dex  8.0 MB
   classes4.dex  7.8 MB    classes5.dex  8.0 MB    classes6.dex  8.8 MB
   classes7.dex  4.5 MB

65 个 .so 文件，arm64-v8a + armeabi-v7a + armeabi
161 个 assets 文件（含若干 Lottie 动画 json、配置 cfg/、子 SDK jar 包等）
```

> **大头 .so**：`libBaiduMapSDK_map_v7_6_4.so` (11.9MB)、`libhyphenate.so` (7.1MB 环信 IM)、`libindoor.so`、`libcipherdb.so`、`libttmplayer_lite.so` (1.5MB 字节播放器)、`libPglbizssdk_ml.so`

## 三、权限清单（**74 条 — 严重超标**）

### 3.1 高敏感权限（PIPL/MASVS 高危）
- `ACCESS_BACKGROUND_LOCATION` + `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION` — **后台精确定位**
- `READ_CONTACTS` — 读通讯录
- `READ_PHONE_STATE` + `READ_BASIC_PHONE_STATE` — 设备/号码识别
- `RECORD_AUDIO` + `CAMERA` — 麦克风 + 摄像头
- `ACTIVITY_RECOGNITION` + `miui.permission.READ_STEPS` — 用户运动 / 步数
- `READ_MEDIA_AUDIO` / `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` — 全媒体库
- `QUERY_ALL_PACKAGES` — **扫描全部已安装 App（合规高风险，国内监管重点）**
- `PACKAGE_USAGE_STATS` — 读其它应用使用统计

### 3.2 系统级权限
- `SYSTEM_ALERT_WINDOW` — 悬浮窗
- `WRITE_SETTINGS` — 修改系统设置
- `MODIFY_PHONE_STATE` — 修改电话状态
- `REQUEST_INSTALL_PACKAGES` — 静默安装其它 APK
- `SCHEDULE_EXACT_ALARM` — 精确定时（Android 14+ 限制）
- `GET_TASKS` / `REORDER_TASKS` — 已废弃但还在请求
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` — 申请白名单

### 3.3 推送 / 厂商权限（堆叠了几乎全部国内厂商）
小米 / 华为 / 荣耀 / OPPO / VIVO / 魅族 / ColorOS / Mob / 个推 / 高德 / 阿里 MSA

## 四、组件统计

| 类型 | 数量 |
|---|---|
| Activity | **235** |
| Service | 46 |
| Receiver | 19 |
| ContentProvider | 29 |

> 业务 Activity 集中在 `com.youloft.watcher.pages.*`，按目录可拆出：
> `login`、`im`、`friend`、`track`、`vip`、`mine`、`risk`（含 RealNameAuth）、`camera`、`voice`、`lock`、`widget`、`permission`、`privacy`、`test`（含 TestLocationMockActivity / TestLocationStatusActivity 等调试入口）

## 五、对外暴露面（exported + intent-filter）

### 5.1 Deep Link
| Scheme | 落点 Activity |
|---|---|
| **`ylwatcher://`** | `com.youloft.watcher.pages.EmptySplashActivity` ← **自有协议入口** |
| `tencent102361775://` | 腾讯 QQ 互联回调（appId = 102361775） |

### 5.2 调试/测试 Activity（应该是仅 debug 但要确认是否打在 release 包）
- `com.youloft.watcher.pages.test.TestConfigActivity`
- `com.youloft.watcher.pages.test.TestLocationStatusActivity`
- `com.youloft.watcher.pages.test.TestLocationMockActivity` ← **位置 Mock 调试**
- `com.youloft.watcher.pages.test.TestLocationUpdateActivity`

> 如果这些在 release 里 exported，可直接 `adb shell am start` 触发，能绕过部分前置逻辑。

## 六、第三方 SDK 雷达（按重要性）

### 6.1 即时通讯 / 业务核心
| SDK | 包名前缀 | 体量 |
|---|---|---|
| **环信 EaseMob** | `com.hyphenate.*` | libhyphenate.so 7.1MB（IM 核心 + 视频/语音通话） |
| **环信 UI** | `com.hyphenate.easeui` | Activity 含 EaseShowVideoActivity、EaseBaiduMapActivity 等 |

### 6.2 定位 / 地图
| SDK | 体量 |
|---|---|
| 百度地图 + 定位 | libBaiduMapSDK_map_v7_6_4.so (11.9MB) + libBaiduMapSDK_base + liblocSDK8b.so |
| 室内定位 libindoor.so | 1.6MB |

### 6.3 广告 / 商业化（极重）
- 字节穿山甲 `com.bytedance.sdk.openadsdk.*` + `libpanglearmor.so`
- 字节抖音直播 `com.bytedance.android.openliveplugin.*` + `com.byted.live.lite.*` + `libttmplayer_lite.so`
- 字节抖音 OpenSDK（含 DouyinAuthorize 两个 Activity）
- 腾讯广点通 GDT `com.qq.e.ads.*` + `assets/gdt_plugin/gdtadv2.jar` (2MB)
- 百度联盟 `com.baidu.mobads.sdk.*` + `assets/bdxadsdk.jar` (1.7MB)
- 快手广告 `com.kwad.sdk.*`
- AnyThink ATInitializationProvider — 聚合广告
- byazt.* / smartdigimkt.* — 高度混淆的广告/营销 SDK（**重点观察**）

### 6.4 推送（六家全占）
小米 MiPush · 华为 HMSPush · 荣耀 Push · OPPO McsPush · VIVO Push · 魅族 Push · 个推 igexin · Mob

### 6.5 监控 / 行为分析
- **ThinkingData**（cn.thinkingdata.analytics）— 数数科技
- **阿里云 SLS** `com.aliyun.sls.android.producer` + libsls_producer.so（825KB） — 日志服务上报
- **腾讯 Bugly / 友盟 spy** — libumeng-spy.so + libcrashsdk.so + libumonitor.so
- **效率 EFS** com.efs.sdk.memleaksdk — 美团/字节系内存监控

### 6.6 设备指纹 / 一键登录 / 安全
- **MobID / Mob 系列** `com.mob.id.*` + `com.mob.guard.*` — 设备 ID + **拉活/保活**
- **MSA OAID** `com.asus.msa.SupplementaryDID` — 国信办 OAID
- **联通号码认证** `com.sdk.mobile.manager.login.cucc` — 一键登录
- **图灵盾** `libturingad.so` — 设备指纹/反作弊
- **libtobEmbedEncrypt.so** — 字节"嵌入加密"
- **libzxprotect.so / libsgcore.so** — 待 native 反汇编确认

### 6.7 工具 / 框架
- AndroidX 完整 + Camera2 + DataBinding + Room
- Kotlin + Coroutines（top-level `kotlin/` 目录）
- OkHttp3（`okhttp3/` 直接目录）
- MMKV（腾讯键值存储，libmmkv.so）
- Lottie（assets/*.json 大量动画文件）
- BlankJ AndroidUtilCode
- 拼音库 `pinyindb/`
- LucKy LuckPicture（图片选择器）

## 七、初步合规与安全观察

### 红黄牌
- 🔴 `QUERY_ALL_PACKAGES`：扫描全装应用，**PIPL 重监管**
- 🔴 6 家推送 SDK 全集成 + Mob 拉活/保活 — 严重影响**最小必要原则**
- 🔴 `REQUEST_INSTALL_PACKAGES`：能静默安装外部 APK
- 🔴 `READ_CONTACTS` + `RECORD_AUDIO` 同时存在
- 🟡 `signed_v1=true & signed_v2=true & signed_v3=false` — 缺 v3 在 Android 9+ 可降级；建议升级签名
- 🟡 235 个 Activity + 29 个 Provider — 暴露面巨大，**逐个核查 exported & permission**
- 🟡 调试 Activity `Test*` 是否在 release 包中可见 — 待动态验证
- 🟡 多家广告/分析 SDK 重叠，**数据回传链路超 10 条**（每家 SDK 都会上报设备指纹）

### 待 Stage 2 验证
1. 自有协议 `ylwatcher://` 的所有支持参数与处理逻辑 — 可能存在未鉴权跳转
2. 是否对 `libtobEmbedEncrypt.so` / `libzxprotect.so` 调用本机签名 — Stage 2 通过 jadx 反编译看 JNI
3. byazt.* 系列实际归属（字节抖音 + Pangolin 中间层混淆？）
4. assets/cfg/a/*.cfg/.rs/.sty — 可能是百度地图离线资源，也可能是配置脚本

---

> **下一步**：jadx 后台反编译进行中，约 5-15 分钟。完成后进入 Stage 2：
> 1. Application 入口 + 启动链
> 2. 网络层（OkHttp 拦截器 + 签名/加密入口定位）
> 3. ylwatcher:// 路由解析
> 4. 关键业务接口请求体抽样
