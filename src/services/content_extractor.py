"""arXiv 论文全文抓取服务（HTML 优先，PDF 回退）"""
from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

from src.logger import setup_logger
from src.utils import load_json, save_json

BASE_HTML = "https://arxiv.org/html/{id}"
BASE_PDF = "https://arxiv.org/pdf/{id}.pdf"
BASE_ABSTRACT = "https://arxiv.org/abs/{id}"
HEADERS = {"User-Agent": "arxiv-fetch/1.0"}

logger = setup_logger()


def find_available_version(arxiv_id: str, delay: float = 1.0) -> Optional[str]:
    """尝试找到可用的论文版本。"""
    import re as _re
    base_id = _re.sub(r"v\d+$", "", arxiv_id)

    url = BASE_ABSTRACT.format(id=arxiv_id)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            versions = _re.findall(r'href="/html/(' + _re.escape(base_id) + r'v\d+)"', r.text)
            if versions:
                return versions[0]
    except Exception:
        pass

    for v in ("", "v2", "v3", "v4", "v5"):
        test_id = base_id + ("v1" if not v and not arxiv_id.endswith("v1") else v)
        if test_id == arxiv_id:
            continue
        try:
            r = requests.get(BASE_HTML.format(id=test_id), headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return test_id
        except Exception:
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
                logger.warning(f"429 rate limit, sleeping {t:.0f}s")
                time.sleep(t)
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt < 3:
                time.sleep(delay * 2 ** attempt)
                continue
            logger.warning(f"fetch_html {arxiv_id} failed: {e}")
            return None


def fetch_pdf_bytes(arxiv_id: str, delay: float = 3.0) -> Optional[bytes]:
    url = BASE_PDF.format(id=arxiv_id)
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                t = float(r.headers.get("Retry-After", delay * 2 ** attempt * 2))
                logger.warning(f"429 rate limit, sleeping {t:.0f}s")
                time.sleep(t)
                continue
            r.raise_for_status()
            return r.content
        except Exception as e:
            if attempt < 3:
                time.sleep(delay * 2 ** attempt)
                continue
            logger.warning(f"fetch_pdf_bytes {arxiv_id} failed: {e}")
            return None


def parse_pdf(raw_bytes: bytes) -> Optional[str]:
    try:
        text = extract_text(io.BytesIO(raw_bytes)).strip()
        return text if text else None
    except Exception as e:
        logger.warning(f"parse_pdf failed: {e}")
        return None


def strip_references(text: str) -> str:
    """去掉正文末尾的参考文献节。"""
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
    return text.rstrip()


def parse_html(raw: str, arxiv_id: str) -> Optional[str]:
    soup = BeautifulSoup(raw, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "head"]):
        tag.decompose()

    main = (
        soup.find("div", class_="ltx_pagecontent")
        or soup.find("div", role="main")
        or soup.body
    )
    if not main:
        return None

    for ref_sec in main.find_all(["section", "div"], id=re.compile(r"^bib", re.I)):
        ref_sec.decompose()
    for ref_h in main.find_all(["h1", "h2", "h3", "h4", "p"],
                                string=re.compile(r"^(reference|bibliography|acknowledgments?)", re.I)):
        for sibling in ref_h.find_next_siblings():
            sibling.decompose()
        ref_h.decompose()

    lines = []
    for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "dd", "blockquote"]):
        text = elem.get_text(separator="\n", strip=True)
        if text:
            lines.append(text)

    return "\n\n".join(lines)


def fetch_content(
    input_path: str | Path = "results/arxiv_results.json",
    limit: Optional[int] = 3,
    delay: float = 3.0,
) -> list:
    """
    抓取论文全文，写入 results/arxiv_results_content.json。
    HTML 不可用时自动回退到 PDF，PDF 不可用时尝试其他版本。
    """
    papers = load_json(input_path)
    if not papers:
        raise FileNotFoundError(f"{input_path} 不存在或为空")

    results_dir = Path(input_path).parent
    output_path = results_dir / "arxiv_results_content.json"

    if limit:
        papers = papers[:limit]

    results = []
    for i, paper in enumerate(papers):
        arxiv_id = paper["arxiv_id"]
        print(f"[{i + 1}/{len(papers)}] {arxiv_id} ...", end=" ", flush=True)

        content = None
        html_url = None
        source = "none"
        used_arxiv_id = arxiv_id

        raw_html = fetch_html(arxiv_id, delay)
        if raw_html is not None:
            content = parse_html(raw_html, arxiv_id)
            html_url = BASE_HTML.format(id=arxiv_id)
            source = "html"
            if content:
                print(f"HTML OK ({len(content):,} chars)")
            else:
                print("HTML 解析失败，尝试 PDF ...")

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

        if content is None:
            print("尝试其他版本 ...")
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

        entry = {
            **paper,
            "used_arxiv_id": used_arxiv_id,
            "html_url": html_url,
            "content": content,
            "content_source": source,
        }
        results.append(entry)
        if i < len(papers) - 1:
            time.sleep(delay)

    save_json(results, output_path)
    logger.info(f"已保存 {len(results)} 条到 {output_path}")
    return results
