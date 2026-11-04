# LinkUp 第 23 号报告：#20 前半——通讯录匹配屏，顺带用真解密把上轮的封套协议复验了一遍

> 日期：2026-11-04 ｜ 承接 `report/22`

## 一、少见的干净情况：这屏两版**逐行一致**

`ContactInfoListActivity` 在 1.5.6（333 行）与 1.6.6（332 行）之间只有一处行为差异——**权限门换判据**
（`report/21` §六那条：远程配置 `showPermissionChannel` → 硬编码"渠道号==3301"）。其余观察者、文案、
顺序、字段全同。所以这屏不用做"资源 1.6.6 / 行为 1.5.6"的取舍讨论。

它是 #15 留的两条空跳转里的第一条：`openContactList()` 现在是真 `startActivity`，
添加好友屏点"从通讯录添加"→ 授权 → **真进屏**。

## 二、它复用 `AddFriendViewModel`，而且列表不是通讯录

原版就把这屏挂在同一个 VM 上（`ViewModelLazy(AddFriendViewModel::class)`），三个通道全用现成的：
`search` 出列表、`preConfirm` 查人、`apply` 收申请结果。

一句容易读错的话：**屏上显示的不是通讯录，而是"通讯录里那些已经注册了 LinkUp 的人"**。
本机号码只负责被上传匹配。

## 三、读取器（`datasource/c`）逐条照搬

- 投影 `_id, display_name, has_phone_number`
- 选择 `display_name NOT LIKE '%@%'`（把"邮箱写在显示名里"的那批排掉——运营商同步会造出这种行）
- 排序 `display_name COLLATE NOCASE`
- 每个联系人：先查 Email 取**第一行** `data1`；**只有 `has_phone_number > 0`** 才查 Phone 取第一行 ——
  一人只取一个号码，原版从不往下走第二行
- 收录条件：`(邮箱非空 且 匹配 EMAIL_ADDRESS 且 邮箱 ≠ 显示名(忽略大小写)) 或 号码非空`

## 四、清洗链条上那条"脏"事实，我没有顺手修

VM 把号码清洗成 `Regex("(\+\d{1,3}\s*)|(\s+)").replace(raw, "").trim()`，再 `distinct()`。
关键在于：**只有邮箱、没有号码的联系人不会消失**，它会变成一个**空字符串**留在列表里，
`distinct()` 只去掉多余的 `""` 而保留一个。也就是说原版真会发出：

```json
{"phoneList":["13800138000",""]}
```

我照搬并钉住，没有"优化"掉。证据方式是本卡最硬的一条：测试里造一对真实 RSA 密钥，让屏幕走完整流程，
然后把**上传的封套解回明文**——`keyEncrypted` 用私钥 RSA-OAEP 解开得到那 16 字节随机 key，
`encrypted` 用它做 AES/CBC 解回 `{keyID,ciphertext,timestamp}`，`ciphertext` 再 Base64 解出 `phoneList`：

```
assertEquals(listOf("13800138000", ""), phonesInTheEnvelope(encrypted, keyEncrypted, pair.private))
```

一条断言同时验了三件事：`+86 `/内部空格被剥、两个写法的同一号码折叠、空串按原版保留。
顺带端到端复验了 `report/21` §五那套封套协议（加密层第一次被真解开，而不是只验长度非空）。

**要不要保留这个空串是产品/后端决定**，不是逆向能替他们判的，已进待验。

## 五、与添加好友屏不同的两处顺序（各一条测试钉住）

| | 添加好友屏 | 通讯录屏 |
|---|---|---|
| 申请成功提示 | 权限门开着时由**弹窗收起回调**提示 | **先 toast**，再开权限弹窗 |
| 权限弹窗出现条件 | 成功就开 | **只在 `applyStatus != 1`** 分支开 |
| 权限弹窗 source | 2/3/4/6 按来路 | **固定 5**（手机通讯录） |
| 核对弹窗 type | 1/2/3/5 | **固定 4**（手机通讯录） |

## 六、行的渲染细节（一处是"两屏本来就不一样"）

- `tv_match_code` = `getString(add_friend_match_code) + userId` —— **标签和 id 之间没有空格**，屏上是
  "匹配码:900"。而添加好友屏 1.6.6 那行根本**不带标签**，只显示每四位分组的 id（"1234 5678 90"），
  复制出去的又是没有空格的裸 id。三种写法各不相同，是**原版如此**，不是我漏了格式化。
- 性别按**字符串**判：`"0"` → 无图标、`"1"` → 男、其他 → 女。
- 显示名沿用 `getName()`：**备注优先于昵称**。
- 分隔线只在**最后一行**隐藏；整行（item 根视图）点击触发查询。

## 七、抽了一个窄接口：`LoadingOverlay`

原版 `onCreate` **先亮遮罩再读通讯录**（跨进程读通讯录可能几秒不起）。#15 的 `AddFriendPlatform` 里那对
`showLoading/hideLoading` 对这屏来说太重（它还挂着剪贴板/键盘/分享），所以抽出
`interface LoadingOverlay`，`AddFriendPlatform : LoadingOverlay`，实现是 #19 那个每屏一个实例的
`ActivityLoadingOverlay`。本屏只依赖窄接口，测试里换一个记录调用的假实现就够了。

## 八、数字

新增 **24 条测试**（屏 18 + 读取器/清洗 6，另在添加好友屏加 1 条"跳的是真屏"）：
`:app` **177 tests / 0 failures**、`:net` **10 / 0**，合计 **187 全绿**。`assembleDebug` 通过，
APK 字节数与上轮相同（61,848,174 B ≈ 59.0 MiB，新增类被 dex 填充吸收了，已核三个新类确实在包里、
两张布局也进了 res）。业务布局 inflate **仍 306/335**，无倒退。

清单加了本屏条目，以及 `READ_CONTACTS`——**这条权限 1.6.6 清单里本来就有**（已核 `_raw/manifest_166.xml`），
不是我替它补的。

## 九、本卡没做的（别误会）

1. **真机上那段游标遍历**：子句照搬且有单测，但本机没有可注入的 `ContentResolver` 假提供者，
   "一人只取第一个号码"这类行为只能上真机看（待验第 36 条）。
2. **扫码屏 `QRCodeScanActivity`**：#20 的后半（相机 + zxing 解码侧），本轮未动。
3. **空串号码的去留**：行为照搬，判定留给产品/后端。
4. 老几样不变：埋点汇 `mf.b`、同意后 IM 侧效应、`AgreeAddActivity`、隐私两阶段回灌、
   微信/QQ 分享本体、渠道号（仍等 #17 与你的拍板）。
