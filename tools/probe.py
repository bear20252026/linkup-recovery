# -*- coding: utf-8 -*-
# LinkUp API 探测：用已验证的签名算法检测各后端存活与协议状态（只发只读 GET）
import time, json, hashlib, socket
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

KEY = IV = b"be2524844ec4bb25"
UA = "okhttp/4.9.3"

def aes_hex(s):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(s.encode(), 16)).hex()

def sign(s):
    return hashlib.md5(aes_hex(s).encode()).hexdigest()

def get(host, path, params=None, signed=True, timeout=10):
    qs = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    si = f"{path}?{qs}"
    url = f"https://{host}{path}" + (f"?{qs}" if qs else "")
    h = {"Accept": "application/x-protobuf", "User-Agent": UA, "origin": "ANDROID_SDK"}
    if signed:
        h["Signature"] = sign(si)
    try:
        r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
        body = r.content[:300].decode("utf-8", "replace")
        return f"[{r.status_code}] {body}"
    except Exception as e:
        return f"ERR {e}"

def dns_try(host, port=443):
    try:
        ip = socket.gethostbyname(host)
        s = socket.create_connection((host, port), timeout=5)
        s.close()
        return f"ALIVE ip={ip}"
    except Exception as e:
        return f"DEAD {type(e).__name__}: {e}"

print("===RESULT_BEGIN===")
base = {"app_id": "linkup", "platform": "android", "version": "1.6.6"}

print("\n-- 1) linkup-test /api/client/config 带 av 参数 --")
for av in ("1.6.6", "v1", "166"):
    p = dict(base, ts=str(int(time.time())), av=av)
    print(f"av={av!r}:", get("linkup-test.51wnl-cq.com", "/api/client/config", p))

print("\n-- 2) configsys 配置服务（找生产API地址）--")
for extra in ({"appid": "linkup", "os": "android", "ver": "1.6.6"},
              {"app_id": "linkup", "platform": "android", "version": "1.6.6"},
              {"appid": "watcher"}):
    print(f"params={extra}:", get("configsys.51wnl-cq.com", "/api/config/getconfigs", extra, signed=False))

print("\n-- 3) 生产环境候选主机连通性 --")
for h in ("linkup.51wnl-cq.com", "api.51wnl-cq.com", "watcher.51wnl-cq.com",
          "guard.51wnl-cq.com", "im.51wnl-cq.com", "linkup-api.51wnl-cq.com",
          "api.tttick.com", "watcher.tttick.com"):
    print(f"{h}:", dns_try(h))

print("\n-- 4) dmp 定位上报服务签名探测 --")
print("dmp /api/client/config:", get("dmp.51wnl-cq.com", "/api/client/config", dict(base, ts=str(int(time.time())), av="1.6.6")))
print("dmp / :", get("dmp.51wnl-cq.com", "/", {}, signed=True))
print("===RESULT_END===")
