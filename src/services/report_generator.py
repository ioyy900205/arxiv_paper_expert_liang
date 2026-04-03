"""报告生成服务（Markdown + HTML）"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from dateutil import parser as date_parser

from src.logger import setup_logger
from src.utils import load_json

logger = setup_logger()


CATEGORY_ORDER = ["audiollm", "quant", "frontend", "llm", "backend", "other", "speech", "nlp", "cv", "multimodal"]

CATEGORY_COLORS = {
    "frontend": {"bg": "#e8f5e9", "text": "#1b5e20", "border": "#4caf50"},
    "llm":       {"bg": "#fff3e0", "text": "#e65100", "border": "#ff9800"},
    "backend":   {"bg": "#e3f2fd", "text": "#0d47a1", "border": "#2196f3"},
    "other":     {"bg": "#eceff1", "text": "#37474f", "border": "#78909c"},
    "audiollm":  {"bg": "#fce4ec", "text": "#880e4f", "border": "#e91e63"},
    "quant":     {"bg": "#f3e5f5", "text": "#4a148c", "border": "#9c27b0"},
    "speech":    {"bg": "#fff8e1", "text": "#ff6f00", "border": "#ffc107"},
    "multimodal":{"bg": "#f3e5f5", "text": "#4a148c", "border": "#9c27b0"},
    "nlp":       {"bg": "#e8eaf6", "text": "#283593", "border": "#3f51b5"},
    "cv":        {"bg": "#e0f7fa", "text": "#006064", "border": "#00bcd4"},
    "default":   {"bg": "#f5f5f5", "text": "#424242", "border": "#9e9e9e"},
}

CATEGORY_NAMES = {
    "frontend":  "前端",
    "llm":       "LLM",
    "backend":   "后端",
    "other":     "其他",
    "audiollm":  "AudioLLM",
    "quant":     "量化",
    "speech":    "Speech",
    "multimodal":"多模态",
    "nlp":       "NLP",
    "cv":        "CV",
    "default":   "其他",
}


def escape_html(text):
    if not isinstance(text, str):
        text = str(text)
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))


def get_sorted_categories(categories_dict):
    sorted_cats = [c for c in CATEGORY_ORDER if c in categories_dict]
    for cat in sorted(categories_dict.keys()):
        if cat not in sorted_cats:
            sorted_cats.append(cat)
    return sorted_cats


def get_paper_date_range(papers):
    dates = []
    for paper in papers:
        published = paper.get("published") or paper.get("updated", "")
        if published:
            try:
                dt = date_parser.parse(published)
                dates.append(dt)
            except Exception:
                continue
    if not dates:
        return None, None, None
    min_date, max_date = min(dates), max(dates)
    if min_date.date() == max_date.date():
        range_str = min_date.strftime("%Y-%m-%d")
    else:
        range_str = f"{min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}"
    return min_date, max_date, range_str


def load_date_info_from_source(input_file):
    inp = Path(input_file)
    if inp.exists():
        with open(inp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            first = data[0]
            if first.get("published"):
                return get_paper_date_range(data)

    for fallback in ["arxiv_results_content.json", "arxiv_results.json"]:
        fb = inp.parent / fallback
        if fb.exists():
            with open(fb, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list) and d and d[0].get("published"):
                return get_paper_date_range(d)
    return None, None, None


# ---- Markdown ----

def format_analysis_md(paper):
    aid = paper.get("arxiv_id", "")
    title = paper.get("title", "Untitled")
    cat = paper.get("category", "unknown")
    analysis = paper.get("analysis", {})

    lines = []
    lines.append(f"## {title}")
    lines.append(f'<a id="{aid.replace(".", "_")}"></a>\n')
    lines.append(f"> **arXiv ID**: `{aid}` | **分类**: `{cat.upper()}`\n")

    one_sentence = analysis.get("一句话总结", "")
    if one_sentence:
        lines.append("### 一句话总结\n")
        lines.append(f"> {one_sentence}\n")

    motivation = analysis.get("研究动机", {})
    if motivation:
        lines.append("### 研究动机\n")
        if isinstance(motivation, dict):
            c, e = motivation.get("结论", ""), motivation.get("展开", "")
            if c: lines.append(f"**{c}**\n")
            if e: lines.append(f"{e}\n")
        else:
            lines.append(f"{motivation}\n")

    highlights = analysis.get("核心亮点", [])
    if highlights:
        lines.append("### 核心亮点\n")
        for h in highlights:
            desc, quote = h.get("描述", ""), h.get("金句", "")
            lines.append(f"- **{desc}**")
            if quote: lines.append(f"  > {quote}")
            lines.append("")
        lines.append("")

    findings = analysis.get("反直觉发现", [])
    if findings:
        lines.append("### 反直觉发现\n")
        for f in findings:
            finding, why = f.get("发现", ""), f.get("为何反直觉", "")
            if finding: lines.append(f"- **{finding}**")
            if why: lines.append(f"  - 为何反直觉：{why}")
        lines.append("")

    tech = analysis.get("关键技术", {})
    if tech:
        lines.append("### 关键技术\n")
        if isinstance(tech, dict):
            c, e = tech.get("结论", ""), tech.get("展开", "")
            if c: lines.append(f"**{c}**\n")
            if e: lines.append(f"{e}\n")
        else:
            lines.append(f"{tech}\n")

    results = analysis.get("实验结果", {})
    if results:
        lines.append("### 实验结果\n")
        if isinstance(results, dict):
            c, e = results.get("结论", ""), results.get("展开", "")
            if c: lines.append(f"**{c}**\n")
            if e: lines.append(f"{e}\n")
        else:
            lines.append(f"{results}\n")

    limitations = analysis.get("局限性/缺陷", [])
    if limitations:
        lines.append("### 局限性/缺陷\n")
        for lim in limitations:
            if lim: lines.append(f"- {lim}")
        lines.append("")

    conclusion_data = analysis.get("论文结论", {})
    if conclusion_data:
        lines.append("### 论文结论\n")
        if isinstance(conclusion_data, dict):
            c, j = conclusion_data.get("结论", ""), conclusion_data.get("价值判断", "")
            if c: lines.append(f"**{c}**\n")
            if j: lines.append(f"{j}\n")
        else:
            lines.append(f"{conclusion_data}\n")

    scenarios = analysis.get("适用场景", {})
    if scenarios:
        lines.append("### 适用场景\n")
        if isinstance(scenarios, dict):
            c, b = scenarios.get("结论", ""), scenarios.get("边界条件", "")
            if c: lines.append(f"**{c}**\n")
            if b: lines.append(f"{b}\n")
        else:
            lines.append(f"{scenarios}\n")

    comment = analysis.get("犀利点评", "")
    if comment:
        lines.append("### 犀利点评\n")
        lines.append(f"> {comment}\n")

    model = paper.get("model_used", "")
    tokens = paper.get("tokens_used", 0)
    if model:
        lines.append(f"---\n")
        lines.append(f"*模型: {model} | Tokens: {tokens}*\n")

    lines.append("---\n")
    return "\n".join(lines)


def generate_toc_markdown(papers, date_range_str=None):
    categories = defaultdict(list)
    for paper in papers:
        categories[paper.get("category", "unknown")].append(paper)

    lines = []
    lines.append("# 论文分析报告\n")
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    if date_range_str:
        lines.append(f"_论文时间范围: {date_range_str} | 生成时间: {now_str}_\n")
    else:
        lines.append(f"_由 AI 自动生成 | {now_str}_\n")

    lines.append("## 目录概览\n")
    for cat in get_sorted_categories(categories):
        name = CATEGORY_NAMES.get(cat, cat.upper())
        lines.append(f"- [**{name} ({cat.upper()})**](#{cat}) ({len(categories[cat])} 篇)")
    lines.append("")

    lines.append("## 论文列表\n")
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "Untitled")[:65]
        cat = paper.get("category", "unknown")
        aid = paper.get("arxiv_id", "").replace(".", "_")
        lines.append(f"{i}. [{title}...](#{aid}) [`{cat.upper()}`]")
    lines.append("")
    lines.append("---\n")
    return "\n".join(lines)


def generate_markdown_report(papers, date_range_str=None):
    categories = defaultdict(list)
    for paper in papers:
        categories[paper.get("category", "unknown")].append(paper)

    lines = [generate_toc_markdown(papers, date_range_str)]

    for cat in get_sorted_categories(categories):
        name = CATEGORY_NAMES.get(cat, cat.upper())
        lines.append(f"\n## {name} ({cat.upper()})\n")
        lines.append(f"_{len(categories[cat])} 篇论文_\n")
        for paper in categories[cat]:
            lines.append(format_analysis_md(paper))

    return "\n".join(lines)


# ---- HTML ----

def generate_paper_html(paper):
    aid = paper.get("arxiv_id", "").replace(".", "_")
    title = escape_html(paper.get("title", "Untitled"))
    cat = paper.get("category", "unknown")
    analysis = paper.get("analysis", {})
    colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
    one_sentence = analysis.get("一句话总结", "")

    def blue_section(sec_title, content):
        return f'''<div class="blue-section">
            <div class="blue-title">{sec_title}</div>
            <div class="blue-content">{content}</div>
        </div>'''

    def field_content(motivation):
        if not motivation:
            return ""
        if isinstance(motivation, dict):
            c, e = motivation.get("结论", ""), motivation.get("展开", "")
            content = ""
            if c: content += f'<p class="conclusion">{escape_html(c)}</p>'
            if e: content += f'<p>{escape_html(e)}</p>'
            return content
        return f'<p>{escape_html(str(motivation))}</p>'

    html = f'''<article class="paper" id="paper-{aid}">
    <header class="paper-header" style="--cat-bg: {colors["bg"]}; --cat-text: {colors["text"]}; --cat-border: {colors["border"]}" onclick="togglePaper('{aid}')">
        <div class="paper-header-left">
            <span class="paper-toggle-icon">+</span>
            <div class="paper-title-area">
                <h2 class="paper-title">{title}</h2>
                <div class="paper-meta">
                    <span class="arxiv-id">arXiv: {paper.get("arxiv_id", "")}</span>
                    <span class="tag">{cat.upper()}</span>
                </div>
            </div>
        </div>
        {(f'<div class="one-sentence-preview">{escape_html(one_sentence)}</div>') if one_sentence else ''}
    </header>
    <div class="paper-body">
'''

    if one_sentence:
        html += blue_section(
            "一句话总结",
            f'<blockquote class="summary-quote">{escape_html(one_sentence)}</blockquote>'
        )

    for section_title, field_key, fmt_fn in [
        ("研究动机",   "研究动机",   field_content),
        ("关键技术",   "关键技术",   field_content),
        ("实验结果",   "实验结果",   field_content),
        ("论文结论",   "论文结论",   field_content),
        ("适用场景",   "适用场景",   field_content),
    ]:
        data = analysis.get(field_key, {})
        content = fmt_fn(data)
        if content:
            html += blue_section(section_title, content)

    highlights = analysis.get("核心亮点", [])
    if highlights:
        content = '<ul class="highlights">'
        for h in highlights:
            desc = escape_html(h.get("描述", ""))
            quote = escape_html(h.get("金句", ""))
            content += f'<li><p class="desc">{desc}</p>'
            if quote: content += f'<blockquote class="quote">{quote}</blockquote>'
            content += '</li>'
        content += '</ul>'
        html += blue_section(f"核心亮点 ({len(highlights)})", content)

    findings = analysis.get("反直觉发现", [])
    if findings:
        content = '<ul class="findings">'
        for f in findings:
            finding = escape_html(f.get("发现", ""))
            why = escape_html(f.get("为何反直觉", ""))
            content += f'<li><p class="finding">{finding}</p><p class="why">为何反直觉：{why}</p></li>'
        content += '</ul>'
        html += blue_section(f"反直觉发现 ({len(findings)})", content)

    limitations = analysis.get("局限性/缺陷", [])
    if limitations:
        content = '<ul class="limitations">'
        for lim in limitations:
            if lim: content += f'<li>{escape_html(lim)}</li>'
        content += '</ul>'
        html += blue_section(f"局限性/缺陷 ({len(limitations)})", content)

    comment = analysis.get("犀利点评", "")
    if comment:
        html += blue_section(
            "犀利点评",
            f'<blockquote class="comment-quote">{escape_html(comment)}</blockquote>'
        )

    html += '''
            </div>
        </article>'''
    return html


def generate_html_report(papers, date_range_str=None):
    categories = defaultdict(list)
    for paper in papers:
        categories[paper.get("category", "unknown")].append(paper)
    sorted_cats = get_sorted_categories(categories)

    css = """
        :root {
            --bg-primary: #ffffff; --bg-secondary: #f8f9fa; --bg-tertiary: #e9ecef;
            --text-primary: #212529; --text-secondary: #495057; --text-muted: #6c757d;
            --divider: #dee2e6; --accent: #4263eb; --accent-light: #e7eaff;
            --shadow: 0 2px 12px rgba(0,0,0,0.06); --radius: 10px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               background: var(--bg-secondary); color: var(--text-primary);
               line-height: 1.75; font-size: 15px; }
        .container { max-width: 1100px; margin: 0 auto; padding: 2rem; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 3rem 2rem; border-radius: var(--radius);
                  margin-bottom: 2rem; box-shadow: var(--shadow); }
        .header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.3rem; }
        .header .subtitle { opacity: 0.85; font-size: 0.95rem; }
        .toc { background: white; border-radius: var(--radius); padding: 1.5rem 2rem;
               margin-bottom: 2rem; box-shadow: var(--shadow); }
        .toc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .toc-header h2 { font-size: 1.3rem; }
        .paper-count { background: var(--accent); color: white; padding: 0.2rem 0.7rem;
                       border-radius: 20px; font-size: 0.85rem; }
        .toc-overview h3, .toc-papers h3 { font-size: 0.9rem; color: var(--text-muted);
                                             text-transform: uppercase; letter-spacing: 0.5px; margin: 1rem 0 0.6rem; }
        .category-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .category-tag { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.35rem 0.8rem;
                        border-radius: 20px; font-size: 0.85rem; font-weight: 600;
                        background: color-mix(in srgb, var(--cat-color) 12%, white);
                        color: var(--cat-color); border: 1px solid color-mix(in srgb, var(--cat-color) 30%, white);
                        text-decoration: none; transition: all 0.2s; }
        .category-tag:hover { background: color-mix(in srgb, var(--cat-color) 20%, white); text-decoration: none; }
        .category-tag span { background: var(--cat-color); color: white; padding: 0 0.4rem;
                             border-radius: 10px; font-size: 0.75rem; }
        .paper-nav { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 0.4rem; }
        .nav-item { display: flex; align-items: baseline; gap: 0.5rem; }
        .nav-num { color: var(--accent); font-weight: 600; font-size: 0.85rem; min-width: 1.5rem; }
        .nav-item a { color: var(--text-primary); text-decoration: none; font-size: 0.9rem; }
        .nav-item a:hover { color: var(--accent); text-decoration: underline; }
        .category-section { margin-bottom: 2.5rem; }
        .category-header { display: flex; align-items: center; gap: 1rem; padding: 0.8rem 1.2rem;
                           border-radius: var(--radius); background: white; margin-bottom: 1rem;
                           box-shadow: var(--shadow); border-left: 4px solid var(--accent); }
        .category-header h2 { font-size: 1.2rem; color: var(--accent); }
        .category-header .count { background: var(--accent-light); color: var(--accent);
                                   padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
        .paper { background: white; border-radius: var(--radius); margin-bottom: 1.5rem;
                 box-shadow: var(--shadow); overflow: hidden; }
        .paper-header { padding: 1rem 1.5rem; background: var(--cat-bg, var(--bg-secondary));
                        border-left: 4px solid var(--cat-border, var(--accent)); cursor: pointer;
                        transition: background 0.2s; }
        .paper-header:hover { filter: brightness(0.98); }
        .paper-header-left { display: flex; align-items: flex-start; gap: 0.8rem; }
        .paper-toggle-icon { font-size: 1.2rem; font-weight: bold; color: var(--cat-border, var(--accent));
                             line-height: 1.3; transition: transform 0.2s; }
        .paper.expanded .paper-toggle-icon { transform: rotate(45deg); }
        .paper-title-area { flex: 1; }
        .paper-title { font-size: 1.1rem; font-weight: 600; color: var(--cat-text, var(--text-primary));
                        margin-bottom: 0.4rem; line-height: 1.4; }
        .paper-meta { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
        .arxiv-id { font-family: monospace; font-size: 0.8rem; color: var(--cat-text, var(--text-muted)); opacity: 0.8; }
        .tag { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;
               background: white; color: var(--cat-border, var(--accent)); }
        .one-sentence-preview { margin-top: 0.6rem; margin-left: 2rem; padding: 0.5rem 0.8rem;
                                background: rgba(255,255,255,0.7);
                                border-left: 3px solid var(--cat-border, var(--accent));
                                font-size: 0.9rem; color: var(--text-secondary); font-style: italic;
                                border-radius: 0 6px 6px 0; }
        .paper-body { display: none; padding: 0; }
        .paper.expanded .paper-body { display: block; }
        .blue-section { border-bottom: 1px solid var(--divider); padding: 0.9rem 1.5rem; }
        .blue-section:last-child { border-bottom: none; }
        .blue-title { font-weight: 600; font-size: 0.95rem; color: var(--accent);
                      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.7rem; }
        .blue-title::before { content: ""; display: inline-block; width: 3px; height: 1em;
                               background: var(--accent); border-radius: 2px; }
        .blue-content { font-size: 0.9rem; color: var(--text-secondary); line-height: 1.7; }
        .blue-content blockquote { background: var(--accent-light); border-left: 4px solid var(--accent);
                                    padding: 0.8rem 1rem; border-radius: 0 6px 6px 0; font-style: italic; }
        .blue-content .summary-quote { font-size: 0.95rem; }
        .blue-content .comment-quote { background: #fffbeb; border-left-color: #f59e0b; }
        .blue-content .conclusion { font-weight: 600; color: var(--text-primary); }
        .blue-content ul { padding-left: 0; }
        .blue-content li { margin-bottom: 0; }
        .blue-content .highlights li, .blue-content .findings li {
            background: var(--bg-secondary); padding: 0.8rem; border-radius: 8px;
            margin-bottom: 0.7rem; list-style: none; }
        .blue-content .highlights li:last-child, .blue-content .findings li:last-child { margin-bottom: 0; }
        .blue-content .desc { margin-bottom: 0.4rem; }
        .blue-content .quote { font-size: 0.9rem; color: var(--text-muted);
                                border-left: 3px solid var(--accent); padding-left: 0.8rem; margin-top: 0.5rem; }
        .blue-content .finding { font-weight: 600; margin-bottom: 0.3rem; }
        .blue-content .why { font-size: 0.9rem; color: var(--text-muted); margin: 0; }
        .blue-content .limitations { padding-left: 1.2rem; }
        .blue-content .limitations li { background: none; padding: 0.2rem 0; list-style: disc;
                                         color: var(--text-secondary); }
        .footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem; }
        .back-to-top { position: fixed; bottom: 2rem; right: 2rem; background: var(--accent); color: white;
                        width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center;
                        justify-content: center; text-decoration: none; box-shadow: 0 2px 8px rgba(66,99,235,0.3);
                        font-size: 1.2rem; transition: transform 0.2s, box-shadow 0.2s; }
        .back-to-top:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(66,99,235,0.4);
                             color: white; text-decoration: none; }
        @media (max-width: 768px) { .container { padding: 1rem; } .paper-nav { grid-template-columns: 1fr; }
                                     .header { padding: 2rem 1.5rem; } .header h1 { font-size: 1.5rem; } }
    """

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文分析报告</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>论文分析报告</h1>
            <p class="subtitle">论文时间范围: {date_range_str or "未知"} | {len(papers)} 篇论文 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </header>

        <div class="toc">
            <div class="toc-header">
                <h2>目录</h2>
                <span class="paper-count">{len(papers)} 篇</span>
            </div>
            <div class="toc-overview">
                <h3>按分类</h3>
                <div class="category-tags">
'''
    for cat in sorted_cats:
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        name = CATEGORY_NAMES.get(cat, cat.upper())
        html += f'                    <a href="#{cat}" class="category-tag" style="--cat-color: {colors["border"]}">{name}<span>{len(categories[cat])}</span></a>\n'

    html += '''                </div>
            </div>
            <div class="toc-papers">
                <h3>论文列表</h3>
                <div class="paper-nav">
'''
    for i, paper in enumerate(papers, 1):
        t = escape_html(paper.get("title", "Untitled")[:55])
        c = escape_html(paper.get("category", "unknown"))
        a = escape_html(paper.get("arxiv_id", "").replace(".", "_"))
        html += f'                    <div class="nav-item"><span class="nav-num">{i}</span><a href="#{a}">{t}</a></div>\n'

    html += '''                </div>
            </div>
        </div>
'''

    for cat in sorted_cats:
        cat_papers = categories[cat]
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        name = CATEGORY_NAMES.get(cat, cat.upper())
        html += f'''
        <section class="category-section" id="{cat}">
            <header class="category-header" style="--accent: {colors['border']}">
                <h2>{name}</h2>
                <span class="count">{len(cat_papers)} 篇</span>
            </header>
'''
        for paper in cat_papers:
            html += generate_paper_html(paper) + "\n"
        html += '        </section>\n'

    html += '''
        <footer class="footer">
            <p>报告生成完成</p>
        </footer>
    </div>
    <a href="#" class="back-to-top" title="回到顶部">^</a>
    <script>
        function togglePaper(paperId) {
            document.getElementById('paper-' + paperId).classList.toggle('expanded');
        }
    </script>
</body>
</html>'''

    return html


def generate_report(
    input_path: str | Path = "results/arxiv_results_content_analysis.json",
    output_dir: Optional[str | Path] = None,
    date_range_str: Optional[str] = None,
) -> None:
    """生成 HTML 和 Markdown 格式的报告。"""
    inp = Path(input_path)
    if not inp.exists():
        raise FileNotFoundError(f"{input_path} 不存在")

    out_dir = Path(output_dir) if output_dir else inp.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if inp.stem.endswith("_analysis"):
        output_name = inp.stem[:-len("_analysis")] + "_report"
    elif inp.stem.startswith("analysis"):
        output_name = inp.stem.replace("analysis", "report", 1)
    else:
        output_name = inp.stem + "_report"

    output_html = out_dir / f"{output_name}.html"
    output_md = out_dir / f"{output_name}.md"

    with open(inp, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = data if isinstance(data, list) else data.get("papers", [data])
    logger.info(f"共 {len(papers)} 篇论文")

    if date_range_str is None:
        _, _, date_range_str = load_date_info_from_source(inp)
    if date_range_str:
        logger.info(f"论文时间范围: {date_range_str}")

    html_content = generate_html_report(papers, date_range_str)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"HTML 报告已保存: {output_html}")

    md_content = generate_markdown_report(papers, date_range_str)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Markdown 报告已保存: {output_md}")
