# 25 · 渠道段与远程配置（卡 #17）

**一句话结论**：这两件一直挂在"外部依赖"名下的东西都不是外部依赖。渠道号是**自家打包环节写进 APK
签名块的一段 JSON**，远程配置是**自家域名的一个 HTTP GET**。读侧与写侧都已还原并自检，
剩下只有"装到真机上让 app 自己读一次"。

卡型：还原 + 落地（无新屏）。独占文件：`net/.../ApkSigningBlock.kt`、`net/.../ChannelTagger.kt`、
`net/.../ConfigService.kt`、`app/.../data/local/SigningBlockInstallChannel.kt`、
`app/.../data/local/StoredRemoteConfig.kt`、`app/.../data/local/InstallChannel.kt`、
`app/.../RecoveryProbeActivity.kt`。

---

## 一、读侧：`utils.p` → 签名块，逐条对得上

原版链路（1.5.6 包名 `hc`，1.6.6 同一套改叫 `kc`；只列 1.5.6 的行号）：

| 步 | 出处 | 做了什么 |
|---|---|---|
| `utils.p.d()` | `utils/p.java:33` | 对外只有一个渠道号；值取自 `f66996b`（`wi.h0.b` = lazy，**进程内只读一次**） |
| `p.c()` | `utils/p.java:22-25` | `hc.i.d(context, "0")`，null 再兜一次 `"0"` |
| `hc.i.d/e` | `hc/i.java:42-54` | `applicationInfo.sourceDir` → `File` → `hc.d.a(file)` |
| `hc.d.a` | `hc/d.java:17-25` | 摊平成 Map 后，把 `channel` 键单拎出来，**其余键留在 `hc.c.b()`** |
| `hc.d.b` | `hc/d.java:27-45` | `new JSONObject(字符串)`，逐 key `getString` → `Map<String,String>`；`JSONException` → null |
| `hc.f.d/c/a` | `hc/f.java:16-23,96-107` | 按 pair id 取字节 → `new String(bytes, "UTF-8")`；`RandomAccessFile(file, "r")`，异常全吞 → null |
| `hc.a.f` | `hc/a.java:105-128` | 遍历签名块全部 pair：`[len:8][id:4][data]`，`len` 含 id；`LinkedHashMap<Integer,ByteBuffer>` |
| `hc.a.c/b/d/h` | `hc/a.java:57-103,151-182` | 定位 EOCD → 读 CD offset → 回退 24 字节验 `APK Sig Block 42` 与首尾 size 一致 |

### `hc.a` 就是美团 Walle 的 `ApkUtil`

2026-11-04 拉 Walle 上游 `payload_reader/src/main/java/com/meituan/android/walle/ApkUtil.java` 逐常量对照，
`hc.a` 的 12 个常量**全部命中**：

| 原版 | 值 | Walle 里的名字 | app 是否使用 |
|---|---|---|---|
| `f71818g` | `1903654775` = `0x71777777` | `APK_CHANNEL_BLOCK_ID` | **用**（`hc.d.c`） |
| `f71815d` | `1896449818` = `0x7109871A` | `APK_SIGNATURE_SCHEME_V2_BLOCK_ID` | 不用 |
| `f71816e` | `1114793335` = `0x42726577` | `VERITY_PADDING_BLOCK_ID` | 不用 |
| `f71812a` / `f71813b` | 两个 long | `APK_SIG_BLOCK_MAGIC_HI/LO`（`APK Sig Block 42` 的小端高低半） | 用 |
| `f71814c` `f71817f` `f71820i` `f71821j` `f71822k` `f71823l` | 32 / 4096 / 22 / `0x06054b50` / 65535 / 20 | 块最小长 / 页对齐 / EOCD 最小长 / EOCD 魔数 / uint16 上限 / 注释长字段偏移 | 用 |

结论有两条，方向相反，都要记：

1. **打包环节是 Walle 形状**（号段、块布局、EOCD 扫描全部来自 Walle）；
2. **payload 不是 Walle 的**。Walle 往 `0x71777777` 里写它自己的二进制 payload（长度前缀的 key/value），
   而 `hc.d.b` 是把这段字节直接当 JSON 解。所以**不能用 Walle gradle 插件打标**——写进去的原版读不出来。
   重建里的写入端因此是自己实现的（`ChannelTagger`）。

---

## 二、硬事实：**两个原包都带这段**，内容一致

2026-11-04 直接在盘上解析 `_raw/com.youloft.watcher1.6.6.apk` 与 `_raw/com.youloft.watcher1.5.6.rebuilt.apk`
的签名块（`size`/CD offset/魔数/首尾 size 全部核对通过）：

```
1.6.6  size=127516180  cd=127243827  block_size=16406  pairs=4
  0x7109871A  v2 签名          1306 B
  0x504B4453  未知段           14527 B     ← 文件内字节序 "SDKP"，归属待查
  0x42726577  verity padding   483 B
  0x71777777  {"channel":"3305"}   18 B

1.5.6  size=124775328  cd=124510053  block_size=16406  pairs=4
  0x7109871A  1306 B / 0x504B4453  14439 B / 0x42726577  571 B / 0x71777777  {"channel":"3305"} 18 B
```

这条为什么值钱：

1. 打包脚本已经丢了，但**它的输出格式被完整还原**——18 字节、UTF-8、无空格、`channel` 单键；
2. **线上渠道是 `3305`**，而 `utils.p` 里比较的是 `3801 / 3300 / 3301 / 3302 / 3303 / 3304 / 4000`
   （1.6.6 `p.java:36-72`，其中 `j()` 比的是 `utils.e.f66469f = "4000"`）——**一个都不命中**：
   加友页底提示 `AddFriendTipsPolicy` 返回 null，任何渠道特判都不开；
3. 顺带钉死了 #15 只能记成"改判了"的那条差异，见第五节。

`0x504B4453` 那 14 KB 的段我**没有猜**：既不是 Walle 的号段也不是 apksig 的已知号段，内容高熵，
两包都有。列进待查（DESIGN 第九节第 42 条）。

---

## 三、写侧：打完段**不用重签**（实测）

`ApkSigningBlock.stamp(source, target, id, payload)` 重排文件为
`[ZIP entries][APK Signing Block][Central Directory][EOCD]`，并重写 EOCD 里的 CD offset。

拿我们自己的 `app-debug.apk` 走完整命令：

```
$ bash tools/gradle.sh --offline :net:tagChannel --args="<apk> 3305"
tagged demo-debug.apk: channel=3305 extras={}

$ apksigner verify -v <stamped>
Verifies
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme: false
Signer #1 certificate DN: C=US, O=Android, CN=Android Debug      ← 与打标前同一张证书

$ unzip -t <stamped> | tail -1
No errors detected in compressed data of …

签名块：0x7109871A(1390) + 0x42726577(2650) + 0x71777777(18)
```

原理：v2/v3 的摘要只覆盖**平台自己的** pair，额外 pair 在签名数据之外——这条在 #11 那轮已经量过一次，
本轮把它变成"我们也能打"。注意 AGP 打的包本来就有 verity padding 段，所以打完与原包结构一致，只多一段渠道。

自检不是玄学：`ChannelTagger` 打完立刻用 `jsonSection` 读回来比对，读不回同样字符串就 `check` 失败。

---

## 四、配置服务身份：`of.b` / `nf.b` 是自己写的 OkHttp 客户端

`of/b.java`（1.5.6，300 行）+ `ConfigUtils.java`（209 行）读全后逐条还原，且每条都做了只读实测：

| 事实 | 出处 / 实测（2026-11-04） |
|---|---|
| 地址 `cfg.51wnl-cq.com/api/getallconfig.ashx` **现在 302** 到 `configsys.51wnl-cq.com/api/config/getconfigs?appid&appver&lastupdate` | `of.b.f76660d`；实测 302 且保留 query |
| `appid` 恒 `android-watcher`；**`appver` 1.5.6 发 `"156"`、1.6.6 发 `"166"`** | `ConfigUtils.java:54` vs 1.6.6 `ConfigUtils.java:59`；实测两个 appver 回**同一份** `Parameter_Map` |
| 回包 `{"status":1,"r":17533440860101,"rver":"156_1753344086_101010100","msg":{"Parameter_Map":"<base64>"}}` | 实测原文（`recovered/live_config_sample_2026-11-04.json`，net 测试资源同名钉住） |
| `msg` 里**每个值都是 base64**，逐键摊进设置 | `of.b.d` = `Base64.decode(str, DEFAULT)`；`of.b.o:283-285` `SettingProvider.E(context, key, d(value))` |
| **令牌是 `r`**，存 `online_lastupdate` | `of.b.o:273-277`：`getString("r")` 立刻被 `getLongValue("r")+""` 覆盖（前一行是废的）；**实测**带 `lastupdate=<r>` 服务器回 `{"msg":{},"status":1,"r":<same>}` |
| 节流两条：`online_lastrequest_ver` ≠ 当前 appver ⇒ 清空令牌走全量；否则 `abs(now - online_lastrequest) < 600000` 直接 return | `of.b.o:247-253` |
| 拦截器追加设备身份参数：`bd`=包名、`cid`=`Youloft_Android`（`of.c` 默认值）、`av`=版本名、`chn`=渠道**加 `"-0"`**、`ov`=`Build.VERSION.RELEASE`；`did`/`cityCode` 原版留空；app 的 `of.d` 扩展点是**空实现** | `of.b.l:188-230`、`of/c.java:25-28`、`ConfigUtils$a.c():47` |
| 拉取时机：**启动**。`SdkInitManager:435` → `ConfigUtils.m()` → `of.b.j(ctx, provider)` + `of.b.n()`（`f76659c` 防重入） | 重建**没照搬**，见第八节 |
| `showPermissionChannel` 在 1.6.6 已成**死键** | 1.6.6 `ConfigUtils` 只剩通用 `j(key)`，`o()/n()` 整条没了；1.6.6 全部 app 代码 grep 不到该串。`registerAfterShowPermission` **两版都没读过** |

18 个键里真被 1.5.6 代码引用的：`showPermissionChannel`、`guard_triggerCount`、`im_triggerDays`、
`linkupCooldown`、`chargingDelay`、`wifiConnectionDelay`、`screenLockUnlockDelay`、
`enableAniWhenMarkerMoveDistance`、`scheduleReportPeriod`；调用点都写死默认值，配置只是覆盖。

---

## 五、两条权限判据，现在有了真值

| | 1.5.6 | 1.6.6 |
|---|---|---|
| 判据 | `ConfigUtils.n()`：列表含本渠道 **或** 含 `p.b()`（恒 `"-1"`）| `p.h()`：`channel == "3301"` |
| 调用点 | 6 处：`AddFriendActivity:351`、`ContactInfoListActivity:246`、`SearchFriendActivity:330`、`FriendRequestListActivity:388`、`FriendRequestDetailActivity:175`、`FriendRequestDialog:206` | 4 处（#15 已记） |
| 对线上 `3305` 包 | 今天的列表 `["3300","3301","-1"]` 含 `-1` ⇒ **恒弹**（对所有渠道） | `3305 != 3301` ⇒ **恒不弹** |

也就是说"换判据"不是等价重构：**这次改动让线上所有包从此不再问权限**。
重建包按 1.6.6（`askPermissionsAfterAdd`），同时把 1.5.6 那条留在 `asksAfterAddFriendByConfig()` 里
并写清了它解释的是"这个配置键当年干什么用"——两条都有测试。

---

## 六、落在代码里

**`:net`（纯 JVM，可 CLI）**
- `ApkSigningBlock.kt`：`pairs` / `jsonSection` / `zipComment` / `stamp`，块布局与常量按第一节逐条对齐；
- `ChannelTagger.kt` + `net/build.gradle.kts` 的 `tagChannel` 任务：`gradle :net:tagChannel --args=<apk> <渠道> [k=v…]`；
- `ConfigService.kt`：URL、base64 摊平、**`r` 令牌**、两条节流（`shouldFetch` / `lastUpdateFor` / `isStale`）、
  设备参数 `params`、`APP_VERSION="166"`（`LEGACY_APP_VERSION="156"` 留作证据）。

**`:app`**
- `SigningBlockInstallChannel.kt`：对应 `hc.i`/`hc.c`——`channel` 单拎、其余进 `extras()`、段缺失回 `"0"`；
  `from(context)` 取 `applicationInfo.sourceDir`；
- `StoredRemoteConfig.kt`：读侧（`Parameter_Map` → `stringList`）+ 写侧 `writeConfigFetch` +
  `refreshRemoteConfig`（令牌回显、空 `msg` 只盖时间戳）。三个存储键名照搬 `online_lastupdate` /
  `online_lastrequest` / `online_lastrequest_ver`（原版的 `configLastFetchAt` 是我上一轮的发明，已换成真名）；
- `InstallChannel.kt`：`PermissionChannelGate` 两条规则并存；`AddFriendTipsPolicy` 四个号；
  `PendingRemoteConfig` 占位类删除；
- `FriendRepository.kt`（图）：`installChannel` = 签名块读数、`remoteConfig` = 存储读数、
  `configService` 带上第一节的五个设备参数；
- `AndroidDeviceContext.kt`：签名里的 `channel` 与 UI 判据**同一个来源**（`channels?.id()`）。
- `RecoveryProbeActivity.kt`：多打两节 —— 本机 APK 的渠道读数（id/extras/提示/1.6.6 判据）与
  一次真配置拉取（URL、该不该拉、令牌回显、存下来的 `showPermissionChannel`、1.5.6 判据）。

---

## 七、验收（可复制执行）

```bash
bash tools/gradle.sh --offline :net:test :app:testDebugUnitTest :app:assembleDebug
# 期望：:net 29 / 0（ApkSigningBlock 9 + ConfigService 10 + 封套 3 + 模型 2 + 签名 5）
#      :app 197 / 0（SigningBlockInstallChannel 4、LocalCacheTest 13）→ 合计 226 全绿

bash tools/gradle.sh --offline :net:tagChannel --args="app/build/outputs/apk/debug/app-debug.apk 3305"
# 期望末行：tagged app-debug.apk: channel=3305 extras={}

java -jar "$ANDROID_SDK/build-tools/35.0.0/lib/apksigner.jar" verify -v \
     app/build/outputs/apk/debug/app-debug.apk | head -3
# 期望：Verifies / v2 = true

unzip -t app/build/outputs/apk/debug/app-debug.apk | tail -1     # 期望：No errors detected
```

装机验收（我做不了，见 DESIGN 第九节 40-42）：装打标后的包 → 开探针页 →
应显示 `channel.id=3305`、`stamp extras={}`、`addFriendTips=null`、`askPermissionsAfterAdd=false`，
配置那节应显示 `showPermissionChannel=["3300","3301","-1"]`。

---

## 八、没做完 / 等你拍板

1. **启动时自动拉配置没有照搬**。原版 `SdkInitManager` 启动就拉；重建里只有探针页手动拉
   （`refreshRemoteConfig` 已备好在图上调）。要不要跟、以及"同意隐私政策之前是否允许打这个域名"，
   是产品/合规决定，不是我能从 APK 里读出来的。
2. **发布链要不要自动打标**（`assembleRelease` 之后跑 `tagChannel`）。本轮只把写侧做成可跑的命令。
3. **重建包该打哪个渠道号**：按线上取 `3305` 最保真；若想让新包继续问权限，得打 `3301` 或改回 1.5.6 判据。
4. `0x504B4453` 段归属、`3305` 是哪个分发渠道、打包环节是否还有别的步骤：三条都只能问 CI/运维。
5. `hc.c.b()`（extras）在原包里只有一个键，`extras()` 恒空；实现它是因为原版结构就是这样，不代表线上有数据。
