from __future__ import annotations
import logging
import requests
import time

log = logging.getLogger(__name__)


class YorkyClient:
    def __init__(self, base_url: str, api_key: str, page_size: int = 100,
                 page_sleep_seconds: float = 2.0, poster=requests,
                 sleeper=time.sleep, max_pages: int = 1000):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.page_size = page_size
        self.page_sleep_seconds = page_sleep_seconds
        self.poster = poster
        self.sleeper = sleeper
        self.max_pages = max_pages
        self.fetch_succeeded = False

    def _fetch_page(self, offset: int) -> tuple[list[dict], bool]:
        url = f"{self.base_url}/api/depot/expand/trackList/push"
        headers = {"apiKey": self.api_key, "Content-Type": "application/json"}
        body = {"limit": self.page_size, "offset": offset}
        resp = self.poster.post(url, json=body, headers=headers, timeout=30)
        data = resp.json()
        if data.get("code") != 200:
            log.error("56yorky 返回非200: %s", data.get("message"))
            return [], False
        return (data.get("data") or {}).get("list") or [], True

    def fetch_all_tracks(self) -> list[dict]:
        all_rows: list[dict] = []
        offset = 0
        for _ in range(self.max_pages):
            rows, ok = self._fetch_page(offset)
            if ok:
                self.fetch_succeeded = True
            if not rows:
                break
            all_rows.extend(rows)
            self.sleeper(self.page_sleep_seconds)  # 遵守 2 秒/次限速
            if len(rows) < self.page_size:
                break
            offset += self.page_size
        return all_rows
