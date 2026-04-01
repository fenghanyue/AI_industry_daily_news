# -*- coding: utf-8 -*-
"""
新闻抓取 - 搜昨天的 AI 新闻
"""

import os
import re
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL     = "https://google.serper.dev/news"

_DATE_FMTS = ["%b %d, %Y", "%Y-%m-%d", "%d %b %Y", "%Y/%m/%d", "%m/%d/%Y"]


def _parse_date(date_str: str):
    if not date_str:
        return None
    m = re.match(r"(\d+)\s*(hour|day|week|month|小时|天|周|个月|分钟)", date_str, re.I)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        unit_map = {
            "hour": "hour", "小时": "hour", "分钟": "hour",
            "day":  "day",  "天":   "day",
            "week": "week", "周":   "week",
            "month": "month", "个月": "month",
        }
        mapped = unit_map.get(unit.lower(), "day")
        delta  = {"hour": timedelta(hours=n), "day": timedelta(days=n),
                  "week": timedelta(weeks=n), "month": timedelta(days=n*30)}.get(mapped, timedelta(days=n))
        return datetime.now(timezone.utc) - delta
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_ymd(date_str: str) -> str:
    dt = _parse_date(date_str)
    return dt.strftime("%Y/%m/%d") if dt else date_str


def fetch_category(cat_id: str, queries: List[str], lookback_days: int = 2) -> List[Dict]:
    """
    搜一个分类，合并多个查询词，本地过滤日期后返回
    """
    # 只保留昨天和今天的文章（容忍时区误差）
    now     = datetime.now(timezone.utc)
    cutoff  = now - timedelta(days=lookback_days)
    seen_links = set()
    articles   = []

    for query in queries:
        try:
            resp = requests.post(
                SERPER_URL,
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "cn", "hl": "zh-cn", "num": 10, "tbs": "qdr:d2"},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("news", []):
                link     = item.get("link", "")
                raw_date = item.get("date", "")
                pub_dt   = _parse_date(raw_date)

                # 本地日期过滤：能解析出日期的，超过 lookback_days 直接丢弃
                if pub_dt and pub_dt < cutoff:
                    logger.debug("  丢弃旧文章 [%s]: %s", raw_date, item.get("title", "")[:30])
                    continue

                # 去重
                if link and link in seen_links:
                    continue
                seen_links.add(link)

                articles.append({
                    "title":     item.get("title",   ""),
                    "summary":   item.get("snippet", ""),
                    "link":      item.get("link",    ""),
                    "published": _to_ymd(raw_date),
                    "source":    item.get("source",  ""),
                    "raw_date":  raw_date,  # 原始时间，给豆包二次核验用
                })
        except Exception as e:
            logger.warning("搜索失败 [%s - %s]: %s", cat_id, query, e)

    logger.info("  [%s] %d 条候选", cat_id, len(articles))
    return articles


def fetch_all(categories: List[Dict], lookback_days: int = 2) -> Dict[str, List[Dict]]:
    """抓取所有分类，返回 {cat_id: [articles]}"""
    result = {}
    total  = 0
    for cat in categories:
        arts = fetch_category(cat["id"], cat["queries"], lookback_days)
        result[cat["id"]] = arts
        total += len(arts)
    logger.info("抓取完成，共 %d 条候选", total)
    return result
