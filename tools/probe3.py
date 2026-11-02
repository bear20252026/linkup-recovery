# -*- coding: utf-8 -*-
# probe3: 用 1.6.6 真实协议(新密钥+拦截器参数)验证 linkup-test
import time, requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

KEY = IV = b"6R4aXTSK3OghHIgA"
UA = "okhttp/4.9.3"
H = "https://linkup-test.51wnl-cq.com"

def sign(si):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(si.encode(), 16)).hex()

def get(path, extra=None):
    q = [
        ("tz", "480"), ("lang", "zh"), ("userId", "0"), ("client", "android"),
        ("deviceId", "probe0001device"), ("channel", "official"),
        ("av", "1.6.6"), ("t", str(int(time.time()*1000))),
        ("distinctId", "probe-dist-1"), ("shushuDeviceId", "probe-ss-1"), ("mainUser", "0"),
    ]
    if extra: q += extra
    qs = "&".join(f"{k}={v}" for k, v in q)
    si = f"{path}?{qs}"
    try:
        r = requests.get(f"{H}{path}?{qs}", headers={"User-Agent": UA, "Signature": sign(si), "Accept": "application/json"}, timeout=10)
        return f"[{r.status_code}] {r.content[:400].decode('utf-8','replace')}"
    except Exception as e:
        return f"ERR {e}"

print("===P3_BEGIN===")
print("signed /api/client/config :", get("/api/client/config"))
print("signed /api/user/info     :", get("/api/user/info"))
print("signed /api/vip/index     :", get("/api/vip/index"))
print("signed /api/version/check :", get("/api/version/check"))
qs_only = "&".join(f"{k}={v}" for k, v in [("tz","480"),("lang","zh"),("userId","0"),("client","android"),("deviceId","probe0001device"),("channel","official"),("av","1.6.6"),("t",str(int(time.time()*1000))),("distinctId","probe-dist-1"),("shushuDeviceId","probe-ss-1"),("mainUser","0")])
try:
    r = requests.get(f"{H}/api/client/config?{qs_only}", headers={"User-Agent": UA}, timeout=10)
    print("unsigned /api/client/config:", f"[{r.status_code}] {r.content[:200].decode('utf-8','replace')}")
except Exception as e:
    print("unsigned ERR", e)
print("===P3_END===")
