# LinkUp 第 10 号报告：`:fastkit` 建起来了，并量出还原 UI 今天能跑多少

> 日期：2026-11-02
> 承接：`report/09`（AAR 剥离，留下"FastKit 缺失导致列表行 inflate 不了"）
> 结果：**业务命名布局 335 个里 260 个今天能在 JVM 上真 inflate（77%）**

---

## 一、`:fastkit` 模块

新建 `rebuild/fastkit/`（namespace `com.mc.fastkit`，依赖 `:res166` + appcompat + constraintlayout）。
依据是 1.5.6 反编译产物（91 个可读文件）与银行里 **201 个顶层 `<attr name="mc_*"/>`**——
布局用到的 78 个 `mc_*` 属性**一个都不缺**，不需要补任何声明。
（原库用的是 `R.styleable.ShapedTextView_mc_radius` 这种 styleable 索引，但 styleable 只存在于编译期，
APK 里只剩展平的 attr，所以这里改为各视图自带 attr 数组读取。）

实现的类（覆盖布局中出现的全部 14 个 fastkit 标签）：

| 类 | 出现次数 | 类 | 出现次数 |
|---|---|---|---|
| `ShapedTextView` | 232 | `ShapedLabelView` | 69 |
| `ShapedLinearLayout` | 128 | `StatusBarHost` | 45 |
| `ShapedFrameLayout` | 88 | `ShapedRelativeLayout` | 27 |
| `ShapedImageView` | 73 | `NavigationBarHost` | 26 |
| `ShapedConstraintLayout` | 70 | `ShapedEditText` + 3 个 Shadow* | 各 1–2 |

`ShapeStyle` 里还原的行为，枚举值都是从银行 `attrs.xml` 读出来而不是猜：

- `mc_renderMode`：`background=0 / foreground=1` ⇒ 决定画到 background 还是 foreground
- `mc_gradientOrientation`：`top_bottom=0, tr_bl=1, right_left=2, br_tl=3, bottom_top=4, bl_tr=5, left_right=6, tl_br=7`
- 四角独立半径走 `cornerRadii`，四角一致时走 `cornerRadius`
- 虚线描边 `mc_dashWidth/mc_dashGap`、渐变中心 `mc_gradientCenterX/Y`
- `mc_cornerSize` 同时支持 **dimension 与 fraction**（fraction 在 outline 回调里按短边换算），`mc_isRounded` 取半圆
- `ShapedLabelView` 照原类结构：一个 ImageView + 两个 TextView，用 ConstraintLayout 约束串联

**两处刻意没做，说明白比假装完成好**：

1. `mc_font`（reference）读到了但不套用 Typeface——原库带自己的字体缓存，硬接会静默改变字形。
2. **`SheetLayout` 未实现**（23 处属性、3 个布局）。它是带状态机与拖拽手势的底栏组件，
   写个"能 inflate 但不会弹"的空壳就是半拉子工程；那 3 个布局仍留在失败清单里。

## 二、全量 inflate 体检：把"能跑多少"变成数字

`app/src/test/.../UiInflateSurvey.kt` 反射枚举 `:res166` 的 `R.layout` 全部字段，在 `Theme.Watcher` 下逐个吹开，
产出 `build/ui_inflate_report.txt`（原因排名）与 `build/ui_inflate_per_layout.csv`（逐布局），
再由 `tools/summarize_inflate.py` 汇总成 `recovered/ui_inflate_summary.json`。

| 口径 | 总数 | 今天能 inflate | 比例 |
|---|---|---|---|
| 全部布局 | 829 | **404** | 48% |
| **业务命名布局** | 335 | **260** | **77%** |
| 广告 SDK 前缀布局（`ksad_/sdm_/anythink_`） | 360 | 84 | 23% |

425 个失败按归属（这才是排期用的表）：

| 归属 | 失败数 | 性质 |
|---|---|---|
| 广告 SDK 自带 UI | **276** | 接回广告 SDK 就回来，**不是我们的屏** |
| 其它三方 UI 库 | 58 | 轮播/选择器/SwitchButton/Camera PreviewView 等 |
| **APP-OWNED 自有 View** | **43** | **真正要我们重建的**，共 25 个类 |
| 环信 EaseUI | 40 | 接回环信 SDK 即恢复 |
| androidx 组件 | 5 | 版本/未接 |
| 非类名原因 | 3 | 含 2 个 `FragmentContainerView must be within a FragmentActivity`（测试方法限制） |

最挡路的自有 View（数字=受影响布局数）：

```
5 view.voice.VoiceTimesView   4 view.StrokeTextView   4 view.PayTypeView   3 view.lock.UnlockButton
2 view.PswInputView  2 view.SendCodeButton  2 view.AvatarView  2 view.MaxHeightRecyclerView
2 view.RelationButton  2 view.RollingTextView  1 view.AutoReportSettingsView  1 webview.WebComponent …
```

**这张表可直接当排期用**：补掉这 25 个类，业务屏通过率从 77% 继续往上；其余失败是"接回某个 SDK"，不是"重写某个屏"。

## 三、体检方法自己踩的两个坑（已修，记录以免重犯）

1. `<merge>` 必须 `attachToRoot=true`。第一版一律传 `false`，**57 个布局被误判失败**——那是测试方法的限制，
   不是布局坏掉。改成先 `false`、命中 merge 提示再以 `true` 重试后，OK 从 379 升到 404。
2. 失败原因必须取**异常链最内层**并按 `Error inflating class X` 归类。只截外层 message 前 140 字符时，
   450 条失败全是同一句 `InflateException: Binary XML file line #N`，等于没测。

## 四、当前验证状态

```
gradle :net:test                5 tests
gradle :app:testDebugUnitTest   5 tests（含 RecoveredUiTest 2 个 + UiInflateSurvey 1 个）→ 合计 10 tests / 0 failures
gradle :net:liveVerify          PROTOCOL_RECOVERED=1（生产 link.tttick.com）
gradle :app:assembleDebug       57.9MB APK
```

`item_friend_request.xml`（FastKit 行布局）已进入显式断言——正是 `report/09` 说"跑不了"的那一类，解开。

## 五、仍未验

1. 真机目视与交互（本机无设备）。Robolectric 只证"视图树建得出来"，不证像素。
2. `SheetLayout` 3 个布局、`mc_font` 字体、以及广告/环信/其它三方库未接回造成的 374 个失败。
3. Shape 渲染与原版是否逐像素一致：原库自绘阴影与状态层，这里用 `GradientDrawable` + 平台 outline 阴影替代，
   API 28 及以下 `mc_shadowColor` 着色会丢。
