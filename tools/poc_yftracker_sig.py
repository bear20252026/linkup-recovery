"""PoC: 复现 YfTracker 签名算法
signature = MD5( hex( AES-128-CBC-PKCS5Padding( UTF8(input), KEY, IV ) ) )
KEY = IV = b"be2524844ec4bb25"  (16 字节 ASCII)
"""
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import hashlib

KEY = b"be2524844ec4bb25"
IV  = b"be2524844ec4bb25"

def aes128_encrypt(plain: str) -> str:
    """返回 hex 字符串（小写），与 Kotlin 实现的 bytesToHex 一致"""
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    ct = cipher.encrypt(pad(plain.encode("utf-8"), AES.block_size))
    return ct.hex()

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def signature_get(input_str: str) -> str:
    return md5(aes128_encrypt(input_str))

if __name__ == "__main__":
    # 一些样例
    cases = [
        "",
        "hello",
        "/api/v1/location/report",
        "/api/v1/friend/list?uid=12345",
    ]
    for c in cases:
        print(f"input={c!r}")
        print(f"  aes128_hex = {aes128_encrypt(c) if c else '(empty)'}")
        print(f"  signature  = {signature_get(c)}")
