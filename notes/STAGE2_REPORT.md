# LinkUp 逆向 Stage 2 — 网络协议 / 签名 / 凭证泄漏

> 工具：androguard 4.1.3 + ELF Analysis (pyelftools)  
> 范围：网络栈定位、签名算法逆向、加密密钥提取、凭证泄漏审计  
> 时间：2026-05-19

---

## 一、网络栈架构

| 层 | 实现 |
|---|---|
| 主统一入口 | `com.youloft.yftracker.helpers.OkHttpManager` (单例) |
| HTTP 客户端 | 原生 OkHttp3（**未使用 Retrofit**——`retrofit2.Retrofit$Builder.<init>` 无业务调用方） |
| 配置 | `com.youloft.yftracker.Constant.INSTANCE.getBaseUrl()` （prod = `https://dmp.51wnl-cq.com`） |
| 调试切换 | `xf.b.a.e()` true → `https://dmp-test.51wnl-cq.com` |
| 业务包 OkHttp.newCall 调用方 | 仅 6 处：yftracker.OkHttpManager + manager.j3$e (语音下载) + manager.r2 (查公网IP) + pages.test.TestLocationMockActivity + utils.download.c + com.byazt.kg.* (字节内置) |
| **业务包内 Interceptor 数量** | **0 — 完全没有自定义 OkHttp 拦截器** |

> ✅ 结论：**LinkUp 几乎所有业务请求统一走 `OkHttpManager`**，签名逻辑集中在 `addCommonHeader` 一处。

---

## 二、签名算法（**完整破解**）

### 2.1 算法定义（来自 `EncryptUtils`）

```java
// 静态常量
KEY = "be2524844ec4bb25"   // 16-byte UTF-8 (不是 hex 解码, 直接当字节用)
IV  = "be2524844ec4bb25"   // 16-byte UTF-8  ← KEY == IV (实现弱点!)
AES_ALGORITHM = "AES/CBC/PKCS5Padding"
CHARSET = "UTF-8"

// 算法
aes128Encrypt(s): String = bytesToHex( AES-128-CBC-PKCS5(UTF8(s), KEY, IV) )
md5(s):           String = lowerHex(MD5(UTF8(s)))   // 32 字符小写

signatureGet(s):  String = md5( aes128Encrypt(s) )
```

### 2.2 加签流程（来自 `OkHttpManager`）

```java
addCommonHeader(signInput, requestBuilder):
   requestBuilder.addHeader("Signature", signatureGet(signInput))
   requestBuilder.addHeader("origin", "ANDROID_SDK")
```

### 2.3 请求模板

| 方法 | 签名输入 | 是否签名 | URL 拼接 |
|---|---|---|---|
| `getAsync(path, params, headers)` | `path + "?" + k1=v1&k2=v2…`（与 GET querystring 一致） | ✅ 有 | `appendUrl(path?qs)` |
| `postAsync(path, params)` (form) | (无) | ❌ **未签名** | `appendUrl(path)` |
| `postProtoAsync(path, bytes, headers)` | `path + md5(bytes)` | ✅ 有 | `appendUrl(path)` |

> `appendUrl(p)` = `if p.startsWith("http") return p else return baseUrl + p`

### 2.4 PoC 已验证

```python
# notes/poc_yftracker_sig.py
signatureGet("/api/v1/location/report") = "41883b37518449ec376615b19530d9b6"
signatureGet("/api/v1/friend/list?uid=12345") = "dad2a45d58dd0042a52b7af6e1504434"
```

---

## 三、🚨 **凭证泄漏（高危）**

### 3.1 微信 AppSecret 直接出现在 APK 中
```java
// com.youloft.watcher.manager.SdkInitManager.B()
PlatformConfig.setWeixin(
    "wxccdc26e51e8c56ce",                  // AppID
    "1d157c6aebeb3c4a6734e2e64797a290"     // ⚠️ AppSecret 直写客户端
)
```

> **严重违规**：微信开放平台明确禁止 `AppSecret` 出现在客户端。任何持有 APK 的人都能：
> - 拿用户 `code` 换 `access_token`（绕过服务端）
> - 用 `unionid` 关联跨应用账号
> - 调用受限的 OAuth 接口
> 
> 这属于 **OWASP MASVS-CRYPTO-1 / MSTG-CRYPTO-1 — 密钥未存储在受保护位置**。

### 3.2 QQ 互联 AppKey 直接出现
```java
PlatformConfig.setQQZone(
    "102361775",                                   // AppID
    "IznPzr5t3Jic2Zt1F94l2VOMAbNalFuV"             // AppKey
)
```

### 3.3 ThinkingData AppID + 服务地址
- AppID `c0b19c51c663417dbb490fd8245957ad`
- Server `https://ss.51wnl.com`

### 3.4 YfTracker AES 密钥固定 + KEY==IV
- 见 §2.1，密钥写死 `be2524844ec4bb25`，无密钥轮换
- KEY == IV 是 AES-CBC 实现错误（使可预测的 ciphertext block / replay 风险变大）

### 3.5 release 包遗留开发环境配置
```
com.youloft.watcher.utils.ConfigUtils → http://192.168.1.110:8005/api/config/getconfigs
```
- **明文 HTTP 协议** + **内网 IP** 进入了 release 包
- 暗示存在条件触发的内网回退分支，应排查是否在某状态下真的命中

### 3.6 release 包内嵌位置测试入口
```
com.youloft.watcher.pages.test.TestLocationMockActivity
   → https://lovetest-oss-volcengine.51wnl-cq.com/watcher/CMS/test/location.txt
```
- 同时还有 `TestConfigActivity / TestLocationStatusActivity / TestLocationUpdateActivity`
- Stage 3 需用 `adb shell am start` 验证是否 exported 且可触发

---

## 四、Native 层定位

| .so | 实质 | 与业务关系 |
|---|---|---|
| **libtobEmbedEncrypt.so** | 字节系 BDSword AES-CBC-PKCS7 + SHA512 | `com.byakv.z.TTEncryptUtils`（穿山甲请求加密，**不是 LinkUp 业务签名**） |
| **libzxprotect.so** | 含 75 个 JNI 在 `com.zx.a.I8b7.*` 包 | 第三方号码认证/设备认证 SDK（`com.zx.sdk.api.ZXManager` 入口），与 LinkUp 业务签名**无关** |
| libcipherdb.so | SQLCipher | 环信 IM 本地消息加密库 |
| libhyphenate.so | 环信 IM 核心，842 JNI | 即时通讯运行时 |
| libsgcore.so | 快手 SGCore (反作弊) | 广告 SDK 支撑 |
| libturingad.so | 图灵盾设备指纹 | 反作弊 |
| libumeng-spy.so | 友盟设备 ID | 三方统计 |

> ✅ 结论：**LinkUp 业务签名完全在 Java 层（AES+MD5），不需要 hook native 库**。Frida 直接 hook `EncryptUtils.aes128Encrypt` 或 `OkHttpManager.signatureGet` 即可。

---

## 五、域名清单（业务相关）

| 域名 | 用途 | 协议 |
|---|---|---|
| `https://dmp.51wnl-cq.com` | YfTracker 主上报/业务 API（prod） | HTTPS |
| `https://dmp-test.51wnl-cq.com` | YfTracker 测试环境 | HTTPS |
| `https://ss.51wnl.com` | ThinkingData 行为分析 | HTTPS |
| `https://lovetest-oss-volcengine.51wnl-cq.com` | 位置 Mock 测试资源 | HTTPS |
| `http://192.168.1.110:8005` | ⚠️ release 遗留开发环境 | **HTTP** |
| `http://api.ipify.org` | 第三方公网 IP 查询（manager.r2） | HTTP |

---

## 六、Stage 2 关键漏洞速览（Stage 3 完整审计前哨）

| 风险 | 等级 | 利用难度 | 影响面 |
|---|---|---|---|
| 微信 AppSecret 硬编码 | 🔴 严重 | 直读 APK | 跨应用账号关联、伪造服务端鉴权 |
| QQ AppKey 硬编码 | 🟠 高 | 直读 APK | QQ 互联接口滥用 |
| AES KEY == IV + 全应用固定 | 🟡 中 | 已 PoC | 任意签名伪造、构造合法请求 |
| GET 签名仅基于 URL（不含 body/timestamp） | 🟡 中 | 重放工具 | 重放攻击 |
| `postAsync` form POST 无签名 | 🟠 高 | 直接构造 | 任意 form 表单接口可伪造 |
| HTTP 明文 + 内网 IP 留在 release | 🟡 中 | 触发条件待定 | 信息泄漏、可能的 MITM |
| 调试 Activity 4 个 exported（待 Stage 3 验证） | 🟡 中 | `adb am start` | 位置 Mock 等敏感能力 |
| 签名 hex+md5 算法可在任意语言重现（Java/Python/JS） | — | 已 PoC | 完全替代官方客户端 |

---

## 七、下一步（Stage 3）

1. **抓包验证**：用 mitmproxy + Frida SSL Pinning bypass，捕获 LinkUp 真实请求，对比 `signatureGet` PoC
2. **接口客户端 PoC**：写 Python `requests` 客户端，跑通 1-2 个核心接口（如登录、好友列表）
3. **调试 Activity 触发测试**：`adb shell am start -n com.youloft.watcher/.pages.test.TestLocationMockActivity` 看是否真能起来
4. **OWASP MASVS / PIPL 合规审计**：把 Stage 1+2 发现汇总成结构化审计报告
5. **微信 AppSecret 利用面评估**：评估这个泄漏到底能干什么
