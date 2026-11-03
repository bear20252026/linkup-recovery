# LinkUp 第 14 号报告：第一屏逐屏重建跑通，好友申请列表 17 条回归全绿

> 日期：2026-11-03 ｜ 承接 `report/13`

## 一、为什么先做这一屏

前 13 号报告都在铺地基（协议、路由、强类型模型、资源银行、组件库）。地基铺完之后再不下屏，
就永远不知道这套东西拼不拼得成能跑的界面。第一屏挑 **好友申请列表 `FriendRequestListActivity`**，
因为它一屏就压中了逐屏重建要解的四类问题，而且它在 1.5.6 里是**可读源码**，不用对着混淆体猜：

1. 分页列表（滚动到底继续拉、到底就停）；
2. 行渲染状态机（同意 / 已添加 / 已过期 / 风险提示 / 首末行圆角）；
3. 写接口动作（同意加好友 `POST api/relation/confirm`）；
4. 跨屏跳转（详情页、好友信息页、添加好友页、两个弹窗）。

## 二、这一屏还原到的事实（每条都有出处，不是印象）

| 事实 | 出处 |
|---|---|
| 分页状态在 Activity 里，不在 ViewModel；`page` 从 **1** 起，`list.size < 20` 判到底 | `FriendRequestListActivity.java` 字段 `f64684u/f64685v/f64686w`、`v0()` |
| 请求失败**不推进页码**，只 toast `tips_net_err` | `getData$1.invokeSuspend` 的 catch → `ext.b.toResponse()` |
| 只有第一页读 `isFriendLimit` 决定配额位 | `if (f64684u == 1) x = data.isFriendLimit` |
| 空态用的是 `emptyView.layoutEmpty`，非空时 `k()`(GONE) 而不是隐藏整个 include | `m0(...).emptyView.layoutEmpty` |
| 触发加载的条件是"最后完整可见位置 ≥ 条目数 − 3"且 `childCount > 0` | `onScrollStateChanged` |
| "同意"键有 **500ms 去抖** | `A0()` 首句 `now - f64688y < 500` |
| 四条前置闸门顺序：超 30 天 → 非 VIP 且服务端说配额满 → 对方已注销 → 对方自己满 | `A0()` 从上到下 |
| 请求体 `{code, relation, sensSetting}` **并且** query 也带 `code` | `ApiDataSource$confirmAdd` 的 `a1.j0(...)` + `aVar.F(j10, map)` |
| 服务端不一定回 `friendUserId`，客户端把申请者的 userId **回填进响应**再广播 | `FriendRequestListViewModel$a.invokeSuspend` |
| 成功后：命中该 userId 的行 `setStatus(1)` + `notifyItemChanged`，配额位按 `(本地好友数-1) >= data.friendLimit` 重算 | `C0()` |
| 行首圆角在**左**两角、行尾在**右**两角，半径 28dp；末行分割线 `INVISIBLE(4)` 而不是 GONE | `t0.java` 的 `P().k/t` `P().l/r`、`setVisibility(4)` |
| 三态标签：`status∈{1,4}`→已添加；`status≠0 或 <30 天`→同意；其余→已过期 | `t0.java` 后两分支 |
| 风险提示只在 `riskLevel==3` 显示；文案只在再满足 `riskTypes.contains(4)` 时才覆写 | `t0.java` 两次 `llWarning` 赋值 + `FriendRequest.isHighRisk()/addMultipleFriends()` |
| 行点击：`status 0/4`→申请详情，`1`→好友信息，注销用户只 toast | `z0()` |

天数算法也照抄：`(date2.time - date1.time) / 86400000` 再取 `abs`（`zb.f.e()`），不是 Calendar 日历日差。

## 三、把两处会拖累后面每一屏的地基错误纠掉了

| 之前记的 | 真相 | 影响 |
|---|---|---|
| ViewBinding 开在 `:res166`（资源银行）就能用 | **编不过**：银行里 936 个布局引用的自定义 View（百度地图、各家广告 SDK、环信）不在该模块 classpath，codegen 出的 Java 直接 100 个错误 | 绑定改留 `:app`；**重建哪一屏就把那一屏的 layout 从银行复制进 `app/src/main/res/layout/`**（应用模块覆盖同名库资源，不 duplicate）。绑定包名因此是 `com.youloft.watcher.databinding`，与原版一致 |
| BRVAH 是 `com.github.CymChad:…:3.0.10` | APK 里的包名是 `com.chad.library.**adapter4**`（4.x 才有的包），3.0.10 是 `adapter.base`，API 完全不同 | 现按公开可解析的 `io.github.cymchad:BaseRecyclerViewAdapterHelper4:4.1.7` 接。**APK 内的精确小版本没提取出来**，已列入待验（第九号清单第 7 条） |

`97 条路由那份清单`不受影响；本轮同时把上一轮遗留的 `gen_beans.py` 缺陷收干（`static` 字段不再被当成 bean 字段，`CREATOR` 不再混进 DTO）。

## 四、fastkit 补的是一个真接口，不是新花样

原版 bind 里那句 `binding.root.P().k(px).t(px).w0()` 反查到底：`P()` 返回 `dc.a`，
`k/t/l/r` 是四个**角半径**写入口，`w0()` 是重建 drawable。所以 `:fastkit` 把一次性应用 XML 的
`ShapeStyle.apply` 改成可持有、可改、可重绘的 `ShapeAttrs`（XML 值全部留在对象里，改角不会丢描边和渐变），
7 个 Shaped 视图统一实现 `Shaped { val shapeAttrs }`。**这是被调用点逼出来的接口**——之前只做
"读 XML 画一次"，业务屏一 bind 就缺 API。

## 五、两处原版的坑，我保留没"顺手修"

| 坑 | 现象 | 为什么不修 |
|---|---|---|
| 风险文案只在命中时覆写 | 复用行可能残留上一行的提示文字 | 修法是 else 分支写回默认文案；这属于产品可见的行为改变，交产品定，还原期不夹带 |
| `status` 既不是 0/1/4 时，行尾仍出现可点的"同意" | 中态（如已拒绝）也能点同意 | 后端是否接受这种态的 confirm 无法在此判定；改了就和线上行为不一致 |

两条都在 `FriendRequestAdapter.kt` 处留了一行注释指回本节，测试也把当前行为锁住（`row state follows the recovered branches`），改动时一定会被测试拦下。

## 六、这一屏留下的口子（都有主，不是散落 TODO）

| 口子 | 现在 | 归属 |
|---|---|---|
| 6 个跳转目标 `AddFriendActivity` / `FriendRequestDetailActivity` / `FriendInfoActivity` / `AgreeAddActivity` / `FriendNumLimitDialog` / `FriendPermissionsSettingsDialog` | `FriendRequestNavigation` 接口 + 空实现 | 各自屏重建时填；测试用 Recorder 断言意图 |
| `isVip` / `cachedFriendCount` / `askPermissionsAfterAdd` | `LinkUpApplication` 上 open 默认值 | MMKV 层（`CacheUtils`/`ConfigUtils`）卡片 |
| 确认后逐项同步权限 `PrivacyRepository.updatePermissions` | 未接 | 隐私权限卡片 |
| 全局错误处理（登录态失效刷新重试 `utils.m0`） | 未接，失败只 toast | 网络层卡片 |
| IM 本地同步（成功后 `manager.u.H/M`） | 未接 | 环信/IM 卡片 |
| 埋点 `mf.b.i("好友申请页")` | 未接 | 数数/埋点卡片 |

## 七、数字与验证

```
gradle :net:test                    7 tests / 0 failures
gradle :app:testDebugUnitTest      20 tests / 0 failures   （好友申请屏 17 条）
gradle :app:assembleDebug          通过，app-debug.apk 60.6MB
python tools/summarize_inflate.py  业务命名布局 306 / 335（91%），全部 447 / 798 —— 与上一轮持平，没有倒退
```

这一屏的测试**不是**反射进私有方法、也不是桩：`launch()` 里 RecyclerView 被真实 measure/layout，
`agree through the row button…` 走的是 `tv_agree.performClick()` → BRVAH 子键点击 → Activity 闸门
→ ViewModel → repository → 状态回写 → 跳转Recorder → `finish()` 整条链；toast 用 `ShadowToast`
断真实文案（取自 `res166` 的原文，不硬编码中文）。分页、去抖、四条闸门、空态、返回键、加友键都有对应断言。

## 八、下一屏照这个模板要做的五步

1. 在 1.5.6 里找到该屏的可读源（`pages/**`），把字段/分支逐条列成出处表——**列不出处就不写**；
2. 把该屏用到的 layout 从 `res166` 复制进 `app/src/main/res/layout/`，绑定即用 `com.youloft.watcher.databinding`；
3. bean 缺字段/方法就补 `tools/gen_beans.py` 重出 DTO，业务方法（如 `isHighRisk()`）写在 app 层扩展，不改生成物；
4. 屏间跳转一律先进一个接口（本屏是 `FriendRequestNavigation`），空实现 + Recorder 断言意图；
5. Robolectric 覆盖：行状态机纯函数 + 真视图点击链路 + 每条前置闸门各一条 + 失败/空态各一条。

## 九、本轮发布边界

公开仓只跟代码、文档与"被布局引用"的那批动画资源。从 APK 解出来的厂商 SDK 二进制（25MB）与反编译器发行包
（`tools/jadx` 75MB）不推；本轮把它们写进 `tools/publish.sh` 的固定排除，避免靠手抄目录再抄出事故。
新建的业务代码是否要转私有仓，仍按 `report/00` 第六节的边界等拍板。
