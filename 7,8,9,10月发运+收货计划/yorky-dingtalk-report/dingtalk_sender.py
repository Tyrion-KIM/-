from __future__ import annotations
import hmac
import hashlib
import base64
import urllib.parse
import time
import requests


def sign_dingtalk(secret: str, timestamp: int) -> str:
    """钉钉机器人加签：返回 urlencoded 的 base64 签名串。"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return urllib.parse.quote_plus(sign)


def build_signed_webhook(webhook: str, secret: str, timestamp: int) -> str:
    sign = sign_dingtalk(secret, timestamp)
    sep = "&" if "?" in webhook else "?"
    return f"{webhook}{sep}timestamp={timestamp}&sign={sign}"
