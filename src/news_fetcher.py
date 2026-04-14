# -*- coding: utf-8 -*-
"""
新闻抓取 - Gmail Google Alerts 模式

通过 IMAP 读取 Gmail 中的 Google Alerts 邮件，解析出新闻条目。
需要设置环境变量：GMAIL_ADDRESS、GMAIL_APP_PASSWORD
"""

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def fetch_all(categories: List[Dict], lookback_days: int = 1,
              alert_subjects: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    通过 Gmail Google Alerts 抓取所有分类的新闻，返回 {cat_id: [articles]}。

    需要设置 GMAIL_ADDRESS 和 GMAIL_APP_PASSWORD 环境变量。
    alert_subjects: 只处理标题包含这些关键词的 Alert 邮件，用于区分行业。
    """
    gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pwd  = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_addr or not gmail_pwd:
        raise ValueError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD 未设置")

    from src.gmail_fetcher import fetch_alerts_from_gmail, assign_to_categories

    logger.info("使用 Gmail Google Alerts 模式")
    all_articles = fetch_alerts_from_gmail(
        gmail_address=gmail_addr,
        gmail_password=gmail_pwd,
        lookback_days=lookback_days,
        alert_subjects=alert_subjects,
    )

    if not all_articles:
        logger.warning("Gmail 未解析到文章")
        return {cat["id"]: [] for cat in categories}

    result = assign_to_categories(all_articles, categories)
    total = sum(len(v) for v in result.values())
    logger.info("Gmail Alerts 抓取完成，共 %d 条候选", total)
    return result