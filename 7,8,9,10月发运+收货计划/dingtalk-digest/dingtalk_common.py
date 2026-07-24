#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""钉钉 MCP / 机器人 通用工具，供日报与行程简报脚本共用。"""

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")


def load_config(path=CONFIG_PATH):
    # 优先读环境变量（GitHub Secrets 注入），无则读 config.json（本地调试用）
    cfg = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    return {
        "mcp_url": os.environ.get("DINGTALK_MCP_URL") or cfg.get("mcp_url", ""),
        "calendar_mcp_url": os.environ.get("DINGTALK_CALENDAR_MCP_URL") or cfg.get("calendar_mcp_url", ""),
        "table_mcp_url": os.environ.get("DINGTALK_TABLE_MCP_URL") or cfg.get("table_mcp_url", ""),
        "base_id": os.environ.get("DINGTALK_BASE_ID") or cfg.get("base_id", ""),
        "table_id": os.environ.get("DINGTALK_TABLE_ID") or cfg.get("table_id", ""),
        "robot_webhook": os.environ.get("DINGTALK_ROBOT_WEBHOOK") or cfg.get("robot_webhook", ""),
        "robot_secret": os.environ.get("DINGTALK_ROBOT_SECRET") or cfg.get("robot_secret", ""),
    }


def setup_utf8_console():
    """Windows 控制台中文输出。"""
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class McpClient:
    """钉钉 MCP Streamable-HTTP 客户端（每个网关一个实例）。"""

    def __init__(self, url):
        self.url = url
        self._id = 0
        self._initialize()

    def _next_id(self):
        self._id += 1
        return self._id

    def _post(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e
        if not body or not body.strip():
            return {}
        try:
            return json.loads(body)
        except ValueError:
            raise RuntimeError(f"非 JSON 响应: {body[:200]}")

    def _initialize(self):
        self._post({
            "jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "dingtalk-digest", "version": "1.0.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, name, arguments):
        resp = self._post({
            "jsonrpc": "2.0", "id": self._next_id(), "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in resp:
            raise RuntimeError(f"工具 {name} 返回错误: {resp['error']}")
        result = resp.get("result", {})
        sc = result.get("structuredContent")
        if sc is not None:
            return sc
        for c in result.get("content") or []:
            if c.get("type") == "text":
                try:
                    return json.loads(c["text"])
                except (ValueError, KeyError):
                    return c.get("text")
        return result


def _dingtalk_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send_via_robot(webhook, secret, title, markdown_text):
    """通过钉钉自定义机器人（加签）发一条 markdown 消息。成功返回响应 dict。"""
    import time
    timestamp = str(int(time.time() * 1000))
    sign = urllib.parse.quote_plus(_dingtalk_sign(secret, timestamp))
    sep = "&" if "?" in webhook else "?"
    url = f"{webhook}{sep}timestamp={timestamp}&sign={sign}"
    payload = {"msgtype": "markdown", "markdown": {"title": title, "text": markdown_text}}
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"机器人 HTTP {e.code}: {detail}") from e
    try:
        result = json.loads(body)
    except ValueError:
        raise RuntimeError(f"机器人非 JSON 响应: {body[:300]}")
    if result.get("errcode") not in (0, None):
        raise RuntimeError(f"机器人返回错误: {result}")
    return result

