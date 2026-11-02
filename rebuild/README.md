# LinkUp 重建工作区

源码丢失后，从 1.5.6 / 1.6.6 两个安装包恢复并重建客户端的工作区。

## 现在能跑的命令

```bash
# 离线回归：5 个单元测试锁住签名协议，不需要手机也不需要网络
sh tools/gradle.sh :net:test

# 实机验证：用重建的网络层向真实测试服发一条签名请求
sh tools/gradle.sh :net:liveVerify      # 期望打印 PROTOCOL_RECOVERED=1

# 出 APK
sh tools/gradle.sh :app:assembleDebug
```

`tools/gradle.sh` 直接用本机 `~/.gradle` 里已缓存的 Gradle 9.3.1，所以不用装 Gradle；需要 JDK 17+。

## 目录

| 路径 | 内容 |
|---|---|
| `net/` | 纯 JVM 网络层模块：AES 签名、公共参数拦截器、97 条路由的 Retrofit 接口 |
| `app/` | Android 壳，包名沿用 `com.youloft.watcher`，已带入 1.6.6 的 25MB assets |
| `recovered/` | 分析与验收产物：路由表、API 契约、模块清单、设计文档 |
| `tools/` | 反编译与还原脚本（可重复执行） |
| `_raw/` | 两个 APK、反编译输出、apktool 输出（**体积大且含内部代码，不入库**） |

## 恢复状态

已验证：GET + 签名被真实服务端接受（`status=200`）。
未验证：POST 体签名、97 条路由逐条字段——都需要真实登录态，见 `recovered/DESIGN_CN.md` 第八节。

## 红线

`_raw/` 与 `recovered/` 含公司产品内部结构与三方密钥。**不要把这个目录推到公开仓库。**

## 在本仓库里 clone 之后

`assets/`、两个 APK、反编译输出都不在 git 里（体积原因，且都能从 Release v1.0 重现）：

```bash
sh tools/stage_assets.sh   # 打印重建这些输入所需的四条命令
```

`net/` 模块不依赖 assets，clone 后直接 `sh tools/gradle.sh :net:test` 即可跑离线回归。

## 资源银行 `:res166`

1.6.6 的 `res/` 整棵已迁入（3982 文件：936 布局、2169 条默认文案 + 中文变体）。
`R.layout.activity_login` / `R.string.input_address_tag_hint` 在 `:app` 里直接可解析。

注意：`:res166` 里已含 AppCompat/Material 的 attrs/styles 副本，**`:app` 不要再加 androidx UI 依赖**，
否则 `attr/navigationMode` 之类会重复定义而链接失败。将来要加回 AAR，先做库自有资源剥离。
详见 `../report/07_resource_migration_CN.md`。

## 强类型 API 面

`tools/gen_beans.py` 从 1.6.6 的 bean 生成 79 个 data class，并重出 `LinkUpApi.kt`：
96/97 条路由有类型响应（唯一那条 `JsonElement` 是原代码就写的 `ApiResponse<Object>`）。
依据是两个 APK 都没有保留 `@SerializedName` ⇒ JSON key 就是字段名，且已被生产实时回包证实。

```bash
sh tools/gradle.sh :net:test        # 7 tests：5 个签名协议 + 2 个模型解析（用抓包留证）
sh tools/gradle.sh :net:liveVerify  # 打生产，不通自动退回测试服；两台都不通则构建失败
```

## AAR 已接回，界面可测

`res166` 里的库自有资源已按各 AAR 的真实清单剥离（770 文件 + 3892 条目，见 `tools/strip_lib_res.py`
与 `recovered/stripped_lib_resources.json`），`:app` 现在正常依赖 appcompat/material/constraintlayout/
recyclerview/lottie/BRVAH 等。`android.nonTransitiveRClass=false`，否则 `:app` 的 `R` 看不到 `:res166`。

```bash
sh tools/gradle.sh :app:testDebugUnitTest   # Robolectric：真 inflate 还原布局，无需设备
sh tools/gradle.sh :app:assembleDebug       # 57.9MB APK
```

已知缺口：`com.mc.fastkit`（545 处引用，内部组件库，公开仓没有）需从 APK 反编译产物抽成 `:fastkit`，
在那之前列表行这类布局 inflate 不了。详见 `../report/09_aar_strip_and_ui_runs_CN.md`。
