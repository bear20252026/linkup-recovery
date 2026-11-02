# -*- coding: utf-8 -*-
# probe4: step1 发送短信验证码 (sms/send 免签名)
import time, requests
BASE = "https://linkup-test.51wnl-cq.com"
UA = "okhttp/4.9.3"
PHONE = "15927132025"
def qs(extra):
    q = list(extra) + [
        ("tz","480"),("lang","zh"),("userId","0"),("client","android"),
        ("deviceId","probe0001device"),("channel","official"),
        ("av","1.6.6"),("t",str(int(time.time()*1000))),
        ("distinctId","probe-dist-1"),("shushuDeviceId","probe-ss-1"),("mainUser","0"),
    ]
    return "&".join(f"{k}={v}" for k,v in q)
print("===SMS_BEGIN===")
try:
    r = requests.get(f"{BASE}/api/sms/send?{qs([('phone',PHONE),('region','86')])}", headers={"User-Agent":UA}, timeout=10)
    print(f" sms/send region=86: [{r.status_code}] {r.content[:300].decode('utf-8','replace')}")
except Exception as e:
    print("ERR", e)
print("===SMS_END===")
