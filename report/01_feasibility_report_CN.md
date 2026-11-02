# LinkUp (com.youloft.watcher) v1.5.6 源码恢复可行性报告

> 分析对象：com.youloft.watcher1.5.6.apk (119 MB)
> 分析方式：本机静态解包 + dex 字符串/结构提取 + 公开逆向资料交叉验证
> 结论先行：客户端可以恢复到"接近源码"的程度；原始 Java/Kotlin 源码无法从 APK 100% 还原，但反编译产出 + 本报告资产足以支撑完整重写。后端与签名密钥不在 APK 内。

## 一、应用身份

| 项目 | 值 |
|---|---|
| 应用名 | LinkUp（自动报备 & 定位轨迹） |
| 包名 | com.youloft.watcher |
| 版本 | 1.5.6（应用商店公开最新版 1.6.4，可下载对比补充信息） |
| 开发方 | 万年历团队（重庆，域名 51wnl-cq.com；公开笔记记载主体为"重庆可兰达科技"） |
| 渠道 | 小米商店、腾讯应用宝在架 |
| 深链 | ylwatcher:// ；QQ 互联 appId 102361775（AppKey 本版本为 ubL50e1vplPn3FsVVbDfQjAcgnU0eZ7P） |
| 加固 | 无壳（未发现加壳特征，dex 明文可读）——这是恢复可行性的最大好消息 |

授权提醒：该应用是公开发布的商业产品。若贵司即为其版权方（自研/受托开发），恢复属于正当自救；请先内部确认权属，再进行商业化重建。

## 二、能恢复什么 / 不能恢复什么

### 可从 APK 完整恢复（100%）
1. 全部资源：res/（46MB）、assets/（24MB，Lottie 动画、配置、百度地图资源）
2. AndroidManifest：235 Activity / 46 Service / 19 Receiver / 29 Provider、全部权限、深链
3. 组件与类结构：3929 个自有业务类完整清单（classes_youloft.txt）
4. 网络协议与签名算法（见第四节，已完整破解，含 PoC）
5. 业务 API 端点清单 40 条（api_endpoints_final.txt）
6. 第三方 SDK 清单与版本（sdk_versions.txt、libs_list.txt）

### 可恢复到"接近源码"（需在 PC 上跑 jadx）
- 原始业务逻辑：jadx 反编译 7 个 dex（约 52MB）可得到可读 Java（Kotlin 经混淆变量名有损，但结构、常量、调用关系完整）。本包无加固，jadx 直接可用。
- 布局文件：apktool 可还原为文本 XML。

### APK 里根本没有、必须另寻的
1. 后端服务端源码（dmp.51wnl-cq.com 背后的服务）
2. 签名 keystore（丢失则只能换签名重新上架）
3. 三方平台后台账号密码（微信开放平台/环信/百度地图/各推送后台）
4. 原始可维护源码（注释、工程配置、CI 脚本）

## 三、技术栈（重建工程骨架依据）

- Kotlin + Coroutines + AndroidX（Room 2.6.1、DataBinding 296 个绑定类、Camera2、Splashscreen）
- 网络：原生 OkHttp3（无 Retrofit），统一走自研 com.youloft.yftracker.helpers.OkHttpManager 单例
- 存储：MMKV + Room + SQLCipher（环信消息库）
- IM：环信 Hyphenate（libhyphenate.so 7.1MB + easeui）
- 地图/定位：百度地图 7.6.4 + 百度定位 liblocSDK8b + 室内定位 libindoor
- 推送：小米/华为/荣耀/OPPO/vivo/魅族/个推/Mob
- 广告：穿山甲 + 广点通 + 百度联盟 + 快手 + AnyThink 聚合 + 字节直播插件
- 埋点：ThinkingData（ss.51wnl.com）+ 阿里云 SLS + 友盟/Bugly
- 登录：手机号+短信、联通一键登录、微信/QQ/抖音授权
- 其他：Lottie、SVGA、AndroidUtilCode、pictureselector

## 四、网络层与签名算法（已破解，照此重写即可）

来源：GitHub 公开逆向笔记（gh_notes/STAGE2_REPORT.md）+ 本机 dex 交叉验证一致。

主入口：com.youloft.yftracker.helpers.OkHttpManager（单例）
baseUrl：生产 https://dmp.51wnl-cq.com ；测试 https://dmp-test.51wnl-cq.com
配置接口：https://cfg.51wnl-cq.com/api/getallconfig.ashx

签名算法（EncryptUtils）：
  KEY = "be2524844ec4bb25"   （16字节UTF-8，本机 dex 已验证存在）
  IV  = "be2524844ec4bb25"   （KEY == IV，原实现缺陷，重写时建议修复）
  aes128Encrypt(s) = hex( AES-128-CBC-PKCS5( UTF8(s), KEY, IV ) )
  md5(s)           = 小写hex MD5
  signatureGet(s)  = md5( aes128Encrypt(s) )

公共请求头：Signature: signatureGet(签名输入)；origin: "ANDROID_SDK"

签名输入规则：
  GET  → path + "?" + 按序拼接的querystring
  POST(form) → 原版不签名（重写时建议补签）
  postProtoAsync → path + md5(body字节)

## 五、业务 API 端点（40 条，详见 api_endpoints_final.txt）

- 用户：/user/login /user/info /user/update/info /user/logout /user/unregister /user/change_bind /user/update/push/token /user/report/getui_cid /user/show/report /user/cut/list /user/default_avatar
- 短信登录：/sms/send /sms/login/cut /sms/click_to_login
- 定位上报：/location/report /location/batch/report /location/v2/tracks
- 好友关系：/relation/apply /relation/apply_list /relation/match_by_phone
- IM：/im/chat
- VIP：/vip/index /api/vip/share_to_friend
- 通用：/api/client/config /api/feedback/create /push/binding /report_event /api/app/sls/sts /api/app/data/report/protobuf
- 一键登录：/v1/gy/ct_login/get_menukey /v1/gy/ct_login/token_upload /v1/gy/ct_login/token_validate

## 六、业务模块地图（pages/ 共 2083 个类）

pages/login 启动登录绑定手机一键登录
pages/friend 加好友、通讯录匹配、扫码、好友详情/申请列表
pages/im 聊天、表情、消息设置、图片/位置消息、历史搜索（环信）
pages/voice 实时语音、动效
pages/track 轨迹记录、地址标签
pages/home 卡片编辑、离线提醒
pages/todo 待办
pages/lock 应用锁（一键锁机）
pages/protection 应用密码
pages/permission 权限引导
pages/privacy 隐私设置
pages/mine 关于、反馈、数据安全、地图设置、自动报备设置
pages/vip 会员
pages/risk 实名认证
pages/camera 拍摄、图片预览
pages/user 资料编辑
pages/test 调试入口（位置Mock，release 也打进去了）
pages/main 主框架 MainActivity
widget/ 桌面小组件（WidgetUpdateService + SchedulerReportJob）
web/ 内置 H5
service/push 各厂商推送通道

## 七、恢复路线图

第 0 步 —— 先在公司内部找原文件（成本最低，别跳过）
- 自建 git 服务器 / Gitee 企业版 / GitLab 备份、外包交付物与合同附件
- 离职开发电脑、公司 NAS/云盘、微信/邮件历史发送的 zip
- CI/打包机工作目录、Gradle 缓存与本地分支
- 环信/百度/推送等三方后台：账号还在，配置与文档可全部找回

第 1 步 —— PC 反编译拿"参考实现"（半天）
  jadx -d out_jadx --show-bad-code --deobf-min 3 com.youloft.watcher1.5.6.apk
  apktool d com.youloft.watcher1.5.6.apk -o out_apktool
  从 out_jadx/sources/com/youloft/ 开始读：yftracker/**（核心）、watcher/manager/**、watcher/pages/**

第 2 步 —— 重建工程（2-6 周量级）
1. 新建工程（包名保持 com.youloft.watcher 可复用三方后台配置）
2. 移植顺序：网络层（照第四节）→ 登录 → 好友 → 定位上报 → 环信 IM → 轨迹/锁机
3. 资源用本包 res/assets；布局用 apktool 文本 XML
4. 后端若也丢失：API 契约按第五节 + 抓包对齐字段
5. 新 keystore 重新签名上架

第 3 步 —— 找回后立即补救：源码入私有 git + 异地备份 + 密钥托管

## 八、随附文件清单

01_恢复可行性报告.md —— 本报告
02_jadx反编译指南.md —— PC 反编译操作细节
res_and_assets.zip —— 全部资源+assets
classes_youloft.txt —— 3929 个自有业务类清单
classes_yftracker.txt —— 自研定位上报 SDK 类清单（87 个）
api_endpoints_final.txt —— 40 条业务 API
sdk_versions.txt / libs_list.txt / assets_list.txt —— 依赖与资产清单
manifest_ascii.txt —— Manifest 提取文本
gh_notes/ —— GitHub 公开逆向笔记 11 篇（含网络层 smali 级还原、签名 PoC）
