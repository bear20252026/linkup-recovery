# LinkUp 第 9 号报告：库自有资源剥离完成，还原界面在 JVM 上真 inflate 过

> 日期：2026-11-02
> 承接：`report/07`（资源迁入，留了"不能再依赖 androidx UI 库"的约束）、`report/08`（强类型模型）
> 结果：**那条约束已解除**，AAR 全部接回，`RecoveredUiTest` 用 Robolectric 真跑通还原布局

---

## 一、剥离是怎么做的：用真实清单，不用前缀猜

`:res166` 装的是 APK **合并后**的资源表，里面本来就有 AppCompat/Material 等库的全部副本；
`:app` 一旦同时依赖这些 AAR，`attr/navigationMode` 之类就会重复定义，`aapt2 link` 失败。

`tools/strip_lib_res.py` 的减法基于事实：

1. `gradle :app:dependencies --configuration debugRuntimeClasspath` 解析出 **154** 个模块（传递依赖也算进来），
   再让一次构建把 `.aar` 拉进缓存；
2. 从每个 `.aar` 读 `res/**`（文件型）与 `res/values*/values.xml`（条目型），得到 **5040** 个库资源标识；
3. `:res166` 里同 type 同 name 的删掉，values 条目按类型移除。

**一个差点漏掉的关键点**：`appcompat-1.7.0.aar` 里 `navigationMode` 这类 attr **不是顶层定义**，而是写在
`<declare-styleable name="ActionBar">` 的子节点里。第一版脚本只收顶层条目，attr 移除数停在 398，
构建照样失败；补上"遍历 styleable 子 attr"之后跳到 **1263**，一次通过。
处理方式也刻意保守：子 attr **降级成引用** `<attr name="x"/>`，不删整个 styleable——
否则业务自己声明的 styleable 会被连带误伤。

剥离量：

| 类别 | 删除 |
|---|---|
| 文件 | **770**（drawable 348、layout 114、color 213、anim 44、animator 33、interpolator 18） |
| values 条目 | **3892**（style 1080、dimen 863、color 485、**attr 1263**、id 116、integer 71、bool 4、plurals 4、drawable 6） |

明细 `recovered/stripped_lib_resources.json`。**未剥离的原始树仍在 `_raw/out_apktool_166/res`**，
整条链可重放：`migrate_res.py → fix_res_names.py → apply_res_deltas.py → strip_lib_res.py`。

## 二、接回的依赖与一处配置

appcompat 1.7.0、material 1.10.0、constraintlayout 2.1.4、recyclerview 1.3.1、viewpager2 1.1.0-beta02、
swiperefreshlayout 1.1.0、fragment-ktx 1.6.1、activity-ktx 1.8.0、lifecycle-runtime-ktx 2.7.0、
core-ktx 1.13.0、lottie 6.4.0、BaseRecyclerViewAdapterHelper 3.0.10（需要 jitpack 仓库）。

`android.nonTransitiveRClass` 必须改回 **false**：`R` 只有非传递模式下才会把依赖模块
（`:res166`）的资源并进 `:app` 的 `R`，否则 `R.layout.activity_friend_request_list` 直接解析不到。

## 三、"界面真跑起来"的证据是什么、不是什么

**是**：`app/src/test/kotlin/com/youloft/watcher/RecoveredUiTest.kt`（Robolectric 4.11.1，`@Config(sdk=[34])`）
在还原出来的 `Theme.Watcher` 之下真 inflate `activity_friend_request_list.xml`，断言：

- 根是 `androidx.constraintlayout.widget.ConstraintLayout`
- `layout_title`、`iv_back`、`iv_add_friend`、`recyclerView`、`emptyView` 全部解析到
- 标题栏 TextView 的文案解析成「好友申请」
- `Theme.Watcher` 能解开 `android:windowBackground` 与 `colorPrimary`（后者必须来自 material/appcompat 的 attr）

这比"XML 文本存在"强一档：**布局 + 样式 + 自定义属性 + 图片 + include 在运行时能整体解开**。

同时也写了第一个真业务屏 `FriendRequestListActivity`（AppCompatActivity + LinearLayoutManager +
已类型化的 `apiRelationApplyList(page, pageSize)`）。

**不是**：没有设备，所以没有任何肉眼可见的渲染验证；`lifecycleScope` 里的真实请求也没在测试中执行
（测试故意不 idle main looper，避免打真网络）。Robolectric 只能证到"能解开、能建出视图树"这一层。

全套：**9 tests / 0 failures**（5 协议 + 2 模型解析 + 2 界面 inflate），`:app:assembleDebug` → **57.9MB APK**。

## 四、新发现一条丢失的依赖：`com.mc.fastkit`

业务布局里 **545 处**引用 `com.mc.fastkit.*`（`ShapedImageView` / `ShapedConstraintLayout` /
`ShapedLinearLayout` / `ShapedTextView` 等）。它**不在 Maven Central，也不在任何公开仓**，
基本可确定是我方内部组件库——也就是说**它的源码同样在这次丢失范围内**。

好消息：APK 里有它。1.5.6 反编译产物中有 **91 个可读的 `com/mc/fastkit/**` 文件**
（子包 `dialog / ext / log / ui / utils / view / widget`），1.6.6 有 94 个。

直接后果：`item_friend_request.xml` 这类**列表行**布局目前 inflate 不了，所以好友申请屏还只有"外壳能跑"。
建议单开一张卡把 FastKit 抽成 `:fastkit` 模块——它的引用面比任何单个业务屏都大，值得先做。

顺带记录：97 条路由里 **9 条路径带前导斜杠**（`/api/relation/apply_list` 等），其余不带。这是 dex 里的原样，
Retrofit 对前导斜杠按根相对处理，同一 host 下行为一致，故**保持原样未"修正"**。

## 五、待验清单（仍未验，别当已验）

1. 真机目视与交互（本机无设备）。
2. 列表行 inflate —— 等 `:fastkit`。
3. 依赖版本与原包的一致性：本次按 `data/sdk_versions.txt` 取原版本，但 lottie/BRVAH 用的是较新版本，
   行为可能有差异；接真机后需回归。
4. `Theme.Watcher` 在真机上的状态栏/深色模式表现（Bridge 主题，非纯 Material 主题）。
