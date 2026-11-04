# LinkUp 第 18 号报告：共用弹窗层落地，六个动作的真实交互解绑（含窗口库的已知限制）

> 日期：2026-11-03 ｜ 承接 `report/17`

## 一、这一轮解了什么

前三屏留了六个"只记录意图、不弹东西"的空位。这一轮把弹窗本体做出来，六个动作当场可点：
删除确认、改关系、改备注、改权限、配额提示（两处入口）。
`FriendInfoDialogs` 这个临时接口被删掉，`FriendFlowNavigation.showFriendNumLimitDialog` /
`showPermissionSettings` 从空实现换成真弹窗。

## 二、必须先说清楚的：窗口库是**真·子集**，不是原样 1:1

原版链路（当场从反编译里读出来的规模）：

| 层 | 规模 | 本次 |
|---|---|---|
| `dialog.e`（接口，~30 个链式 setter：遮罩色、状态栏/导航栏、动画集、tag、Gravity、宽高…） | 458 行 | 未搬 |
| `dialog.XDialog`（宿主 Lifecycle、键盘跟随、重复弹出守卫、OnKey/OnShow、软键盘 ADJUST_PAN） | **2013 行** | 只搬了「宿主正在销毁 / 已经在显示 → 拒绝弹出」这条守卫 |
| `dialog.BindingDialog<V,T>`（反射泛型参数 inflate ViewBinding） | 68 行 | 搬了（改成单泛型参数：原版第二个参数只为链式 setter 服务，本轮没有链式 setter） |
| app 侧 `base.BaseFrameDialog`（getContext 助手 + 重复弹出守卫） | 122 行 | 未搬，本轮弹窗直接继承 `BindingDialog` |
| `dialog.SimpleDialog` / `BottomSheetDialog` | 41 / 185 行 | 未搬 |

所以**别把「五个弹窗可用」读成「组件库可用」**。`DESIGN_CN.md` 五点十三 + 第九号清单当场记了这条限制。

一处时机差异：原版 `e.a.a(dialog, 0)` 是 `b0(millis)` → `lifecycleScope` 协程排程收起；本轮弹窗没有协程宿主，
改用 `contentContainer.post{ dismiss() }`。差别只在一帧的排程时机，按钮先后次序不变。

## 三、五个弹窗 + 一个选择器：当场读出来的事实

| 组件 | 事实 | 出处 |
|---|---|---|
| `pages.common.ConfirmDialog` | 默认 cancel=`cancel`、confirm=`confirm`、内容行不设就隐藏；两个按钮都走「间隔点击」；**任一键都收起，但只有确认键回报决策**；遮罩默认 `color_7f000000` | 构造 + `L1()` + `O1/P1` |
| `view.RelationButton` | 四张磁贴由 `bean.friend.RelationView` 四元组驱动（磁贴 / 对勾 / 文字 / 角标）；选中 = 宽 80→100dp、着色 `colorCardVariant`→`colorBrand`、角标淡入、对勾显示；**值没变直接 return**；默认回调空 | `setRelation` / `c0` |
| `friend.dialog.UpdateRelationDialog` | 磁贴只改内部选择、**不回报**；✕ 收起不回报；确认键**先收起再回报** | `Q1` / `R1` |
| `user.dialog.UpdateUsernameDialog` | `InputFilter.LengthFilter`（默认 10）+ `%d/%d` 计数；空输入禁用确认（除非 `alwaysEnabled`，备注入口正是这条）；预填光标到末尾；内容设置后 **300ms** 弹键盘 | `L1()` + 内部 `a` + `h0` |
| `friend.dialog.FriendPermissionsSettingsDialog` | 9 个勾选按 location/track/phoneUse/call/phoneState/sensitive/appUse/lockPhone/realtimeVoice 对位；**`cb_sens_screen_shot` 布局里有、原版从不读写** → 保持不动，新 Permission 第十个保持 false；**在收起时回报**（所以 ✕ 回报 null，调用方读作"用户走开"）；传进 null 权限自己收起；`showClose=false` 收起 ✕；按 source 埋点 1/2/3/4/5/6，其它空 | `L1()` / `h0` / `b0` |
| `friend.dialog.FriendNumLimitDialog` | 只有两个动作：`tv_vip` → 回报 + 收起；✕ → 只收起（原版此处还先开 VIP 购买页 `manager.s.b(context, 15)`） | `O1` / `P1` |

## 四、接上线的地方，以及故意没接的

* `FriendInfoActivity.dialogs` 默认改成真弹窗。新增一条**生产路径**测试：当场点删除键 → 量出真
  ConfirmDialog 的标题（`确认删除该好友吗？`）→ 当场点确认 → 请求发出 + 收起 + `finish`。
  这条测的是线上那条链，不是 mock。
* 申请流 `showPermissionSettings` 换成真弹窗（按原种子：全开、收起 ✕、source=1）；回报 null 才走
  "开 AddResult + finish"。**非 null 分支没有半接线**：`PrivacyRepository.updatePermissions` 的
  "先 POST `friend_sens`、失败再逐类型回灌"两阶段流程属隐私权限那张卡。
* `showFriendNumLimitDialog` 换成真弹窗；VIP 购买页（`manager.s`）仍是空位。

## 五、数字与验证

```
gradle :app:testDebugUnitTest     82 / 0
      ├ 弹窗 + 选择器 14（新增）
      ├ 好友信息 18（新增那条生产路径测试）
      ├ 我的好友 15、申请列表 18、申请详情 14
      └ 原有布局回归 3
gradle :net:test                   7 / 0
gradle :app:assembleDebug          通过，60.6MB，实测 APK 内含四个新弹窗/选择器类（dex）与 5 个活动条目（清单）
python tools/summarize_inflate.py  业务命名布局 306 / 335（91%）——持平，没有倒退
```

弹窗测试走真视图树：`show()` → `findViewById` → `performClick()`，并用 `shadowOf(mainLooper).idle()`
把"收起时回报"那一步排程跑完，因此"✕ 回报 null"、"确认先收起再回报"、"空输入禁用确认"这些
都是从屏幕上点出来的，不是从 mock 里读出来的。

## 六、这条窗口库现在还不能当什么用

1. 薄外壳：宿主 Lifecycle、键盘跟随、动画集、状态栏、tag/Gravity/宽高那套 setter **没**搬。
   下一个用到链式 setter 的弹窗（多半是会话/相册那张），必须先补 XDialog 那一层。
2. 用 `post` 代替协程排程收起，时机差一帧。
3. 权限弹窗的按-source 埋映射有、汇没有（汇本身是另一张卡），只有测试钉住映射。
4. 硬编码中文：配额提示里"你们已不是好友 / 该账号已注销"这类文案在原版就是字面量（已记第 20 条）；
   `FriendNumLimitDialog` 的 VIP 文案走布局，没动。
5. VIP 购买页 / 会话页 / AddFriend 三个入口仍是空位。

## 七、下一屏

弹窗层补完，好友流只剩 `AddFriendActivity`（三种 mode 的入口，`friend_delete` 广播的第一批订阅方）。
建议下一轮做 #15，或者转向 #11（MMKV 缓存层）——后者能把前三屏那三个假默认值换成真读数，
是端到端验收的前置。
