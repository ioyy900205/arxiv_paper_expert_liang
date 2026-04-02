#!/usr/bin/env python3

"""

arxiv 论文分析报告生成器

同时生成浅色主题 HTML 和带目录的 Markdown 格式报告

正文内容默认展开，可折叠

"""



import json
import argparse

from pathlib import Path

from datetime import datetime

from collections import defaultdict



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





def generate_section_html(section_id, title, content, collapsible=True):

    """生成 section HTML"""

    if not collapsible:

        return f'''

        <div class="section-box">

            <div class="section-title-bar">

                <span class="section-name">{title}</span>

            </div>

            <div class="section-body">

                {content}

            </div>

        </div>'''



    return f'''

        <div class="section-box expanded" data-section="{section_id}">

            <div class="section-title-bar" onclick="toggleSection('{section_id}')">

                <span class="section-name">{title}</span>

                <span class="section-toggle">−</span>

            </div>

            <div class="section-body">

                {content}

            </div>

        </div>'''





def generate_paper_html(paper):

    """生成单篇论文的 HTML"""

    aid = paper.get("arxiv_id", "").replace(".", "_")

    title = escape_html(paper.get("title", "Untitled"))

    cat = paper.get("category", "unknown")

    analysis = paper.get("analysis", {})

    colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])

    one_sentence = analysis.get("一句话总结", "")



    html = f'''

        <article class="paper" id="paper-{aid}">

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

                {f'<div class="one-sentence-preview">{escape_html(one_sentence)}</div>' if one_sentence else ''}

            </header>

            <div class="paper-body">

'''



    # ============ 蓝色区域：直接输出内容，无折叠 ============

    def blue_section(title, content):

        return f'''<div class="blue-section">

            <div class="blue-title">{title}</div>

            <div class="blue-content">{content}</div>

        </div>'''



    # 一句话总结（保留在 paper-body 内，作为第一个蓝色区块）

    if one_sentence:

        html += blue_section(

            "一句话总结",

            f'<blockquote class="summary-quote">{escape_html(one_sentence)}</blockquote>'

        )



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

            html += blue_section("研究动机", content)



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

        html += blue_section(f"核心亮点 ({len(highlights)})", content)



    # 反直觉发现

    findings = analysis.get("反直觉发现", [])

    if findings:

        content = '<ul class="findings">'

        for f in findings:

            finding = escape_html(f.get("发现", ""))

            why = escape_html(f.get("为何反直觉", ""))

            content += f'<li><p class="finding">{finding}</p><p class="why">为何反直觉：{why}</p></li>'

        content += '</ul>'

        html += blue_section(f"反直觉发现 ({len(findings)})", content)



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

            html += blue_section("关键技术", content)



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

            html += blue_section("实验结果", content)



    # 局限性

    limitations = analysis.get("局限性/缺陷", [])

    if limitations:

        content = '<ul class="limitations">'

        for lim in limitations:

            if lim:

                content += f'<li>{escape_html(lim)}</li>'

        content += '</ul>'

        html += blue_section(f"局限性/缺陷 ({len(limitations)})", content)



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

            html += blue_section("论文结论", content)



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

            html += blue_section("适用场景", content)



    # 犀利点评

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







def generate_html_report(papers):
    """生成完整的 HTML 报告"""
    categories = defaultdict(list)
    for paper in papers:
        cat = paper.get("category", "unknown")
        categories[cat].append(paper)

    sorted_cats = get_sorted_categories(categories)

    # Static CSS template
    css_template = """
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #212529;
            --text-secondary: #495057;
            --text-muted: #6c757d;
            --divider: #dee2e6;
            --accent: #4263eb;
            --accent-light: #e7eaff;
            --shadow: 0 2px 12px rgba(0,0,0,0.06);
            --radius: 10px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-secondary);
            color: var(--text-primary);
            line-height: 1.75;
            font-size: 15px;
        }

        .container { max-width: 1100px; margin: 0 auto; padding: 2rem; }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: var(--radius);
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }
        .header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.3rem; }
        .header .subtitle { opacity: 0.85; font-size: 0.95rem; }

        .toc {
            background: white;
            border-radius: var(--radius);
            padding: 1.5rem 2rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }
        .toc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .toc-header h2 { font-size: 1.3rem; color: var(--text-primary); }
        .paper-count { background: var(--accent); color: white; padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.85rem; }
        .toc-overview h3, .toc-papers h3 { font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 1rem 0 0.6rem; }

        .category-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .category-tag {
            display: inline-flex; align-items: center; gap: 0.4rem;
            padding: 0.35rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;
            background: color-mix(in srgb, var(--cat-color) 12%, white);
            color: var(--cat-color); border: 1px solid color-mix(in srgb, var(--cat-color) 30%, white);
            text-decoration: none; transition: all 0.2s;
        }
        .category-tag:hover { background: color-mix(in srgb, var(--cat-color) 20%, white); text-decoration: none; }
        .category-tag span { background: var(--cat-color); color: white; padding: 0 0.4rem; border-radius: 10px; font-size: 0.75rem; }

        .paper-nav { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 0.4rem; }
        .nav-item { display: flex; align-items: baseline; gap: 0.5rem; }
        .nav-num { color: var(--accent); font-weight: 600; font-size: 0.85rem; min-width: 1.5rem; }
        .nav-item a { color: var(--text-primary); text-decoration: none; font-size: 0.9rem; }
        .nav-item a:hover { color: var(--accent); text-decoration: underline; }

        .category-section { margin-bottom: 2.5rem; }
        .category-header {
            display: flex; align-items: center; gap: 1rem;
            padding: 0.8rem 1.2rem; border-radius: var(--radius);
            background: white; margin-bottom: 1rem; box-shadow: var(--shadow);
            border-left: 4px solid var(--accent);
        }
        .category-header h2 { font-size: 1.2rem; color: var(--accent); }
        .category-header .count { background: var(--accent-light); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }

        .paper { background: white; border-radius: var(--radius); margin-bottom: 1.5rem; box-shadow: var(--shadow); overflow: hidden; }
        .paper-header {
            padding: 1rem 1.5rem;
            background: var(--cat-bg, var(--bg-secondary));
            border-left: 4px solid var(--cat-border, var(--accent));
            cursor: pointer;
            transition: background 0.2s;
        }
        .paper-header:hover { filter: brightness(0.98); }
        .paper-header-left { display: flex; align-items: flex-start; gap: 0.8rem; }
        .paper-toggle-icon {
            font-size: 1.2rem; font-weight: bold; color: var(--cat-border, var(--accent));
            line-height: 1.3; transition: transform 0.2s;
        }
        .paper.expanded .paper-toggle-icon { transform: rotate(45deg); }
        .paper-title-area { flex: 1; }
        .paper-title { font-size: 1.1rem; font-weight: 600; color: var(--cat-text, var(--text-primary)); margin-bottom: 0.4rem; line-height: 1.4; }
        .paper-meta { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
        .arxiv-id { font-family: monospace; font-size: 0.8rem; color: var(--cat-text, var(--text-muted)); opacity: 0.8; }
        .tag { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: white; color: var(--cat-border, var(--accent)); }

        .one-sentence-preview {
            margin-top: 0.6rem; margin-left: 2rem;
            padding: 0.5rem 0.8rem;
            background: rgba(255,255,255,0.7);
            border-left: 3px solid var(--cat-border, var(--accent));
            font-size: 0.9rem; color: var(--text-secondary); font-style: italic;
            border-radius: 0 6px 6px 0;
        }

        .paper-body { display: none; padding: 0; }
        .paper.expanded .paper-body { display: block; }

        .blue-section {
            border-bottom: 1px solid var(--divider);
            padding: 0.9rem 1.5rem;
        }
        .blue-section:last-child { border-bottom: none; }

        .blue-title {
            font-weight: 600; font-size: 0.95rem; color: var(--accent);
            display: flex; align-items: center; gap: 0.5rem;
            margin-bottom: 0.7rem;
        }
        .blue-title::before { content: ""; display: inline-block; width: 3px; height: 1em; background: var(--accent); border-radius: 2px; }

        .blue-content {
            font-size: 0.9rem; color: var(--text-secondary); line-height: 1.7;
        }
        .blue-content blockquote {
            background: var(--accent-light); border-left: 4px solid var(--accent);
            padding: 0.8rem 1rem; border-radius: 0 6px 6px 0; font-style: italic;
        }
        .blue-content .summary-quote { font-size: 0.95rem; }
        .blue-content .comment-quote { background: #fffbeb; border-left-color: #f59e0b; }
        .blue-content .conclusion { font-weight: 600; color: var(--text-primary); }

        .blue-content ul { padding-left: 0; }
        .blue-content li { margin-bottom: 0; }
        .blue-content .highlights li, .blue-content .findings li {
            background: var(--bg-secondary); padding: 0.8rem; border-radius: 8px;
            margin-bottom: 0.7rem; list-style: none;
        }
        .blue-content .highlights li:last-child, .blue-content .findings li:last-child { margin-bottom: 0; }
        .blue-content .desc { margin-bottom: 0.4rem; }
        .blue-content .quote {
            font-size: 0.9rem; color: var(--text-muted); border-left: 3px solid var(--accent);
            padding-left: 0.8rem; margin-top: 0.5rem;
        }
        .blue-content .finding { font-weight: 600; margin-bottom: 0.3rem; }
        .blue-content .why { font-size: 0.9rem; color: var(--text-muted); margin: 0; }
        .blue-content .limitations { padding-left: 1.2rem; }
        .blue-content .limitations li { background: none; padding: 0.2rem 0; list-style: disc; color: var(--text-secondary); }

        .footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem; }
        .back-to-top {
            position: fixed; bottom: 2rem; right: 2rem; background: var(--accent); color: white;
            width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center;
            justify-content: center; text-decoration: none; box-shadow: 0 2px 8px rgba(66,99,235,0.3);
            font-size: 1.2rem; transition: transform 0.2s, box-shadow 0.2s;
        }
        .back-to-top:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(66,99,235,0.4); color: white; text-decoration: none; }

        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .paper-nav { grid-template-columns: 1fr; }
            .header { padding: 2rem 1.5rem; }
            .header h1 { font-size: 1.5rem; }
        }
    """

    html = '<!DOCTYPE html>\n'
    html += '<html lang="zh-CN">\n'
    html += '<head>\n'
    html += '    <meta charset="UTF-8">\n'
    html += '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '    <title>论文分析报告</title>\n'
    html += '    <style>\n'
    html += css_template
    html += '    </style>\n'
    html += '</head>\n'
    html += '<body>\n'
    html += '    <div class="container">\n'
    html += '        <header class="header">\n'
    html += '            <h1>论文分析报告</h1>\n'
    html += '            <p class="subtitle">由 AI 自动生成 | ' + str(len(papers)) + ' 篇论文 | ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '</p>\n'
    html += '        </header>\n'
    html += '\n'
    html += '        <div class="toc">\n'
    html += '            <div class="toc-header">\n'
    html += '                <h2>目录</h2>\n'
    html += '                <span class="paper-count">' + str(len(papers)) + ' 篇</span>\n'
    html += '            </div>\n'
    html += '            <div class="toc-overview">\n'
    html += '                <h3>按分类</h3>\n'
    html += '                <div class="category-tags">\n'

    for cat in sorted_cats:
        cat_color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        name = CATEGORY_NAMES.get(cat, cat.upper())
        html += '                    <a href="#' + cat + '" class="category-tag" style="--cat-color: ' + cat_color["border"] + '">' + name + '<span>' + str(len(categories[cat])) + '</span></a>\n'

    html += '                </div>\n'
    html += '            </div>\n'
    html += '            <div class="toc-papers">\n'
    html += '                <h3>论文列表</h3>\n'
    html += '                <div class="paper-nav">\n'

    for i, paper in enumerate(papers, 1):
        title = escape_html(paper.get("title", "Untitled")[:55])
        cat = escape_html(paper.get("category", "unknown"))
        aid = escape_html(paper.get("arxiv_id", "").replace(".", "_"))
        html += '                    <div class="nav-item"><span class="nav-num">' + str(i) + '</span><a href="#' + aid + '">' + title + '</a></div>\n'

    html += '                </div>\n'
    html += '            </div>\n'
    html += '        </div>\n'
    html += '\n'

    for cat in sorted_cats:
        cat_papers = categories[cat]
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        name = CATEGORY_NAMES.get(cat, cat.upper())

        html += '\n'
        html += '        <section class="category-section" id="' + cat + '">\n'
        html += '            <header class="category-header" style="--accent: ' + colors['border'] + '">\n'
        html += '                <h2>' + name + '</h2>\n'
        html += '                <span class="count">' + str(len(cat_papers)) + ' 篇</span>\n'
        html += '            </header>\n'

        for paper in cat_papers:
            html += generate_paper_html(paper) + "\n"
        html += '        </section>\n'

    html += '\n'
    html += '        <footer class="footer">\n'
    html += '            <p>报告生成完成</p>\n'
    html += '        </footer>\n'
    html += '    </div>\n'
    html += '    <a href="#" class="back-to-top" title="回到顶部">↑</a>\n'
    html += '\n'
    html += '    <script>\n'
    html += '        function togglePaper(paperId) {\n'
    html += '            const paper = document.getElementById(\'paper-\' + paperId);\n'
    html += '            paper.classList.toggle(\'expanded\');\n'
    html += '        }\n'
    html += '    </script>\n'
    html += '</body>\n'
    html += '</html>'

    return html


def main():
    parser = argparse.ArgumentParser(description="生成 arXiv 论文分析报告")
    parser.add_argument("input", nargs="?", default="results/arxiv_results_content_analysis.json",
                        help="输入的 analysis JSON 文件（默认: results/arxiv_results_content_analysis.json）")
    parser.add_argument("-o", "--output-dir", default="results",
                        help="输出目录（默认: results）")
    args = parser.parse_args()

    input_file = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        return

    # 确定输出文件名
    if input_file.stem.endswith("_analysis"):
        output_name = input_file.stem[:-len("_analysis")] + "_report"
    elif input_file.stem.startswith("analysis"):
        output_name = input_file.stem.replace("analysis", "report", 1)
    else:
        output_name = input_file.stem + "_report"

    output_html = output_dir / f"{output_name}.html"
    output_md = output_dir / f"{output_name}.md"

    print(f"读取数据: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        papers = data
    elif isinstance(data, dict):
        papers = data.get("papers", [data])
    else:
        print("错误: JSON 格式不正确")
        return

    print(f"共 {len(papers)} 篇论文")

    print(f"生成 HTML 报告: {output_html}")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(generate_html_report(papers))

    print(f"生成 Markdown 报告: {output_md}")
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(papers))

    print("完成!")


if __name__ == "__main__":
    main()
