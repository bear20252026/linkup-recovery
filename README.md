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
