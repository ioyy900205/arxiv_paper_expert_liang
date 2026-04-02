#!/usr/bin/env python3
"""
arxiv 论文分析报告生成器
同时生成浅色主题 HTML 和带目录的 Markdown 格式报告
支持折叠式选项卡布局
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============ 配置 ============
INPUT_FILE = Path(__file__).parent.parent / "results" / "analysis_5days.json"
OUTPUT_HTML = Path(__file__).parent.parent / "results" / "paper_analysis_report.html"
OUTPUT_MD = Path(__file__).parent.parent / "results" / "paper_analysis_report.md"

# ============ Category 排序（前端 > LLM > 后端 > 其他）============
CATEGORY_ORDER = ["frontend", "llm", "backend", "audiollm", "speech", "nlp", "cv", "multimodal"]

# ============ Category 配色（浅色主题） ============
CATEGORY_COLORS = {
    "frontend": {"bg": "#e8f5e9", "text": "#1b5e20", "border": "#4caf50"},
    "llm": {"bg": "#fff3e0", "text": "#e65100", "border": "#ff9800"},
    "backend": {"bg": "#e3f2fd", "text": "#0d47a1", "border": "#2196f3"},
    "audiollm": {"bg": "#fce4ec", "text": "#880e4f", "border": "#e91e63"},
    "speech": {"bg": "#fff8e1", "text": "#ff6f00", "border": "#ffc107"},
    "multimodal": {"bg": "#f3e5f5", "text": "#4a148c", "border": "#9c27b0"},
    "nlp": {"bg": "#e8eaf6", "text": "#283593", "border": "#3f51b5"},
    "cv": {"bg": "#e0f7fa", "text": "#006064", "border": "#00bcd4"},
    "default": {"bg": "#f5f5f5", "text": "#424242", "border": "#9e9e9e"},
}

CATEGORY_NAMES = {
    "frontend": "前端",
    "llm": "LLM",
    "backend": "后端",
    "audiollm": "AudioLLM",
    "speech": "Speech",
    "multimodal": "多模态",
    "nlp": "NLP",
    "cv": "CV",
    "default": "其他",
}


def escape_html(text):
    """转义 HTML 特殊字符"""
    if not isinstance(text, str):
        text = str(text)
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def get_sorted_categories(categories_dict):
    """按指定顺序返回分类列表，只返回存在的分类"""
    sorted_cats = []
    for cat in CATEGORY_ORDER:
        if cat in categories_dict:
            sorted_cats.append(cat)
    # 添加未在 CATEGORY_ORDER 中的分类（按字母序）
    for cat in sorted(categories_dict.keys()):
        if cat not in sorted_cats:
            sorted_cats.append(cat)
    return sorted_cats


def generate_toc_markdown(papers):
    """生成 Markdown 目录"""
    categories = defaultdict(list)
    for paper in papers:
        cat = paper.get("category", "unknown")
        categories[cat].append(paper)

    lines = []
    lines.append("# 论文分析报告\n")
    lines.append(f"_由 AI 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    # 目录概览
    lines.append("## 目录概览\n")
    for cat in get_sorted_categories(categories):
        name = CATEGORY_NAMES.get(cat, cat.upper())
        lines.append(f"- [**{name} ({cat.upper()})**](#{cat}) ({len(categories[cat])} 篇)")
    lines.append("")

    # 论文列表
    lines.append("## 论文列表\n")
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "Untitled")[:65]
        cat = paper.get("category", "unknown")
        aid = paper.get("arxiv_id", "").replace(".", "_")
        lines.append(f"{i}. [{title}...](#{aid}) [`{cat.upper()}`]")
    lines.append("")
    lines.append("---\n")
    return "\n".join(lines)


def generate_markdown_report(papers):
    """生成 Markdown 报告（带目录）"""
    categories = defaultdict(list)
    for paper in papers:
        cat = paper.get("category", "unknown")
        categories[cat].append(paper)

    lines = []
    lines.append(generate_toc_markdown(papers))

    for cat in get_sorted_categories(categories):
        name = CATEGORY_NAMES.get(cat, cat.upper())
        lines.append(f'\n## {name} ({cat.upper()})\n')
        lines.append(f'_{len(categories[cat])} 篇论文_\n')
        for paper in categories[cat]:
            lines.append(format_analysis_md(paper))

    return "\n".join(lines)


def format_analysis_md(paper):
    """将单篇论文的分析格式化为 Markdown"""
    aid = paper.get("arxiv_id", "")
    title = paper.get("title", "Untitled")
    cat = paper.get("category", "unknown")
    analysis = paper.get("analysis", {})

    lines = []
    lines.append(f'## {title}')
    lines.append(f'<a id="{aid.replace(".", "_")}"></a>\n')
    lines.append(f'> **arXiv ID**: `{aid}` | **分类**: `{cat.upper()}`\n')

    one_sentence = analysis.get("一句话总结", "")
    if one_sentence:
        lines.append("### 一句话总结\n")
        lines.append(f"> {one_sentence}\n")

    motivation = analysis.get("研究动机", {})
    if motivation:
        lines.append("### 研究动机\n")
        if isinstance(motivation, dict):
            conclusion = motivation.get("结论", "")
            expand = motivation.get("展开", "")
            if conclusion:
                lines.append(f"**{conclusion}**\n")
            if expand:
                lines.append(f"{expand}\n")
        else:
            lines.append(f"{motivation}\n")

    highlights = analysis.get("核心亮点", [])
    if highlights:
        lines.append("### 核心亮点\n")
        for h in highlights:
            desc = h.get("描述", "")
            quote = h.get("金句", "")
            lines.append(f"- **{desc}**")
            if quote:
                lines.append(f"  > {quote}")
            lines.append("")

    findings = analysis.get("反直觉发现", [])
    if findings:
        lines.append("### 反直觉发现\n")
        for f in findings:
            finding = f.get("发现", "")
            why = f.get("为何反直觉", "")
            if finding:
                lines.append(f"- **{finding}**")
            if why:
                lines.append(f"  - 为何反直觉：{why}")
        lines.append("")

    tech = analysis.get("关键技术", {})
    if tech:
        lines.append("### 关键技术\n")
        if isinstance(tech, dict):
            conclusion = tech.get("结论", "")
            expand = tech.get("展开", "")
            if conclusion:
                lines.append(f"**{conclusion}**\n")
            if expand:
                lines.append(f"{expand}\n")
        else:
            lines.append(f"{tech}\n")

    results = analysis.get("实验结果", {})
    if results:
        lines.append("### 实验结果\n")
        if isinstance(results, dict):
            conclusion = results.get("结论", "")
            expand = results.get("展开", "")
            if conclusion:
                lines.append(f"**{conclusion}**\n")
            if expand:
                lines.append(f"{expand}\n")
        else:
            lines.append(f"{results}\n")

    limitations = analysis.get("局限性/缺陷", [])
    if limitations:
        lines.append("### 局限性/缺陷\n")
        for lim in limitations:
            if lim:
                lines.append(f"- {lim}")
        lines.append("")

    conclusion_data = analysis.get("论文结论", {})
    if conclusion_data:
        lines.append("### 论文结论\n")
        if isinstance(conclusion_data, dict):
            c = conclusion_data.get("结论", "")
            judgment = conclusion_data.get("价值判断", "")
            if c:
                lines.append(f"**{c}**\n")
            if judgment:
                lines.append(f"{judgment}\n")
        else:
            lines.append(f"{conclusion_data}\n")

    scenarios = analysis.get("适用场景", {})
    if scenarios:
        lines.append("### 适用场景\n")
        if isinstance(scenarios, dict):
            c = scenarios.get("结论", "")
            bounds = scenarios.get("边界条件", "")
            if c:
                lines.append(f"**{c}**\n")
            if bounds:
                lines.append(f"{bounds}\n")
        else:
            lines.append(f"{scenarios}\n")

    comment = analysis.get("犀利点评", "")
    if comment:
        lines.append("### 犀利点评\n")
        lines.append(f"> {comment}\n")

    mode = paper.get("mode", "")
    model = paper.get("model_used", "")
    tokens = paper.get("tokens_used", 0)
    if mode or model:
        lines.append(f"---\n")
        lines.append(f"*分析模式: {mode} | 模型: {model} | Tokens: {tokens}*\n")

    lines.append("---\n")
    return "\n".join(lines)


def generate_paper_sections_html(paper, cat):
    """生成单篇论文的可折叠 sections HTML"""
    analysis = paper.get("analysis", {})
    aid = paper.get("arxiv_id", "").replace(".", "_")
    colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])

    sections_html = []

    # 一句话总结 - 默认展开
    one_sentence = analysis.get("一句话总结", "")
    if one_sentence:
        sections_html.append(f'''
            <div class="section-item expanded" data-section="summary-{aid}">
                <div class="section-header" onclick="toggleSection('summary-{aid}')">
                    <span class="section-title">一句话总结</span>
                    <span class="toggle-icon">−</span>
                </div>
                <div class="section-content">
                    <blockquote>{escape_html(one_sentence)}</blockquote>
                </div>
            </div>''')

    # 研究动机
    motivation = analysis.get("研究动机", {})
    if motivation:
        content = ""
        if isinstance(motivation, dict):
            conclusion = motivation.get("结论", "")
            expand = motivation.get("展开", "")
            if conclusion:
                content += f'<p class="conclusion">{escape_html(conclusion)}</p>'
            if expand:
                content += f'<p>{escape_html(expand)}</p>'
        else:
            content = f'<p>{escape_html(str(motivation))}</p>'
        if content:
            sections_html.append(f'''
            <div class="section-item" data-section="motivation-{aid}">
                <div class="section-header" onclick="toggleSection('motivation-{aid}')">
                    <span class="section-title">研究动机</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 核心亮点
    highlights = analysis.get("核心亮点", [])
    if highlights:
        content = '<ul class="highlights">'
        for h in highlights:
            desc = escape_html(h.get("描述", ""))
            quote = escape_html(h.get("金句", ""))
            content += f'<li><p class="desc">{desc}</p>'
            if quote:
                content += f'<blockquote class="quote">{quote}</blockquote>'
            content += '</li>'
        content += '</ul>'
        sections_html.append(f'''
            <div class="section-item" data-section="highlights-{aid}">
                <div class="section-header" onclick="toggleSection('highlights-{aid}')">
                    <span class="section-title">核心亮点 ({len(highlights)})</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 反直觉发现
    findings = analysis.get("反直觉发现", [])
    if findings:
        content = '<ul class="findings">'
        for f in findings:
            finding = escape_html(f.get("发现", ""))
            why = escape_html(f.get("为何反直觉", ""))
            content += f'<li><p class="finding">{finding}</p><p class="why">为何反直觉：{why}</p></li>'
        content += '</ul>'
        sections_html.append(f'''
            <div class="section-item" data-section="findings-{aid}">
                <div class="section-header" onclick="toggleSection('findings-{aid}')">
                    <span class="section-title">反直觉发现 ({len(findings)})</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 关键技术
    tech = analysis.get("关键技术", {})
    if tech:
        content = ""
        if isinstance(tech, dict):
            conclusion = tech.get("结论", "")
            expand = tech.get("展开", "")
            if conclusion:
                content += f'<p class="conclusion">{escape_html(conclusion)}</p>'
            if expand:
                content += f'<p>{escape_html(expand)}</p>'
        else:
            content = f'<p>{escape_html(str(tech))}</p>'
        if content:
            sections_html.append(f'''
            <div class="section-item" data-section="tech-{aid}">
                <div class="section-header" onclick="toggleSection('tech-{aid}')">
                    <span class="section-title">关键技术</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 实验结果
    results = analysis.get("实验结果", {})
    if results:
        content = ""
        if isinstance(results, dict):
            conclusion = results.get("结论", "")
            expand = results.get("展开", "")
            if conclusion:
                content += f'<p class="conclusion">{escape_html(conclusion)}</p>'
            if expand:
                content += f'<p>{escape_html(expand)}</p>'
        else:
            content = f'<p>{escape_html(str(results))}</p>'
        if content:
            sections_html.append(f'''
            <div class="section-item" data-section="results-{aid}">
                <div class="section-header" onclick="toggleSection('results-{aid}')">
                    <span class="section-title">实验结果</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 局限性
    limitations = analysis.get("局限性/缺陷", [])
    if limitations:
        content = '<ul class="limitations">'
        for lim in limitations:
            if lim:
                content += f'<li>{escape_html(lim)}</li>'
        content += '</ul>'
        sections_html.append(f'''
            <div class="section-item" data-section="limitations-{aid}">
                <div class="section-header" onclick="toggleSection('limitations-{aid}')">
                    <span class="section-title">局限性/缺陷 ({len(limitations)})</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 论文结论
    conclusion_data = analysis.get("论文结论", {})
    if conclusion_data:
        content = ""
        if isinstance(conclusion_data, dict):
            c = conclusion_data.get("结论", "")
            judgment = conclusion_data.get("价值判断", "")
            if c:
                content += f'<p class="conclusion">{escape_html(c)}</p>'
            if judgment:
                content += f'<p>{escape_html(judgment)}</p>'
        else:
            content = f'<p>{escape_html(str(conclusion_data))}</p>'
        if content:
            sections_html.append(f'''
            <div class="section-item" data-section="conclusion-{aid}">
                <div class="section-header" onclick="toggleSection('conclusion-{aid}')">
                    <span class="section-title">论文结论</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 适用场景
    scenarios = analysis.get("适用场景", {})
    if scenarios:
        content = ""
        if isinstance(scenarios, dict):
            c = scenarios.get("结论", "")
            bounds = scenarios.get("边界条件", "")
            if c:
                content += f'<p class="conclusion">{escape_html(c)}</p>'
            if bounds:
                content += f'<p>{escape_html(bounds)}</p>'
        else:
            content = f'<p>{escape_html(str(scenarios))}</p>'
        if content:
            sections_html.append(f'''
            <div class="section-item" data-section="scenarios-{aid}">
                <div class="section-header" onclick="toggleSection('scenarios-{aid}')">
                    <span class="section-title">适用场景</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">{content}</div>
            </div>''')

    # 犀利点评
    comment = analysis.get("犀利点评", "")
    if comment:
        sections_html.append(f'''
            <div class="section-item" data-section="comment-{aid}">
                <div class="section-header" onclick="toggleSection('comment-{aid}')">
                    <span class="section-title">犀利点评</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="section-content collapsed">
                    <blockquote class="comment-quote">{escape_html(comment)}</blockquote>
                </div>
            </div>''')

    return "\n".join(sections_html)


def generate_html_report(papers):
    """生成完整的 HTML 报告（折叠式选项卡布局）"""
    categories = defaultdict(list)
    for paper in papers:
        cat = paper.get("category", "unknown")
        categories[cat].append(paper)

    sorted_cats = get_sorted_categories(categories)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文分析报告</title>
    <style>
        :root {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #212529;
            --text-secondary: #495057;
            --text-muted: #6c757d;
            --border-color: #dee2e6;
            --accent: #4263eb;
            --accent-light: #e7eaff;
            --shadow: 0 2px 12px rgba(0,0,0,0.06);
            --radius: 10px;
            --sidebar-width: 280px;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-secondary);
            color: var(--text-primary);
            line-height: 1.7;
            font-size: 15px;
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 0.3rem; }}
        .header .subtitle {{ opacity: 0.85; font-size: 0.9rem; }}

        /* Main Layout */
        .main-layout {{
            display: flex;
            min-height: calc(100vh - 100px);
        }}

        /* Sidebar */
        .sidebar {{
            width: var(--sidebar-width);
            background: white;
            border-right: 1px solid var(--border-color);
            overflow-y: auto;
            position: sticky;
            top: 0;
            height: calc(100vh);
            padding: 1rem 0;
        }}

        .sidebar-header {{
            padding: 0.5rem 1rem 1rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 0.5rem;
        }}
        .sidebar-header h2 {{ font-size: 1rem; color: var(--text-primary); }}
        .sidebar-header .total {{ font-size: 0.8rem; color: var(--text-muted); }}

        /* Category Groups */
        .cat-group {{
            border-bottom: 1px solid var(--border-color);
        }}

        .cat-header {{
            display: flex;
            align-items: center;
            padding: 0.8rem 1rem;
            cursor: pointer;
            transition: background 0.2s;
            gap: 0.5rem;
        }}
        .cat-header:hover {{ background: var(--bg-secondary); }}

        .cat-toggle {{
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
            color: var(--text-muted);
            transition: transform 0.2s;
        }}
        .cat-group.expanded .cat-toggle {{ transform: rotate(90deg); }}

        .cat-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .cat-name {{
            flex: 1;
            font-weight: 600;
            font-size: 0.95rem;
        }}

        .cat-count {{
            background: var(--bg-tertiary);
            color: var(--text-muted);
            padding: 0.1rem 0.5rem;
            border-radius: 10px;
            font-size: 0.75rem;
        }}

        .cat-papers {{
            display: none;
            padding: 0.3rem 0 0.5rem 2.5rem;
        }}
        .cat-group.expanded .cat-papers {{ display: block; }}

        .paper-link {{
            display: block;
            padding: 0.4rem 0.6rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: 4px;
            transition: background 0.2s;
            cursor: pointer;
        }}
        .paper-link:hover {{ background: var(--accent-light); color: var(--accent); }}
        .paper-link.active {{ background: var(--accent-light); color: var(--accent); font-weight: 600; }}

        /* Content Area */
        .content {{
            flex: 1;
            padding: 1.5rem 2rem;
            overflow-y: auto;
        }}

        .paper-detail {{
            display: none;
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        .paper-detail.active {{ display: block; }}

        .paper-header {{
            padding: 1rem 1.2rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }}
        .paper-back {{
            background: none;
            border: none;
            cursor: pointer;
            color: var(--accent);
            font-size: 1.2rem;
            padding: 0.2rem;
        }}
        .paper-back:hover {{ opacity: 0.7; }}

        .paper-title-area {{ flex: 1; }}
        .paper-title {{ font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.3rem; line-height: 1.4; }}
        .paper-meta {{ display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
        .arxiv-id {{ font-family: monospace; font-size: 0.8rem; color: var(--text-muted); }}
        .tag {{
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Sections */
        .section-item {{
            border-bottom: 1px solid var(--border-color);
        }}
        .section-item:last-child {{ border-bottom: none; }}

        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.8rem 1.2rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .section-header:hover {{ background: var(--bg-secondary); }}

        .section-title {{
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
        }}

        .toggle-icon {{
            color: var(--accent);
            font-weight: bold;
            font-size: 1rem;
            transition: transform 0.2s;
        }}

        .section-content {{
            padding: 0 1.2rem 1rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
            line-height: 1.7;
        }}
        .section-content.collapsed {{ display: none; }}
        .section-item.expanded .section-content {{ display: block; }}
        .section-item.expanded .toggle-icon {{ transform: rotate(180deg); }}

        .section-content blockquote {{
            background: var(--accent-light);
            border-left: 3px solid var(--accent);
            padding: 0.6rem 0.8rem;
            border-radius: 0 4px 4px 0;
            font-style: italic;
        }}
        .section-content .comment-quote {{
            background: #fffbeb;
            border-left-color: #f59e0b;
        }}
        .section-content .conclusion {{ font-weight: 600; color: var(--text-primary); }}

        .section-content ul {{
            padding-left: 1.2rem;
            margin: 0;
        }}
        .section-content li {{ margin-bottom: 0.5rem; }}
        .section-content .highlights li, .section-content .findings li {{
            background: var(--bg-secondary);
            padding: 0.6rem 0.8rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            list-style: none;
            margin-left: -1.2rem;
        }}
        .section-content .desc {{ margin-bottom: 0.3rem; }}
        .section-content .quote {{
            font-size: 0.85rem;
            color: var(--text-muted);
            border-left: 2px solid var(--accent);
            padding-left: 0.6rem;
            margin-top: 0.4rem;
        }}
        .section-content .finding {{ font-weight: 600; margin-bottom: 0.2rem; }}
        .section-content .why {{ font-size: 0.85rem; color: var(--text-muted); }}
        .section-content .limitations li {{
            background: none;
            padding: 0.2rem 0;
            list-style: disc;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 1.5rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            background: white;
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
            }}
            .main-layout {{ flex-direction: column; }}
            .content {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <h1>论文分析报告</h1>
        <p class="subtitle">由 AI 自动生成 | {len(papers)} 篇论文 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </header>

    <div class="main-layout">
        <nav class="sidebar">
            <div class="sidebar-header">
                <h2>目录导航</h2>
                <div class="total">{len(papers)} 篇论文 | {len(sorted_cats)} 个分类</div>
            </div>
'''

    # 生成侧边栏分类列表
    for cat in sorted_cats:
        cat_papers = categories[cat]
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        name = CATEGORY_NAMES.get(cat, cat.upper())
        html += f'''
            <div class="cat-group" id="cat-{cat}">
                <div class="cat-header" onclick="toggleCategory('{cat}')">
                    <span class="cat-toggle">▶</span>
                    <span class="cat-dot" style="background: {colors['border']}"></span>
                    <span class="cat-name">{name}</span>
                    <span class="cat-count">{len(cat_papers)}</span>
                </div>
                <div class="cat-papers">
'''
        for paper in cat_papers:
            aid = paper.get("arxiv_id", "").replace(".", "_")
            title = escape_html(paper.get("title", "Untitled")[:40])
            html += f'                    <div class="paper-link" onclick="showPaper(\'{aid}\', \'{cat}\')">{title}</div>\n'
        html += '                </div>\n            </div>\n'

    html += '''
        </nav>

        <main class="content">
            <div id="welcome-message" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                <p style="font-size: 1.1rem;">从左侧目录选择分类和论文查看详情</p>
            </div>
'''

    # 生成论文详情区域
    for paper in papers:
        aid = paper.get("arxiv_id", "").replace(".", "_")
        cat = paper.get("category", "unknown")
        title = escape_html(paper.get("title", "Untitled"))
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        sections = generate_paper_sections_html(paper, cat)

        html += f'''
            <div class="paper-detail" id="paper-{aid}">
                <div class="paper-header" style="border-left: 4px solid {colors['border']}">
                    <button class="paper-back" onclick="hidePaper('{aid}')">←</button>
                    <div class="paper-title-area">
                        <h2 class="paper-title">{title}</h2>
                        <div class="paper-meta">
                            <span class="arxiv-id">arXiv: {paper.get('arxiv_id', '')}</span>
                            <span class="tag" style="background: {colors['bg']}; color: {colors['text']}">{cat.upper()}</span>
                        </div>
                    </div>
                </div>
                <div class="paper-sections">
{sections}
                </div>
            </div>
'''

    html += '''
        </main>
    </div>

    <footer class="footer">
        报告生成完成
    </footer>

    <script>
        function toggleCategory(catId) {
            const group = document.getElementById('cat-' + catId);
            group.classList.toggle('expanded');
        }

        function showPaper(paperId, catId) {
            // Hide welcome message
            document.getElementById('welcome-message').style.display = 'none';

            // Hide all papers
            document.querySelectorAll('.paper-detail').forEach(p => p.classList.remove('active'));

            // Show selected paper
            document.getElementById('paper-' + paperId).classList.add('active');

            // Update active state in sidebar
            document.querySelectorAll('.paper-link').forEach(l => l.classList.remove('active'));
            event.target.classList.add('active');

            // Expand the category
            document.querySelectorAll('.cat-group').forEach(g => g.classList.add('expanded'));

            // Scroll to top
            document.querySelector('.content').scrollTop = 0;
        }

        function hidePaper(paperId) {
            document.getElementById('paper-' + paperId).classList.remove('active');
            document.getElementById('welcome-message').style.display = 'block';

            // Update active state
            document.querySelectorAll('.paper-link').forEach(l => l.classList.remove('active'));
        }

        function toggleSection(sectionId) {
            const section = document.querySelector('[data-section="' + sectionId + '"]');
            section.classList.toggle('expanded');

            const icon = section.querySelector('.toggle-icon');
            icon.textContent = section.classList.contains('expanded') ? '−' : '+';
        }

        // Auto-expand first category
        document.addEventListener('DOMContentLoaded', function() {
            const firstCat = document.querySelector('.cat-group');
            if (firstCat) firstCat.classList.add('expanded');
        });
    </script>
</body>
</html>'''

    return html


def main():
    if not INPUT_FILE.exists():
        print(f"错误: 输入文件不存在: {INPUT_FILE}")
        return

    print(f"读取数据: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        papers = data
    elif isinstance(data, dict):
        papers = data.get("papers", [data])
    else:
        print("错误: JSON 格式不正确")
        return

    print(f"共 {len(papers)} 篇论文")

    print(f"生成 HTML 报告: {OUTPUT_HTML}")
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(generate_html_report(papers))

    print(f"生成 Markdown 报告: {OUTPUT_MD}")
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(papers))

    print("完成!")


if __name__ == "__main__":
    main()
