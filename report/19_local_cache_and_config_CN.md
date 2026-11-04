# LinkUp 第 19 号报告：#11 本地缓存与配置读数——读的那一半接上了，写的没接

> 日期：2026-11-04 ｜ 承接 `report/18`

## 一、这一轮解决的是"别再骗自己"

前三屏里 `isVip` / `cachedFriendCount` / `askPermissionsAfterAdd` 是三个写死在 `LinkUpApplication` 上的
默认值，屏能跑、测试能过，但装到真机上永远走同一条分支。这一轮把**读取**按原样接上，并且把
"那两个值到底从哪来"查到底——结论是其中一条根本不在我们自己的后端上。

## 二、存储地图（键与实例都是当场核出来的）

| 值 | 存在哪 | 键 |
|---|---|---|
| 账号记录 | `MMKV.defaultMMKV(MULTI_PROCESS_MODE, null)` | **`user2`**（Gson JSON） |
| 好友列表 | `MMKV.mmkvWithID(userId.toString(), MULTI_PROCESS_MODE, null)` | **`friendList`** |
| 当前用户 id | 就是 `user2` 里的 `userId`；per-user 实例的名字由它决定 | — |

规则照抄，不改：

```
isVip            = user.vipSubType > 0 || user.shareToMeList.any { it.vipSubType > 0 }
cachedFriendCount= 列表大小，缺缓存记 0        // 调用方自己 -1 去掉本机账号，也是原样
```

JSON 坏了或缺键 → 回落默认 `User()`，不抛（原版同样是 `?: 默认`）。

**为什么专门留一条测试钉键名**：`user2` / `friendList` / `showPermissionChannel` 这三个字符串写错时，
程序不会报错、测试也不会红——只会永远读到默认值。这类"静默默认值"是恢复工程最容易骗到人的形态，
`report/16` 记过 DTO 的同款坑，这里是它的镜像。

## 三、两个"值从哪来"，查到底的结论

1. **渠道号不在 MMKV、也不在 BuildConfig。** 原版 `hc.i/hc.d` 的做法是：**把自己的 APK 当 zip 打开**
   （`applicationInfo.sourceDir`），从 **APK 签名块里一段魔数 `1903654775` 的自定义 section** 读出 JSON，
   取其中的 `channel` 键；读不到时回默认 `"0"`。我们重建出来的 APK 现在**没有**这一段 → 走 `"0"`。
   要让它真对，得"打包时写入 + 安装后读出"配套做，属发布链那张卡（待验第 22 条）。
2. **`showPermissionChannel` 不来自我们的后端。** `ConfigUtils` 全部走三方远程配置 SDK
   （`of.b.f("android-watcher", "156")`，段名 `Parameter_Map`，fastjson 解析）。
   我拿仓库里存的生产实时回包样本核过：我们自己的 `clientConfig` 里**既没有 `Parameter_Map`
   也没有 `showPermissionChannel`** ⇒ 这条不能靠自家路由凑数，只能等 SDK 接回（待验第 23 条）。
   规则本身已按原样实现并可测：`entries.any { it == 当前渠道 } || entries.any { it == "-1" }`，
   其中 `"-1"` 是原版写死的通配值（`p.b()`）。

## 四、诚实的落点：现在装包还是 false / 0 / false

读取接通了，但**写入方还没重建**：登录流没写 `user2`，IM 好友缓存没写 `friendList`，
配置 SDK 没接、渠道段没写。所以今天装上新包，这三个值依旧是 `false / 0 / false`——
**区别在于这不再是代码写死的**，一旦上游接上就自动生效。这一句要写在报告里，
免得有人看到"缓存层已重建"就以为配额弹窗能弹出来了。

还有一段**故意没搬**：原版在 `user2` 读不到时，会再回读一个**旧的 Parcelable blob**（很早期版本的升级路径）。
我们的 DTO 不是 Parcelable，这段没接，后果也写明白：那批老用户装新包会显示成未登录（待验第 20 条）。

## 五、数字与验证

```
gradle :net:test                    7 / 0
gradle :app:testDebugUnitTest      92 / 0
      ├ 本地缓存 + 配置 9（新增）
      ├ 弹窗 + 选择器 14、好友信息 19、我的好友 15、申请列表 18、申请详情 14
      └ 原有布局回归 3
gradle :app:assembleDebug          通过（MMKV 2.2.2 从公开仓库解析成功）
python tools/summarize_inflate.py  业务命名布局 306 / 335（91%）——持平
```

新依赖只有一个：`com.tencent:mmkv:2.2.2`。APK 里 MMKV 的 `BuildConfig` 只留下 `FLAVOR = "DefaultCpp"`，
**没有版本字符串**，所以按公开最新版接——和 `report/14` 里 BRVAH 的处理一样，进待验清单第 21 条：
真机若出现"读不到旧数据"或"多进程读写不一致"，先怀疑这里。
测试全部走注入的内存实现，不碰 native 库。

## 六、下一轮

好友流的屏与接缝基本通了，剩两个入口屏：**#15 `AddFriendActivity`**（也是渠道号/远程配置最早的消费者之一），
以及会话与地图那批屏。若要往"真机可验收"推进，下一轮最省力的是先接**登录流写入 `user2`**，
那样 `isVip` 与配额弹窗当场就能在真机上验。
