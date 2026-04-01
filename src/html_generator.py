# -*- coding: utf-8 -*-
"""
HTML 生成器 - 把处理好的新闻生成日报 HTML
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path(__file__).parent.parent / "output"

IMPORTANCE_MAP = {
    "重要": ("tag-high", "重要"),
    "关注": ("tag-mid",  "关注"),
    "一般": ("tag-low",  "一般"),
}

# 提示词模板，{title} {digest} {source} {tags} {today} 会被替换
PROMPT_TEMPLATE = """你是一位 AI 行业资深研究员，请对以下新闻进行深度分析。

━━━━━━━━━━━━━━━━━━━━━━
【新闻标题】{title}
【摘要】{digest}
【来源】{source}
【标签】{tags}
【日期】{today}
━━━━━━━━━━━━━━━━━━━━━━

请按以下结构输出深度分析报告：

## 1. 事件还原（200字以内）
用简洁准确的语言还原事件全貌，补充你已知的背景信息。

## 2. 核心意义
- 这件事为什么重要？在行业发展脉络中处于什么位置？
- 打破了哪些原有认知或格局？

## 3. 受益方 vs 受损方
分别列出直接和间接受益者、受损者，并说明逻辑。

## 4. 潜在风险与隐忧
这个事件背后有哪些容易被忽视的风险点？官方叙事里有哪些值得质疑的地方？

## 5. 接下来 30 天观察清单
列出 3-5 个具体的观察指标或信号，帮助判断这件事的后续走向。

## 6. 一句话结论
用一句话总结你的核心判断，要有明确立场，不要模棱两可。

要求：分析要有独立判断，避免复述新闻内容，重点放在"这意味着什么"而非"发生了什么"。"""


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _news_item_html(item: Dict) -> str:
    tag_cls, tag_label = IMPORTANCE_MAP.get(item.get("importance", "一般"), ("tag-low", "一般"))
    title   = _escape(item.get("headline", ""))
    digest  = _escape(item.get("digest", ""))
    source  = _escape(item.get("source", ""))
    link    = item.get("link", "#")
    tags_raw= item.get("tags", "")
    tags_disp = "".join(f'<span class="detail-tag">{_escape(t.strip())}</span>'
                        for t in tags_raw.split(",") if t.strip())

    # 提示词里用的纯文本（不需要 escape，JS 会处理）
    prompt = PROMPT_TEMPLATE.format(
        title=item.get("headline", ""),
        digest=item.get("digest", ""),
        source=item.get("source", ""),
        tags=tags_raw.replace(",", "、"),
        today=datetime.now().strftime("%Y-%m-%d"),
    )
    # 把提示词 JS 转义，存进 data 属性
    prompt_escaped = prompt.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    return f"""
    <div class="news-item" data-prompt="{_escape(prompt)}">
      <div class="news-summary" onclick="toggle(this)">
        <div class="news-dot"></div>
        <div class="news-headline">{title}</div>
        <span class="news-tag {tag_cls}">{tag_label}</span>
        <div class="news-arrow">&#9658;</div>
      </div>
      <div class="news-detail">
        <div class="detail-body">{digest}</div>
        <div class="detail-actions">
          <a href="{_escape(link)}" target="_blank" class="detail-link">查看原文 &rarr;</a>
          <button class="copy-btn" onclick="copyPrompt(this)">&#8984; 点击复制深度分析提示词</button>
          <span class="detail-source">来源：{source}</span>
        </div>
        <div class="detail-tags">{tags_disp}</div>
      </div>
    </div>"""


def _section_html(cat: Dict, items: List[Dict]) -> str:
    if not items:
        return ""
    emoji = _escape(cat["emoji"])
    name  = _escape(cat["name"])
    color = cat["color"]
    items_html = "\n".join(_news_item_html(it) for it in items)
    return f"""
  <div class="section" id="{cat['id']}" style="--cat-color:{color}">
    <div class="section-header">
      <span class="section-icon">{emoji}</span>
      <span class="section-title">{name}</span>
      <span class="section-count">{len(items)}</span>
    </div>
    {items_html}
  </div>"""


def generate_html(categories: List[Dict], summarized: Dict[str, List[Dict]]) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)
    today     = datetime.now().strftime("%Y年%m月%d日")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")
    filename  = "AI-Daily-%s.html" % datetime.now().strftime("%Y%m%d")
    output    = str(OUTPUT_DIR / filename)

    total = sum(len(v) for v in summarized.values())
    important = sum(1 for v in summarized.values()
                    for it in v if it.get("importance") == "重要")

    # 导航 tab
    nav_tabs = "\n".join(
        f'  <a class="nav-tab" href="#{c["id"]}">{_escape(c["emoji"])} {_escape(c["name"])}</a>'
        for c in categories if summarized.get(c["id"])
    )

    # 各分类内容
    sections = "\n".join(
        _section_html(c, summarized.get(c["id"], []))
        for c in categories
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 行业日报 · {yesterday}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0a0a0f;--surface:#12121a;--surface2:#1a1a26;
    --border:#2a2a3a;--text:#e8e8f0;--muted:#7070a0;
    --accent:#ff6b35;--accent2:#00d4ff;--green:#00ff88;
  }}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:var(--bg);color:var(--text);font-family:'Noto Serif SC',serif;min-height:100vh;}}

  .header{{background:var(--surface);border-bottom:1px solid var(--border);padding:18px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
  .header-left{{display:flex;align-items:center;gap:16px;}}
  .logo{{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--accent);letter-spacing:3px;font-weight:600;}}
  .divider-v{{width:1px;height:22px;background:var(--border);}}
  .date-label{{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted);}}
  .header-right{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);}}

  .nav-tabs{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 32px;display:flex;overflow-x:auto;scrollbar-width:none;position:sticky;top:61px;z-index:99;}}
  .nav-tabs::-webkit-scrollbar{{display:none;}}
  .nav-tab{{padding:11px 18px;font-size:12px;font-family:'JetBrains Mono',monospace;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:all 0.2s;text-decoration:none;}}
  .nav-tab:hover{{color:var(--text);}}
  .nav-tab.active{{color:var(--accent);border-bottom-color:var(--accent);}}

  .main{{max-width:900px;margin:0 auto;padding:28px 24px;}}

  .stats-bar{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px 24px;margin-bottom:28px;display:flex;gap:28px;align-items:center;flex-wrap:wrap;}}
  .stat-item{{display:flex;flex-direction:column;gap:4px;}}
  .stat-num{{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:600;color:var(--text);line-height:1;}}
  .stat-label{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;}}
  .stat-divider{{width:1px;height:32px;background:var(--border);}}

  .section{{margin-bottom:36px;}}
  .section-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--border);}}
  .section-icon{{font-size:15px;}}
  .section-title{{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--cat-color,var(--accent));}}
  .section-count{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);background:var(--surface2);padding:2px 7px;border-radius:10px;margin-left:auto;}}

  .news-item{{border:1px solid var(--border);border-radius:6px;margin-bottom:5px;background:var(--surface);overflow:hidden;transition:border-color 0.2s;}}
  .news-item:hover{{border-color:#444460;}}
  .news-item.open{{border-color:#444480;}}
  .news-summary{{padding:11px 14px;cursor:pointer;display:flex;align-items:flex-start;gap:10px;user-select:none;}}
  .news-dot{{width:6px;height:6px;border-radius:50%;background:var(--muted);margin-top:7px;flex-shrink:0;transition:background 0.2s;}}
  .news-item:hover .news-dot,.news-item.open .news-dot{{background:var(--accent);}}
  .news-headline{{font-size:14px;line-height:1.6;color:var(--text);flex:1;}}
  .news-tag{{font-family:'JetBrains Mono',monospace;font-size:10px;padding:2px 7px;border-radius:3px;flex-shrink:0;margin-top:3px;}}
  .tag-high{{background:rgba(255,107,53,0.15);color:#ff6b35;}}
  .tag-mid{{background:rgba(0,212,255,0.1);color:#00d4ff;}}
  .tag-low{{background:rgba(112,112,160,0.15);color:var(--muted);}}
  .news-arrow{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);margin-top:5px;transition:transform 0.25s;flex-shrink:0;}}
  .news-item.open .news-arrow{{transform:rotate(90deg);color:var(--accent);}}

  .news-detail{{display:none;padding:0 14px 14px 30px;border-top:1px solid var(--border);background:var(--surface2);}}
  .news-item.open .news-detail{{display:block;}}
  .detail-body{{font-size:13px;line-height:1.9;color:#b0b0cc;padding:12px 0 10px;}}
  .detail-actions{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px;}}
  .detail-link{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent2);text-decoration:none;border-bottom:1px solid rgba(0,212,255,0.3);padding-bottom:1px;}}
  .detail-link:hover{{border-color:var(--accent2);}}
  .detail-source{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);}}

  .copy-btn{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:#0a0a0f;background:var(--accent2);border:1px solid var(--accent2);padding:5px 14px;border-radius:3px;cursor:pointer;transition:all 0.2s;display:inline-flex;align-items:center;gap:6px;box-shadow:0 0 10px rgba(0,212,255,0.25);}}
  .copy-btn:hover{{background:#33ddff;border-color:#33ddff;box-shadow:0 0 18px rgba(0,212,255,0.45);transform:translateY(-1px);}}
  .copy-btn:active{{transform:translateY(0);}}
  .copy-btn.copied{{color:#0a0a0f;background:var(--green);border-color:var(--green);box-shadow:0 0 14px rgba(0,255,136,0.4);}}

  .detail-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;}}
  .detail-tag{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);background:var(--surface);border:1px solid var(--border);padding:2px 8px;border-radius:3px;}}
  .footer{{text-align:center;padding:36px 24px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);border-top:1px solid var(--border);}}

  @media(max-width:600px){{.header{{padding:12px 14px;}}.main{{padding:16px 12px;}}.nav-tabs{{padding:0 12px;}}}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo">AI DAILY</div>
    <div class="divider-v"></div>
    <div class="date-label">{today} · 早报</div>
  </div>
  <div class="header-right">共 {total} 条 · 今日 {today} 发布</div>
</div>

<div class="nav-tabs">
{nav_tabs}
</div>

<div class="main">
  <div class="stats-bar">
    <div class="stat-item"><div class="stat-num">{total}</div><div class="stat-label">今日条目</div></div>
    <div class="stat-divider"></div>
    <div class="stat-item"><div class="stat-num">{important}</div><div class="stat-label">重要事件</div></div>
    <div class="stat-divider"></div>
    <div class="stat-item"><div class="stat-num">{len([c for c in categories if summarized.get(c['id'])])}</div><div class="stat-label">覆盖分类</div></div>
    <div class="stat-divider"></div>
    <div class="stat-item"><div class="stat-num" style="color:var(--green);font-size:15px">{yesterday}</div><div class="stat-label">数据时效</div></div>
  </div>

{sections}
</div>

<div class="footer">AI DAILY &middot; {yesterday} &middot; Serper + 豆包 AI &middot; 仅供参考</div>

<script>
function toggle(el) {{ el.closest('.news-item').classList.toggle('open'); }}

function copyPrompt(btn) {{
  const item   = btn.closest('.news-item');
  const prompt = item.dataset.prompt || '';
  const orig   = btn.innerHTML;
  const done   = () => {{
    btn.classList.add('copied');
    btn.innerHTML = '&#10003; 提示词已复制，去任意 AI 粘贴';
    setTimeout(() => {{ btn.classList.remove('copied'); btn.innerHTML = orig; }}, 3000);
  }};
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(prompt).then(done).catch(fb);
  }} else {{ fb(); }}
  function fb() {{
    const ta = document.createElement('textarea');
    ta.value = prompt; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy');
    document.body.removeChild(ta); done();
  }}
}}

const tabs = document.querySelectorAll('.nav-tab');
const secs  = document.querySelectorAll('.section');
window.addEventListener('scroll', () => {{
  let cur = '';
  secs.forEach(s => {{ if (window.scrollY >= s.offsetTop - 120) cur = s.id; }});
  tabs.forEach(t => t.classList.toggle('active', t.getAttribute('href') === '#' + cur));
}});
tabs.forEach(t => {{
  t.addEventListener('click', e => {{
    e.preventDefault();
    document.querySelector(t.getAttribute('href'))?.scrollIntoView({{behavior:'smooth',block:'start'}});
  }});
}});
// 默认激活第一个 tab
if (tabs.length) tabs[0].classList.add('active');
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("HTML 生成成功: %s", output)
    return output
