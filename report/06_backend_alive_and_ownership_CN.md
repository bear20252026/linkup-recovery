# LinkUp 第 6 号报告：后端归属澄清 + 生产 API 其实还活着

> 日期：2026-11-02
> 承接：`report/03`（服务器探测）、`report/04`（1.6.6 协议破解）、`report/05`（本地重建）
> 本报告**推翻 `report/05` 第六节的一个判断**，并给出两条改变排期的事实。

---

## 一、归属：我方就是万年历 / 重庆可兰达本体

`report/05` 第六节从 RDAP 看到三个域名的注册主体后，推断"后端与 Jenkins 可能属于对面公司，
所以不去探测那台机器的管理面板"。**这个推断是错的**：我方就是万年历 / 重庆可兰达这个主体本身，
本次是自家部门人员操作失误导致源码大范围错乱。

因此：后端服务、Jenkins CI、生产库、各三方平台后台（微信开放平台 / QQ 互联 / 环信 / 百度地图 /
小米华为荣耀OPPOvivo魅族个推Mob / 穿山甲广点通百度联盟快手AnyThink / 数数 / 阿里云SLS / 友盟Bugly）
**全部归我方**。找回它们属于正当自救，不需要对外授权流程。

RDAP 事实（仍然有效，只是主体是我方）：

| 域名 | 注册 | 到期 | 注册商 |
|---|---|---|---|
| 51wnl-cq.com | 2016-01-13 | **2029-01-13** | Alibaba Cloud Computing (Beijing) |
| 51wnl.com | 2011-08-26 | **2028-08-26** | 同上 |
| tttick.com | 2017-09-12 | **2027-09-12** | 同上 |

三条都续费到 2027–2029 ⇒ 后端资产仍在付费维护，不是被放弃的产品。

## 二、重大发现：生产业务 API 活在 `link.tttick.com`

`report/03` 把 `link.tttick.com` 记成"深链服务"，于是结论变成"生产 API 已下线，只剩测试环境"。
本轮实测：**这个域名同时路由 `/api`，而且返回的是另一套环境的真实数据**。

重建的 `:net` 客户端直接打它（不是用旧 APK，是新建的 Kotlin 代码）：

```
$ gradle :net:liveVerify --args=https://link.tttick.com/
clientConfig -> status=200 msg=success
               dataKeys=[notRelativesLockShow, halfScreenVipPageShow, vipMarketingCopy, ifCheckRegin,
                         profileSkipButton, autoReportAddressShow, imGroupHuawei, imGroupIos …]
userInfo     -> HTTP 401 (reached business layer, auth required)
versionCheck -> HTTP 401 (reached business layer, auth required)
PROTOCOL_RECOVERED=1
```

判定它是独立环境而非测试服的镜像：同一键 `notRelativesLockShow` 在测试服是 `true`，在这里是 `false`。

各主机实测角色（只读，**未碰任何写接口**，`/api/sms/send` 之类一律没发，避免触发真实短信）：

| 主机 | 实测 |
|---|---|
| `link.tttick.com` | **业务 API 活着**：config 200，`user/info`、`vip/index`、`version/check`、`sensitive/server_timer` 均 401 permission denied |
| `linkup-test.51wnl-cq.com` | 业务 API 活着，且强制校验 Signature |
| `linkup.51wnl-cq.com` | 只剩火山引擎 OSS 静态桶：`{"Code":"NoSuchKey"}`，`server: Byte-nginx` |
| `dmp.51wnl-cq.com` | 只有定位上报（Go，`404 page not found`） |
| `score.51wnl-cq.com` | IIS 默认页 |
| `configsys.51wnl-cq.com/api/getallconfig.ashx` | 404（`cfg.` 那台返回 55 字节空配置，服务端已不靠它下发） |
| Jenkins | **公网不可达**：`linkup-test…/login`、`/jenkins/login` 均 404，`139.129.22.130:8080` 外部连不上 |

### 对排期的直接影响

1. **后端不需要重写。** `report/00` 里"最大不确定性在后端"这一条可以划掉。
2. **97 条路由的字段可以在生产服逐条打出来**，不用靠 1.5.6 猜、也不用抓包对齐。
3. 服务端 Go 源码（Jenkins job `desyb_always_guard.api`）现在的价值是"维护与还原精度"，
   不再是"能不能上线"的前置条件。要找的是内网 CI 与 git 地址，不是对外沟通。

## 三、要报给安全/运维的一条

`link.tttick.com` 这台网关**没有启用 Signature 中间件**：不带 `Signature` 头的请求照样进业务层
（同一请求在测试服会被 `参数异常1001` 拒）。也就是说线上 API 现在只有 JWT 一道闸，
客户端硬编码密钥 `6R4aXTSK3OghHIgA` 在这台上形同虚设——脚本可以直接打线上接口，
只要不碰需要登录态的路由就一路绿灯（例如 `/api/client/config` 无签名返回 200）。

客户端侧继续按已还原算法签名，不受影响。**要不要在生产网关补齐签名校验，请单独拍板**：
补齐才挡得住脚本，但会让所有"没带 Signature 的老客户端/H5 直连"失败，需要先摸清还有哪些调用方。

## 四、另一条已确认的发布事故

1.6.6 把测试服地址 `ag.a.f1732c = "https://linkup-test.51wnl-cq.com/"` **硬编码进了正式包**，
即线上客户端一直在打测试环境。重建工程已把地址收敛到 `LinkUpEndpoints`
（`PRODUCTION` / `API` / `TRACKER_LEGACY`）并默认走生产，不要再复制这个写法。

## 五、代码与文档同步

- `rebuild/net/.../LinkUpClient.kt`：新增 `LinkUpEndpoints.PRODUCTION = "https://link.tttick.com/"`
- `rebuild/net/.../LiveVerify.kt`：支持 `--args=<baseUrl>`，两台都可验
- `rebuild/recovered/DESIGN_CN.md`：新增第七节"后端现状"，架构决定补第 7 条（baseUrl 分环境），
  待验清单第 5 项标记为已答
- 验证状态：`gradle :net:test` 5 tests / 0 failures；`:net:liveVerify` 两台均 `PROTOCOL_RECOVERED=1`；
  `:app:assembleDebug` 产出 17.9MB APK
