# -*- coding: utf-8 -*-
"""
AI 摘要 - 豆包对每个分类的文章进行筛选、核验时间、压缩摘要
"""

import os
import re
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)

DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_API_KEY  = os.environ.get("DOUBAO_API_KEY", "")
DOUBAO_MODEL    = os.environ.get("DOUBAO_MODEL", "")

# ───────── 日期解析（与 news_fetcher 保持一致） ─────────
_DATE_FMTS = ["%b %d, %Y", "%Y-%m-%d", "%d %b %Y", "%Y/%m/%d", "%m/%d/%Y"]


def _parse_date(date_str: str):
    """解析各种日期格式，返回 datetime 或 None"""
    if not date_str:
        return None
    m = re.match(r"(\d+)\s*(hour|day|week|month|小时|天|周|个月|分钟|minute|min)", date_str, re.I)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        unit_map = {
            "hour": "hour", "小时": "hour", "分钟": "minute", "minute": "minute", "min": "minute",
            "day": "day", "天": "day",
            "week": "week", "周": "week",
            "month": "month", "个月": "month",
        }
        mapped = unit_map.get(unit, "day")
        delta = {
            "minute": timedelta(minutes=n),
            "hour":   timedelta(hours=n),
            "day":    timedelta(days=n),
            "week":   timedelta(weeks=n),
            "month":  timedelta(days=n * 30),
        }.get(mapped, timedelta(days=n))
        return datetime.now(timezone.utc) - delta
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_within_range(date_str: str, max_hours: int = 48) -> bool:
    """
    判断 date_str 是否在最近 max_hours 小时以内。
    解析失败返回 False（宁可误杀，不放过旧闻）。
    """
    dt = _parse_date(date_str)
    if dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
    return dt >= cutoff


# ───────── 核心：AI 输出后的代码级日期校验 ─────────

def _validate_dates(items: List[Dict], original_articles: List[Dict], max_hours: int = 48) -> List[Dict]:
    """
    拿 AI 返回的每条 item，通过 link 回溯原始文章的 raw_date，
    用代码硬性校验日期。不在时间范围内的直接丢弃。

    策略：
      1. link 能匹配到原始文章 → 用原始 raw_date 校验
      2. link 匹配不到（AI 可能改了链接）→ 用标题模糊匹配兜底
      3. 完全匹配不到原始文章 → 丢弃（来路不明）
    """
    # 建立 link → raw_date 的索引
    link_to_date = {}
    title_to_date = {}
    for art in original_articles:
        link = art.get("link", "").strip()
        if link:
            link_to_date[link] = art.get("raw_date", "")
        title = art.get("title", "").strip()
        if title:
            title_to_date[title] = art.get("raw_date", "")

    validated = []
    for item in items:
        item_link  = item.get("link", "").strip()
        headline   = item.get("headline", "")
        raw_date   = None

        # 方式 1：精确匹配 link
        if item_link in link_to_date:
            raw_date = link_to_date[item_link]
        else:
            # 方式 2：标题模糊匹配（AI 可能重写了标题，用关键词匹配）
            for orig_title, rd in title_to_date.items():
                # 简单的子串匹配：headline 的前10个字出现在原标题中
                if len(headline) >= 4 and headline[:10] in orig_title:
                    raw_date = rd
                    break
                # 或者原标题的前10个字出现在 headline 中
                if len(orig_title) >= 4 and orig_title[:10] in headline:
                    raw_date = rd
                    break

        # 判断结果
        if raw_date is None:
            # 完全找不到原始文章，来路不明，丢弃
            logger.warning("  日期校验: 丢弃(无法回溯原文) → %s", headline)
            continue

        if not _is_within_range(raw_date, max_hours):
            logger.warning("  日期校验: 丢弃(旧闻) [%s] → %s", raw_date, headline)
            continue

        validated.append(item)
        logger.debug("  日期校验: 通过 [%s] → %s", raw_date, headline)

    return validated


# ───────── 豆包对话 ─────────

def _parse_json(text: str):
    text = text.strip()
    if "```" in text:
        for p in text.split("```"):
            t = p[4:] if p.startswith("json") else p
            if "{" in t or "[" in t:
                text = t
                break
    start = min((text.find("{") if "{" in text else 9999),
                (text.find("[") if "[" in text else 9999))
    end   = max(text.rfind("}"), text.rfind("]")) + 1
    if start < end:
        text = text[start:end]
    return json.loads(text.strip())


def _chat(messages: list, max_tokens: int = 3000, temperature: float = 0.2) -> str:
    resp = requests.post(
        DOUBAO_BASE_URL,
        headers={"Authorization": f"Bearer {DOUBAO_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": DOUBAO_MODEL, "messages": messages,
              "max_tokens": max_tokens, "temperature": temperature},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def summarize_category(cat: Dict, articles: List[Dict], today: str, yesterday: str) -> List[Dict]:
    if not articles:
        return []

    news_text = ""
    for i, a in enumerate(articles):
        news_text += (
            f"[{i}] 原始时间字段：「{a['raw_date']}」| 来源：{a['source']}\n"
            f"    标题：{a['title']}\n"
            f"    链接：{a['link']}\n"
            f"    摘要：{a['summary'][:150]}\n\n"
        )

    prompt = f"""今天是 {today}，昨天是 {yesterday}。

你是 AI 行业编辑，正在整理【{cat['name']}】分类的昨日新闻。

以下是候选文章（共 {len(articles)} 条），每条都有"原始时间字段"：

{news_text}

=== 第一步：严格时间核验 ===

对每条文章的"原始时间字段"逐一判断，规则如下：

相对时间（如"X小时前"、"X hours ago"）：
- 今天是 {today}，以此推算：
- 24小时以内 = 今天或昨天，保留
- 超过24小时 = 丢弃

中文相对时间（如"X天前"、"X分钟前"）：
- "X分钟前"、"X小时前" = 保留
- "1天前" = 昨天，保留
- "2天前"及以上 = 丢弃

绝对日期（如 2026/03/20、Mar 20, 2026）：
- 只保留日期等于昨天 {yesterday} 的
- 其他日期一律丢弃

时间字段为空或无法判断：丢弃，不要猜测

=== 第二步：筛选整理 ===

从通过时间核验的文章里，选出最值得关注的 3-5 条。
内容高度重复的合并成一条。

=== 第三步：每条输出 ===

- headline：重写标题，20字以内，主语+事件，简洁有力
- digest：120字左右的摘要（不能少于100字，不能超过140字），要写清楚：
  1. 具体发生了什么（谁、做了什么、关键数据）
  2. 为什么重要或有什么影响
  3. 背景补充（如果有）
  注意：120字是硬性要求，宁可多写细节也不要凑字数
- importance：重要/关注/一般
- source：来源媒体名
- link：从文章的"链接："字段原样复制，一字不改
- tags：2-4个关键词，逗号分隔

只输出 JSON，不要其他文字：
{{
  "items": [
    {{
      "headline": "标题",
      "digest": "120字左右的摘要",
      "importance": "重要/关注/一般",
      "source": "来源",
      "link": "原始链接原样复制",
      "tags": "标签1,标签2"
    }}
  ]
}}

如果没有通过时间核验的文章，输出：{{"items": []}}"""

    for attempt in range(3):
        try:
            raw    = _chat([{"role": "user", "content": prompt}], max_tokens=3000)
            parsed = _parse_json(raw)
            items  = parsed.get("items", [])
            logger.info("  [%s] AI 返回 %d 条（原 %d 条）", cat["name"], len(items), len(articles))

            # ★ 关键改动：AI 输出后，用代码再校验一次日期 ★
            items = _validate_dates(items, articles, max_hours=48)
            logger.info("  [%s] 日期校验后保留 %d 条", cat["name"], len(items))

            return items
        except Exception as e:
            logger.warning("  [%s] 第%d次失败: %s", cat["name"], attempt + 1, e)
            if attempt < 2:
                import time; time.sleep(10)
    logger.error("  [%s] 3次重试均失败，跳过", cat["name"])
    return []


def summarize_all(categories: List[Dict], raw_news: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    today     = datetime.now().strftime("%Y年%m月%d日")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

    result = {}
    for cat in categories:
        cat_id   = cat["id"]
        articles = raw_news.get(cat_id, [])
        logger.info("豆包处理: [%s] %d 条候选", cat["name"], len(articles))
        result[cat_id] = summarize_category(cat, articles, today, yesterday)

    return result
