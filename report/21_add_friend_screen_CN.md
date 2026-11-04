# LinkUp 第 21 号报告：#15 添加好友屏——四条找人路径闭环，顺带还原了通讯录搜索的封套协议

> 日期：2026-11-04 ｜ 承接 `report/20`

## 一、这一屏推翻了我自己定的一条规则的适用范围

前面几轮定的规则是「资源取 1.6.6，行为取 1.5.6」，理由是 1.6.6 被 R8 压扁、读不动。添加好友屏是个反例：

* 1.6.6 的 **ViewBinding 字段名全部保留**（`ActivityAddFriendBinding` 33 个字段逐个可读），于是那一屏的逻辑
  基本是逐行明文的；
* 而 1.6.6 的这屏**比 1.5.6 多一整个功能块**。

| 能力 | 1.5.6 | 1.6.6 |
|---|---|---|
| 搜索 | 点输入框 → 另开 `SearchFriendActivity` | **屏内搜索**：输入框 + TextWatcher 控制清空键/搜索键 + IME 搜索键 + focus 与键盘遮罩 + 直接消费搜索结果 |
| 结果通道 | 只用 `pre_confirm` | 还消费 `match_by_phone`，从 `SearchFriend.list` 现建一个 `Friend` |
| 申请成功提示 | 只在权限弹窗收起时 toast | 权限门不开时**立刻** toast（多一个 `else if` 分支） |
| 入口标签 | 19 个 source | 21 个（新增 20 实时截屏 / 21 隐私设置） |
| 分享 URL 里的 `av` | `1.5.6` | `1.6.6` |

所以这屏按 **1.6.6 的行为**重建，1.5.6 退成"给被压扁的方法名对号"的旁证。规则已改进 `recovered/DESIGN_CN.md`
第六节第 12 条。

## 二、三处 View 落差，逐一定性（不是一句"没搬"糊过去）

1.5.6 的 `M()` 碰 `llHuaweiTips` / `ivDownload` / `sclScan`，1.6.6 的 binding 里一个没有。

* `iv_download` + `ShareMatchCodeView`：**下载二维码卡片整条入口被删**。连带 `saveBitmap` / `p()` 这条
  toast 通道在本屏已无可触达调用点 → 没重建（原版 1.6.6 也留着那两个死方法，我不搬死代码）。
* `llHuaweiTips`：**不是删除，是换宿主**。1.5.6 把 `tv_tips` 包在一个默认隐藏的 LinearLayout 里；1.6.6 让
  页底那一条 `tv_tips` 自己显示。渠道判定式与三条文案分支**完全一致**（只是方法字母被重排 `i/k/g/f`→`i/l/g/f`）。
* `scl_scan` → `tvScanAdd`：扫一扫从整行卡片变成一个胶囊按钮。

## 三、匹配码：显示带空格、复制不带

```kotlin
binding.tvMatchCode.text = userId.toString().chunked(4).joinToString(" ")   // 1234 5678 90
platform.copy(userIdText)                                                    // 裸 id
```

原版点击回调传的是 `String.valueOf(user.getUserId())`，**不是屏上那串**。1.5.6 则是 `"匹配码:" + " " + userId`
（不分组）。两条都有测试钉住。另外 1.6.6 的 `tvNick` **不再填昵称**，用的是布局里写死的"我的匹配码"。

## 四、四条路径 × 两套来源编号

这屏最容易搞混的地方：原版同时维护**两个不同的数**。

| 路径 | 核对信息弹窗 `type` | 权限弹窗 `source` |
|---|---|---|
| 手输 8 位 → `pre_confirm` | 2 | 3 |
| 手输其他 → `match_by_phone` | 3 | 4 |
| 扫一扫 | 1 | 2 |
| H5（`source==7` 且 extra `match_code_from_h5`≠0） | 5 | 6 |
| 通讯录（由 `ContactInfoListActivity` 自己发） | 4 | 5 |

判定树（`f1()`）：输入非空才发；8 位当匹配码走 `pre_confirm`，其余走封套上传；`add_type` 埋点串同步取
"搜索匹配码"/"搜索手机号"。ViewModel 里还有一条**6 位也算码**的分支（`size==1 && (len==8||len==6)`），
而且原版**先封套、后分流** —— 6/8 位会白算一次 RSA+AES。原样保留，测试钉的是"8 位不会调 match_by_phone"。

扫码（`e1()`）：结果串长 8 → 直接当匹配码；否则解 `Uri.fragment` 里 `userid=` 到 `&`、必须纯数字；都不成 →
`invalid_qr_code`。两条成功路都把 `dialogSource` 置 2，且**先清空搜索串**（这决定 type 落 1 还是 2）。

## 五、通讯录封套协议（本轮最硬的一块，首次完整还原）

`net/.../ContactSearchEnvelope.kt`，五层：

1. `GET api/tool/rsa/public_key` → 剥 PEM。**结束标记是四个横杠** `----END PUBLIC KEY-----`（原版字面量就这么写）
   → 去所有空白 → Base64(NO_WRAP) 解 DER → X509 → RSA 公钥。
2. 内层 `{"phoneList":[…]}` **只做 Base64、不加密**，放进 `ciphertext` 字段。
3. 外层 `{"keyID":<我的 userId>,"ciphertext":…,"timestamp":<秒>}` 用**随机 16 字节**做 AES/CBC/PKCS7，
   **IV 就是同一串随机 key**。
4. 那 16 字节用 `RSA/ECB/OAEPWithSHA-256AndMGF1Padding` 加密。
5. `POST /api/relation/match_by_phone`，body `{"encrypted":<b64>,"keyEncrypted":<b64>}`。

**公钥拿不到时的约定**（这个不像正常设计，但原版就是这样）：不发请求、不报网络错，自己 post 一个
`status=10086` 的空壳响应 —— 8 位给 `Friend(sslCertificateError=true)`，否则
`SearchFriend(sslCertificateError=true)`；界面读到 10086 就**连"匹配码无效"都不弹**，只清空输入框放回光标。

测试抓到一个真 bug：Gson 默认把 `=` HTML 转义成 `\u003d`，**会毁掉内层 Base64**（原版用 org.json 不受影响），
必须 `disableHtmlEscaping()`。另外标准五横杠页脚按原版字面量剥会残留一个 `-` → Base64 解不出 → 读成"无公钥"。
服务端到底发哪种页脚**无法在本机判定**，已进待验第 26 条。

## 六、权限门换判据了：从远程配置改成硬编码渠道

同一个动作（加完好友后弹不弹权限设置），两版判据不同 —— 这顺手答掉了 `report/19` 里外部依赖的一半：

* 1.5.6：`ConfigUtils.n()` = 远程配置 `showPermissionChannel` 列表含本渠道，或含通配 `"-1"`。
* 1.6.6：**四个调用点**（`AddFriendActivity:409`、`ContactInfoListActivity:245`、
  `FriendRequestDetailActivity:174`、`FriendRequestListActivity:387`）全部改成 `utils.p.i()`，
  即 **渠道号 == `"3301"`**，与远程配置无关。

`askPermissionsAfterAdd` 因此改用 1.6.6 规则；1.5.6 规则保留成 `asksAfterAddFriendByConfig()` 并有测试——
那是真实历史行为，也解释了那个配置键当初是干什么的。渠道常量表（两版一致）：3801 走"定位轨迹互授权"文案 /
3301 走 `add_friend_bottom_tip` / 3300 与 3302 走另一条硬编码 / 其余渠道不显示提示。

**副作用要说明**：我们的包没有渠道段（走默认 `"0"`），所以现在 `askPermissionsAfterAdd` 恒 false。
要真机验这条，得先补 #17（签名块渠道段）。

## 七、核对信息弹窗顺带重建

两版逐行一致（1.5.6 284 行 / 1.6.6 290 行）。三条事实：

* 预选关系按**性别配对**：异性 → 恋人(1)，两个男生 → 挚友(2)，性别未知 → 其他(4)；并把对方性别画成
  `tv_name` 的右侧 compound drawable。
* 对方到上限时 `tv_confirm` **GONE**、换成会员角标 `iv_label_vip`，点它 → `ext.s.a(ctx, 16, "多个好友")`；
  监听器里还有一道 `isFriendLimit` 早退（视图已隐藏，原版仍防一手）。
* `onConfirm(relation, dismissParent)` 的第二参数是**给调用方关本弹窗用的**；本屏不用它。

## 八、代码清单

新增：`pages/friend/AddFriendActivity.kt`、`AddFriendViewModel.kt`、`AddFriendDialogs.kt`、
`AddFriendPlatform.kt`、`pages/friend/dialog/VerifyInfoDialog.kt`、`view/QrCodeRenderer.kt`、
`fastkit/.../utils/KeyboardUtils.kt`、`net/.../ContactSearchEnvelope.kt`；两个布局按惯例复制进 `:app`
（`activity_add_friend`、`dialog_verify_info`）；清单注册 Activity 并补 `<queries>`（Android 11+ 包可见性，
不写的话"装没装微信"永远返回假）。

改动：`FriendRepository` 补 4 条 relation 端点（`pre_confirm` / `apply` / `public_key` / `match_by_phone`）；
`FriendFlowNavigation.openAddFriend()` **从空实现换成真跳转**（申请列表 8、好友列表 6、空视图 0 三条线闭环），
并新增 `openContactList()` / `openQrScanner()` / `openVip()`；`FriendPermissionsSettingsDialog` 加
`onDismissed` 钩子（原版在同一弹窗上挂了两个收起回调，而我们的回报本身就是靠 dismiss 走的，所以给钩子
而不是让调用方自设 listener——那会把回报顶掉）。

## 九、数字

`:app` **140 tests / 0 failures**（本轮 +32 屏 +6 弹窗），`:net` **10 / 0**（+3 封套），合计 **150 全绿**。
APK `59,060,629 B`（≈59.1MB），4277 个条目，`AddFriendActivity`/`VerifyInfoDialog` 已进 dex、布局已进 res。
**注**：上一轮的 61.3MB 是增量构建产物，本轮 `--rerun-tasks` 全量重打稳定在 59.1MB，两次构建的 2.2MB 差我没去追。

业务布局 inflate **仍 306 / 335（91%）**，本轮没有倒退（`tools/summarize_inflate.py` 重跑核对：仍失败 29 个，
缺的自有 View 还是那 5 个类 —— ShotPreviewView / VipCard / SlideRecyclerView / FixWheelView / ProductsView）。
这两个布局本来就出自 1.6.6 银行、早已能 inflate，复制进 `:app` 只为接 ViewBinding，不改变这个数。

## 十、诚实清单：本轮**没有**重建的东西

1. **二维码绘制**：原版 `utils/z0.d(url, scale, size, margins, logo)` = `com.google.zxing` + 自绘模块
   （H 纠错、UTF-8、静区 0、圆角点阵、可选中心 logo，尺寸 115dp）。zxing 不在依赖里 →
   `QrCodeRenderer.Pending` 返回 null → **装包后 QR 卡片是空白的**，只留 `iv_code` 的位置。自成一张卡。
2. **LoadingDialog**（播 `loading.svga`）：`showLoading/hideLoading` 只有时序、没有画面。
3. **微信/QQ 分享本体**（`utils/h1`、`utils/i0` 缩略图上传、`utils/m`）：**装没装**用包查询等价复现了
   （原版的 `isWXAppInstalled/isQQInstalled` 本来就是包查询），分享调用是空实现。
4. **QR png 上传 H5**（走 `api/tool/uploadLog` + helper `p1`）：空实现。
5. **`ContactInfoListActivity` / `QRCodeScanActivity`**：只留跳转意图；扫码结果由 `onQrResult(raw)` 收，
   真 launcher 等那屏落地后接。
6. **埋点汇 `mf.b`**：21 条 source 标签与 `add_type`/`relationship`/`add_result` 事件形状由测试钉住，无处可发。
7. **同意后的 IM 侧效应**：`widget.im.e.w(userId,1)` 角标、`AgreeAddActivity` 拉起、会话提示气泡 —— IM 卡。
8. **权限库 XXPermissions 未接回**：用 androidx `RequestPermission` 复刻，"永久拒绝跳系统设置"改用
   `shouldShowRequestPermissionRationale` 判定；原版 `onGranted(allGranted=false)` 也会 toast，单权限
   contracts 没这个分支。两处等价替换都记进待验第 32 条。
9. **`:fastkit:test` 本来就跑不过**：单测资源合并引用 material 属性而 fastkit 不依赖 material。
   这是既有缺口、与本轮无关，我没顺手修。
