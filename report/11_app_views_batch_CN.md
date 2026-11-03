# LinkUp 第 11 号报告：自有 View 批量重建，业务屏可跑率 77% → 86%

> 日期：2026-11-02 ｜ 承接 `report/10`（FastKit 与 inflate 体检）
> 做法：按体检排出的清单逐个补 `com.youloft.watcher.view.*`

## 一、结果

| 口径 | report/10 | 本轮 |
|---|---|---|
| 业务命名布局可 inflate | 260 / 335（77%） | **290 / 335（86%）** |
| 全部布局 | 404 / 829 | **434 / 829** |
| 仍因**自有 View 缺失**失败的布局 | 43 | **6** |
| 10 个单测 | 全绿 | **全绿** |

## 二、补了哪些类

新建 `app/src/main/kotlin/com/youloft/watcher/view/`，按**布局里写的包名**建到对应子包：

- 根包 `view/`：`MaxHeightRecyclerView`、`StrokeTextView`、`RollingTextView`、`BottomLineTextView`、
  `SendCodeButton`、`DotIndicatorView`、`ScreenUsageView`、`AvatarView`、`PayTypeView`、
  `PswInputView`、`RelationButton`、`AutoReportSettingsView`、`ChatPhoneStausView`
- `view/lock/`：`UnlockButton`、`LockedPreview`、`LockActionView`、`QuestionStatusView`、`LockAnswerView`
- `view/voice/`：`VoiceTimesView`、`VoiceButton`
- `view/mine/`：`AvatarsView`、`UserInfoView`
- `view/vip/`：`VipPolicyView`（1.6.6 里是 `LinearLayout implements Checkable`，勾选状态代理给
  内部 `cb_read_vip_policy`，协议富文本留给拥有它的 VIP 屏）

行为照反编译语义实现的（不是空壳）：`MaxHeightRecyclerView.onMeasure` 的 AT_MOST 限高、
`StrokeTextView` 的文字描边 + 渐变 shader、`BottomLineTextView` 局部下划线、
`SendCodeButton` 的 60s `CountDownTimer`、`ScreenUsageView` 的进度环、
`AvatarView` 的三个自定义属性。`app:maxHeight` 在 APK 里是 aapt2 链接期隐式创建的 attr，
银行没有显式声明，这里在 `app/src/main/res/values/rebuild_attrs.xml` 补了一条。

## 三、这轮最大的教训：包名必须照布局写的那个字面量

第一版我把 `VoiceTimesView`、`UnlockButton`、`AvatarsView`、`UserInfoView`、`LockedPreview`、
`LockActionView`、`QuestionStatusView` 全建在 `com.youloft.watcher.view` 根包下，体检数字只从
77% 挪到 81%——因为布局里写的是 **`com.youloft.watcher.view.voice.VoiceTimesView`** 这种带子包的
全名，类放错包等于没建。**判断依据必须是布局里的字符串，不是 1.5.6 的目录印象**；按子包归位后
立刻从 274 跳到 287，并顺带把被外层遮住的内层缺失（`LockAnswerView`、`VoiceButton`、`VipCard`）暴露出来。

另一个反向教训：我一开始按 1.6.6 猜 `VipPolicyView` 的基类，先写成 `AppCompatTextView` + 引用了
不存在的字符串资源——那是凭印象编。回到 1.6.6 源码确认是 `LinearLayout implements Checkable`、
布局里有 `cb_read_vip_policy` 之后才写对。**看不清就回去读源，不要凑。**

## 四、剩下 6 个（每个只挡 1 个布局，都是真活）

```
com.youloft.watcher.view.SwitchButton                  28KB 自绘开关，需完整移植
com.youloft.watcher.view.SlideRecyclerView             12KB 侧滑 item
com.youloft.webview.WebComponent                       WebView 封装（JS 桥）
com.youloft.watcher.pages.shot.view.ShotPreviewView    1.5.6 里没有，只能照 1.6.6 混淆体重建
com.youloft.watcher.view.lock.FixWheelView             依赖 com.contrarywind WheelView，需先接回该库
com.youloft.watcher.view.mine.VipCard                  会员卡片自绘
```

再往上的失败量级已经不在我们身上了：**广告 SDK 自带 276 个**、其它三方 UI 库 63 个、环信 EaseUI 40 个、
androidx 5 个——这些是"接回依赖"，不是"重写代码"。

## 五、验证

```
gradle :net:test                5 tests
gradle :app:testDebugUnitTest   5 tests（含全量 829 布局体检）→ 10 tests / 0 failures
gradle :app:assembleDebug       通过
python tools/summarize_inflate.py   读 app/build/ui_inflate_per_layout.csv 出这张表
```

未验：真机目视（无设备）；描边/渐变等自绘与原版是否逐像素一致。
