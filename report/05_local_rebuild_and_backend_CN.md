# LinkUp 重建第 5 号报告：本地打通 + 协议实机验证 + 后端归属

> 日期：2026-11-02
> 承接：`report/00`（可行性）、`report/03`（服务器探测）、`report/04`（1.6.6 协议破解）
> 本轮工作区：本机 `D:\linkup-rebuild`，代码在本仓库 `rebuild/` 目录

---

## 一、本轮最重要的变化：不再需要 Mac mini，也不再需要 Actions

前面所有报告都有一个前提——"手机无 Java 环境，反编译必须在 Mac mini 上跑，验证协议要 push 到 GitHub Actions 再读日志"。

**这台 Windows 机器上其实全套都有**：JDK 21、Android SDK（platforms 33–37、build-tools 34–36）、Gradle 9.3.1、AGP 8.11.1 与 9.1.0 的 jar 已在本地缓存、Kotlin 2.4.0 已缓存。于是本轮全部改成本地：

| 动作 | 之前 | 现在 |
|---|---|---|
| 反编译 1.5.6 | **从未做过**（Release 里只有 1.6.6 源码） | 本机 3.5 分钟，28031 个 Java 文件 |
| 1.6.6 布局文本化 | 未做（jadx 用了 `--no-res`） | 本机 30 秒，936 个 layout + 2169 条文案 |
| 协议验证一次 | push → 等 Actions → 读日志 | `sh tools/gradle.sh :net:liveVerify` 一条命令 |

## 二、协议不是"破解成功"，是"重建出来的代码在真实服务器上跑通了"

新写的 `rebuild/net/`（Kotlin，纯 JVM）签名后请求测试服，拿到真实业务数据：

```
clientConfig -> status=200 msg=success
data keys = notRelativesLockShow, halfScreenVipPageShow, vipMarketingCopy, ifCheckRegin,
            profileSkipButton, autoReportAddressShow,
            imGroupHuawei, imGroupIos, imGroupHonor, imGroupVivo, imGroupXiaomi, imGroupOppo
userInfo/versionCheck -> HTTP 401（签名关已过，卡在 JWT，符合预期）
完整原始响应留证：rebuild/recovered/live_config_sample.json
```

网络层照 1.6.6 的 `gh/d.java` + `com.youloft.watcher.utils.a` 逐行还原，本轮新读到两处**前面报告写错或没写**的细节：

1. 拦截器的放行条件不是"所有第三方域名"，而是**只对 `api.weixin.qq.com` 放行**（`ag.a.f1737h` 就是微信域名，不是业务域名）。
2. POST 体签名那一步，原实现先算出**大写** hex 的 MD5，再 `.toLowerCase()`。中间那个 `com.mc.fastkit.ext.f.f()` 用的是大写字符表——直接照 `md5Hex()` 写没问题，但别省掉小写化。
3. `Authorization` 这个头名是从 R8 残留的 `ve.f.f81194d` 常量确认的；`retrofit2/w.java` 里的报错字符串（"@QueryMap parameter type must be Map."、"@Body parameters cannot be used with…"）还活着，靠它把被改名的 `hm/a…hm/y` 全部还原成了 Retrofit 注解。

离线回归：`gradle :net:test` = **5 tests / 0 failures**，覆盖 11 个公共参数顺序、"签名解密回来必须等于 path?query"、POST 体 md5、`login`/`sms` 豁免、微信域名放行。

## 三、路由表恢复：97 条，动词与参数名都拿到了

`gh/a.java` 里 R8 只保留了路径字符串，注解类被改名。用 `retrofit2/w.java` 反推出映射后还原：

- **97 条路由**（50 GET / 47 POST），参数：44 个具名 `@Query`、44 个 `@Body Map<String,Object>`
- **没有任何 FormUrlEncoded / Multipart** → 1.6.6 的 POST 全部走 JSON 体
- 方法原名已被压成 `A/B0/C…`，但 `gh.a$C0997a` 的默认参数桥接里**保留了原始 Kotlin 函数名**（`getFriendList`、`getPrivacySetting`、`getAccessToken`…），可作为语义对照
- 产物：`rebuild/recovered/routes_166.json`、`api_166_contract.md`

一处待对齐：有个查询参数在 dex 里是常量引用 `SocializeConstants.KEY_PIC` 而非字面量，重建时先按 `"pic"` 试。

## 四、本机能编出 APK 了

```
app/build/outputs/apk/debug/app-debug.apk   17.9 MB
package: com.youloft.watcher.debug  versionCode=166  versionName=1.6.6
minSdk 26 / targetSdk 34 / application-label "LinkUp"
```

壳里只有一个 `RecoveryProbeActivity`：装上后自己发一条签名请求，把服务端返回的配置键显示在屏幕上。它是 Android 侧通路探针，不是业务界面。

**这一项目前只做到"能编出包"**：这台机器当时没有连接设备（`adb devices` 为空），所以真机跑通要你们手动验。

## 五、界面侧比原报告乐观

1.6.6 的 936 个布局里，**以 `<layout>` 为根的 DataBinding 布局 = 0 个**（1.5.6 反而有 296 个 DataBinding 生成类）。说明新版已改用普通布局，**XML 可基本原样迁入重建工程**，不用重写绑定表达式。其中业务命名（`activity_/fragment_/dialog_/item_/view_`）327 个，其余 609 个来自三方库不必迁。

工作量分布（1.5.6 可读业务文件 981 个，扣掉 296 个 DataBinding 生成物与 1.4MB 的 `R.java`，**真正要人重写约 660 个文件**）：

```
friend 48 | user 35 | im 29 | login 24 | vip 23 | home 19 | todo 17 | lock 16
privacy 14 | track 14 | voice 10 | mine 9 | permission 7 | test 7(不重建) | common 6
protection 6 | camera 5 | guide/main/risk 3 each | widget 2 | more 1 | sens 1
另：bean 113、view 77、utils 60、adapter 29、manager 23、widget 13、repository 10、datasource 4
```

`test/` 是位置 Mock 调试页，release 包也带上了，**重建时直接丢掉**。

## 六、后端归属调查（本轮新证据）

被动查询（注册数据 + 域名根路径只读 GET），结果：

| 域名 | 注册 | 到期 | 注册商 | DNS |
|---|---|---|---|---|
| 51wnl-cq.com | 2016-01-13 | **2029-01-13** | Alibaba Cloud Computing (Beijing) | VIP3/VIP4.ALIDNS.COM |
| 51wnl.com | 2011-08-26 | **2028-08-26** | 同上 | 同上 |
| tttick.com | 2017-09-12 | **2027-09-12** | 同上 | 同上 |

主机存活状态（TLS 正常、根路径 404 = 服务在跑）：

```
linkup-test.51wnl-cq.com  404     dmp.51wnl-cq.com        404
score.51wnl-cq.com        404     configsys.51wnl-cq.com  404
web-link.tttick.com      404 server:tencent-cos           ss.51wnl.com  404
```

**三条域名都续费到 2027–2029，主体是阿里云注册**——这不是一个已经放弃的产品，后端资产仍在付费维护中。加上测试服错误信息里泄露的 CI 路径：

```
/var/jenkins_home/workspace/desyb_always_guard.api
always_guard/internal/middleware/signature.go / jwt.go
```

服务端源码大概率仍在那台 Jenkins 上。**这是本轮最该有人去做、但我没做的一件事**，原因：这三个域名的注册主体是"万年历/重庆可兰达"一方，而不是我方。**未经书面确认就去探测对方的管理面板（Jenkins 登录页、8080 等端口）属于越界**，我不替你们做这个决定。

要做的动作（需要公司出面）：
1. 确认这次合作的主体关系——我方是"受托开发方"还是"版权方"？`report/01` 里写"公司决定以安装包为基础重建"，但如果后端与 CI 归属对方公司，那要找的是**对方运维**而不是自己翻。
2. 若归属我方：直接向运维索取 Jenkins workspace `desyb_always_guard.api` 与 Git 服务器地址；Go 服务在 `signature.go`/`jwt.go` 两层中间件，字段定义一看就清楚，重建量级立刻减半。
3. 若归属对方：把本轮已还原的 97 条路由契约作为接口约定与对方对齐，能省下抓包对字段的全部时间。

## 七、待验清单（我在本机物理上做不了的）

| # | 待验项 | 缺什么 |
|---|---|---|
| 1 | POST + 体签名被真服务端接受 | 需要真实登录态与合法手机号；`md5(body)` 这条目前只有离线测试覆盖 |
| 2 | 探针页真机显示 200 | 本机 `adb devices` 为空，需连设备装包 |
| 3 | 97 条路由逐条字段对齐 | 需要登录态逐条打 |
| 4 | 定位上报旧链路（`dmp.51wnl-cq.com` + 旧密钥 `be2524844ec4bb25` + 多套一层 MD5） | 属另一套协议，尚未接入重建工程 |
| 5 | 后端/Jenkins 归属 | 见第六节，需公司出面 |
| 6 | keystore 是否还在 | 丢了就要新签名 + 老用户重装方案 |

## 八、本仓库新增内容

```
rebuild/README.md                    怎么跑（三条命令）
rebuild/net/                         已实机验证的网络层：AesCbc、SignatureInterceptor、97 条路由、ApiResponse
rebuild/app/                         Android 壳（沿用包名 com.youloft.watcher），探针 Activity
rebuild/recovered/routes_166.json    97 条路由（动词/参数/原 dex 方法名）
rebuild/recovered/api_166_contract.md 逐条路由契约表
rebuild/recovered/live_config_sample.json 测试服对重建签名的真实响应留证
rebuild/recovered/module_inventory.md     模块文件数统计
rebuild/recovered/DESIGN_CN.md            重建设计文档（架构决定 6 条 + 工作量清单）
rebuild/tools/                       jadx/apktool/路由还原/生成接口的脚本，可重复执行
```

`assets/`、两个 APK、反编译输出都不进 git（体积 + 可从 Release v1.0 重现），恢复方式见 `rebuild/tools/stage_assets.sh`。

## 九、风险提示（新增一条）

本轮按公司决定把**重建源码**推入了这个**公开**仓库。此前 `report/00` §6.4 写的是"恢复工作区公开存放，但后续不要将内部新增代码混入公开仓库"——现在推的是从公开 APK 衍生的反编译重建代码，与那条备注的范围已经不一致。建议：**今后新写的业务代码改放私有仓库**，本公开仓库只保留分析与契约产物；且 `recovered/live_config_sample.json` 这类真实回包样例在正式上架前应做脱敏复查。
