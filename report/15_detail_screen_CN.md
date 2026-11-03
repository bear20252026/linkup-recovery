# LinkUp 第 15 号报告：第二屏跑通，列表到详情的跳转第一次是真的

> 日期：2026-11-03 ｜ 承接 `report/14`

## 一、这一屏补上的是"闭环"，不是又一个切片

上一轮的好友申请列表留了 6 个空跳转目标。这轮把第一个 **申请详情 `FriendRequestDetailActivity`**
重建出来，并把 `FriendRequestNavigation.openFriendRequestDetail` 从空实现换成真 `startActivity`。
于是第一次出现"从 A 屏点进去、B 屏把数据接住、动作打完再跳走"的完整链路，而且它是由测试盯着的：
列表屏那条用例真按生产路径 `start()` 发起，再断言被启动的组件名、Intent 里的 bean 存活、
以及 `myFriendLimit` 这个额外标记。

## 二、这一屏还原到的事实

| 事实 | 出处（1.5.6 可读源） |
|---|---|
| Intent 契约：`getParcelableExtra("data")` + `getBooleanExtra("myFriendLimit", false)` | `M()` 前两行与调用方 `a(context, request, z10)` |
| **整屏只有一个"同意"键，没有拒绝键** | `activity_friend_request_detail.xml` 全文，没有第二个按钮 |
| 三条前置闸门顺序：超 30 天 → 非 VIP 且**我**配额满（弹窗）→ **对方**配额满（toast） | `o0()` |
| 与列表屏不同，这里**没有**"对方已注销"判断 | `o0()` 无对应分支 |
| `status != 0` ⇒ 按钮 `setEnabled(false)` 且文案换成"与该用户已为非好友关系" | `M()` 末段 |
| 关系四分支 1 恋人 / 2 挚友 / 3 亲人 / 其他；性别 1 男 2 女，性别图标挂在文字**尾侧** | `p0()`、`z.k(tvSex, GravityCompat.END, drawable)` |
| 匹配码走 HTML：`匹配码：<font color=#324058>%d</font>` | `ext.l.d(getString(mine_match_code, userId))` |
| 同意键是 **500ms 间隔点击**（`ext.r.c(view, 0L, …, mask=1, …)` 的默认值取 500） | `ext/r.java` → `g0.x` |
| 结果 `msg != null` 就 toast，**不判空串**（列表屏判长度） | `k0()` |
| 成功后：渠道开关开 → 权限设置弹窗（不 finish）；否则 → `AgreeAddActivity` + `finish()` | `k0()` |
| 详情屏 ViewModel 是 `MutableLiveData.postValue`，列表屏是 `SharedFlow` | 两个 ViewModel 字段类型 |
| 详情屏**不**回填 `friendUserId`（列表屏回填） | 两处 `invokeSuspend` 对比 |

我上一轮给这一屏写的任务描述里记了"拒绝/同意双动作 + VerifyInfoDialog"——**那是我记错**，
代码里既没有拒绝键，这一屏也不经过 `VerifyInfoDialog`。任务卡已按代码改正。

## 三、顺带定死一条会影响每一屏的架构问题

原版所有 bean 实现 `Parcelable`，而本工程的重建把 DTO 放在**纯 JVM 的 `:net`** 模块里
（这样才能在没有手机的情况下跑签名与协议回归），`android.os.Parcelable` 在那里根本不存在。
但"把整个 bean 交给下一屏"是这个 app 的通用跨屏方式，绕不过去。

定下来的做法：`tools/gen_beans.py` 按字段图判定，**给不含 `JsonElement`、不带泛型的 61/79 个 bean**
加 `java.io.Serializable`，跨屏继续 `putExtra("data", bean)`。剩下 18 个持有原始 JSON 的 bean
**不打标记**——不给一个只有到运行时才 `NotSerializableException` 的假承诺。
将来若把 bean 迁回 `:app`，再整体换回 Parcelable，届时屏代码不用改（契约键名不变）。

## 四、数字与验证

```
gradle :net:test                    7 tests / 0 failures
gradle :app:testDebugUnitTest      35 tests / 0 failures
      ├ 列表屏 18（新增"真跳转 + bean 存活"1 条）
      ├ 详情屏 14
      └ 原有布局回归 3
gradle :app:assembleDebug          通过，60.6MB
      实测 APK 内含 FriendRequestDetailActivity（classes13.dex）与清单条目
      （screenOrientation=portrait，与原版一致；二进制清单按 UTF-16 核对，不是靠"看着像"）
python tools/summarize_inflate.py  业务命名布局 306 / 335（91%）——两轮持平，没有倒退
干净 clone 复跑                    :app 详情+列表测试与 assembleDebug 通过（1m28s）
```

详情屏的测试一律用生产路径 `FriendRequestDetailActivity.start` 造出的 Intent 结构（extra 键名在测试里
引用同一份常量，改契约就红），而不是各自拼一份私有键名字符串。

## 五、这一屏留下的口子

| 口子 | 现状 |
|---|---|
| `AgreeAddActivity`（成功页）、`FriendPermissionsSettingsDialog`、`FriendNumLimitDialog`、`FriendInfoActivity`、`AddFriendActivity` | 仍是 `FriendRequestNavigation` 上的空实现，各屏重建时填 |
| `PrivacyRepository.updatePermissions`（权限弹窗确认后逐项同步） | 未接，属隐私权限卡片 |
| fastkit 的点击层 `g0.x`（间隔点击）与 `ext.o.b`（点击反馈） | 间隔用活动内时间戳复现，反馈没有 → 待验清单第 10 条 |
| 头像加载 `fastkit.widget.i.f` | 用 Glide 直连，原版占位/淡入参数取不出 → 待验清单第 11 条 |
| `isVip` / `myFriendLimit` / `askPermissionsAfterAdd` 真实读数 | 仍靠 `LinkUpApplication` 的 open 默认值 → 卡片 #11 |

## 六、下一屏

按同一模板推进，建议先做**列表屏剩下的 `FriendInfoActivity`**（它同时是详情与列表的共同目标），
或直接进"我的好友"列表（复用本轮 BRVAH + 分页闸门模板，边际成本最低）。
