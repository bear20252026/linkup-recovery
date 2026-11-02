# PC 反编译操作指南（LinkUp APK → 可读源码）

手机上没有 Java 运行时，jadx 等工具必须在电脑上跑。全程约 30-60 分钟。

## 1. 准备（Windows / macOS / Linux 皆可）
1. 安装 JDK 17+（Adoptium Temurin 发行版即可）
2. 下载工具：
   - jadx：https://github.com/skylot/jadx/releases （解压即用，自带 jadx-gui 图形界面）
   - apktool：https://apktool.org
3. 把 com.youloft.watcher1.5.6.apk 拷到电脑（本目录或应用宝重新下载均可）

## 2. 反编译 dex → Java（jadx）
jadx -d out_jadx --show-bad-code --deobf-min 3 com.youloft.watcher1.5.6.apk
- 52MB dex 预计 5-20 分钟，产出 4000+ 自有类的 Java 源码
- 图形界面：jadx-gui 打开 APK，全局搜索类名即可
- 阅读顺序（价值从高到低）：
  1. com/youloft/yftracker/ —— 网络层、签名、定位上报 SDK（核心，优先照此重写）
  2. com/youloft/watcher/manager/ —— 业务管理器（登录态、IM 初始化、推送绑定）
  3. com/youloft/watcher/pages/ —— 各页面逻辑
  4. com/youloft/watcher/utils/EncryptUtils —— 签名算法实现
- 混淆说明：业务类大多未混淆（pages/xxx 名称完整）；混淆类多在 view/adapter 层，可对照布局 XML 恢复

## 3. 还原资源为文本 XML（apktool）
apktool d com.youloft.watcher1.5.6.apk -o out_apktool
- out_apktool/res/layout/*.xml —— DataBinding 布局（含绑定表达式）
- out_apktool/AndroidManifest.xml —— 完整清单
- out_apktool/res/values/strings.xml —— 全部文案

## 4. 重建工程要点
1. Android Studio 新建工程：minSdk 26 / targetSdk 34 / Kotlin / DataBinding / Room / MMKV
2. 依赖版本照 sdk_versions.txt；环信/百度地图按官网最新稳定版
3. 网络层先写：OkHttp 单例 + Signature 头算法（AES-128-CBC，KEY=IV="be2524844ec4bb25"，签名=md5(hex(AES(输入)))，头 origin=ANDROID_SDK）——原版 KEY==IV 是缺陷，新代码应修但需与服务端约定
4. apktool 的 layout/values 拷入 app/src/main/res
5. 环信 AppKey、百度地图 AK、各推送 AppID：登录对应三方后台找回（账号一般在公司邮箱/运维手中）

## 5. 验证闭环
- 反编译代码 + api_endpoints_final.txt + gh_notes/08_main_api.txt（OkHttpManager smali 级还原）三者对照，网络层一天内可复现
- 原服务器若仍在线（dmp.51wnl-cq.com），用旧版 App 抓包对齐请求/响应字段后再写服务端
