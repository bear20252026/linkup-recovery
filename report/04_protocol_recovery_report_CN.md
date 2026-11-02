# LinkUp 1.6.6 协议破解报告（已服务器实测验证）

日期：2026-11-02 ｜ 方法：GitHub Actions 反编译 + 真机协议重放

## 一、结论：服务器活着，而且"认"我们了

用 1.6.6 真实协议请求 `linkup-test.51wnl-cq.com`：

| 请求 | 结果 | 含义 |
|---|---|---|
| GET /api/client/config（带签名） | **200 success** 返回真实配置 JSON | 签名算法完全正确 ✓ |
| GET /api/user/info（带签名无token） | 401 JWT permission denied | 签名通过，卡在登录态（正常） |
| GET /api/client/config（不带签名） | 400 参数异常1001 | 签名中间件拦截（正常） |

判定链完整：Signature 中间件 → JWT 登录态 → 业务逻辑。服务器端三层全部在工作，只是**客户端密钥在 1.6.6 换了**，之前用旧密钥探测才一直失败。

## 二、1.6.6 签名算法（com.youloft.watcher.utils.a，即 AESCBCUtil.kt）

```
KEY = IV = "6R4aXTSK3OghHIgA"          ← 新密钥！（旧 be2524844ec4bb25 只剩定位SDK在用）
Signature 头 = hex( AES-128-CBC / PKCS7( UTF8(签名输入) ) )   ← 注意：不再套 MD5！
签名输入   = 请求路径 + "?" + 完整查询串        如 "/api/client/config?tz=480&..."
POST 附加  = 签名输入 += md5(请求体).toLowerCase()
密文解密   = 同密钥 AES-CBC-PKCS7 解 hex（b() 方法，用于解服务端加密响应）
```

### 拦截器 gh/d.java 注入的查询参数（固定顺序）
```
tz=时区偏移 & lang=语言 & userId=用户id & client=android & deviceId=设备id
& channel=渠道 & av=1.6.6 & t=毫秒时间戳 & distinctId=数数id & shushuDeviceId=数数设备id & mainUser=主用户id
```
旧版的 app_id / platform / version / ts 公共参数已全部废除。

### 豁免规则
路径含 `login` 或 `sms` 的请求：**不加 Signature 也不加 Authorization**（注册登录前本来就没有 token）。

### 完整请求头
```
User-Agent: okhttp/4.9.3
Authorization: <JWT token>        （除 login/sms 外）
Signature: <AES hex 签名>         （除 login/sms 外）
```

## 三、1.6.6 关键架构事实

1. **Retrofit 回归**：gh/a.java = Retrofit 接口，路由以 `api/...` 相对路径声明（无前导斜杠）
2. **API 基址硬编码测试环境**：`ag.a.f1732c = "https://linkup-test.51wnl-cq.com/"` —— 生产域名早已不解析，等于 1.6.6 上线时整个后端就只剩测试环境
3. **旧密钥仍在**：`com.youloft.yftracker.util.EncryptUtils`（be2524844ec4bb25）只服务 dmp.51wnl-cq.com 定位上报 SDK
4. RSA：`api/tool/rsa/public_key` 拉取公钥（好友加密聊天用，bean.friend.PublicKey）

## 四、完整路由表（gh/a.java，节选）

登录/用户：api/user/{login,info,logout,unregister,update/info,update/push/token,report/getui_cid,default_avatar,change_bind,cut/list,android/install_app,show/report}
短信：api/sms/{send,login/cut,click_to_login}
VIP：api/vip/index ｜ 版本：api/version/check
配置：api/client/config ｜ 工具：api/tool/{uploadLog,rsa/public_key}
设置：api/setting/{user_list,user_list_v2,update} ｜ 敏感：api/sensitive/user
好友：api/relation/lock/cover/del 等 ｜ 聊天：api/talk/* ｜ 语音：api/index/realtime/voice/delete
纪念日：api/anniversary/createOrEdit ｜ 天气：api/weather/baiduWeather ｜ 火山：api/volcano/token

## 五、三方密钥清单（ag/a.java，全部明文硬编码）

| 用途 | Key |
|---|---|
| 微信开放平台 AppID | wxccdc26e51e8c56ce |
| 微信 AppSecret | 1d157c6aebeb3c4a6734e2e64797a290 |
| QQ 互联 | 102361775 / IznPzr5t3Jic2Zt1F94l2VOMAbNalFuV |
| 其他密钥 | c0b19c51c663417dbb490fd8245957ad、c3yV6ripuyLiVZelKUM7LMNUgwnuHNT7、DcV64jyTOkq1TL0Yov9O9SSP8yiFd9EJ |
| 微信开放平台接入 | api.weixin.qq.com/sns/oauth2（客户端直调 access_token） |
| 企业微信客服 | ww27ba0a83db27b449 |
| 环信 IM | 1107210531203961#guardian |
| 百度静态图 | api.map.baidu.com/staticimage/v2 |

→ 重找三方账号时可直接用这些 AppID 向平台方发起主体认领。

## 六、代码恢复状态

- 完整 Java 源码：GitHub Actions 产物 `linkup-166-src`（28056 个文件，保留30天，仓库 Release 亦有 APK 分卷）
- 密钥轮换声明：like1097 的 `extract/` 只有资源，密钥源在我们自己的 APK，无需轮换（用户已确认不轮换）

## 附：本次使用的可复现脚本

- tools/probe3.py（仓库内）— 新协议验证
- 反编译 intelligence 通道：仓库 workflow dump.yml / decomp.yml
