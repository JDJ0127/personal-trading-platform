from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

RULES = [
    {"keywords": ["算力", "数据中心", "AI"], "sector": "算力、数据中心", "direction": "positive", "score": 82},
    {"keywords": ["半导体", "国产替代"], "sector": "半导体设备", "direction": "positive", "score": 76},
    {"keywords": ["减持", "监管"], "sector": "高位主题", "direction": "negative", "score": 68},
]

SAMPLE_NEWS = [
    {"time": "09:20", "source": "公开政策源", "title": "新型基础设施政策延续，算力和数据中心建设提速"},
    {"time": "10:35", "source": "财经快讯", "title": "半导体国产替代订单预期改善"},
    {"time": "13:40", "source": "交易所公告", "title": "部分高位主题公司披露减持计划"},
]


def build_news_report(trade_date: date | None = None) -> dict[str, Any]:
    events = []
    for index, item in enumerate(SAMPLE_NEWS, start=1):
        mapping = _map_event(item["title"])
        events.append(
            {
                "eventId": f"sample-news-{index}",
                "tradeDate": trade_date.isoformat() if trade_date else "",
                "time": item["time"],
                "source": item["source"],
                "title": item["title"],
                "eventType": "policy/news",
                "sentiment": mapping["direction"],
                "importance": mapping["score"],
                "sector": mapping["sector"],
                "passCount": 0,
                "reason": mapping["reason"],
            }
        )
    return {
        "schemaVersion": 1,
        "tradeDate": trade_date.isoformat() if trade_date else "",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "规则词典MVP",
        "summary": {
            "eventCount": len(events),
            "positiveCount": sum(1 for event in events if event["sentiment"] == "positive"),
            "negativeCount": sum(1 for event in events if event["sentiment"] == "negative"),
            "highImportanceCount": sum(1 for event in events if event["importance"] >= 80),
        },
        "events": events,
    }


def write_news_report(output: str | Path, trade_date: date | None = None) -> dict[str, Any]:
    report = build_news_report(trade_date)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _map_event(title: str) -> dict[str, Any]:
    for rule in RULES:
        matched = [keyword for keyword in rule["keywords"] if keyword in title]
        if matched:
            return {
                "sector": rule["sector"],
                "direction": rule["direction"],
                "score": rule["score"],
                "reason": f"命中关键词：{'、'.join(matched)}",
            }
    return {"sector": "未分类", "direction": "neutral", "score": 40, "reason": "未命中规则词典"}
