# LinkUp 第 22 号报告：#19 二维码绘制与加载遮罩——顺手改掉一条我自己发布出去的错话

> 日期：2026-11-04 ｜ 承接 `report/21`

## 一、先认一条错

上一轮我在 `report/21` 第十节里写二维码绘制器是「H 纠错、UTF-8、静区 0、**圆角点阵**、可选中心 logo」。
这轮把 `utils/z0.java`（1.5.6，328 行；1.6.6 是同体量 `utils/y0.java`）逐行读完，四条里**错了三条**：

| 项 | 上轮写的 | 实际 |
|---|---|---|
| 纠错等级 | H | **Q**（H 是另一条简易生成器 `g()` 用的） |
| 字符集 | UTF-8 | **`"utf-8"`，小写**——值还从个推常量类 `com.igexin.push.f.r.f48119b` 里取 |
| 模块形状 | 圆角点阵 | **正方形**（`moduleShape=0`，填充系数 1.0） |
| 定位眼 | 没提 | **样式 2 = 环形**：中心实心点半径 1.5 模块，环半径 3 模块、线宽 1 模块，7×7 区域内的模块一律不画 |
| 中心 logo | 可选 | 1.5.6 确实嵌头像，**1.6.6 恒传 `null`**（随头像层一起删了） |

错话已同时改进 `recovered/DESIGN_CN.md` 与 `report/21`。**教训是具体的**：那条调用我只读了调用点、没读被
调用体，就把参数当已知写进发布件了。

`z0.d(...)` 在两个版本里都**只有一个调用点**（添加好友屏），且每次参数相同，所以重建类只钉这一套配置。
原版另外几套样式（圆形模块、3–6 边形模块、其他眼样式）在 1.6.6 已无调用点——不做，做了就是死代码。

## 二、为什么把绘制器拆成「版面 + 刷图」两步

`view/MatchCodeQrPainter.kt` 里 `plan(content, sizePx)` 返回**纯数据版面**：画布尺寸、模块边长、居中偏移、
要画的暗模块清单、三只眼的圆心与半径。`draw(plan)` 只是照着版面往 Canvas 上刷。

分开不是洁癖，是因为**本机 Robolectric 的光栅化不可信**。探针实验说得很清楚：

```
画一个 6×6 红方块到 10×10 白底位图
→ getPixels 读回中心 = 白色(-1)，全场只有 24 个红点
同一张标准 zxing 码用 Canvas 画出来 → 解不出
同一张码用 int[] 直接喂 RGBLuminanceSource → 秒解（Hybrid 与 Global 都行）
```

所以像素断言这条路废掉。改成两步：

1. **版面算术逐条断言**——`qrLayout` 就是原版那条
   `reserve = max(extra, min(w/(n+2), h/(n+2))) * 2` → `module = (canvas − reserve) / n` → 再居中；
2. **在测试里把版面重栅格化成 `int[]`，交给真 zxing 解码**，要求解回原 URL。

## 三、第 2 步顺手证明了一件有价值的事：**环形定位眼真的可扫**

这不是我加的样式，是原版的：它把标准 7×7 实心finder换成"环 + 点"。我本来准备接受"zxing 读不出这种花码、
只能靠手机相机"这个结论，但测试直接解回来了：

```
assertEquals(shareUrl, decode(rasterize(plan, quietModules = 4)))
```

因为环 + 间隙 + 中心点在扫描线上正好给出 finder 判据要的 **1:1:3:1:1** 比例——环外半径 3.5 模块、
线宽 1 模块，点半径 1.5 模块。这条已写成测试注释，不是口头结论。

顺带两个事实也进了测试：

* 那条 URL（79 字符 @ EC Q）是**版本 7 = 45×45 模块**；在 288px 画布上 `reserve=(288/47)*2=12`、
  `module=(288−12)/45=6`、偏移 9px——即**版面自带约 1.5 模块的内边距**。
* `iv_code` 的背景是**全透明**的，所以白卡片 `scl_code` 本身就是静区的一部分。截图时不能把码铺满边框，
  原版 `rl_code` 140dp 里放 130dp 的 `iv_code` 不是随手写的。

## 四、LoadingDialog 的三条事实

照 1.5.6 `pages/common/LoadingDialog.java`（76 行）搬，值得单列：

* 窗口 **`FLAG_NOT_FOCUSABLE`**（原版 `window.setFlags(8, 8)`）——遮罩永远不抢输入法焦点，所以它盖在搜索框
  上时键盘不会被顶掉；
* show 时 `startAnimation()`、dismiss 时 `pauseAnimation()`（原版 `E0/F0` 里的 `v()`/`z()`；我用 `javap`
  对过 `SVGAImageView` 的方法名才敢这么接），播的是 `assets/loading.svga`；
* **最短显示时间**：被要求立刻收起时，若还没满 `minShownMillis` 就推迟剩下的时间。默认 250ms，
  **但 `BaseFrameActivity.showLoading()` 用 `0L` 构造**，所以好友屏这条下限实际是关的。规则照搬，
  因为别的调用点用得到——测试注入时钟把它三条分支都钉了（推迟 / 到点就收 / 零下限立即收）。

平台缝 `RealAddFriendPlatform` 按原版**每屏复用一个实例**（原版缓存在 LiveData 里），并保留"activity 已死
就不显示"的守卫。`QrCodeRenderer` 上的 `Pending` 空实现随之删掉——生产已经有真绘制器，留着就是骗人。

## 五、数字

`:app` **153 tests / 0 failures**（本卡 +13：绘制器 9、加载遮罩 3、接线 1），`:net` **10 / 0**，合计
**163 全绿**。`assembleDebug` 通过，APK **61,848,174 B**（≈61.8MB，上轮 59.06MB，涨的就是 zxing 与重打包）。
已核包里确实有：`MatchCodeQrPainter`、`LoadingDialog`、`zxing/qrcode/encoder/Encoder`、`dialog_loading` 资源、
`assets/loading.svga`。业务布局 inflate **仍 306/335**，无倒退。

依赖新增 **`com.google.zxing:core:3.5.3`**。APK 内只留类名、没有版本串，和 MMKV / BRVAH 一样按公开最新接
（已进待验第 35 条；另外 `Encoder`/`ByteMatrix` 属 zxing 内部 API 而不是 `MultiFormatWriter` 那条公共面，
对不上老版本模块排布时要先怀疑这里）。

又踩回一个老坑并当场用回原配工具：**`gradle :app:dependencies` 只解析 POM**，zxing 的 jar 根本没下来；
必须跑 `tools/gradle.sh :app:fetchDebugArtifacts` 才会真的下载——那个 helper 任务本来就是为这事写的。

## 六、还没做的（别误会）

1. **真人拿手机扫这块屏**：本机证明的是"版面能被 zxing 读"，不等于相机抗畸变、透明底在不同主题下的
   对比度、130dp 显示尺寸够不够——待验第 30 条。
2. **`QRCodeScanActivity` 的解码侧**（zxing `MultiFormatReader` + 相机）：属 #20 那张卡，本轮只做生成侧。
3. **1.5.6 的头像嵌码合图** `z0.a(qr, logo)`（logo 缩到 1/3 宽居中）：1.6.6 无调用点，没搬。
4. **SVGA 动画观感**：资源与视图都接上了，Robolectric 里只验时序与窗口标志，遮罩透明度、圆角、动画
   顺不顺眼要装包看（待验第 34 条）。
5. **上轮其余未做的项不变**：微信/QQ 分享本体、QR png 上传 H5、`ContactInfoListActivity`、埋点汇 `mf.b`、
   同意后 IM 侧效应、XXPermissions 的两处等价替换。
