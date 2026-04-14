# -*- coding: utf-8 -*-
"""
新闻抓取 - 多来源版（Gmail Google Alerts 优先，Serper 备用）

数据源优先级：
  1. Gmail 中的 Google Alerts 邮件（免费、无额度限制）
  2. Serper API（收费，作为备用或补充）

两种来源返回的数据结构完全一致，下游 ai_summarizer 无需修改。
"""

import os
import re
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
#  Serper 相关（保留作为备用）
# ═══════════════════════════════════════════════════

SERPER_URL = "https://google.serper.dev/news"

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


def fetch_category_serper(cat_id: str, queries: List[str],
                          serper_api_key: str, lookback_days: int = 1) -> List[Dict]:
    """Serper 搜一个分类（原逻辑保留）"""
    now     = datetime.now(timezone.utc)
    cutoff  = now - timedelta(days=lookback_days)
    seen_links = set()
    articles   = []

    for query in queries:
        try:
            resp = requests.post(
                SERPER_URL,
                headers={"X-API-KEY": serper_api_key, "Content-Type": "application/json"},
                json={"q": query, "gl": "cn", "hl": "zh-cn", "num": 10, "tbs": "qdr:d"},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("news", []):
                link     = item.get("link", "")
                raw_date = item.get("date", "")
                pub_dt   = _parse_date(raw_date)

                if pub_dt and pub_dt < cutoff:
                    continue
                if link and link in seen_links:
                    continue
                seen_links.add(link)

                articles.append({
                    "title":     item.get("title",   ""),
                    "summary":   item.get("snippet", ""),
                    "link":      item.get("link",    ""),
                    "published": _to_ymd(raw_date),
                    "source":    item.get("source",  ""),
                    "raw_date":  raw_date,
                })
        except Exception as e:
            logger.warning("Serper 搜索失败 [%s - %s]: %s", cat_id, query, e)

    logger.info("  [%s] Serper %d 条候选", cat_id, len(articles))
    return articles


# ═══════════════════════════════════════════════════
#  统一入口
# ═══════════════════════════════════════════════════

def fetch_all(categories: List[Dict], lookback_days: int = 2,
              serper_key_env: str = "SERPER_API_KEY") -> Dict[str, List[Dict]]:
    """
    抓取所有分类的新闻，返回 {cat_id: [articles]}。

    优先使用 Gmail Google Alerts：
      - 需要设置 GMAIL_ADDRESS 和 GMAIL_APP_PASSWORD 环境变量
      - 从 Gmail 读取所有 Alerts 邮件，按关键词分配到各分类

    备用 Serper API：
      - 如果 Gmail 未配置或抓取失败，回退到 Serper
      - 需要对应的 serper_key_env 环境变量
    """
    gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pwd  = os.environ.get("GMAIL_APP_PASSWORD", "")

    # ── 尝试 Gmail Google Alerts ──
    if gmail_addr and gmail_pwd:
        try:
            from src.gmail_fetcher import fetch_alerts_from_gmail, assign_to_categories

            logger.info("使用 Gmail Google Alerts 模式")
            all_articles = fetch_alerts_from_gmail(
                gmail_address=gmail_addr,
                gmail_password=gmail_pwd,
                lookback_days=lookback_days,
            )

            if all_articles:
                result = assign_to_categories(all_articles, categories)
                total = sum(len(v) for v in result.values())
                logger.info("Gmail Alerts 抓取完成，共 %d 条候选", total)
                return result
            else:
                logger.warning("Gmail 未解析到文章，尝试 Serper 备用")
        except Exception as e:
            logger.error("Gmail 抓取失败: %s，尝试 Serper 备用", e)

    # ── 备用：Serper API ──
    serper_api_key = os.environ.get(serper_key_env, "")
    if not serper_api_key:
        # 如果 Gmail 和 Serper 都没配置
        if not gmail_addr:
            raise ValueError(
                f"GMAIL_ADDRESS/GMAIL_APP_PASSWORD 和 {serper_key_env} 均未设置，"
                "至少需要配置一个数据源"
            )
        raise ValueError(f"Gmail 抓取失败且 {serper_key_env} 未设置，无法获取新闻")

    logger.info("使用 Serper API 模式 (key_env=%s)", serper_key_env)
    result = {}
    total  = 0
    for cat in categories:
        arts = fetch_category_serper(cat["id"], cat["queries"], serper_api_key, lookback_days)
        result[cat["id"]] = arts
        total += len(arts)
    logger.info("Serper 抓取完成，共 %d 条候选", total)
    return result