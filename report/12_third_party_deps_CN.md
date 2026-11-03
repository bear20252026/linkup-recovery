# LinkUp 第 12 号报告：接回三方依赖，业务屏可 inflate 率 86% → 90%

> 日期：2026-11-02 ｜ 承接 `report/11`（自有 View 批量重建）
> 本轮：把公开仓能解出的三方 UI 库接回 `:app`，并修掉资源剥离流水线自身的三个 bug

## 一、接回的依赖（Gradle 实解析验证过，不是抄来的清单）

```
androidx.camera:{camera-core,camera-camera2,camera-lifecycle,camera-view}:1.4.0
io.supercharge:shimmerlayout:2.1.0
com.github.yalantis:ucrop:2.2.11
io.github.scwang90:{refresh-layout-kernel,refresh-header-classics}:2.0.5
io.github.youth5201314:banner:2.2.3
com.github.chrisbanes:PhotoView:2.3.0
com.github.bumptech.glide:glide:4.16.0
com.kyleduo.switchbutton:library:2.1.0
com.github.yyued:SVGAPlayer-Android:2.6.1
io.github.lucksiege:pictureselector:v3.11.2
com.github.gzu-liyujiang:AndroidPicker:4.1.13
com.github.daimajia:AndroidSwipeLayout:v1.1.8   （需 exclude com.android.support，见下）
```

两处必要的适配，都是**真实冲突不是装饰**：

- `com.github.daimajia:AndroidSwipeLayout:v1.1.8` 还挂着 2014 年的 `com.android.support:support-v4:21.0.3`，
  与 `androidx.core:core:1.13.0` 撞 `android.support.v4.app.INotificationSideChannel`。
  用 `dependencyInsight` 定位到它就是唯一来源，**只对它定向 `exclude(group = "com.android.support")`**，不做全局排除。
- `SVGAPlayer-Android` 的 manifest 里 `allowBackup=true` 与本包 `false` 冲突，`AndroidManifest.xml` 加
  `tools:replace="android:allowBackup"`。

## 二、结果

| 口径 | report/11 | 本轮 |
|---|---|---|
| **业务命名布局可 inflate** | 290 / 335（86%） | **303 / 335（90%）** |
| 全部布局 | 434 / 829 | **444 / 798**（银行里库自有布局又被剥掉 31 个） |
| "其它三方 UI 库"造成的失败 | 63 | **23** |
| 仍因自有 View 失败的布局 | 6 | 8（见下，剥掉遮挡后暴露出新的一层） |

自有 View 现在只剩 3 个类各挡 1 个布局：`view.im.CameraButtonView`、`view.SwitchButton`、
`webview.WebComponent`（`ShotPreviewView` / `FixWheelView` / `VipCard` / `SlideRecyclerView` 等仍在总失败里）。

**没动的两块是大头且原因明确**：
- 广告 SDK 自带 UI **276 个布局**（`com.kwad` 快手、`com.smartdigimkt`、`com.anythink`）——
  这些要走厂商 maven 与商用账号，不是 `mavenCentral/jitpack` 能解的，需要公司从厂商后台拿仓库地址与 AppKey；
- 环信 EaseUI **40 个布局**——`maven.hyphenate.com` 从本机连不通（curl 超时），
  且 EaseUI 历史上常被当源码模块拷进工程，可能根本没有制品；要么拿到厂商仓库，要么按 `:fastkit` 的路子从 APK 抽。

另有 3 个库坐标没猜中（`com.dinuscxj:circleprogressbar`、`com.github.lihangoffice:ShadowLayout`、
`com.github.warkiz.*:indicatorseekbar`），合计约 8–10 个布局，已写在 `app/build.gradle.kts` 注释里。

## 三、剥离流水线的三个 bug（都是自己的，值得记下来）

1. **`tools/rebuild_bank.sh` 之前不幂等**：`migrate_res.py` 是往目标目录里**拷贝**而不是重建，
   上一轮改名后的 `avd_x__0.xml` 与新拷来的 `$avd_x__0.xml` 并存，导致 `fix_res_names.py` 全部
   `SKIP collision`、`renamed: 0`，`$` 文件原样留在树里，构建报非法资源名。已在脚本里加
   `rm -rf res166/src/main/res`。**症状是"改了没生效"，根因是脏目录。**
2. **GAV 正则把 `v` 前缀版本整条漏掉**：`([0-9][A-Za-z0-9._-]*)` 匹配不到 `v1.1.8`、`v3.11.2`，
   于是 daimajia、pictureselector 从头到尾没进剥离清单——表现为 `attr/drag_edge`、`attr/show_mode`
   重复定义。放宽成 `([A-Za-z0-9][A-Za-z0-9._+-]*)` 后一次通过。**这类"看起来跑成功了其实静默漏掉"
   的过滤器，要比对处理条目数是否随依赖增长**（本轮 88 → 107 个构件、814 → 916 个文件被剥离，才是对的信号）。
3. **`fetchDebugArtifacts` 用 `configuration.resolve()` 拿不到东西**：AGP 的
   `debugRuntimeClasspath` 是带属性的变体 classpath，直接 resolve 会在 `:fastkit` 的多 variant 上歧义失败；
   而它的 `dependencies` 集合本身是空的（声明在 `implementation` 上，靠 extendsFrom 继承），
   所以 detached 镜像拿到 0 个依赖。改成取 `allDependencies` 里的 `ExternalModuleDependency`
   再建 detached configuration，才真正下载 107 个构件。**`gradle :app:dependencies` 只解析元数据不下 AAR**，
   剥离脚本必须先把制品拉下来，否则新库完全不被剥。

## 四、当前命令

```bash
sh tools/rebuild_bank.sh          # 依赖变更后必须重跑：刷新清单→重迁→改名→deltas→剥离
sh tools/gradle.sh :net:test      # 5 tests
sh tools/gradle.sh :app:testDebugUnitTest   # 含全量 inflate 体检
sh tools/gradle.sh :app:assembleDebug       # 60.6MB APK
python tools/summarize_inflate.py           # 读 CSV 出这张表
```

## 五、未验

- 这些库的版本是我按"公开仓能解到的较新版"选的，**不等于原包版本**（原包 `sdk_versions.txt` 只留了
  androidx/Dagger 那批）。接真机后需按行为回归，尤其 Glide/PhotoView/PictureSelector 的 API 变化。
- 广告与环信两块未接，对应 316 个布局仍不可跑，属于外部依赖与账号问题而非代码问题。
- 真机目视仍未做（本机无设备）。
