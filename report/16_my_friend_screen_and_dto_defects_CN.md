# LinkUp 第 16 号报告：第三屏「我的好友」跑通，顺带挖出两处"能编译、结果错"的 DTO 缺陷

> 日期：2026-11-03 ｜ 承接 `report/15`

## 一、这一屏和前两屏不是一个形状

`MyFriendActivity` **没有 ViewModel、没有分页、不发 HTTP**。原版订阅的是 `manager.u`
（IM 推送 + 本地缓存维护的好友列表 + 一条"好友变更命令"频道），屏幕只做四件事：排序、标题、
点击路由、消费命令。所以这一屏的价值不只在屏本身，而在于把"重建工程缺 IM/缓存层"这件事
**用接口固定下来**（`FriendListSource`），而不是塞一个假数据源把屏糊过去。

## 二、还原到的事实

| 事实 | 出处（1.5.6 可读源） |
|---|---|
| 列表为空时**屏幕自己 `finish()`** | `h0()` 首行 |
| `userId <= 0` 的行不进列表；主账号 `add(0, …)` 排最前 | `h0()` |
| 标题 `我的好友（%d）` 用的是**过滤后**的数量 | `h0()` 末段 |
| 过滤后为空 ⇒ 底部"添加新朋友"键 GONE | 同上 |
| 行点击：`userId==0` 直接 return；`unregisterTime>0` 只 toast；否则 `FriendInfoActivity(userId, type=2, name)` | `j0()` |
| 加友入口三个不同的 mode：本屏底部键 **6**、空态按钮 **0**、申请列表标题栏 **8** | 三处 `AddFriendActivity.a.b(...)` 的 mask 位 |
| 命令频道：`type ∉ {ADD=1, ADD_SELF=100}` 才处理，且处理前**先把命令置 null 消费掉** | `g0()` + 内部协程 |
| 处理要**等 RESUMED**；落回 null/ADD 类时 cancel 掉上一个 job | `g0()`、字段 `f64725p` |
| 适配器靠构造参数 `styleMode` 切四种行形态；本屏 mode 0 隐藏性别/添加时间/勾选 | `adapter/FriendListVAdapter.f0()` |
| `Info.getName()` = remark 非空取 remark，否则 nickname | `bean/FriendList.java` |
| `isExpFriend()` = `userId == 0`；角标画在 (行左 +34dp, 行上 −11dp) | `FriendListVDecoration` |

**一条"不是 bug 的事实"**：本屏把 `userId<=0` 过滤掉了，而 `isExpFriend()` 就是 `userId==0`——
所以**「我的好友」永远不会有体验好友角标**，那条分支属于用同一 decoration 但不过滤的其他屏。
写清楚是因为这种地方最容易被"顺手补一下"改错。

## 三、两处静默缺陷：编译过、测试也可能过，只有打线上才露馅

`FriendList.Info` 这一屏逼出来的。两个坑同属一类：**不报错，只是结果一直是默认值**。

| 缺陷 | 表现 | 修法 | 结果 |
|---|---|---|---|
| 生成器只读顶层类，**嵌套 bean 被摊平**（1.6.6 有 35 个文件带 `public static final class`） | `FriendList` 既吞了 `Info` 的 23 个字段，自己的 `list` 又退化成 `List<JsonElement?>?`；`FriendList.Info` 这个类型在重建里**不存在**，依赖它的屏全写不出来 | 按花括号范围把每个类体自己的字段分干净；嵌套类生成成 `data class FriendList { … data class Info(…) }`；跨文件引用写限定名 `Parent.Inner`，简单名与顶层类撞车时退回 `JsonElement`（宁可退让不猜父类） | 9 个嵌套 bean 恢复；`List<JsonElement?>?` 从 6 处降到 3 处（剩下的是真取不到类型的） |
| **jadx 改名污染 JSON key**：字段与包名段冲突时 jadx 写成 `f63406id`，并留 `renamed from: id` 注释 | 两个 APK 的 `@SerializedName` 都被 R8 抹掉 ⇒ **JSON key == Java 字段名** ⇒ 照抄改名结果就是该字段永远解析不出来，静默为 0 | 从那条注释取回真名，并要求残名确实以真名结尾才替换 | 11 处 `id` / `rh` 还原 |

为什么这条值得单独写：如果 fake 数据是照着错字段名造的，**测试一样是绿的**。
所以生成器改动之后必须重跑带线上抓包留证的那条 `:net:test`，不能只跑新增屏的测试。

## 四、两处框架落差与我的取法

| 落差 | 取法 | 为什么不是别的 |
|---|---|---|
| 原版用 `lifecycleScope.launchWhenResumed`，lifecycle 2.7 已把它**删除** | `lifecycle.whenStateAtLeast(RESUMED) { … }` | `repeatOnLifecycle(RESUMED)` 每次回前台重放，会把同一条命令处理两遍；`whenStateAtLeast` 才是"等到该状态跑一次"的等价物 |
| BRVAH 的 state view 在数据为空时**占据一个 item 槽位** | 断言"几个人"改看 `items.size`，不看 `itemCount` | 空列表 + 空态视图时 `itemCount == 1`，把 `itemCount` 当人数会得出错误结论 |
| fastkit 的 `g0.O/g0.x`（间隔点击）与 `widget.i`（图片加载）没重建 | 屏内用一个时间戳复现 500ms 间隔；图片直接走 Glide | 已列进待验清单（`DESIGN_CN.md` 第九节 10/11 条），不假装还原 |

## 五、数字与验证

```
gradle :net:test                    7 / 0
gradle :app:testDebugUnitTest      49 / 0
      ├ 我的好友 14（含一条"数据源必须是同一个实例"的守卫）
      ├ 申请列表 18、申请详情 14
      └ 原有布局回归 3
gradle :app:assembleDebug          通过，APK 60.6MB
      实测 APK 内含 MyFriendActivity（classes13.dex）+ 清单条目（portrait，与原版一致）
python tools/summarize_inflate.py  业务命名布局 306 / 335（91%）——三屏持平，没有倒退
```

好友流三屏合计 **46 条**测试全绿；`report/14` 第八节那五步模板在这一屏全部用上了，
包括"目标屏没重建就先进接口、测试断言跳转意图"。

## 六、这一屏留下的口子

| 口子 | 现状 |
|---|---|
| `FriendListSource` 的真实生产者（IM manager + 本地缓存） | 接口已按原版观测面定形；`PendingFriendListSource` 只是占位，卡片 #11 |
| `AddFriendActivity` / `FriendInfoActivity` 及三个弹窗 | 仍是 `FriendFlowNavigation` 上的空实现，mode/type 参数已按原值传 |
| 体验好友角标的真实出现场景 | 要连"不过滤 userId 的那一屏"一起做（待验第 14 条） |
| `mf.b.i("我的Tab-我的好友")` 埋点 | 未接，属埋点卡片 |

## 七、下一屏

好友流还剩 `FriendInfoActivity`（被两屏指着，type 已定）与 `AddFriendActivity`（三种 mode）。
建议下一屏做 **`FriendInfoActivity`**：它能一次性把 `openFriendInfo` 的空实现换成真跳转，
并把这一屏的"行点击 → 好友详情"闭环补全。
