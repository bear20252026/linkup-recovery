# LinkUp 后端服务器探测报告
探测时间：2026-11-02（北京时间 2026-11-02 下午）
方式：DNS + HTTPS 直连 + 带签名的只读 GET 探测（密钥 be2524844ec4bb25，算法与客户端一致）

## 一、结论：服务器都在

| 主机 | IP | 状态 | 说明 |
|---|---|---|---|
| linkup-test.51wnl-cq.com | 139.129.22.130 | 🟢 在线 | **测试环境主 API，签名中间件正常工作** |
| dmp.51wnl-cq.com | 47.104.110.90 | 🟢 在线 | 定位上报服务（Go） |
| web-link.tttick.com | 111.4.224.113 | 🟢 在线 | 静态/协议页 |
| link.tttick.com | 47.105.44.122 | 🟢 在线 | 深链服务 |
| score.51wnl-cq.com | 118.190.181.4 | 🟢 在线 | 积分服务 |
| cfg/configsys.51wnl-cq.com | 115.28.254.36 | 🟢 在线 | 配置服务（302 迁移到 configsys） |
| lovetest-oss-volcengine.51wnl-cq.com | — | 🟢 在线 | 火山引擎 OSS 静态资源 |
| **linkup.51wnl-cq.com（生产）** | 111.19.148.139 等 | ⚠️ 异常 | **现指向火山引擎 OSS 静态桶，API 请求返回 NoSuchKey——生产 API 已不在该域名** |

候选生产域名 api./watcher./guard./im./linkup-api.51wnl-cq.com、api./watcher.tttick.com 均不存在（DNS 不解析）。

## 二、关键证据
1. 测试服 `/api/client/config` 响应泄露后端信息：
   - 服务名 always_guard.api（"守护API"，与 App 内 tab_guard 一致）
   - CI 路径 /var/jenkins_home/workspace/desyb_always_guard.api
   - 校验链 signature.go:31（av 格式）→ :40（query 签名分支）→ :61（1003 签名校验）
2. av=1.6.6 通过格式校验（av=v1/166 被拒）→ 测试服仍按 1.6.x 协议族运行
3. /user/login、/vip/index、/config 在测试服 404 → 路由表与 1.5.6 时代端点不同
4. 生产域名现返回 OSS NoSuchKey（RequestId ba4d07e8...）→ 生产 API 已下线或迁移到动态下发地址

## 三、对重建工作的影响
- 后端测试环境完整存活：客户端协议（签名算法、参数名）可在测试服上反复验证——**重建的网络层有活的"判卷老师"**
- 生产 API 疑似停服/迁移：需向公司确认生产后端现状与服务器源码归属（见行动清单第 2 项）
- 精确签名格式（1001/1003 的最后一步）待 Mac 上 jadx 反编译 1.6.6 的 OkHttpManager 后一击即中

## 四、探测工具
- tools/probe.py、tools/probe2.py、.github/workflows/sig.yml（已推送到 github.com/bear20252026/linkup-recovery）
- 运行方式：GitHub Actions 手动触发（仓库公开、免费额度）；日志即报告
