# -*- coding: utf-8 -*-
"""
AI 行业日报 - 分类与搜索词配置
"""

REPORT_TITLE = "AI 行业日报"
REPORT_EMOJI = "🤖"

# ── Google Alerts 邮件过滤 ──
# 只处理邮件标题中包含以下关键词的 Alert 邮件
# Google Alerts 邮件标题格式: "Google 快讯 - 大模型 发布"
# 填写你在 google.com/alerts 创建时用的搜索词（或其中的关键部分）
ALERT_SUBJECTS = [
    "人工智能",
    "AI",
    "大模型",
    "LLM",
    "GPT",
    "Claude",
    "Gemini",
    "SDK",
    "API 开发者",
    "AI 产品",
    "AI 研究",
    "AI 融资",
    "AI 监管",
    "AI 传闻",
]

CATEGORIES = [
    {
        "id":      "news",
        "name":    "要闻",
        "emoji":   "⭐",
        "color":   "#ff6b35",
        "queries": ["AI 人工智能 重大 最新", "人工智能 行业 重磅"],
    },
    {
        "id":      "model",
        "name":    "模型发布",
        "emoji":   "🚀",
        "color":   "#00d4ff",
        "queries": ["大模型 发布 最新", "LLM 模型 开源 发布"],
    },
    {
        "id":      "dev",
        "name":    "开发生态",
        "emoji":   "<>",
        "color":   "#00ff88",
        "queries": ["AI API SDK 开发者 更新"],
    },
    {
        "id":      "product",
        "name":    "产品应用",
        "emoji":   "📦",
        "color":   "#ffd700",
        "queries": ["AI 产品 功能 更新 上线"],
    },
    {
        "id":      "tech",
        "name":    "技术与洞察",
        "emoji":   "🔬",
        "color":   "#b47fff",
        "queries": ["AI 研究 论文 技术突破"],
    },
    {
        "id":      "industry",
        "name":    "行业动态",
        "emoji":   "📊",
        "color":   "#ff9999",
        "queries": ["AI 行业 融资 投资 收购"],
    },
    {
        "id":      "policy",
        "name":    "法规监管",
        "emoji":   "⚖️",
        "color":   "#ffaa44",
        "queries": ["AI 监管 法规 政策 合规"],
    },
    {
        "id":      "future",
        "name":    "前瞻与传闻",
        "emoji":   "🔮",
        "color":   "#99ffcc",
        "queries": ["AI 传闻 预测 路线图 泄露"],
    },
]