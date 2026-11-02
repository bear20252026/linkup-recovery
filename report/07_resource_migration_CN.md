# LinkUp 第 7 号报告：1.6.6 全部布局与文案已迁入重建工程并通过链接

> 日期：2026-11-02
> 前置：`report/05`（本地重建）、`report/06`（后端归属与生产 API）
> 结果：`:app:assembleDebug` 绿，APK 内含 **937 个布局 + 2272 条文案**，协议验证未受影响

---

## 一、迁了什么

新建资源库模块 `:res166`，把 1.6.6 的 `res/` **整棵**搬进来，不改一个字节：

| 项 | 数量 |
|---|---|
| 迁入文件 | **3982** 个（37.8 MB） |
| 布局 | **936**（其中业务命名 327：`activity_/fragment_/dialog_/item_/view_`） |
| 默认文案 | **2169** 条（其中像三方库的只有约 115 条，**业务文案占绝对多数**） |
| 中文变体 | `values-zh` 363 条、`values-zh-rCN` 195 条，另含 zh-rTW / zh-rHK |
| 色值/尺寸/样式/属性 | `color` 198、`drawable` 827(+各密度 1688)、`anim` 125、`animator` 34、`font` 5、`xml` 18、`raw` 13 |
| 跳过 | **146** 个纯语言目录（`values-af`…`values-zu`），它们是 AppCompat/Material 的翻译，接入真实 AAR 时会自带 |

产物实测（`aapt2 dump`）：APK 内 `res/layout/` 937 个文件、`resources.arsc` 1.56MB、string 资源 2272 条；
`res/layout/activity_login.xml`、`activity_main.xml`、`activity_tracker.xml`、`fragment_voice_edit.xml` 均在包内。

APK 从 17.9MB 涨到 **50.6MB**（几乎全是搬进来的图与布局）。

## 二、三个坑，每个都值得后来人知道

### 1. AGP 会把真实报错吞掉（Windows）
`mergeDebugResources` 失败时只报
`InvalidPathException: Illegal char <:> … com.youloft.watcher.app-mergeDebugResources-25:/values/values.xml`，
看不到 aapt2 的原话。原因是 AGP 的 blame logger 拿"伪路径"去 `Path.of()`，在 Windows 上必炸。

**绕法**：把合并产物直接喂给 aapt2 看原文——
`aapt2 compile --dir <把 merged.dir 拷成 res/values/values.xml> -o out.zip`，
一眼就看出是 **attr 重复定义**（`navigationMode`、`actionBarSize`、`tintMode`…）。

### 2. `:res166` 与 androidx AAR 不能同时在依赖图里
APK 的 `res/` 是**合并后**的产物，里面已经带着 AppCompat/Material 的全部 `attrs.xml`/`styles.xml` 副本。
`:app` 一旦同时依赖 `:res166` 和 `androidx.appcompat`，两份 `attr/navigationMode` 撞车 → 上面那个链接错误。

处理：**`:app` 暂时摘掉全部 androidx UI 依赖**（appcompat/activity/core-ktx），探针页改用
`android.app.Activity`，主题直接挂还原出来的 `@style/Theme.Watcher`
（父级 `Theme.MaterialComponents.Light.NoActionBar.Bridge`，其定义也在迁进来的 styles.xml 里）。

**将来要把 AAR 加回来时，必须先给 `:res166` 做一次"库自有资源剥离"**——按前缀
（`abc_ / mtrl_ / design_ / material_ / notification_ / …`）把库自有条目分出去，否则必然重复定义。
这一步留作下一张卡，别顺手加依赖。

### 3. "缺失资源"有三个其实是空占位
初查报 `@array/side_bar_array`、`@drawable/material_ic_keyboard_arrow_{next,previous}_black_24dp` 找不到。
真实情况：它们在 `values/arrays.xml`、`values/drawables.xml` 里以
`<item type="array" name="…"/>` 这种**空 item** 存在——id 表保留了、值被 `shrinkResources` 削掉了。
对应布局（环信联系人侧栏、Material 日历）没有任何代码路径会 inflate，是死引用。
补一份定义反而会撞重复。**原始 APK 就带着这些悬空引用，照原样留着才对。**

（顺带：apktool 把动画矢量帧命名成 `$avd_hide_password__0.xml`，`$` 不是合法资源名字符；
统一去掉 `$` 并同步改写 18 个 XML 里的 `@drawable/$…` 引用。另外 141 个 `*.9.png` 的 `.9`
是合法名字，别当非法字符处理——这个坑我自己踩过一次，差点把 9-patch 全改名。）

## 三、对保真度的唯一改动

`values/strings.xml#indicator_color_error` 里库的错误文案含字面 `@`：
`indicator color attribute : “@color/colorID or #000000”`，被 aapt2 当引用解析。转义成 `\@`。
这是**整棵树唯一被编辑的一个条目**，其余 3981 个文件与 APK 原文逐字节一致。
清单见 `recovered/res_migration_deltas.json`，脚本 `tools/apply_res_deltas.py` 可重复执行。

## 四、现在这套能怎么用

- 团队在 Android Studio 里打开 `:app`，`R.layout.activity_login`、`R.string.input_address_tag_hint`
  这类引用**直接可解析**——不用再对着 apktool 的目录翻。
- 逐屏重建时：拿 `:res166` 的原布局 + 1.5.6 的同名可读 Activity/Fragment 逻辑，
  一页一页往 `:app` 里写实现；`pages/` 的文件数分布见 `report/05` 第五节。
- 复核命令（都绿）：
  ```bash
  sh tools/gradle.sh :net:test          # 5 tests / 0 failures
  sh tools/gradle.sh :net:liveVerify    # PROTOCOL_RECOVERED=1
  sh tools/gradle.sh :app:assembleDebug # 50.6MB，937 布局入包
  ```

## 五、仍未验的（别当成已验）

1. **这个 APK 能不能正常启动**：编译与打包已证，但本机 `adb devices` 为空，
   探针页在 `Theme.Watcher`（Material Bridge 主题）下能否渲染，必须真机装一次才知道。
2. 迁移过来的**运行时**三方视图（`com.baidu.maps.*`、`com.hyphenate.easeui.*`、Lottie、SVGA 等）
   在 XML 里只是字符串，编译不报错；真正 inflate 需要对应 AAR，届时会撞第二个坑，见上文剥离方案。
3. 146 个语言目录未迁。若产品需要海外语言，接上 AAR 即自带；业务文案本身只有中文。
