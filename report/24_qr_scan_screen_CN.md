# LinkUp 第 24 号报告：#20 后半——扫码屏落地，添加好友的四条找人路径全部闭合

> 日期：2026-11-04 ｜ 承接 `report/23`

## 一、这屏挂着别人家的库，而我没把那个库接回来

原版 `QRCodeScanActivity extends com.king.zxing.BarcodeCameraScanActivity`（公开库，Maven Central 上是
[`com.king.zxing:zxing-lite`](https://mvnrepository.com/artifact/com.king.zxing/zxing-lite/2.0.3/dependencies)，
自带 CameraX 依赖）。这轮**故意不接它**，三条理由：

1. **版本从 APK 里取不出来**。MMKV、BRVAH、zxing-core 已经各欠一条待验，不想再加一笔不知道版本的依赖。
2. **1.6.6 的布局本来就写着 CameraX**：`activity_qr_code_scan.xml` 直接放
   `androidx.camera.view.PreviewView`，而 CameraX（core/camera2/lifecycle/view 1.4.0）与
   `com.google.zxing:core` 都已经在依赖里。
3. **库替我们做的部分很薄**：只有"预览 + 逐帧解码循环"。结果约定、遮罩、扫描线、相册分支、闪光灯
   全是这屏自己的代码。

代价我不藏：**那套配置里有两个布尔我没能对上名字**（见第五节）。已确认 `com/king` 不在新包里。

## 二、从原版逐条核出来、照搬的行为

| 事实 | 出处 |
|---|---|
| 结果键 `SCAN_RESULT`，`setResult(RESULT_OK, …)` 然后 `finish()` | `f64728i`(1.5.6) / `f63935i`(1.6.6) 同名 |
| **只解 QR**：`decodeFormats = QR_CODE_FILTER_DATA` | `mb.c.f75453c = b(BarcodeFormat.QR_CODE)` |
| **整帧分析**：`cropRatio = 1.0f`（库默认 0.8f） | `bVar.q(…).n(1.0f)`，setter 上带着 `@FloatRange(0.5,1.0)` |
| 命中一次**立即停止分析**，回前台才恢复 | `h(result)` 里先 `s().o(false)`；`onPause/onResume` 成对开关 |
| 扫描线 **2000ms**、`REVERSE`、无限循环、从当前 translationY 到父容器底 | `S()`；时长即 `com.blankj.utilcode.util.q.f20405k = 2000L` |
| 遮罩 = `Color.argb(153,0,0,0)` 外套 `utils.t`，**用 `PorterDuff.CLEAR` 在 `fl_qr_scan` 的矩形上挖洞**，且在 `post{}` 里建（要等布局完成才拿得到 left/top/right/bottom） | `U()` + `utils/t.java` |
| 相册走**系统 `ACTION_PICK` + `image/*`**，不是自家 PictureSelector 那套 UI | `c.onGranted` |
| 权限按 **SDK≥29 分叉**：`READ_MEDIA_IMAGES` / `READ_EXTERNAL_STORAGE` | `W()` |
| 相册图**两遍解码**：先 `inJustDecodeBounds` 量，再按 **800×800** 定 `inSampleSize` | `b.C0867b` + `O(options,800,800)` |
| 命中后震动（`VIBRATE` 确实在 1.6.6 清单里） | 配置链里的 `s(true)`；60ms 是我们自己取的时长 |

清单侧也是核过再写的：`CAMERA`、`READ_MEDIA_IMAGES`、`READ_EXTERNAL_STORAGE`（**带
`android:maxSdkVersion="32"`**）、`VIBRATE` 四条都在 1.6.6 原清单里，活动条目同样是
`screenOrientation="portrait"`。

## 三、一个反直觉的算术细节

`O(options, 800, 800)` 那条降采样循环**比的是"一半"的尺寸**：

```kotlin
while (halfHeight / sample >= reqHeight && halfWidth / sample >= reqWidth) sample *= 2
```

所以 4000×3000 对 800×800 的答案是 **2**，不是直觉上的 4。我第一版测试期望就写成了 4，被自己的测试
纠正了——这条现在按实际值钉住。

## 四、本机测不了像素，这轮又撞上一次

扫码测试本该直接喂 #19 `MatchCodeQrPainter.render()` 出来的位图解码器，但上一轮记下的
**Robolectric 光栅化缺陷**让它解不出（Canvas 画的东西不进像素缓冲）。处理办法：把"版面 → `int[]`"
的栅格化从绘制器测试里提成共享工具 `app/src/test/.../view/QrPlanRaster.kt`，扫码测试用
`Bitmap.createBitmap(pixels, …)`（`setPixels` 路径可靠）再喂 `QrDecoder`。

于是多出一条我原本没打算做、但很值的**端到端**：

```
画码器排的版面 → 像素 → 真解码器 → 同一串 URL
```

同一屏里还有一条负向测试：全白位图必须解不出东西（`assertNull`），免得"能解"是因为解码器在瞎猜。

## 五、没对上名字的那三个开关（诚实记账，没猜）

原版配置链：`q(QR_FORMATS).p(false).n(1.0f).m(0).s(true).u(true)`。其中 `n()`=cropRatio（有
`@FloatRange` 佐证）、`q()`=decodeFormats（类型对上）；`p(false)`、`m(0)`、`s(true)`、`u(true)` 分别落到
`f75447h / f75450k / f75442c / f75443d` 四个字段——**没有库源码就定不了名**（候选是：是否播提示音、
是否震动、是否连续扫描、是否查重、期望帧率）。我只实现了"命中震动"这一条，理由是 `VIBRATE` 权限确实在
原清单里；其余没实现也没瞎起名，记进待验第 38 条。

## 六、接线与回路

- `AddFriendActivity` 恢复**用结果启动器**发扫码（原版 `B.launch(...)` 就是这个形状）：
  相机授权通过 → `scanLauncher.launch(QRCodeScanActivity.intent(this))` → 结果喂给早已测过的
  `onQrResult(raw)`（8 位当匹配码 / `Uri.fragment` 里 `userid=` 必须纯数字 / 否则 `invalid_qr_code`）。
- `FriendFlowNavigation.openQrScanner()` 同时换成真 `startActivity`，给"只要扫、不取结果"的调用方用。
- 相机绑定整条走 `CameraBinder` 缝（Robolectric 下没有 `ProcessCameraProvider`），测试里不绑相机。

至此 #15 留下的两条空跳转（通讯录、扫码）**全部闭合**，添加好友四条路径都通到底。

## 七、数字

新增 **14 条测试**（屏 11 + 权限分叉 2 + 添加好友回路 1）：`:app` **190 tests / 0 failures**、
`:net` **10 / 0**，合计 **200 全绿**。`assembleDebug` 通过，APK 61,848,174 B；已核 `QRCodeScanActivity`、
`QrDecoder`、`ScanMaskDrawable` 与布局在包里、`com/king` 不在。业务布局 inflate **仍 306/335**，无倒退。

## 八、本卡没做的（别误会）

1. **真机预览与逐帧解码**：装包才能验（打开即出画面、预览方向/镜像、暗光与远距离识别率、退出后相机是否释放）
   ——待验第 37 条。
2. **闪光灯实际效果**、**遮罩挖洞观感**：代码已接，本机无法断言（待验第 39 条）。
3. **系统相册选图的完整链路**：`ACTION_PICK` 要真机才有回包，测试只覆盖"无 uri 就忽略"。
4. 三个未命名的配置开关、埋点汇 `mf.b`、`AgreeAddActivity`、IM 侧效应、隐私两阶段回灌。
5. **两件等你拍板的事没动**：渠道号（#17）与通讯录空串号码的去留。
