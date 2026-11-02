# -*- coding: utf-8 -*-
# probe5: step2 登录拿JWT + step4 签名验证 user/info
import time, requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
BASE="https://linkup-test.51wnl-cq.com"; UA="okhttp/4.9.3"
KEY=IV=b"6R4aXTSK3OghHIgA"
PHONE="15927132025"; CODE="8426"; DEV="probe0001device"
def base_params(uid="0"):
    return [("tz","480"),("lang","zh"),("userId",str(uid)),("client","android"),
        ("deviceId",DEV),("channel","official"),("av","1.6.6"),
        ("t",str(int(time.time()*1000))),("distinctId","probe-dist-1"),
        ("shushuDeviceId","probe-ss-1"),("mainUser","0")]
def sign(si):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(si.encode(),16)).hex()
print("===LOGIN_BEGIN===")
qs="&".join(f"{k}={v}" for k,v in base_params())
body={"typeId":1,"phone":PHONE,"smsCode":CODE,"region":"86"}
try:
    r=requests.post(f"{BASE}/api/user/login?{qs}",json=body,headers={"User-Agent":UA},timeout=10)
    print("login:",f"[{r.status_code}]",r.content[:600].decode('utf-8','replace'))
    data=(r.json().get("data") or {}) if r.status_code==200 else {}
except Exception as e:
    print("login ERR",e); data={}
token=data.get("token",""); uid=data.get("userId","0")
print("token_len:",len(token),"token_head:",token[:12],"userId:",uid)
if token:
    qs2="&".join(f"{k}={v}" for k,v in base_params(uid))
    si=f"/api/user/info?{qs2}"
    h={"User-Agent":UA,"Authorization":token,"Signature":sign(si)}
    try:
        r2=requests.get(f"{BASE}/api/user/info?{qs2}",headers=h,timeout=10)
        print("user/info:",f"[{r2.status_code}]",r2.content[:800].decode('utf-8','replace'))
    except Exception as e:
        print("info ERR",e)
print("===LOGIN_END===")
