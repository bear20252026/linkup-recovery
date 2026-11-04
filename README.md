# LinkUp 源码恢复工作区（公司授权）

本仓库用于 LinkUp（包名 com.youloft.watcher）客户端源码丢失后的恢复重建工作。
**版权声明：LinkUp 客户端版权归原版权方所有，本仓库内容仅供该公司内部源码恢复使用，禁止任何商用、转载与再分发。**

## 内容
| 文件 | 说明 |
|---|---|
| apk156.part_aa/ab | LinkUp 1.5.6 APK 分块（cat 拼合） |
| apk166.part_aa/ab | LinkUp 1.6.6 APK 分块 |
| jadx-1.5.6.zip | 反编译工具（跨平台） |
| apktool_3.0.3.jar | 资源还原工具 |
| run_all.sh | Mac/Linux 一键脚本（下载+拼合+校验+反编译+打包） |
| report/ | 项目情况报告 / 可行性报告 / 操作指南 |
| notes/ | 公开逆向参考资料 |

## 校验值（MD5）
- 1.5.6: `8d8e19b9f7435e2f5b33355c9cc897d4`
- 1.6.6: `5ddd548a8b01b3b85fa1f9153c75d393`

## Mac mini 上一键执行
```
git clone https://github.com/bear20252026/linkup-recovery.git
cd linkup-recovery
sh run_all.sh
```
前提：已装 git 和 Java 17（`brew install --cask temurin@17`；脚本会自动检查并提示）。
产物 `linkup_decompiled.zip` 生成后发回手机继续分析。

## 2026-11-02 更新：重建工程已进仓库

反编译与协议验证全部改到本机 Windows 完成（JDK21 + Android SDK + jadx + apktool + Gradle 都在本地），不再依赖 Mac mini。

- 新增 `rebuild/`：已实机验证的网络层（`net/`，签名请求在 linkup-test 上拿到 `status=200`）、Android 壳（`app/`，本机能出 17.9MB debug APK）、还原出的 97 条路由契约（`recovered/`）
- 新增 `report/05_local_rebuild_and_backend_CN.md`：本轮结论、后端归属调查、待验清单
- 修正两处前面报告的事实：拦截器只对 `api.weixin.qq.com` 放行（不是所有第三方域名）；1.6.6 的 936 个布局里 DataBinding `<layout>` 根标签为 0 个

跑法：

```bash
cd rebuild && sh tools/gradle.sh :net:test        # 5 个离线回归，锁住签名协议
cd rebuild && sh tools/gradle.sh :net:liveVerify  # 对真实测试服发一条签名请求
```

## 2026-11-02 更正（重要）

`report/05` 第六节推测"后端可能属对面公司"——**错的，我方就是万年历/重庆可兰达本体**。
更关键的是：**生产业务 API 活在 `link.tttick.com`，后端不需要重写**，重建客户端把 baseUrl 指过去即可
（`gradle :net:liveVerify --args=https://link.tttick.com/` 已实测 200）。详见 `report/06_backend_alive_and_ownership_CN.md`。

## 2026-11-02 再更新：布局与文案已整体迁入

新增 `rebuild/res166/`：1.6.6 的 3982 个资源文件（936 布局、2169 条文案），`:app` 依赖它后可直接引用。
`gradle :app:assembleDebug` 产出 50.6MB APK（937 布局入包、2272 条 string）。
坑与约束见 `report/07_resource_migration_CN.md`。注：该 APK 能否正常启动仍需真机验（本机无设备）。

## 2026-11-02 再更新：API 面已强类型

`tools/gen_beans.py` 生成 79 个 data class，96/97 条路由有类型响应；两个 APK 都没保留 `@SerializedName`，
说明线上 JSON key 就是字段名，并已用生产实时回包验证。测试 7 个全绿。
`liveVerify` 修掉一个假绿隐患（旧版探测失败也返回成功）。详见 `report/08_typed_models_CN.md`。

## 2026-11-02 再更新：AAR 接回 + 界面在 JVM 上真跑通

`res166` 完成库自有资源剥离（依据各 AAR 真实清单，非前缀猜测；attr 重复大多藏在 styleable 子节点里），
`:app` 接回 appcompat/material/constraintlayout 等。新增 Robolectric 测试真 inflate 还原布局，
全套 9 tests / 0 failures，APK 57.9MB。另发现内部组件库 `com.mc.fastkit`（545 处引用）也不在公开仓，
需从 APK 抽回。详见 `report/09_aar_strip_and_ui_runs_CN.md`。

## 2026-11-02 再更新：内部组件库 :fastkit 已重建，UI 可跑面量化完成

`com.mc.fastkit`（545 处引用、公开仓没有）按 1.5.6 反编译产物重建为 `:fastkit`，覆盖布局中全部 14 个标签。
Robolectric 逐个 inflate 全部 829 个布局的结果：**业务命名布局 335 个里 260 个今天能跑（77%）**；
425 个失败中 276 个属广告 SDK 自带 UI、43 个才是我方自有 View（25 个类，已列清单可当排期）。
详见 `report/10_fastkit_and_inflate_survey_CN.md`。10 tests / 0 failures，APK 57.9MB。

## 2026-11-03 再更新：第一屏逐屏重建跑通（好友申请列表）

分页状态机、行渲染三态、同意键的四条前置闸门与 500ms 去抖，全部按 1.5.6 可读源逐条还原并写成出处对照表；
`:app` 单测 20 条（这一屏 17 条）全绿，含真实视图点击到网络层的整链路，APK 60.6MB，业务布局可 inflate 仍 306/335。
顺带纠两处地基错：ViewBinding 只能开在 `:app`（`:res166` 里厂商 View 不在 classpath，codegen 必挂）、
APK 用的 BRVAH 是 `adapter4`（4.x）而不是 3.0.10。详见 `report/14_first_screen_vertical_slice_CN.md`。

## 2026-11-03 再更新：第二屏跑通，列表→详情第一次是真跳转

好友申请详情按 1.5.6 还原（整屏只有"同意"键、三条前置闸门、500ms 间隔点击、非 0 态禁用改文案），
列表屏的跳转目标从空实现换成真 `startActivity`，并由测试断言 bean 在 Intent 里存活。
`:app` 35 tests / 0 failures，APK 内实测含该 Activity 与清单条目。
顺带定死一条影响每一屏的架构问题：DTO 在纯 JVM 模块里拿不到 Parcelable，
改由 `gen_beans.py` 给字段图干净的 61/79 个 bean 加 `java.io.Serializable` 负责跨屏传递。
详见 `report/15_detail_screen_CN.md`。

## 2026-11-03 再更新：第三屏「我的好友」跑通，并挖出两处静默的 DTO 缺陷

这一屏没有 ViewModel、没有分页、不发 HTTP——它订阅的是 IM 维护的好友列表与变更命令，
所以重建把缺的**数据源接口**定形（`FriendListSource`）而不是塞个假数据把屏糊过去。
还原要点：空列表屏自己 finish()、`userId<=0` 先过滤、主账号插最前、加友入口三种 mode、
命令 type∉{1,100} 才处理且先置 null 消费。

顺带两处**能编译、测试也可能过、只有打线上才露馅**的生成器缺陷：嵌套 bean 被摊平
（`FriendList.Info` 在重建里压根不存在）与 jadx 改名污染 JSON key（11 处 `id`/`rh` 永远解析不出来）。
现在按花括号范围分字段、从 `renamed from:` 注释取回真名：9 个嵌套 bean 恢复。

`:app` 49 tests / 0 failures（好友流三屏 46 条），`:net` 7 / 0，APK 内实测含 MyFriendActivity。详见 `report/16`。

## 2026-11-03 再更新：第四屏「好友信息」跑通，四个写动作里三个已是真端点

资料/备注/关系/权限摘要/聊天/删除 + 一条 IM 推送覆盖层。端点是按调用点解出来的（1.5.6 连 Retrofit
注解都被混淆成 `@o/@f/@t`）：`relation/info?queryId`、`relation/del{friendId}`、
`relation/update{friendId,relation}`、`relation/update_remark{friendId,remark}` 已接并已测；
权限更新是"先 POST friend_sens，失败再逐类型回灌"的两阶段流程，**有意没有半接线**。

还原要点里最容易写错的三条：加载失败或 data 为空要退回"非好友"版面（用户名与匹配码改用 Intent 里的值）；
权限摘要就是数 9 个 sens 开关的 true 个数；改关系/改备注的成功响应 data 是客户端回显自己发的值。
仓储层并回原版的单一 `FriendRepository`。两处偏离原版都有测试钉住：不还原 `parseInt` 的崩溃、
不假装那两条硬编码中文 toast 有资源。

`:app` 83 tests / 0 failures（好友流四屏合计 66 条），`:net` 7 / 0，APK 内实测含 FriendInfoActivity。
详见 `report/17_friend_info_screen_CN.md`。

## 2026-11-03 再更新：共用弹窗层落地，六个动作解绑（窗口库是真·子集）

删除确认 / 改关系 / 改备注 / 改权限 / 配额提示 ×2 当场可点；`FriendInfoDialogs` 接口保留当测试口子、新增 `RealFriendInfoDialogs` 作线上实现；`FriendInfoActivity` 新增两条**生产路径**测试（点删除 → 真 ConfirmDialog 标题 → 请求 + finish；点权限行 → 真弹窗的 ✕ 按原版传 false 即 GONE）。

必须记住的限制：原版 `XDialog` 有 **2013 行**（宿主 Lifecycle、键盘跟随、动画集、状态栏、~30 个链式 setter），
本轮只搬了这五个弹窗真正用到的那一层（反射 inflate ViewBinding + 拒绝重复弹出的守卫），
**别把「五个弹窗可用」读成「组件库可用」**；权限弹窗的"非 null 分支"故意没半接线（两阶段逐类型回灌属隐私权限卡）。

`:app` 83 tests / 0 failures（弹窗 + 选择器 14 条新增），`:net` 7 / 0，APK 实测含四个新类与 5 个活动条目。详见 `report/18_dialog_layer_CN.md`。

## 2026-11-04 再更新：#11 本地缓存与配置读数——读的那一半接上了

前三屏留的三个假默认值不再是写死：`isVip` 从 MMKV 默认实例的 `user2`（规则 `vipSubType>0` 或
`shareToMeList` 任一 >0）、好友数从"以 userId 命名"的实例里的 `friendList`、权限开关走原版那条
"渠道号命中列表或含通配 -1"的规则。键名有 9 条测试专门钉住——**键写错不会报错，只会永远读成默认值**。

两处"值从哪来"当场查清：渠道号是原版把**自己的 APK 当 zip 打开**、从签名块里魔数 `1903654775` 的自定义
section 读出来的；`showPermissionChannel` 走**三方配置 SDK**（`of.b.f("android-watcher","156")`），
不是我们自己的 `clientConfig`（用生产回包样本核过，那里面没这个键）。两条都留成可注入接缝。

诚实的结论：写入方（登录流、IM 好友缓存）与那两个来源还没接，所以**现在装包这三个读数仍是 false/0/false**
——但不再是因为代码写死。MMKV 版本 APK 内取不出，按公开 2.2.2 接（已进待验第 21 条）。
`:app` 92 tests / 0 failures（合计 99），详见 `report/19_local_cache_and_config_CN.md`。

## 2026-11-04 再更新：#16 登录写路径接管——`user2` 终于有地方写了

上一轮我说"装包三个读数仍是 false/0/false，因为没人写"。这轮补写：`KeyValueStore.putString`、
`UserCache.save/saveToken`（键 `user2` / `token`，默认实例）、`UserRepository.userInfo()` +
`UserManager(store/refresh/signOut)`。原版的三条关键事实照做：**token 藏在 `User.token` 里**、
刷新时**先比 VIP 变化再写缓存**（写完就拿不到旧值）、**退出是覆盖空账号而不是删键**。
`AndroidDeviceContext` 的 token/userId/mainUser 改读同一份缓存，不再是平行存储；
`channel` 故意没动（真值在 APK 签名块里，没接回前改它等于猜签名输入）。

还剩什么：短信/一键登录屏没重建（号码认证 SDK + `/api/sms/send`，后者我不碰），所以真机今天要么等登录屏、
要么先 `adb` 灌 token；探针屏已加 `GET api/user/info` → 打印 cached userId/mainUser/isVip/tokenStored 这条可验路径。
`:app` 101 tests / 0 failures（合计 108），APK 60.6→61.3MB（MMKV native 库所致）。详见 `report/20`。

## 2026-11-04 再更新：#15 添加好友屏——四条找人路径闭环，顺带还原了通讯录封套协议

这屏是好友流程的**入口**，也是第一屏出现「不能照 1.5.6 重建」的情况：1.6.6 的 ViewBinding 字段名全部活着，
于是行为可读，而且 1.6.6 **比 1.5.6 多一整个屏内搜索链路**（输入框 + 清空键/搜索键 + IME 搜索 + focus 与键盘遮罩
+ 直接消费 `match_by_phone`）。规则已改成「1.6.6 binding 存在就以 1.6.6 行为为准」，写进 DESIGN 第六节第 12 条。

三处 View 落差逐一定性，不是一句「没搬」：`iv_download`＋`ShareMatchCodeView` 确被删除（下载二维码整条入口）；
`llHuaweiTips` 是**换宿主**到页底 `tv_tips`（渠道判据与三条文案分支完全一致）；`sclScan` 变成 `tvScanAdd`。

硬货是**通讯录搜索的封套协议**（首次完整还原并测试）：内层 `{"phoneList":[…]}` 只做 Base64 放进 `ciphertext`、
外层 `{keyID,ciphertext,timestamp}` 用随机 16 字节 AES/CBC/PKCS7 且 **IV 就是同一串 key**、key 用
`RSA/ECB/OAEPWithSHA-256AndMGF1Padding` 包，PEM 结束标记是**四个横杠**；公钥拿不到时不发请求、不报网络错，
自己 post 一个 `10086` 空壳，界面连「匹配码无效」都不弹、只清空输入框。测试顺手抓到一个真 bug：Gson 默认把 `=`
转义成 `\u003d` 会毁掉内层 Base64，必须 `disableHtmlEscaping()`（原版用 org.json 不受影响）。

另一个外部依赖当场解掉一半：加完好友弹不弹权限设置，1.5.6 读远程配置 `showPermissionChannel`（含 `-1` 通配），
**1.6.6 四个调用点全改成「渠道号==3301」硬编码**。我们的包没有渠道段，所以这条现在恒 false —— 要真机验得先做 #17。

`:app` 140 tests / 0 failures（本轮 +32 屏 +6 弹窗）、`:net` 10 / 0（+3 封套），合计 **150 全绿**；APK 59.1MB，
新类与新布局已进包。业务布局 inflate 仍 **306/335**（复制布局进 `:app` 只为接 ViewBinding，不动这个数）。
**没重建的**：zxing 二维码绘制（`QrCodeRenderer.Pending` → 装包后 QR 卡片是空白的）、LoadingDialog 画面、
微信/QQ 分享本体、QR png 上传、`ContactInfoListActivity`/`QRCodeScanActivity`、埋点汇、同意后 IM 侧效应，
以及 XXPermissions（用 androidx contracts 等价复刻，两处差异已记待验）。详见 `report/21`。

## 2026-11-04 再更新：#19 二维码绘制与加载遮罩——顺手改掉一条我发布出去的错话

上一轮我在 `report/21` 的"没重建清单"里写绘制器是「H 纠错、UTF-8、圆角点阵、可选中心 logo」。这轮把
`utils/z0.java`（328 行）逐行读完，**四条里错了三条**：实际是 **纠错 Q**（H 属另一条简易生成器）、字符集
**小写 `"utf-8"`**（值还取自个推常量类）、**正方形模块**（填充系数 1.0，不是圆点）、定位眼是**环形**
（点半径 1.5 模块 + 环半径 3 模块、线宽 1 模块），而 1.6.6 **恒传 logo=null**。错话已同时更正
`report/21` 与 `DESIGN_CN`。教训很具体：只读了调用点、没读被调用体，就把参数当已知写进了发布件。

接了 `com.google.zxing:core:3.5.3`，把绘制器拆成 **`plan()` 纯数据版面 + `draw()` 照版面刷 Canvas**。
拆开的理由不是洁癖而是本机测不了像素：**Robolectric 光栅化不可信**——探针画 6×6 红方块，`getPixels`
读回中心是白、全场只有 24 个红点；而同一张码用 `int[]` 直接喂 `RGBLuminanceSource` 则秒解。于是改成
"版面算术逐条断言 + 在测试里把版面重栅格化成 int[] 交给真 zxing 解码"。

顺带证明了一件有价值的事：**原版的环形定位眼真的可扫**——环、间隙、中心点在扫描线上正好给出 finder
判据要的 1:1:3:1:1。另外两条进了测试：那条 URL 是版本 7 = 45×45 模块、288px 下模块 6px 且自带约 1.5 模块
内边距；`iv_code` 背景全透明，**白卡片 `scl_code` 本身就是静区的一部分**（140dp 里放 130dp 不是随手写的）。

LoadingDialog 三条事实照搬：窗口 **`FLAG_NOT_FOCUSABLE`**（原版 `setFlags(8,8)`，遮罩不抢输入法焦点）、
show 起动画 / dismiss 暂停（播 `assets/loading.svga`）、**最短显示时间**推迟立即收起——默认 250ms，
但 `BaseFrameActivity.showLoading()` 用 `0L` 构造，所以好友屏这条下限实际是关的（规则仍照搬，别的调用点用得到）。

`:app` 153 tests / 0 failures（本卡 +13）、`:net` 10 / 0，合计 **163 全绿**；APK 61.8MB（上轮 59.06MB），
已核 `MatchCodeQrPainter`、`LoadingDialog`、`zxing Encoder`、`dialog_loading`、`assets/loading.svga` 都在包里。
业务布局 inflate 仍 **306/335**，无倒退。又踩回一个老坑：**`gradle :app:dependencies` 只解析 POM**，
zxing 的 jar 得靠 `:app:fetchDebugArtifacts` 才真下载。

**还没做**：真人拿手机扫这块屏（本机只证明版面能被 zxing 读）、扫码屏 `QRCodeScanActivity` 的解码侧（属 #20）、
1.5.6 的头像嵌码合图（1.6.6 无调用点）、SVGA 观感、微信/QQ 分享本体、QR png 上传 H5、埋点汇、同意后 IM 侧效应。
详见 `report/22`。

## 2026-11-04 再更新：#20 前半——通讯录匹配屏，并用真解密把上轮的封套协议复验了一遍

`ContactInfoListActivity` 是"从通讯录添加"的落地屏，也是 `report/21` 留的第一条空跳转：现在点那一行 →
授权 → **真进屏**。少见的干净情况：这屏 1.5.6 与 1.6.6 **逐行一致**，只差权限门判据那一处。
它复用 `AddFriendViewModel` 的三个通道；**屏上显示的不是通讯录，而是"通讯录里已注册 LinkUp 的人"**。

读取器（`datasource/c`）子句逐条照搬：`display_name NOT LIKE '%@%'`、`COLLATE NOCASE`、
**一人只取第一个号码**、收录条件"邮箱是合法地址且≠显示名 或 有号码"。

最有价值的一条是清洗链上那个**脏事实**：只有邮箱没号码的联系人不会消失，它会变成一个**空字符串**进列表，
`distinct()` 只留一个 —— 原版真会发 `{"phoneList":["13800138000",""]}`。我照搬并钉住，钉的方式是
**测试里造真实 RSA 密钥对，把上传的封套解回明文**再断言这个数组：一条断言同时验了 `+86 `/内部空格被剥、
同号码折叠、空串保留，也是 `report/21` §五那套封套协议**第一次被真解开**。要不要去掉空串是产品/后端的事，
已进待验。

两处与添加好友屏不同的顺序各有一条测试钉住：本屏**先 toast 再开权限弹窗**，且弹窗只在 `applyStatus != 1`
分支出现（source 固定 5、核对弹窗 type 固定 4）。行的文案也是"原版如此"：`匹配码:900` **不带空格**，
而添加好友屏只显示分组后的 id。另外抽出窄接口 `LoadingOverlay`（`AddFriendPlatform` 继承它），
因为原版是**先亮遮罩再读通讯录**。

`:app` 177 tests / 0 failures（本卡 +24）、`:net` 10 / 0，合计 **187 全绿**；APK 61,848,174 B，
已核三个新类与两张布局都在包里；业务布局 inflate 仍 **306/335** 无倒退。清单加了本屏条目与
`READ_CONTACTS`——**1.6.6 清单里本来就有这条**，已核，不是我补的。

**没做的**：真机那段游标遍历（本机没有可注入的 ContentResolver 假提供者，待验第 36 条）、
扫码屏 `QRCodeScanActivity`（#20 后半）、空串号码的去留判定、埋点汇、IM 侧效应、微信/QQ 分享本体、渠道号。
详见 `report/23`。
