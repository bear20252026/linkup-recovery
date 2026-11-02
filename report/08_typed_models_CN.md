# LinkUp 第 8 号报告：97 条路由的响应已变成有类型模型

> 日期：2026-11-02
> 前置：`report/04`/`report/05`（协议）、`report/06`（生产 API 存活）
> 结果：**79 个 Kotlin data class、96/97 条路由强类型**，并且是拿生产实时回包解析成功的

---

## 一、为什么字段名可以信

两个 APK 里 **`@SerializedName` 全部被 R8 抹掉**（1.5.6 与 1.6.6 各搜 0 命中）。
Gson 运行时只认注解或字段名，注解既然没了还能正常解析，说明**线上 JSON 的 key 就等于字段名**——
这也解释了 R8 为什么保留了 bean 的字段名。

这条推断被实机证实：`ChannelConfig` 的 9 个字段与生产 `/api/client/config` 返回的键一一对上。

## 二、生成物

| 项 | 数量 |
|---|---|
| 生成的 data class | **79**（`net/src/main/kotlin/com/youloft/linkup/api/dto/Dtos.kt`，908 行） |
| 强类型响应路由 | **96 / 97** |
| 每个类可回溯 | `recovered/bean_map.json`：类名 → `com/youloft/watcher/bean/Xxx.java` 原始文件 |
| 生成器 | `tools/gen_beans.py`，可重复执行；同时重出 `LinkUpApi.kt` |

三条**故意不做**的事，避免看着爽其实假：

1. **不复制三方 SDK 的类**。`api/...` 响应里出现过腾讯 TuringFD 的 `Date<T>`，一开始被当业务 bean 生成，
   结果引用它的字段编译不过。现在只生成 `com.youloft*` 包里的类，其余一律 `JsonElement`——
   那些是广告/风控 SDK 的内部结构，不是本产品的 API 面。
2. **剩下那 1 条 `JsonElement` 是忠实还原，不是缺口**：`POST api/address/tag` 在原代码里就声明成
   `ApiResponse<Object>`，老客户端自己都不解析返回体。
3. **请求体只类型化 4 条**，另外 40 条保持 `Map<String, Any?>`——原实现就是发动态 map，
   硬凑成 data class 会变成"为了让类型好看而编字段"。

## 三、实机闭环

```
$ gradle :net:liveVerify
base           -> https://link.tttick.com/
clientConfig   -> status=200 msg=success
                 notRelativesLockShow=false
                 autoReportAddressShow=0
                 imGroupHuawei=CFjkhdl-4JqqwWukyaSCexFNPqHPHVwA imGroupOppo=-_qObe9ez…
userInfo       -> HTTP 401 (reached business layer, auth required)
PROTOCOL_RECOVERED=1
```

`RecoveredModelTest` 用两份抓包留证（`net/src/test/resources/{prod,test}_client_config.json`）反序列化断言：
**7 tests / 0 failures**（5 个签名协议 + 2 个模型解析）。两份 fixture 也顺手证明了生产与测试服
是两个不同环境：`notRelativesLockShow` 一 false 一 true，`imGroupHuawei` 值完全不同。

## 四、`liveVerify` 之前有个假绿隐患，已修

生产网关偶尔直接掐 TLS 握手（`SSLHandshakeException: Remote host terminated the handshake`）。
旧写法打印一句 error 就 `return`，Gradle 任务照样 **SUCCESS**——探测失败会被当成验证通过。
现在：探测不通就退回测试服，**两台都不通就让构建失败**（`error("no gateway answered")`）。

## 五、要产品/后端拍板的一条：服务端多回 3 个键，客户端从来没用过

`/api/client/config` 生产返回 **12 个键**，而客户端 bean 只有 9 个字段：

| 键 | 1.5.6 | 1.6.6 | 生产 |
|---|---|---|---|
| `ifCheckRegin` | 无 | 无 | 有 |
| `profileSkipButton` | 无 | 无 | 有（生产 true，测试 false） |
| `imGroupIos` | 无 | 无 | 有 |

1.5.6 是 8 个字段，1.6.6 加了 `autoReportAddressShow` 变 9 个，而这 3 个**两版都没建模**，
Gson 一直是静默丢弃。所以它们要么是从 iOS 那边共用配置、要么是服务端准备发但安卓没接的功能开关。
重建时要决定：**接过来（则新增 3 个字段）还是继续丢**。这不是逆向能替我们决定的产品问题。

## 六、已知的建模取舍

- 所有引用类型字段都生成成可空并默认 `null`。原 app 的字段带 `@l`（非空），但 Gson 绕过 Kotlin
  空检查、缺字段就是 null——照原样声明非空会让重建出来的模型在缺字段时直接 NPE。这是**有意的放宽**，
  不是还原失真。
- 同名 simple class 冲突时取 `com.youloft*` 那一个（`bean_map.json` 里可查实际取的是哪个文件）。

## 七、下一步

`LinkUpApi` 已是强类型面，接着按 `report/05` 的模块文件数从大到小逐屏重建，
每屏补一条真实请求进 `liveVerify`。要界面跑起来仍需先解决 `report/07` 里的 AAR 剥离。
