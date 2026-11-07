# LinkUp 源码恢复工作区（公司授权）

本仓库用于 LinkUp（包名 com.youloft.watcher）客户端源码丢失后的恢复重建工作。
**版权声明：LinkUp 客户端版权归原版权方所有，本仓库内容仅供该公司内部源码恢复使用，禁止任何商用、转载与再分发。**

## 2026-11-06：轨迹页原版 UI 外壳

按 1.6.6 原布局恢复轨迹页外观：全屏地图槽、44dp 标题、32dp 圆角面板、原图日期底纹与拖柄，
折叠123dp/半展开383dp/全展开三档随拖动渐变；日期改为星期单字＋日号＋圆形选中背景，说明弹窗底部弹出。
缺失的 FastKit SheetLayout 用已有 Material BottomSheetBehavior 承载，不新引依赖。
新增离线 `TrackUiInstrumentation`（测试 APK 内，替换为内存存储与离线仓库，不触网），在只读模拟器
（API33）实测真拖动展开、日期/列表点击、底部弹窗、折叠、错误刷新与空态，六阶段截图留证。
JVM 轨迹合计42条，客户端全量409条（app285/定位93/网络31）重跑通过。
地图仍标注“尚未接入”，不画假底图；地图 SDK、VIP/隐私与 IM 提醒、后台采集仍未完成。
模拟器验收不等于真机像素验收；详见 `rebuild/recovered/DESIGN_CN.md` 五点二十八与待验67–70。

## 2026-11-06：轨迹列表恢复版

恢复入口已接入本人轨迹列表：15天日期选择、数据圆点、摘要与五类连接线、点击选中/取消、无定位说明弹窗、失败重试。
请求切日会取消旧请求，旧回包不能覆盖新日期；无登录账号不发请求。地图容器明确显示“尚未接入”。
原版地图/滑动面板、VIP与隐私权限交互、常驻采集和停留/离开判定仍未完成，未将入口接到好友产品页面。
本轮没有连接安卓设备，真机视觉与线上只读联调待验；详见 `rebuild/recovered/DESIGN_CN.md` 五点二十七和待验67–70。
新增37条测试通过，`:app` 全套280条重跑通过；连同未改动的定位93/网络31，客户端累计404条。
APK 已构建；服务端49个顶层离线测试重跑通过，3个在线 OpenIM 测试跳过，未冒充本轮联调。

## 内容
| 文件 | 说明 |
|---|---|
| apk156.part_aa/ab | LinkUp 1.5.6 APK 分块（cat 拼合） |
| apk166.part_aa/ab | LinkUp 1.6.6 APK 分块 |
| jadx-1.5.6.zip | 反编译工具（跨平台） |
| apktool_3.0.3.jar | 资源还原工具 |
| run_all.sh | Mac/Linux 一键脚本（下载+拼合+校验+反编译+打包） |
| report/ | 项目情况报告 / 可行性报告 / 操作指南 |
| rebuild/ | 重建工程：客户端（`net`/`app`/`fastkit`）+ 后端第一刀（`server/`，Go 网关 + OpenIMServer 适配层） |
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

## 2026-11-04 再更新：#20 后半——扫码屏落地，添加好友的四条找人路径全部闭合

`QRCodeScanActivity` 原版挂着公开库 `com.king.zxing:zxing-lite`（`BarcodeCameraScanActivity`）。这轮
**故意不接回那个库**：版本从 APK 取不出来（已经欠 MMKV/BRVAH/zxing-core 三笔同类债）、1.6.6 的布局本来就
直接写 `androidx.camera.view.PreviewView`、而 CameraX 与 zxing-core 都已在依赖里；它替我们做的事只剩
"预览 + 逐帧解码循环"这薄薄一层。代价写在报告里，没藏。

照搬的行为（每条都有出处）：结果键 `SCAN_RESULT` + `RESULT_OK` + finish、**只解 QR**、
`cropRatio=1.0`（整帧，库默认 0.8）、**命中一次立即停止分析**、扫描线 **2000ms** REVERSE 无限、
`argb(153,0,0,0)` 遮罩用 `PorterDuff.CLEAR` 在扫码框上**挖洞**（必须在 `post{}` 里建）、相册走系统
`ACTION_PICK image/*`、权限按 **SDK≥29 分叉**、相册图两遍解码按 **800×800** 定 `inSampleSize`、命中震动。
清单四条权限（含 `READ_EXTERNAL_STORAGE maxSdkVersion=32`）**都先核过 1.6.6 原样**。

两个"原来如此"：① 那条降采样循环比的是**一半**的尺寸，所以 4000×3000 对 800×800 的答案是 **2 不是 4**
（我自己第一版期望就写错了，被测试纠正）；② 本机 Robolectric 光栅化不可信这件事**又撞上一次**，于是把
#19 的"版面→像素"栅格化提成测试共享工具，换来一条真端到端：**画码器排的版面 → 像素 → 真解码器解回同一串**，
外加一条负向测试（全白位图必须解不出）。

诚实记账：原版配置链 `p(false)/m(0)/u(true)` 三个开关**没有库源码定不了名**，我只实现了有 `VIBRATE` 权限
作旁证的"命中震动"，其余没猜也没瞎起名（待验第 38 条）。

接线完成：添加好友屏**用结果启动器**发扫码（原版就是 `B.launch`），结果喂给早已测过的判定树；
`openQrScanner()` 也换成真启动。至此 #15 留的两条空跳转全部闭合。

`:app` 190 tests / 0 failures（本卡 +14）、`:net` 10 / 0，合计 **200 全绿**；APK 61,848,174 B，已核
`QRCodeScanActivity`/`QrDecoder`/`ScanMaskDrawable`/布局在包里、`com/king` 不在；业务布局 inflate
仍 **306/335** 无倒退。**没做的**：真机预览与逐帧解码、闪光灯与遮罩观感、相册完整链路、三个未命名开关、
埋点汇、`AgreeAddActivity`、IM 侧效应；另外**渠道号与通讯录空串号码这两件仍在等你拍板**。详见 `report/24`。

## 2026-11-04 再更新：#17 渠道段与远程配置——挂在"外部依赖"名下的两条，其实都是自己家的

**结论一句话**：渠道号是自家打包环节写进 APK 签名块的一段 JSON；远程配置是自家域名的一个 HTTP GET。
两侧代码都落地并自检，只剩装机确认。

读侧：`hc.a` 的 12 个常量与**美团开源 Walle 的 `ApkUtil`** 逐个对上（`0x71777777` 渠道段、
`0x7109871A` v2 段、`0x42726577` verity padding 段、`APK Sig Block 42` 两个半、EOCD 的 22/`0x06054b50`/+20…）。
**但 payload 不是 Walle 的**——原版把这段字节直接 `new JSONObject(...)`，而 Walle 写的是自己的二进制格式，
所以打标不能用 Walle 插件，写入端（`:net:tagChannel`）只能自己实现。

盘上量的硬事实：**两个原包都带这段，内容一模一样** `{"channel":"3305"}`（18 字节）。
而 `utils.p` 里比较的是 3801/3300/3301/3302/3303/3304/4000——**3305 一个都不命中**。
于是 #15 当时只能记成"改判了"的那条权限门差异有了真值：1.5.6 按配置列表（今天的回包是
`["3300","3301","-1"]`，含 `-1` 通配）⇒ **恒弹**；1.6.6 按 `channel=="3301"` ⇒ **线上恒不弹**。
换判据不是等价重构，它让所有线上包从此不再问权限。

写侧实测（跑了两遍）：给自家 `app-debug.apk` 打 `3305` → `apksigner verify -v` 仍 **v2 = true**、
同一张调试证书、`unzip -t` 无错，签名块里 v2 段与 verity padding 段原样并存。
原理照旧：v2/v3 摘要只覆盖平台自己的 pair，额外 pair 在签名数据之外。

配置服务：`of.b`（1.5.6）/`nf.b`（1.6.6）就是自家 OkHttp GET。`cfg.51wnl-cq.com` 现在 302 到
`configsys.51wnl-cq.com/api/config/getconfigs`；**令牌就是回包里的 `r`**——带上
`lastupdate=<r>` 实测服务器回 `{"msg":{}}`，这条把 #15 留的"哪个字段是令牌"问号正式关掉；
`appver` 1.5.6 发 `"156"`、1.6.6 发 `"166"`（实测两份回包内容相同）；`msg` 里 18 个键全 base64、
逐键摊进设置。**`showPermissionChannel` 在 1.6.6 已经是死键**（`ConfigUtils` 里那个访问器整条没了）。

顺带修了自己两条不诚实的记账：存储键名换成原版三个真名（`online_lastupdate`/`online_lastrequest`/
`online_lastrequest_ver`），我上一轮发明的 `configLastFetchAt` 删掉；留档的 `live_config_sample_2026-11-04.json`
里那个 `msg.Parameter_Map` 是我自己写的标签、不是服务端的键名，已改正并注明。

`:net` 29 / 0、`:app` 197 / 0，合计 **226 全绿**；APK 61,848,174 B。**有意没做**：启动时自动拉配置
（原版 `SdkInitManager` 启动就拉，这属于"同意隐私前能不能打这个域名"的产品/合规决定）与发布链自动打标。
**等你拍板**：重建包打哪个渠道号（按线上取 `3305` 最保真）、权限门按 1.6.6 还是退回 1.5.6 配置规则。
未知项：原包里那个 14 KB 的 `0x504B4453` 段归属、`3305` 是哪个分发渠道。详见 `report/25`。

## 2026-11-05 再更新：#18 前半——登录屏与短信弹窗落地，`user2` 从此有了上游

`LoginActivity` + `LoginSmsDialog` + `SendCodeButton`（60 秒倒计时）+ `PolicyRemindDialog` 全部重建完。
#16 那条写入通道（`user2` + `token`）从今天起不再只能靠探针屏手动灌。

**这一轮推翻了五条我自己记错的事**，都有逐行出处（`report/26` 第一节是完整对照表）：
① `typeId` 只有 1/2/3，走 `api/sms/click_to_login`；**微信/QQ 根本不是 typeId**，是另一个端点
`api/user/login`，body 用 `platform`（4/5）——#15 记的"4=微信 5=QQ"是错的。
② 登录写入顺序是**先 `user2` 再 `token`**；#16 我写反了，还在注释里自称"顺序重要且已保留"。
本轮改回，并加了一条**按写入次序断言 key 顺序**的测试，下次再写反就会红。
③ **1.6.6 把 Mob 整族删了**（`sources/com/mob` 整个不存在），换成子包一一对得上的 `cn.fly.verify.FlyVerify`——
等于同一套东西换牌；1.5.6 才是 `com.mob.secverify.SecPure`。
④ `Cut.loginType` 是**字符串**，`toIntOrNull() ?: 1` 交给厂商路由；非 1/3 是"回调 null"，
再由"号码或运营商为空"才落到短信框——不是"非 1/3 直接弹短信框"。
⑤ 有一条**不写缓存**的分支：登录回来但昵称为空（或三方登录已注册账号）时，人被寄存在进程全局 `App.user`，
**只写 token**。这不是 bug，是"资料没补全的人交给补资料屏落地"，所以重建里 `UserManager.inFlight` 是必需品。

两条是实现期自己踩的坑，也一起改了：**`Dialog.getContext()` 带主题时是 `ContextThemeWrapper`**，
我照抄原版的 `context as? Activity` 于是静默失效——"登录成功后关掉登录页"其实没发生，已提成
`BindingDialog.hostActivity`；**`KeyValueStore` 原来只有字符串接口**，而 `lastLoginType` /
`isRequestedNotification` 在原版是 MMKV 的 int/bool，用字符串读的话老用户升级后读不到自己的"上次登录"。

一处**故意不修平**的不一致：QQ 按钮直接点击时原版不禁用，只有走协议提醒弹窗那条续作才
`setEnabled(false)`。照搬，并写了两条测试分别钉住。

安全边界照旧：全程没调 `/api/sms/send`（那会发真短信），短信与登录路径全是 JVM 假仓库驱动的测试。
`CountDownTimer` 在 Robolectric 下**根本不投递消息**（实测喂 59 秒标签不动），所以倒计时抽成可注入的
`SendCodeButton.Countdown`：生产用平台实现，测试手喂 tick——否则这块要么测不到，要么写假绿。

`:app` 235 / 0、`:net` 29 / 0，合计 **264 全绿**（本卡 +38）；APK 61,848,174 B，本卡三份布局 inflate ok，
业务命名布局仍 **306/335** 无倒退。**#18 后半没做**：一键登录弹窗（两个厂商 jar 都拿不到）、
`EmptyLoginActivity` 首启隐私门、`ImproveUserInfoActivity` 与 `MainActivity` 两个跳转目标、
微信 code→`sns/oauth2/access_token`→`platform=4` 那条完整链。**等你拍板新增一条**：
`POST_NOTIFICATIONS` 现在照搬原版在 `onCreate` 每账号只问一次，要不要挪到首启隐私同意之后。详见 `report/26`。

## 2026-11-05 再更新：#21 后端第一刀——Go 网关 + OpenIMServer，17 条路由跑通了

方向按你的决定换了：**关系与消息状态接 OpenIMServer，LinkUp 自有的东西自己做**，服务端用 Go
（与线上丢失的那个服务同栈）。落点 `rebuild/server/`，覆盖 **17 条路由**：登录 5 + 配置/公钥 2 + 关系域 10。
**客户端契约一个字节没改**——路径、`{status,msg,data}`、AES 签名（key==IV 的 AES-128-CBC）、裸 JWT、
四个横杠的 PEM 页脚，全部照 1.6.6 还原出来的形状实现，并有**负向测试**。

家底先摆清楚，免得期待错位：97 条里 OpenIM 能直接顶掉的是**关系域 10 条**＋还没重建的消息/会话面，
约 12–14 条；剩下 83 条（定位、锁机、截图、纪念日、VIP/支付、风控、上报）任何 IM 项目都不替你写。
另外现网 IM 用的是**环信 SaaS**（appkey 在我方手里），所以 OpenIM 是"自己掌控"的选项，不是必须换。

**四条这轮才从代码里核出来的事实**（`report/27` 第二节有逐行出处）：
① `api/relation/confirm` 的 `code` 在 **query**，body 里那份只是重复；
② `api/user/update/info` 的 body 恰好四键 `avatar/nickname/sex/`**`stage`**，键名分别来自
`ImproveUserInfoActivity.f65723w="avatar"`、字面量、被复用的百度广告常量 `ArticleInfo.USER_SEX="sex"`、字面量；
③ `stage` 是"补资料走到第几步"，服务端丢它 ⇒ 每个中途退出的人下次都被打回第一步，**而且不报错**；
④ OpenIM 两个申请列表的响应键大小写不一致（`FriendRequests` vs `friendRequests`，
protocol v0.0.73-alpha.12 的 `relation.pb.go:514`/`:2083`）——Go 的大小写兜底刚好接住，测试把两种拼法都钉住。

**四个我自己写出来的 bug，全部当场被抓**：签名中间件在"跳过校验"分支里顺手没读 body ⇒ 登录 body 永远是
空 map ⇒ 所有登录被自己拒（而我写的拒绝话术还把它伪装成"缺号码认证 SDK"，误导了一轮）；
`IssueCode(phone, ttl)` 收了 ttl 然后 `_ = ttl` 丢掉 ⇒ 验证码永不过期；三方登录的账号键是我编的
`"wx4:"+unionId` 塞在 phone 列 ⇒ **微信绑过手机的人再用短信登录会拿到第二个账号**，已改成 `unionId` 独立成列、
手机来就绑定；`smoke.sh` 自己漏了 query ⇒ 我怀疑了网关两轮，其实是脚本错（副作用是现在有一对
"签名与实际 query 不一致要拒、一致要过"的用例）。还挖出一条发布链的坑：`publish.sh` 的 `rm -rf` 只列了
当时的目录名，**本地删掉的文件会在公开仓复活**，已改为整目录清空再解。同一段还有我自己写错的一条：
本轮新加的目录表里我写了一个 `core-net/`，说它是 1.5.6 那套自研 HTTP 栈，实际那只是个**空目录骨架**
（0 个文件、构建里没有这个模块、从未进过仓库也从未进过公开仓）；yftracker 旧链路的真实状态仍是
"尚未接入"。空骨架已删、那行已去掉——"目录 → 职责"这种表以后要逐行对 `git ls-files` 数一遍。

验收：`go test ./...` **34 绿**（contract 6 / gateway 15 / openim 6 / store 7，全离线）；
`bash rebuild/server/scripts/smoke.sh` **28 绿**——真起进程、真走 TCP、签名由 **openssl** 在 shell 里算，
于是同一条契约在 **JVM / Go / OpenSSL 三个实现**下对上了。客户端侧复验无倒退：`:net` 29 / 0、`:app` 235 / 0。
一条差点被吞掉的验收事故：`gradle … | tail` 之后的 `$?` 是 `tail` 的 0，我第一次就是这么跑的，
屏幕没有 FAILED 而实际是 **BUILD FAILED**——真退出码必须从被测命令自己取。顺带发现
`:fastkit:testDebugUnitTest` 本身是坏的（AAPT 缺 Material 属性），而该模块**零测试源**，已从回归命令里去掉。

**没跑的就是没跑**：OpenIM 真容器栈一次都没起过——C 盘只剩 7.2 GB（99% 满）而 Docker data-root 在 C，
那套镜像解压 2.5–3.5 GB。所以 `internal/openim` 只有 httptest 打桩，"网关 ↔ 真服"记在待验 **47–49**，
不计入绿。smoke 里甚至**故意**把 `-openim` 指到死端口，用来证明不可达时答 `status:500 服务暂时不可用`，
而不是一个看起来像成功的空好友列表。安全边界照旧：这一刀**物理上发不出短信**（没有任何短信通道），
`-dev` 之外拒绝公开的 demo 密钥，RSA 私钥与 store 文件已进 `.gitignore`。
另有**一处刻意与线上不同**：生产网关实测不校验 Signature，重建版默认校验（待验 51 要你/运维拍板）。
详见 `report/27` 与 `rebuild/server/README.md`。

## 2026-11-05 再更新：#21 后半——真 OpenIM 跑通了，服务器当场纠正我四条

按你"迁移到 D"的指示做的，但**没搬 Docker Desktop 的盘**（改它私有配置风险大、会丢你现有镜像）。
改成把 Ubuntu 官方 WSL rootfs（先校验 sha256）`wsl --import` 成装在 **D:\linkup-im\** 的独立发行版，
里面自己跑 dockerd：mongo/redis/etcd/kafka/minio/`openim-server:v3.8.3-patch.18` 全在那里，
**C 盘零增量**，要撤就 `wsl --unregister linkup-im` 一条命令。

这一轮的价值不在"跑通了"，在**跑通过程中服务器当面纠正了我四条**——打桩测试一条都抓不到：
① `get_admin_token` 的 `userID` 是**字符串**，我照 `repeated` 的想当然发成数组 ⇒ **每一次 IM 调用都拿不到
令牌**，整套关系功能 100% 不可用（协议模块里它本来就是 `string`，是我读错）；
② `is_friend` 的请求字段是 **userID1/userID2**，我发的 `ownerUserID` 被 `ArgsError: userID1 is empty` 拒；
③ `is_friend` 回的是 **`inUser1Friends`/`inUser2Friends` 两个方向的旗标**，我读的 `isFriend` 不存在 ⇒ 恒 false；
④ **`delete_friend` 是单向的**：删完 B→A，A 那边 `inUser2Friends` 还是 true ⇒ "好友在另一台手机上复活"，
现在两个方向都删并有测试钉住。另有两条只有真服能给的口径：**不传 `handleResults` = 不过滤**
（未读数只能自己按 `handleResult==0` 数），**重复注册回 1102 RegisteredAlreadyError**
（我原来的 `IsAlreadyKnown` 只认 "exist"，接不住 ⇒ 正常情况被记成失败）。

顺带抓出两个我自己的实现错：`Extra.Since` 写成 `UnixMilli()`，而客户端做 `Date(createAt*1000L)`
⇒ 关系详情显示成公元五万多年（全链路统一成秒 + 测试钉单位区间）；我的补丁脚本被 Python 写成 CRLF，
bash 不报语法错、只是 `dirname` 带 `\r` 走错目录，已用 `.gitattributes` 把 `*.sh`/`*.go` 锁成 LF
（`*.go` 那条还顺带消掉 Windows 上 `gofmt -l` 12/12 的假警报）。

验收矩阵现在是四层：离线 **36 个 Go 测试**（Windows 与 Linux 各跑一遍）、真进程接**死 IM** 的
**28 条 smoke 用例**（证明不可达时报错而不是报空列表）、**真栈端到端 20 条全绿**、
**3 个在线集成测试全绿**（没真服时自动 skip，不拖红离线套件）。OpenIM 的原始应答没做加工，
原样存在 `recovered/openim_live_evidence_2026-11-05/`。待验 **47/48/49 划掉**。

环境侧三条会反复撞上的事实：**WSL 是 NAT 且没有 IPv6 路由**（DNS 只回 AAAA，`curl` 0 秒失败像断网）、
**Docker Hub 直连不通**（`docker.1ms.run` 可用，`daocloud` 对 `openim/*` 回 403）、
**这台机 WSL 空闲就回收 VM**（所以"起栈→等 healthy→跑验收"必须一次调用跑完，否则容器反复重启、
10002 时通时断，验收会莫名其妙红一片）。

**下一刀**：客户端 baseUrl 指过来，两台真机走一遍加友——那才能判定待验 50（三方登录的 `isRegister`
到底答什么）。详见 `report/28`。

## 2026-11-05 再更新：#21 尾声——重建客户端与重建网关第一次会师（30 条全绿），当场抓出三条"各自都绿、合起来才炸"

前面所有绿都是**单侧**的：`:net` 证明"客户端按我以为的形状发/收"，`server` 证明"服务端按我以为的形状发/收"。
这一轮把两个"我以为"接在一起：`gradle :net:gatewayVerify` 用**真 Retrofit 接口 + 真签名拦截器 + 真 Gson 模型**
打重建网关（网关再打真 OpenIMServer），**30 条检查全绿**（`CLIENT_MEETS_OWN_SERVER=1`）。

三条错没有一条是任何单侧测试能发现的：

① **`@Body Map<String, Any?>` 让 40 条 POST 一调用就抛** `Parameter type must not include a type variable or
wildcard: java.util.Map<String, ?>`。Retrofit 在调用那一刻校验泛型类型，而 Kotlin **只读** `Map` 的值参数是
协变的（`out V`）⇒ 编译成通配符。原版 class 文件的签名是 `java.util.Map<String, Object>`
（`gh/a.java:293`），也就是**不变**的 `MutableMap`——问题在变型，不在可空。已改接口 40 处 + 调用点 16 处，
并加 `BodyParameterTypesTest` 反射遍历所有 `@Body` 参数（**改之前先跑，两条都是红的**）。
为什么 235 条 Robolectric 全绿也看不见：屏幕测的是假仓库，真 Retrofit 方法从没被调用过。

② **"匹配码"就是 userId，而且 id 必须 8 位**：`AddFriendActivity.java:862-864` 显示的是
`String.valueOf(user.userId)` 每 4 位插空格，`MATCH_CODE_LENGTH==8` 决定满 8 位才当匹配码，
`User` bean 里根本没有第二个码字段。我服务端不但另造了一个随机 8 位 `matchCode`，还从 **10001** 起号
——5 位 id 在客户端第一条判断就被 toast 拒掉，**请求根本发不出去**。已删掉那套码、`firstUserID=10000001`。

③ **好友列表那一行的 bean 和详情的 bean 不是一套字段**：列表 `FriendList.Info` 用 `createAt`（**秒**，
客户端 `Date(createAt*1000L)`）、`relation`/`sex` 是**数字**、而且**没有 permission 对象**（只有一个绑勾选框的
`permissionValue`）；详情 `FriendInfo` 那边 `relation`/`sex` 才是字符串。我按详情的形状发列表 ⇒ 客户端静默读 0。
同一个坑的镜像面也修了：`Extra.Since` 我写成 `UnixMilli()` ⇒ 关系详情会显示成**公元五万多年**，现在全链路秒。

**更正一条我上一轮说错的**：我说过"Windows 打不到 WSL 的端口（NAT）"——那是撞上了容器被 VM 回收后的重启窗口。
重测 `http://127.0.0.1:10002` 从 Windows 直接 200 通，本轮网关就正常跑在 Windows 上。

**另外**：Gson 的 `serializeNulls` 默认关 ⇒ map 里的 null 值**连键一起丢**，所以原版
`"phone" to null` 在网上就是"没有 phone 键"，服务端不必区分（这条决定了网关怎么读手机号）。

验收矩阵现在是六层：`:net` 31 + `:app` 235 = **266 绿**（+2 是那条签名门禁）、`go test ./...` **36 绿**、
`smoke.sh`（死 IM）**28 绿**、`openim-e2e.sh`（真栈）**20 绿**、`-run Live`（真服集成）**3 绿**、
`gatewayVerify`（客户端↔网关）**30 绿**。待验新增 53–57（`Info` 那 13 个给不出值的键、老账号 id 位数分布、
几个布尔的原始算法、apply 时申请方 sensSetting 存不存、map 构造改动对逐字节抓包的影响），
26 改为"对我们自己的后端已验、线上真实页脚仍未验"。详见 `report/29`。

## 2026-11-05 再更新：#22 前半——定位域服务端（上报 → 按天 → 当天轨迹），服务端 49 绿、会师检查 46 绿

轨迹页与首页地图卡在 `com.baidu.mapapi.map.MapView`（Maven Central 没有，本机取不到），所以这一刀
把**数据面**做实：设备上报位置 → 服务端存下并按天归日 → 轨迹页读某天时拿到折线、事件行和三个汇总数字，
而且**别人不能随便看**。新增 3 条路由，网关累计 20 条（GET 11 / POST 9）。

形状没有一样是设计出来的，全部对着客户端怎么用它反推：`totalDistance` 是**米**
（界面 ÷1000 后拼 "km"，`TrackRecordFragment.java:181`）、`totalStayTime` 是**秒**（:164 ×1000）、
`timePeriod` 是 epoch 秒（:280 `Date(timePeriod*1000)`）；`line.type` 的 1/2/3/4 就是分支里的四个文案与图标
（`less_than_1m` / `less_than_200m` / 无法获取定位 / 没有新定位）——所以"≤1 米算还在同一段停留"这个阈值
是客户端自己给的；`track.type` 2=到达、3=离开，且行只在 `lostType==0` 时才渲染；
`bean/Address` 只有六个键、**没有整串地址字段**，可见整串地址一直是服务端拼的；
`api/location/report` 的 body 是 `Location` bean 本身（10 键含 `type`），不是 map（`gh/a.java:401`）。

**三个服务端量做成 flag，不写成"看起来像恢复值"的常量**：`-stay-seconds`（停留多久算一个到达点）、
`-gap-seconds`（沉默多久算没有新定位）、`-loc-timezone`（一天从哪个时区算，默认 Asia/Shanghai）。
有一条测试专门把阈值改成 600 秒：四分钟的停留不再算到达点，但停留秒数仍要记满 240——证明是真参数。
顺带一个平台事实：Windows 构建的 Go 没有内嵌 tzdb，`LoadLocation` 会失败，所以退回固定 +08:00
而不是让服务起不来。

**权限**：自己永远可以；他人必须有任一方向的关系。拒绝 = HTTP 200 + 信封 `status=403` + 文案
（403 是我定的码——客户端只判 `status != 200` 并 toast `msg`，原服务端的码不可观测，这点写进代码注释）。
会师检查里有一条时序断言：关系删除之后再读对方轨迹必须被拒。

**两条路由故意没做**（不是漏）：`batch/report` 在 1.6.6 全树找不到调用点，body 键名没有依据；
两个 widget 接口要先有"配对的另一人"模型与 `FriendState` 设备态（属敏感事件域）。记待验 58/59。

另外修了 `:net` 一处遗留：`TrackRecordBean.points/tracks` 之前是 `List<JsonElement?>`（生成器没解析
嵌套 bean），换成 `List<TrackRecordBean.Point?>?` / `…Track?>?`——不然轨迹页拿到的是原始 JSON 片段。

数字：定位算法 9 绿 + 定位路由 4 绿，`go test ./...` **49 绿**；客户端 **266 绿**；死 IM smoke 28 绿；
真 OpenIM 端到端 20 绿；`gatewayVerify` **46 绿**（定位链 16 条，全部由客户端真 bean 解出来）。详见 `report/30`。

## 2026-11-06 再更新：#23 定位抽象层——一家接口 + 各家 SDK 与 API，`:location` 93 绿、客户端三层 367 绿

用户这一轮的要求很具体：**"我要一个那种抽象的。定位。他可以兼容各家的 sdk。和 apI。把它单独儿变成一个接口。"**
于是新增 `rebuild/location/` 模块：`LocationProvider`（follow / `singleFix` / `update` / `stop` / `lastFix`）、
`PlaceResolver`（地址↔坐标）、`LocationGateway`（上报 API 侧），三家实现——系统 `LocationManager`（今天真能跑）、
百度（**反射绑定**，签名逐条钉到 APK 反编译行号，测试用同签名替身跑**生产反射代码**）、测试假源。
接口层零三方依赖，并由 `LocationLayerIndependenceTest` 把门：src/main 里出现厂商包名就红。

切分点来自原版自己：**1.6.6 的 `dg/a.java` 已经把配置抽成不可变 `Snapshot(locationMode, scanSpan)`**，
`update()` 相同返回 null，其余十三个百度字段是常量。所以 `LocationRequest` 只带会变的两个，
厂商私有常量留在适配器——换 SDK 时不需要重新谈判的那条缝，原版早就画好了。

这轮最值钱的一条事实：**bean 里存的是 WGS84，SDK 给的是 bd09ll**，换算发生在回调入口
（`x0.java:290` 的 `h0.c`），要算距离时才 `getLatLng09()` 换回去。为了让这件事不是"我觉得等价"，
把原包 `h0.java` 的算术抄成临时 Java **在 JDK 上真跑出 46 行样本**（`rebuild/recovered/geo_golden_156.txt`），
`GeoMathTest` 逐行复现全部 40 个数值；适配器还从 `BDLocation.getCoorType()` 读坐标系而不是假定。

测试当场抓出我五条错，全部已修——这就是"打桩绿"和"真跑绿"的差距：
① `Method.invoke` 对 **void 方法返回 null**，我拿返回值判成败 ⇒ 每次成功都被当失败，百度源根本 start 不起来；
② **嵌套枚举二进制名只有一个 `$`**，我写成两个 ⇒ `locationMode`/`firstLocType` 静默设不上，
   现在 `buildOption` 对任何缺失成员直接失败并写 `missingReason`；
③ `unregisterLocationListener` 是**我凭语义编的**——两版 APK 的 `LocationClient` 都只有两个 register 重载，
   没有注销（这也解释了原版为什么全进程只建一个 client）；
④ `SystemLocationProvider.singleFix` **成功后泄漏框架注册**（只在取消路径清理）；
⑤ `Location.getId()` 在 compileSdk 34 不可见 ⇒ `providerId` 恒为 `"system"`，改用 `location.provider`。

节律逐字移植 `x0.java:156-158` 的 `a(speed)`（40m 距离预算÷速度，夹在 5..20s），并把单位陷阱写在类型上：
原版**只在 `locType==61`** 时把 km/h 除以 3.6，其他定位类型一律记 0 ⇒ "静止"由厂商类型决定；框架源不除。
弄错就是线上上报频率差 3.6 倍。**`x0.java:164-265` 的停留/离开状态机本轮明确没搬**（JADX 寄存器复用严重，
硬抄只会产出"看着像、数字不对"的实现），所以 `type` 一律发 0，服务端 `Summarise` 照常算得出停留与离开。
十七个定位远程配置键连同默认值入表（`manager/l.java:64-80`），`RemoteConfig.number()` + `LocationTuning.fromConfig`
按键覆盖、缺键保留原包兜底。抄录时发现**原版自己一处可疑**：`x0.java:242` 用 `stayDistanceThreshold`（200m）
判"潜在停留范围外"，而语义应是 `potentialStayDistanceThreshold`（20m）——差 10 倍，进待验 62 等人定。

`:app` 接上真实现：`LinkUpLocationGateway`（发出去的是线上那份十键 `Location` bean，坐标 WGS84）、
`LocationSources`（Baidu 优先、系统兜底）、`RecoveryProbeActivity` 多一段只读检查——选到哪家、阈值真值、
`Geocoder` 到底能不能用，这三条只有手机能答（待验 62/64/65/66）。

数字：`sh tools/gradle.sh :location:testDebugUnitTest` **93 绿**（Baidu 反射 23 / 坐标黄金样本 14 /
节律与采集 17 / 系统源 16 / Geocoder 10 / 选择回退 7 / 架构门禁 6）；`:net` 31 + `:app` 243 = **274 绿**
（本轮新增 8 条上报形状与配置阈值）；三层合计 **367 绿，0 skip**。`go test ./...` 49 绿——服务端本轮没动，
`smoke.sh` 与 `gatewayVerify` 同理没重跑，不把旧结果当本轮结论。详见 `report/31`。
