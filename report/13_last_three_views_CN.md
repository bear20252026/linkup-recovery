# LinkUp 第 13 号报告：最后 3 个自有 View 收掉，业务屏 90% → 91%

> 日期：2026-11-02 ｜ 承接 `report/12`

## 一、这三个的真相和做法

| 类 | 挡的布局 | 结论 | 做法 |
|---|---|---|---|
| `view.SwitchButton` | `activity_chat_message_setting` | **它就是 kyleduo SwitchButton 的 vendored 副本**——布局用的是 `sb_background / sb_checked / sb_checked_color / sb_uncheck_color / sb_border_width / sb_show_indicator` 这组上游属性 | 上一轮已接回 `com.kyleduo.switchbutton:library:2.1.0`，这里**薄封装委托**，不重造 29KB 自绘代码 |
| `view.im.CameraButtonView` | `activity_capture` | 聊天相机快门：外环 + 内圆，拍照时内圆收缩，原版用 `TimerTask` 驱动 | 自绘 View，动画换成 `ValueAnimator`（跟 Choreographer 时钟，不需要自己管线程），保留 `startCaptureProgress()/stopCaptureProgress()`，并在 `onDetachedFromWindow` 里收尾 |
| `webview.WebComponent` | `activity_common_web` | FrameLayout 容器，内嵌自家 `CommonWebView`（布局里只写 `android:id="@id/webView"`） | 一并补 `webview.CommonWebView`；公开 API 按反编译里可读到的名字还原：`getWebView() / url() / originalUrl() / title() / activity() / loadUrl()` |

**`CommonWebView` 只做到"容器 + 每页数据袋 + 标题"**。它原版还挂着 JS bridge 与 protocol dispatcher 两套子系统（`getJsBridge()`、`getProtocolDispatcher()`），
那是 H5 容器卡片的活，这里不写空壳冒充——写个返回 null 的 `getJsBridge()` 比不写更容易骗到人。

## 二、数字

| 口径 | report/12 | 本轮 |
|---|---|---|
| **业务命名布局可 inflate** | 303 / 335（90%） | **306 / 335（91%）** |
| 全部布局 | 444 / 798 | 447 / 798 |
| 因自有 View 失败的布局 | 8 | **5** |

## 三、"收掉 3 个"之后新暴露的 5 个（都不便宜，也不是同一类活）

```
view.vip.ProductsView              VIP 商品列表容器（新暴露，被外层遮住）
view.mine.VipCard                  会员卡自绘卡片
view.SlideRecyclerView             侧滑 item 菜单，需自己处理触摸与回收
view.lock.FixWheelView             依赖 com.contrarywind 的 WheelView，要先接回该库（AndroidPicker 已接，但这个类没命中）
pages.shot.view.ShotPreviewView    1.5.6 里没有，只能照 1.6.6 混淆体重建
```

另有两类失败不属于"View"：`pages.camera.CameraFragment`、`pages.todo.TodoFragment` 是布局里用 `<fragment>` 标签引的**真业务页**，
它们的恢复属于逐屏重建；`com.youloft.watcher.debug` 三条是 `FragmentContainerView must be within a FragmentActivity` 之类的测试环境限制。

**结论**：UI 资源层"靠补控件就能解"的部分基本见底了。剩下 91%→100% 的推动力不在 View 上，
而是（a）接回广告/环信等厂商依赖（316 个布局）、（b）逐屏重建 Fragment/Activity 与 H5 桥。

## 四、验证

```
gradle :net:test                 5 tests
gradle :app:testDebugUnitTest    含 798 布局全量 inflate 体检 → 10 tests / 0 failures
gradle :app:assembleDebug        通过
```
未验：真机目视（本机无设备）；`CameraButtonView` 的收缩曲线与原版是否一致（原版计时参数在混淆体里读不准，
这里取 1s 线性收缩）；`SwitchButton` 走 kyleduo 2.1.0 与原本 vendored 版本的行为差异。
