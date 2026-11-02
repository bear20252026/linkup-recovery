# -*- coding: utf-8 -*-
# v2: 利用服务端校验行号做黑盒协议恢复（只发只读请求）
import time, json, hashlib, itertools
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

KEY = IV = b"be2524844ec4bb25"
UA = "okhttp/4.9.3"
H = "linkup-test.51wnl-cq.com"

def aes_hex(s):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(s.encode(), 16)).hex()

def sign(s):
    return hashlib.md5(aes_hex(s).encode()).hexdigest()

def req(path, params, sig_in_mode="pathqs", sig_place="header", method="GET", body=None):
    ts = str(int(time.time()))
    p = dict(params); p["ts"] = ts
    if "av" not in p: p["av"] = "1.6.6"
    qs = "&".join(f"{k}={p[k]}" for k in sorted(p)) if p.get("_sorted") else "&".join(f"{k}={v}" for k, v in p.items() if not str(k).startswith("_"))
    p2 = {k: v for k, v in p.items() if not str(k).startswith("_")}
    if p2.get("_sorted"):
        p2.pop("_sorted"); qs = "&".join(f"{k}={p2[k]}" for k in sorted(p2))
    else:
        qs = "&".join(f"{k}={v}" for k, v in p2.items())
    si = {"pathqs": f"{path}?{qs}", "qsonly": qs, "pathonly": path}[sig_in_mode]
    sg = sign(si)
    headers = {"User-Agent": UA, "origin": "ANDROID_SDK"}
    if sig_place == "header": headers["Signature"] = sg
    url = f"https://{H}{path}?{qs}"
    if sig_place == "query": url += f"&sign={sg}"
    try:
        if method == "POST":
            r = requests.post(url, headers=headers, data=body, timeout=10)
        else:
            r = requests.get(url, headers=headers, timeout=10)
        return f"[{r.status_code}] {r.content[:200].decode('utf-8','replace')}"
    except Exception as e:
        return f"ERR {e}"

BASE = {"app_id": "linkup", "platform": "android", "version": "1.6.6", "channel": "official", "uid": "0", "deviceId": "probe0001"}
print("===P2_BEGIN===")
print("-- A) 逐个去参定位 1003 --")
for drop in ("", "channel", "uid", "deviceId", "app_id", "platform", "version"):
    p = {k: v for k, v in BASE.items() if k not in drop.split()}
    print(f"drop={drop or 'none':9}:", req("/api/client/config", p))
print("-- B) 签名位置变体 --")
print("query :", req("/api/client/config", BASE, sig_place="query"))
print("-- C) 签名输入变体 --")
for m in ("qsonly", "pathonly"):
    print(f"{m:9}:", req("/api/client/config", BASE, sig_in_mode=m))
print("-- D) 排序参数 --")
p = dict(BASE); p["_sorted"] = 1
print("sorted :", req("/api/client/config", p))
print("-- E) POST 变体 --")
print("post   :", req("/api/client/config", BASE, method="POST", body=json.dumps(BASE)))
print("-- F) 其他路由 --")
for path in ("/user/login", "/vip/index", "/config"):
    print(f"{path:12}:", req(path, BASE))
print("===P2_END===")
