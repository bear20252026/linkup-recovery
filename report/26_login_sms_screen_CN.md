# 26 · 登录屏前半：短信那条（卡 #18）

**一句话结论**：登录屏、短信弹窗、60 秒倒计时按钮、协议提醒弹窗都落地了；`api/sms/send` 与
`api/sms/click_to_login` 的形状、成功后的写入顺序、以及"上次登录"角标全部按 1.6.6 钉住。
这一卡补上了 #16 那条写入通道的上游——`user2` 与 `token` 从此由真实登录流程写。

卡型：还原 + 落地（新屏）。独占文件：`app/.../pages/login/**`、`app/.../view/SendCodeButton.kt`、
`app/.../data/LoginRepository.kt`、`app/.../data/local/LoginFlags.kt`、`app/.../ext/ClickableSpans.kt`、
`app/.../res/layout/{activity_login,dialog_login_sms,dialog_policy_remind}.xml`、
`fastkit/.../dialog/BindingDialog.kt`（只加 `hostActivity`）、`fastkit/.../utils/KeyboardUtils.kt`（只加 `showKeyboard`）、
`app/.../data/local/KeyValueStore.kt`（加 int/bool 读写）、`app/.../data/UserManager.kt`（写入顺序与分岔）。

**安全边界**：全程没有真调 `/api/sms/send`——那会发真短信。所有短信/登录路径都是 JVM 假仓库驱动的测试。

---

## 一、这一轮推翻了五条旧记账

| # | 之前记的（#15/#16 报告里） | 1.6.6 实际 | 出处 |
|---|---|---|---|
| 1 | `typeId` 1/2/3/4/5，4=微信、5=QQ | typeId **只有 1/2/3**，走 `api/sms/click_to_login`（绑手机时同 body 换 `api/user/change_bind`）；微信/QQ 是**另一个端点** `api/user/login`，body 是 `unionId,platform,avatar,nickname,phone`，`platform` 4/5 | `datasource/a.java:715-733`、`:873`；`repository/c.java:229-280` |
| 2 | 登录成功"先写 token 再写 user2"，且我在 #16 代码里就是这么做的 | **先 `user2` 再 `token`**：`CacheUtils.i3(user)` 在前，`d3(token)` 在后 | `manager/v0.java:314-330` |
| 3 | 号码认证用 Mob 的 `com.mob.secverify.SecPure` | 1.5.6 确实是 SecPure；**1.6.6 把 Mob 整族删掉了**（`sources/com/mob` 整个不存在），换成同结构的 `cn.fly.verify.FlyVerify`——`coremcl/mgs/id/tools` 这些子包一一对得上，等于同一套东西换了牌子。`com.g.gysdk` 两版都在 | 1.6.6 `manager/v0.java:4,343,485` ↔ 1.5.6 `manager/z0.java:332,445`；两边目录对照 |
| 4 | `Cut.loginType` 是数字，"非 1/3 直接弹短信框" | 它是**字符串**；`toIntOrNull() ?: 1` 交给 `v0.o(type, cb)`；非 1/3 ⇒ **回调 null**；再由"号码或运营商为空"才落短信框 | `LoginActivity.java:434`、`bean/login/Cut.java:47`、`manager/v0.java:463` |
| 5 | 登录响应一律进缓存 | 有一条**不进缓存**的分支：昵称为空的登录（或三方登录已注册账号）被寄存在进程全局 `App.user`，**只写 token** | `manager/v0.java:316-321`、`App.java:41,69-72` |

第 2 条是我自己发布出去的错：#16 把顺序写反了，还在注释里写"顺序重要且已保留"。本轮改回并加了一条
**按写入次序断言**的测试（`UserManagerTest` 用装饰过的 store 记录 key 顺序），下次再改就会红。

第 5 条的含义值得单说：**用户已登录（有 token）但 `user2` 还是旧的**，这不是 bug，是原版把"资料没补全的人"
交给补资料屏去落地。所以重建里 `UserManager` 有一个 `inFlight`（对应 `App.user`）而不是无条件落库。

## 二、决策树（照搬，每条有出处）

```
onCreate
  ├─ lf.b.i("登录注册页")                    （埋点汇未重建，只留标签）
  ├─ from_h5 / match_code 读入               LoginActivity.java:757-758
  ├─ logout=true 才读 lastLoginType → 角标   :759-768
  ├─ 两张 Lottie alpha 0→1，500ms，postDelayed 100ms 起 :769-782
  ├─ 四个按钮点击（全部 500ms 去抖）        :783-814
  ├─ U0()：POST_NOTIFICATIONS 每账号只问一次 :838-845（键在**按用户分实例**：isRequestedNotification）
  └─ F0().u() → GET api/sms/login/cut
        → loginType.toIntOrNull() ?: 1 → OneTapAuth.preLogin(type)
              null          → 协议行去掉运营商条款
              number 空      → 只存字段，不重画协议行（下次 onResume 才出现）
              number 非空    → 协议行追加《运营商条款》
点"手机号" → 未勾协议 → PolicyRemindDialog（确认＝自动勾上 + 重放这次点击）
          → number 或 operator 为空 → LoginSmsDialog；否则 → LoginPhoneDialog（后半）
```

`picksSmsDialog()` 这一条判据是本轮唯一能从两个版本都逐行对上的：1.5.6 `LoginActivity.java:455/460` 与
1.6.6 `:575-578`/`:585-588` 完全同构。

## 三、短信弹窗（`LoginSmsDialog`，1.6.6 481 行）

| 事实 | 出处 |
|---|---|
| 号码长度**恰好 11**（`f64827i`）才放开"发送验证码"；11 且验证码**恰好 4**（`f64826h`）才放开"立即登录" | `LoginSmsDialog.java:440-442`（`b.afterTextChanged`） |
| 验证码凑满 4 位**当场自动提交**，按钮只是第二条路 | `:464-469`（`c.afterTextChanged`） |
| 提交前两侧文本都 `trim`（`kotlin.text.f0.E5`），发送额外再 trim 一次；layout `inputType=number` + `maxLength` 11/4 | `:172-173,254,462-463`，`dialog_login_sms.xml` |
| 删除叉：号码非空才 `VISIBLE`；点击是 `setText(null)`（清空）而不是删一个字符 | `:437-439`、`:243-247` |
| **倒计时期间号码框禁用 + 置灰 `appSecondary` + 删除叉 `INVISIBLE`**，跑完恢复 `appPrimary`/可用 | `I()`/`J()` `:261-278`，挂在 `tvSendCode.a0(onStart,onFinish)` |
| 发送成功：验证码 `setFocusable/…InTouchMode/requestFocus` + 倒计时起飞；失败：只在 `msg` 非空时 toast | `D()` `:184-198` |
| 登录成功顺序：`loginCallback()` → `isRegister` 分流（补资料 / 主屏）→ `CacheUtils.j2(6)` → 关弹窗 → host `finish()` | `E()` `:200-232` |
| 登录失败：只 toast `msg`，弹窗不关、页面不 finish | `:202-208` |
| 弹窗**不响应外部点击**（`isDismissOnTouchOutside` 是没人赋值的字段 ⇒ false） | `:319-321` |
| loading 是 `LoadingDialog(context, 0L)`，显示时禁返回键/禁外部点击，标签 `"LoginSmsLoading"` | `:160-166,292` |
| `dismiss` 时先停倒计时、收键盘、关 loading | `:307-316` |
| 键盘变化按 `imeHeight - statusBarHeight` 平移，且不小于 0 | `:390-392` |
| `onResume` 里 `postDelayed(100)` 再要输入法 | `:396-404` |

`lastLoginType` 手机号路径**恒为 6**（短信与一键都写 6），只有三方才写 4/5 —— 这两处分别写在
弹窗（`:224`）和 ViewModel（`LoginViewModel.java:98`），本轮按原样分放，测试各钉各的。

## 四、倒计时按钮（`view/SendCodeButton`）

`CountDownTimer(60_000, 1_000)`；tick 文案 `重新发送（%d）`、跑完 `重新发送`；计数中文字色
`appSecondary`，空闲 `appPrimary`；初始 `textColor` 是 `{state_checked: appPrimary, 默认: appSecondary}`
的状态列表。**两个容易漏的点**：`performClick()` 在计数期间直接 return（只靠 `enabled` 不够）；
`onDetachedFromWindow()` 会取消计时器，所以它**不跨配置变更存活**（原版弹窗 `dismiss` 还额外调 `Z()`）。

`Z()`（stop）只取消计时器、**不清 counting 标志**——原版如此，已写进测试：停完立刻再 start 仍被拒绝，
只有窗口真正跑完才允许起新的。

## 五、协议行（可点 span）与提醒弹窗

`V0(name,url)`：`我已阅读并同意 + 《隐私政策》 + 《用户协议》 +（有运营商条款时才加"和"）+《运营商名》`，
四类点击分别是：**首句 → 反选勾选框**（`Y0`，这就是"点文字也能同意"）、隐私政策 →
`CommonWebActivity.A`、用户协议 → `C`、运营商条款 → `n(url,name)`。链接色 `colorSpanClick` + 粗体，
首句用 `appPrimary` 不粗。原版用 `com.drake.spannable`，不是依赖，所以自写了一个等价 span helper
（`ext/ClickableSpans.kt`），只覆盖"把文本里某段字做成可点"这一件事。

`PolicyRemindDialog(context, 运营商名, url, 是否隐藏平台条款, onConfirm)`：确认 → 回调 + 关；取消 → 只关。
第 4 个布尔在 1.6.6 是真的存在的分支（`hidePlatformPolicies` 时句子只剩运营商条款），
`LoginActivity` 恒传 false。

## 六、顺手修掉的两条实现期错误（不是还原错误）

1. **`Dialog.getContext()` 不是 Activity**：带主题时 Android 会把它包成 `ContextThemeWrapper`。
   原版基类自己存了传入的 context，所以它的 `context as? Activity` 成立。我照抄这句时静默失效，
   于是"登录成功后关掉登录页"没发生。已把解包提成 `BindingDialog.hostActivity`，并被测试钉住。
2. **`KeyValueStore` 只有字符串接口**：`lastLoginType` 与 `isRequestedNotification` 在原版是 MMKV 的
   int/bool。用字符串读，老用户升级后就读不到自己的"上次登录"。已加 `int/boolean` 读写。

**数字**：`:app` 235 / 0（本卡 +38：屏 15 + 短信弹窗 12 + 倒计时按钮 6 + 写入路径 5），`:net` 29 / 0 不变，
合计 **264 全绿**；`assembleDebug` 通过，APK 61,848,174 B；本卡三份布局（`activity_login`、
`dialog_login_sms`、`dialog_policy_remind`）inflate ok，业务命名布局仍 **306/335**（无倒退，也无新增）。

## 七、验收（可复制执行）

```bash
bash tools/gradle.sh --offline :net:test :app:testDebugUnitTest :app:assembleDebug
# 期望：:net 29 / :app 235 → 合计 264 全绿（本卡 +38）

bash tools/gradle.sh --offline :app:testDebugUnitTest \
  --tests "com.youloft.watcher.pages.login.*" \
  --tests "com.youloft.watcher.view.SendCodeButtonTest" \
  --tests "com.youloft.watcher.data.UserManagerTest"
```

装机才能验的（我没做，也不谎报）：真机短信验证码到达与 60 秒观感、键盘跟随、协议 span 的可点区域、
微信/QQ 真实授权、一键登录（两个 jar 都拿不到）。见 DESIGN 第九节新增条目。

## 八、没做完（#18 后半）

1. `LoginPhoneDialog`：一键登录本体（typeId 1 送 `token+gyuId`；typeId 3 送 `token+opToken+operator`）；
2. `EmptyLoginActivity` + `PrivacyPolicyDialog`：首启隐私门（同意后初始化 SDK 并跳 `GuideActivity`）；
3. `ImproveUserInfoActivity`、`MainActivity`：两个跳转目标，本卡只留 `LoginNavigation` 记录；
4. 微信 code → `api.weixin.qq.com/sns/oauth2/access_token` → `/sns/userinfo` → `platform=4` 完整链；
5. `LoginEvents` 三个流的发布者（`wxapi/WXEntryActivity` 与 QQ 的 `IUiListener`）。

**另需你拍板**：`POST_NOTIFICATIONS` 现在是无条件"每账号问一次"（原版如此，且在 `onCreate`）。
上架审核对这条很敏感，要不要挪到首启隐私同意之后。
