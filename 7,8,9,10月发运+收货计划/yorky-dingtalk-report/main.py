from __future__ import annotations
import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from config import load_config
from yorky_client import YorkyClient
from report_builder import ReportBuilder, ReportData
from dingtalk_sender import send_action_card


def setup_logging(log_dir: str):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / f"{date.today().isoformat()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def run(config_path: str, dry_run: bool) -> int:
    log = logging.getLogger("main")
    try:
        cfg = load_config(config_path)
    except Exception as e:
        logging.error("配置加载失败: %s", e)
        return 2
    setup_logging(cfg.logging.dir)

    today = date.today().isoformat()
    client = YorkyClient(cfg.yorky.base_url, cfg.yorky.api_key,
                         cfg.yorky.page_size, cfg.yorky.page_sleep_seconds)
    records = client.fetch_all_tracks()
    log.info("共拉取 %d 条轨迹记录（fetch_succeeded=%s）",
             len(records), client.fetch_succeeded)

    rb = ReportBuilder(cfg.filter.exclude_track_status,
                       cfg.filter.exclude_delivery_status,
                       cfg.filter.long_tail_threshold, today=today)
    report = rb.build(records)

    # 区分"API 全挂"与"确实无在途单"
    if not records and not client.fetch_succeeded:
        report = ReportData(
            title=f"⚠️ 转运日报拉取失败（{today}）",
            markdown="⚠️ 56yorky 数据拉取失败，请检查 apiKey / 网络 / 接口状态。",
            in_transit_count=0, is_empty=True)

    log.info("在途 %d 单", report.in_transit_count)

    if dry_run:
        print(f"[DRY-RUN] title={report.title}")
        print(report.markdown)
        return 0

    ok = send_action_card(cfg.dingtalk.webhook, cfg.dingtalk.secret,
                          report.title, report.markdown,
                          "查看 56yorky 后台", cfg.dingtalk.backend_url)
    if ok:
        log.info("钉钉推送成功")
        return 0
    log.error("钉钉推送失败")
    return 1


def main():
    ap = argparse.ArgumentParser(description="56yorky 转运日报 → 钉钉")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="不发钉钉、不调真实API的样本预览")
    args = ap.parse_args()
    sys.exit(run(args.config, args.dry_run))


if __name__ == "__main__":
    main()
