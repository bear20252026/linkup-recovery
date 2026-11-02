# -*- coding: utf-8 -*-
# usage: python tools/probe_login.py <sms|login> [code]
import sys, time, requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
BASE="https://linkup-test.51wnl-cq.com"; UA="okhttp/4.9.3"
KEY=IV=b"6R4aXTSK3OghHIgA"
PHONE="15927132025"; DEV="probe0001device"
mode=sys.argv[1] if len(sys.argv)>1 else "sms"
code=sys.argv[2] if len(sys.argv)>2 else ""
def base_params(uid="0"):
    return [("tz","480"),("lang","zh"),("userId",str(uid)),("client","android"),
        ("deviceId",DEV),("channel","official"),("av","1.6.6"),
        ("t",str(int(time.time()*1000))),("distinctId","probe-dist-1"),
        ("shushuDeviceId","probe-ss-1"),("mainUser","0")]
def sign(si):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(si.encode(),16)).hex()
print(f"===MODE_{mode}===")
qs="&".join(f"{k}={v}" for k,v in base_params())
if mode=="sms":
    try:
        r=requests.get(f"{BASE}/api/sms/send?phone={PHONE}&region=86&{qs}",headers={"User-Agent":UA},timeout=10)
        print("sms/send:",f"[{r.status_code}]",r.content[:300].decode('utf-8','replace'))
    except Exception as e:
        print("sms ERR",e)
else:
    body={"typeId":0,"phone":PHONE,"smsCode":code,"region":"86"}
    try:
        r=requests.post(f"{BASE}/api/user/login?{qs}",json=body,headers={"User-Agent":UA},timeout=10)
        print("login:",f"[{r.status_code}]",r.content[:600].decode('utf-8','replace'))
        data=(r.json().get("data") or {}) if r.status_code==200 else {}
    except Exception as e:
        print("login ERR",e); data={}
    token=data.get("token",""); uid=data.get("userId","0")
    print("token_len:",len(token),"userId:",uid)
    if token:
        qs2="&".join(f"{k}={v}" for k,v in base_params(uid))
        si=f"/api/user/info?{qs2}"
        h={"User-Agent":UA,"Authorization":token,"Signature":sign(si)}
        try:
            r2=requests.get(f"{BASE}/api/user/info?{qs2}",headers=h,timeout=10)
            print("user/info:",f"[{r2.status_code}]",r2.content[:800].decode('utf-8','replace'))
        except Exception as e:
            print("info ERR",e)
print("===MODE_END===")
