#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
抓取 arXiv 论文全文，提取为纯文本字符串，追加到 JSON 每条记录的 content 字段。

  python scripts/arxiv_content.py                           # 默认处理 results/arxiv_results.json 前 3 条
  python scripts/arxiv_content.py results/arxiv_results.json -n 10 -o results/content.json
  python scripts/arxiv_content.py results/arxiv_results.json --full        # 全量处理

优先级：HTML 版本 > PDF 版本（HTML 不存在时自动回退；输出 JSON 中 content_source 标记来源）

依赖：pip install requests beautifulsoup4 pdfminer.six
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

BASE_HTML = "https://arxiv.org/html/{id}"
BASE_PDF = "https://arxiv.org/pdf/{id}.pdf"
BASE_ABSTRACT = "https://arxiv.org/abs/{id}"
HEADERS = {"User-Agent": "arxiv-fetch/1.0"}


def find_available_version(arxiv_id: str, delay: float = 1.0) -> Optional[str]:
    """尝试找到可用的论文版本。如果当前版本不可用，尝试其他版本。"""
    import re
    base_id = re.sub(r'v\d+$', '', arxiv_id)
    
    # 获取所有可用版本
    url = BASE_ABSTRACT.format(id=arxiv_id)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            # 从页面中提取所有版本链接
            versions = re.findall(r'href="/html/(' + re.escape(base_id) + r'v\d+)"', r.text)
            if versions:
                return versions[0]  # 返回最新版本
    except:
        pass
    
    # 如果页面解析失败，尝试常见的版本
    for v in ['', 'v2', 'v3', 'v4', 'v5']:
        test_id = base_id + ('v1' if not v and not arxiv_id.endswith('v1') else v)
        if test_id == arxiv_id:
            continue
        try:
            r = requests.get(BASE_HTML.format(id=test_id), headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return test_id
        except:
            continue
    
    return None


def fetch_html(arxiv_id: str, delay: float = 3.0) -> Optional[str]:
    url = BASE_HTML.format(id=arxiv_id)
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=90)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                t = float(r.headers.get("Retry-After", delay * 2 ** attempt * 2))
                print(f"  429，等待 {t:.0f}s...")
                time.sleep(t)
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt < 3:
                time.sleep(delay * 2 ** attempt)
                continue
            print(f"  获取失败: {e}")
            return None


def fetch_pdf_bytes(arxiv_id: str, delay: float = 3.0) -> Optional[bytes]:
    """下载 PDF 原始字节流，用于后续解析。"""
    url = BASE_PDF.format(id=arxiv_id)
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                t = float(r.headers.get("Retry-After", delay * 2 ** attempt * 2))
                print(f"  429，等待 {t:.0f}s...")
                time.sleep(t)
                continue
            r.raise_for_status()
            return r.content
        except Exception as e:
            if attempt < 3:
                time.sleep(delay * 2 ** attempt)
                continue
            print(f"  PDF 下载失败: {e}")
            return None


def parse_pdf(raw_bytes: bytes) -> Optional[str]:
    """从 PDF 字节流中提取纯文本。"""
    try:
        text = extract_text(io.BytesIO(raw_bytes))
        text = text.strip()
        return text if text else None
    except Exception as e:
        print(f"  PDF 解析失败: {e}")
        return None


def strip_references(text: str) -> str:
    """去掉正文末尾的参考文献节（按关键词检测）。"""
    patterns = [
        r"\n\s*References?\s*\n",
        r"\n\s*Bibliography\s*\n",
        r"\n\s*References\s*$",
        r"\n\s*Acknowledgment",
    ]
    earliest = len(text)
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m and m.start() < earliest:
            earliest = m.start()
    if earliest < len(text):
        text = text[:earliest]
    # 清理末尾多余的空行
    text = text.rstrip()
    return text


def parse_html(raw: str, arxiv_id: str) -> Optional[str]:
    soup = BeautifulSoup(raw, "html.parser")

    # 移除无关标签（保留 <p> <h1-4> <li> <dd> <blockquote> 等正文结构）
    for tag in soup.find_all(["script", "style", "nav", "footer", "head"]):
        tag.decompose()

    # 找全文主体（<div class="ltx_pagecontent"> 或 <div role="main">）
    main = (
        soup.find("div", class_="ltx_pagecontent")
        or soup.find("div", role="main")
        or soup.body
    )
    if not main:
        return None

    # 移除参考文献节（通常 id 含 "bib" 或标题含 reference）
    for ref_sec in main.find_all(
        ["section", "div"],
        id=re.compile(r"^bib", re.I)
    ):
        ref_sec.decompose()
    for ref_h in main.find_all(
        ["h1", "h2", "h3", "h4", "p"],
        string=re.compile(r"^(reference|bibliography|acknowledgments?)", re.I)
    ):
        # 先收集所有后续兄弟元素，避免 decompose 后找不到
        for sibling in ref_h.find_next_siblings():
            sibling.decompose()
        # 再删除参考文献标题本身
        ref_h.decompose()

    # 提取纯文本，保留换行结构
    lines = []
    for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "dd", "blockquote"]):
        text = elem.get_text(separator="\n", strip=True)
        if text:
            lines.append(text)

    return "\n\n".join(lines)


def run(input_path: Path,
        output_path: Optional[Path] = None,
        limit: int | None = None,
        delay: float = 3.0) -> None:
    papers = json.loads(input_path.read_text(encoding="utf-8"))
    if limit:
        papers = papers[:limit]

    results = []
    for i, paper in enumerate(papers):
        arxiv_id = paper["arxiv_id"]
        print(f"[{i+1}/{len(papers)}] {arxiv_id} ...", end=" ", flush=True)

        content = None
        html_url = None
        source = "none"
        used_arxiv_id = arxiv_id  # 记录实际使用的版本

        raw_html = fetch_html(arxiv_id, delay)
        if raw_html is not None:
            content = parse_html(raw_html, arxiv_id)
            html_url = BASE_HTML.format(id=arxiv_id)
            source = "html"
            if content:
                print(f"HTML OK ({len(content):,} chars)")
            else:
                print("HTML 解析失败，尝试 PDF ...")

        # HTML 不可用或解析失败 → 回退到 PDF
        if content is None:
            pdf_bytes = fetch_pdf_bytes(arxiv_id, delay)
            if pdf_bytes is not None:
                content = parse_pdf(pdf_bytes)
                if content:
                    content = strip_references(content)
                    html_url = BASE_PDF.format(id=arxiv_id)
                    source = "pdf"
                    print(f"PDF OK ({len(content):,} chars)")
                else:
                    print("PDF 解析失败")

        # HTML 和 PDF 都失败 → 尝试其他版本
        if content is None:
            print("尝试其他版本...")
            alt_version = find_available_version(arxiv_id, delay)
            if alt_version:
                print(f"  找到可用版本: {alt_version}")
                used_arxiv_id = alt_version
                raw_html = fetch_html(alt_version, delay)
                if raw_html is not None:
                    content = parse_html(raw_html, alt_version)
                    html_url = BASE_HTML.format(id=alt_version)
                    source = "html"
                if content is None:
                    pdf_bytes = fetch_pdf_bytes(alt_version, delay)
                    if pdf_bytes is not None:
                        content = parse_pdf(pdf_bytes)
                        if content:
                            content = strip_references(content)
                            html_url = BASE_PDF.format(id=alt_version)
                            source = "pdf"
                if content:
                    print(f"  {source.upper()} OK ({len(content):,} chars)")
                else:
                    print("  所有版本均失败")

        if content is None:
            print("HTML / PDF 均不可用")

        # 更新 paper 记录，使用实际获取的版本 ID
        paper_copy = {**paper, "used_arxiv_id": used_arxiv_id}
        entry = {**paper_copy, "html_url": html_url, "content": content, "content_source": source}
        results.append(entry)
        if i < len(papers) - 1:
            time.sleep(delay)

    out_path = output_path if output_path else input_path.parent / f"{input_path.stem}_content.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存: {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="抓取 arXiv 论文全文（HTML 优先，PDF 回退），输出 JSON（每条含 content 字段）")
    p.add_argument("input", nargs="?", default="results/arxiv_results.json")
    p.add_argument("-o", "--output")
    p.add_argument("-n", "--limit", type=int, default=3)
    p.add_argument("--full", action="store_true", help="处理全部记录（忽略 -n）")
    p.add_argument("--delay", type=float, default=3.0)
    args = p.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.input).parent / f"{Path(args.input).stem}_content.json" if not args.output else Path(args.output),
        limit=None if args.full else args.limit,
        delay=args.delay,
    )
