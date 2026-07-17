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


def send_action_card(webhook: str, secret: str, title: str, markdown: str,
                     btn_title: str, btn_url: str, timeout: int = 10,
                     retries: int = 2, now_ms: int | None = None,
                     poster=requests, sleeper=time.sleep) -> bool:
    """推送 ActionCard。成功（errcode==0）返回 True；耗尽重试返回 False。"""
    ts = now_ms if now_ms is not None else int(time.time() * 1000)
    url = build_signed_webhook(webhook, secret, ts)
    payload = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": title,
            "text": markdown,
            "btnOrientation": "0",
            "btns": [{"title": btn_title, "actionURL": btn_url}],
        },
    }
    attempts = retries + 1
    for i in range(attempts):
        try:
            resp = poster.post(url, json=payload, timeout=timeout)
            data = resp.json()
            if data.get("errcode") == 0:
                return True
        except Exception:
            pass
        if i < attempts - 1:
            sleeper(1)
    return False

