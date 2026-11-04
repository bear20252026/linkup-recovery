# LinkUp 第 17 号报告：第四屏「好友信息」跑通，四个写动作里有三个是真端点

> 日期：2026-11-03 ｜ 承接 `report/16`

## 一、这一屏是四屏里动作最多的

`FriendInfoActivity`：资料展示 + 改备注 + 改关系 + 权限摘要 + 聊天入口 + 删除好友，
外加一条 IM 推送上来的"你们已不是好友 / 该账号已注销"覆盖层。它按 `id` 加载、没有分页。
做完它，上一轮留的两个跳转（申请列表 `type=0`、我的好友 `type=2`）都换成了真 `startActivity`。

## 二、四个端点是按调用点解出来的，其中 1.5.6 的 Retrofit 注解本身也被混淆

1.5.6 里接口方法写作 `@o("api/relation/del")` / `@f("api/relation/info")` / `@t("queryId")` / `@bm.a`，
要先认回 `POST/GET/Query/Body`，再把"路径注解—方法"按就近关系配对，才能确定每个动作打的是哪条路。
结果：

| 动作 | 端点 | 请求体 | 本轮状态 |
|---|---|---|---|
| 资料 | `GET api/relation/info?queryId=` | — | ✅ 已接、已测 |
| 删除 | `POST api/relation/del` | `{friendId}` | ✅ 已接、已测 |
| 改关系 | `POST api/relation/update` | `{friendId, relation}` | ✅ 已接、已测 |
| 改备注 | `POST api/relation/update_remark` | `{friendId, remark}` | ✅ 已接、已测 |
| 改权限 | `POST api/setting/friend_sens` + 失败后逐类型回灌 | `PermissionUpdateBean` | ⛔ 有意未接，见第五节 |

## 三、还原到的事实（挑容易写错的）

| 事实 | 出处 |
|---|---|
| `sex` / `relation` 在这个 bean 里是**字符串**，原版直接 `Integer.parseInt` | `z0()` |
| remark 只在**非空**时写入标签，空则保留原值 | `z0()` |
| 权限摘要＝数 9 个 sens 开关里 true 的个数：>0 → `%d项数据`(appPrimary)；否则 → `无可见数据`(appSecondary)。顺序是 location/track/phoneUse/call/phoneState/sensitive/appUse/lockPhone/realtimeVoice | `w0(Permission)` |
| 加载失败**或 data 为 null** ⇒ `S0()`：隐藏 rl_remark / rl_relation / ll_permissions / ll_add_date / iv_delete / toolbar，显示 `tv_not_friend`；用户名退回 **Intent 里的 nickName**，匹配码用 **Intent 里的 id** 现算 | `S0()` |
| `relation <= 0` 时点关系行什么都不做（不弹窗） | `K0()` |
| 删除确认后成功 ⇒ toast `delete_success` + 按原版主题名 `friend_delete` 广播该 id + `finish()` | `A0()` + `J0()` |
| 改关系 / 改备注的"成功响应"里 data 是**客户端回显自己发出去的值**，不是服务端回包 | `FriendInfoViewModel` 两处 `new ApiResponse(status, msg, relation/remark)` |
| 改备注成功还要刷 IM 与最近会话（`u.M` + `widget.im.e.v()`） | 同上 |
| 推送 type=2 ⇒ 覆盖层可点、toast「你们已不是好友」；type=4 ⇒「该账号已注销」 | `E0/F0/G0` |
| `source` 只喂埋点标签：1 守护Tab-头像功能弹窗、2 消息中心-我的好友、3 im头像、其他空 | `x0()` |
| Intent 三个键就叫 `id` / `source` / `nickName` | `a().a(...)` 与 `M()` |

顺手把仓储层并回原版形状：`FriendRequestRepository` → **`FriendRepository`**，
原版就是一个 `repository/FriendRepository` 覆盖全部 relation 端点，屏不按屏拆接口。

## 四、两处明确偏离原版（都有测试钉住）

1. **不还原崩溃**：`Integer.parseInt(sex/relation)` 在字段缺失时原版会抛。这里取 `toIntOrNull() ?: 0`，
   落进"未知/其他"分支，并有 `unknown sex and relation degrade…` 一条测试钉住行为。
2. **不假装资源化**：两条 toast 在原版的**调用点就是硬编码中文**，资源表里查无此条
   （`grep` 过 2169 条文案）。保留字面量维持行为一致，同时把"要不要进 i18n"记成待验第 20 条，
   而不是悄悄发明一个资源名冒充原版设计。

## 五、没有半接线的地方

`PrivacyRepository.updatePermissions` 是两阶段：先 POST `api/setting/friend_sens`，
若失败且原本有权限对象，再拉一次当前权限、然后**逐类型**（track=2 / call=5 / appUse=7 / location=1 …）
分别回灌。这一块完整属于隐私权限卡片。本轮只把"打开权限弹窗"这步接成真实调用，
回调处留空位并写明去向——**没有**为了让代码看起来完整而先接上半个端点，
因为半个流程比没有流程更容易骗到后来读代码的人。

同样留口的还有四个弹窗本体（`FriendInfoDialogs` 接口 + 假实现交付回调，整条动作链已测通）、
`ChatActivity`（IM 卡片）、`friend_delete` 的订阅方（要等会话列表那批屏）。

## 六、数字与验证

```
gradle :net:test                     7 / 0
gradle :app:testDebugUnitTest      67 / 0
      ├ 好友信息 17（新增，首跑即绿）
      ├ 我的好友 15、申请列表 18、申请详情 14   ← 好友流合计 47
      └ 原有布局回归 3
gradle :app:assembleDebug           通过
      实测 APK 内含 FriendInfoActivity（清单条目 + dex），portrait 与原版一致
python tools/summarize_inflate.py   业务命名布局 306 / 335（91%）——四屏持平，没有倒退
干净 clone 复跑                     :app / :net 全量测试 + assembleDebug 通过
```

这一屏的测试全部走真视图树与真回调：`FakeDialogs` 记录"开了哪个窗、带着什么初始值"，
再交付用户的选择，于是"确认删除 → 发请求 → toast → 广播 → finish"整条链是被断言的，
而不是靠 mock 到一半自证通过。广播用 `Dispatchers.Unconfined` 的订阅者收，确保收到的是那一次事件。

## 七、下一屏

好友流的屏间闭环已经打通（列表 ⇄ 详情 → 信息）。接下来两个自然目标：
**四个共用弹窗**（一次解开 6 个动作的真实交互），或 **AddFriendActivity**（三种 mode 的入口屏，
也是 `friend_delete` / 新申请广播的第一批订阅方所在）。
