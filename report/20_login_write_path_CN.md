# LinkUp 第 20 号报告：#16 登录写路径接管——`user2` 终于有地方写了

> 日期：2026-11-04 ｜ 承接 `report/19`

## 一、这一轮补的是上一轮留下的那句难听话

`report/19` 末尾我写了："现在装包这三个读数仍是 false / 0 / false"。原因是缓存只有读、没有写。
这一轮把写的一半接上，并且把"token 到底从哪来"这种容易想当然的事查到了行号。

## 二、原版写入点（当场核出来的，不是推测）

| 动作 | 实现 | 关键点 |
|---|---|---|
| 存账号 | `CacheUtils.U2(User)` → `defaultMMKV.encode("user2", Gson().toJson(user))` | 与 #11 的读侧完全对齐：默认实例 + 键 `user2` |
| 存 token | `CacheUtils.P2(String)` → `encode("token", value)` | **token 藏在 `User.token` 里**（`z0.g()` 调 `P2(user.getToken())`），不是独立的登录响应字段 |
| 登录收尾 `z0.g(user, isNewUser)` | 按 `nickname 空 / isRegister` 分流 → 落 token → IM 登录 → 埋点 sign-in | 先落身份，再连 IM |
| 刷新（`s2` 里那段） | `api/user/info` → 成功且 data 非空 → **先比 `cache.isVip() != user.isVip()`（或强制位）做副作用 → 再写缓存 → 最后 `postValue`** | 顺序不能换：写完就拿不到旧 VIP 值了 |
| 退出 | `P2("")` + 用同一个键覆盖一个**默认空账号** | **不是删键**，所以 `user2` 一旦出现过就一直在 |

## 三、代码上落了什么

* `KeyValueStore` 补 `putString`（之前只读）；`UserCache` 补 `save / saveToken / token`。
* `UserRepository.userInfo()`（`GET api/user/info`，路由早已在 `:net`）+ `UserManager`
  （`store / refresh / signOut` + 一个 `LiveData<User>`），对应原版 `manager/s2` 与 `manager/z0` 的这两块职责。
* `AndroidDeviceContext` 的 `authToken() / userId / mainUser` 改读**同一份缓存**：
  从此有账号之后，每个请求的 `Authorization` 和 11 个公共参数用的是本机真实身份，
  不再是"探针一套、缓存一套"的平行存储。
* **`channel` 我故意没动**：它的真值在 APK 签名块里（`report/19` 第三节），没接回之前改它
  等于凭空猜一个签名输入参数——那会污染所有请求的签名，比留着本地覆盖更糟。
* `AccountSideEffects.onVipStateChanged`：条件（VIP 变化或强制位）已实现且有测试钉住；
  四个具体副作用（IM 会话刷新、桌面 widget、掉 VIP 时地图模式复位 + 关权限提醒 + 总线广播）没有实现方。

## 四、真机怎么验（我不碰短信接口的前提下）

探针屏（`RecoveryProbeActivity`）加了一段：调 `GET api/user/info` 之后打印
`cached userId / mainUser / isVip / tokenStored`。
这样"写路径通了"这件事在真机上是**可看**的，而且不需要我去调 `/api/sms/send`（那会发真短信，我从头到尾不碰）。

**但要说清还剩什么没做**：短信/一键登录那几屏没重建——`pages/login/LoginActivity` 与 `manager/z0`（1969 行）
还牵着号码认证 SDK（`GYManager.preLogin/ePreLogin`）、短信接口、个推 bindAlias、Umeng sign-in。
所以今天真机上要让 `user2` 真的有值，只有两条路：等登录屏，或者先用 `adb` 往 MMKV 里灌一个有效 token 再用探针屏验。
这条已记进待验第 25 条，第 26 条记的是那四个副作用没有实现方。

## 五、数字

```
gradle :net:test                     7 / 0
gradle :app:testDebugUnitTest      101 / 0
      ├ 账号写路径 UserManagerTest 9（新增）
      ├ 本地缓存 LocalCacheTest 9、弹窗+选择器 14
      ├ 好友信息 19、我的好友 15、申请列表 18、申请详情 14
      └ 原有布局回归 3
gradle :app:assembleDebug           通过；APK 60.6MB → 61.3MB（MMKV 带进来的 native 库，不是代码量）
python tools/summarize_inflate.py   业务命名布局 306 / 335（91%）——持平
```

`UserManagerTest` 里有三条专门防止"以后有人图省事改顺序"：
**先比 VIP 再写缓存**、**data 为空不写**、**失败不写**；还有一条钉住"退出是覆盖空账号而不是删键"。
键名 `user2` / `token` 也各有一条断言——这类字符串写错不会报错，只会永远读到默认值（与 #11 同一课）。
