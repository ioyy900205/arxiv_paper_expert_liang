#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
按主题和时间范围抓取 arXiv 论文信息。

  python arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split

依赖：pip install requests feedparser
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests

BASE_URL = "https://export.arxiv.org/api/query"

# 分类关键词默认（config.json 中 keywords 节会覆盖这些）
_DEFAULT_KW = {
    "frontend": {
        "title_core": [
            "speech enhancement", "noise reduction", "echo cancellation",
            "beamforming", "speech separation", "source separation",
            "dereverberation", "dereverb", "voice activity detection",
            "vad", "keyword spotting", "wake word",
            "audio denoising", "speech denoising",
            "speech quality", "audio quality",
            "bandwidth extension", "endpointer",
            "speech front-end", "audio front-end",
        ],
        "title_tools": [
            "mel spectrogram", "mfcc", "feature extraction",
            "filterbank", "fbank", "audio codec", "neural codec",
            "room impulse response", "rir", "hrtf", "head-related",
            "ambisonics", "binaural", "spatial audio",
            "audio-visual segmentation", "wav2vec", "hubert",
            "self-supervised speech", "speech representation",
            "vocal tract", "articulatory inversion",
            "speech segmentation", "phone classification",
            "gesture recognition", "gesture detection",
            "deepfake detection", "singing voice synthesis",
            "video-to-audio", "text-to-audio",
            "industrial fault", "acoustic fault",
            "perceptual quality", "mos score",
            "audio-visual", "audio visual",
        ],
        "summary_core": [
            "speech enhancement", "noise reduction", "echo cancellation",
            "beamforming", "speech separation", "source separation",
            "dereverberation", "dereverb", "voice activity detection",
            "vad", "keyword spotting", "wake word",
            "audio denoising", "speech denoising",
            "speech quality", "audio quality",
            "bandwidth extension", "endpointer",
            "speech front-end", "audio front-end",
        ],
    },
    "backend": {"context": []},
    "audiollm": [],
}

# 全局关键词（main() 中从 config.json 加载后设置）
_KW: dict = _DEFAULT_KW


def _resolve(cfg: dict, key: str, default: Any = None) -> Any:
    for k in key.split("."):
        if isinstance(cfg, dict) and k in cfg:
            cfg = cfg[k]
        else:
            return default
    return cfg


def _hits(text: str, kws: list) -> bool:
    return any(kw in text for kw in kws)


def classify_paper(title: str, summary: str) -> str:
    """三分类: frontend / backend / audiollm（优先级递减）"""
    tl, sl = title.lower(), summary.lower()
    fe, be, al = _KW.get("frontend", {}), _KW.get("backend", {}), _KW.get("audiollm", [])
    fe_tc = fe.get("title_core", _DEFAULT_KW["frontend"]["title_core"])
    fe_tt = fe.get("title_tools", _DEFAULT_KW["frontend"]["title_tools"])
    fe_sc = fe.get("summary_core", _DEFAULT_KW["frontend"]["summary_core"])
    be_ct = be.get("context", [])

    if _hits(tl, al) or _hits(sl, al):
        return "audiollm"
    if _hits(tl, fe_tc):
        return "frontend"
    if _hits(tl, fe_tt):
        return "backend" if _hits(sl, be_ct) else "frontend"
    if _hits(sl, fe_sc):
        return "frontend"
    return "backend"


def _config_path() -> Path:
    return Path(__file__).parent.parent / "config.json"


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch arXiv papers.")
    p.add_argument("--config", type=Path, default=_config_path())
    p.add_argument("--topic")
    p.add_argument("--start-date")
    p.add_argument("--end-date")
    p.add_argument("--days", type=int, help="搜索最近 N 天（覆盖 start-date/end-date）")
    p.add_argument("--max-results", type=int)
    p.add_argument("--page-size", type=int)
    p.add_argument("--output")
    p.add_argument("--format", choices=["json", "csv"], default="json")
    p.add_argument("--split", action="store_true")
    return p.parse_args()


def build_query(topic: str, start: str, end: str) -> str:
    sd = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    ed = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if ed < sd:
        raise ValueError("end-date 不能早于 start-date")
    def fmt(dt, last=False):
        return dt.strftime("%Y%m%d") + ("2359" if last else "0000")
    markers = ["all:", "ti:", "au:", "cat:", "submittedDate:"]
    q = topic if any(m in topic for m in markers) else f'all:"{topic}"'
    return f"({q}) AND submittedDate:[{fmt(sd)} TO {fmt(ed, True)}]"


def fetch(query: str, start: int, size: int, delay: float) -> list:
    params = {"search_query": query, "start": start, "max_results": size,
              "sortBy": "submittedDate", "sortOrder": "descending"}
    url = f"{BASE_URL}?{requests.compat.urlencode(params)}"
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=60,
                              headers={"User-Agent": "arxiv-fetch/1.0"})
            if r.status_code == 429:
                t = float(r.headers.get("Retry-After", delay * 2 ** attempt))
                print(f"  429，等待 {t:.0f}s...")
                time.sleep(t)
                continue
            r.raise_for_status()
            return feedparser.parse(r.text).entries
        except Exception as e:
            if attempt < 4:
                time.sleep(delay * 2 ** attempt)
                continue
            raise


def extract(entry) -> dict:
    authors = ", ".join(a.name for a in getattr(entry, "authors", []))
    cats = ", ".join(t["term"] for t in getattr(entry, "tags", []))
    pdf = next((l.href for l in getattr(entry, "links", [])
                 if l.get("type") == "application/pdf"), "")
    doi = ""
    for ident in getattr(entry, "arxiv_identifiers", []):
        if ident.startswith("doi:"):
            doi = ident[4:]
            break
    if not doi:
        for l in getattr(entry, "links", []):
            if l.get("title") == "doi":
                doi = l.get("href", "").strip()
                break
    def clean(v): return getattr(entry, v, "").replace("\n", " ").strip()
    return {
        "arxiv_id": entry.id.split("/abs/")[-1],
        "title": clean("title"),
        "authors": authors,
        "published": clean("published"),
        "updated": clean("updated"),
        "summary": clean("summary"),
        "primary_category": (getattr(entry, "arxiv_primary_category", {})
                              .get("term", "") if hasattr(entry, "arxiv_primary_category") else ""),
        "categories": cats,
        "entry_id": entry.id,
        "pdf_url": pdf,
        "doi": doi,
        "category": classify_paper(clean("title"), clean("summary")),
    }


def save_json(rows: list, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def save_csv(rows: list, path: Path) -> None:
    if not rows:
        return
    fields = ["arxiv_id", "title", "authors", "published", "updated",
              "primary_category", "categories", "entry_id", "pdf_url", "doi", "category", "summary"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    global _KW
    _KW = cfg.get("keywords", _DEFAULT_KW)

    topic      = args.topic      or _resolve(cfg, "search.topic")
    max_res    = args.max_results or _resolve(cfg, "search.max_results", 100)
    page_size  = args.page_size  or _resolve(cfg, "search.page_size", 100)
    delay      = _resolve(cfg, "request.delay_seconds", 3)
    out_fmt    = args.format
    out_name   = Path(args.output).name if args.output else _resolve(cfg, "output.filename", "arxiv_results.json")
    out_dir    = args.config.parent / "results"
    out_dir.mkdir(exist_ok=True)

    # 处理 --days 参数
    if args.days:
        from datetime import timedelta
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=args.days)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")
        topic = args.topic or _resolve(cfg, "search.topic")
    else:
        start_date = args.start_date or _resolve(cfg, "search.start_date")
        end_date = args.end_date or _resolve(cfg, "search.end_date")
        topic = args.topic or _resolve(cfg, "search.topic")

    if not topic or not start_date or not end_date:
        raise ValueError("缺少 topic 或日期参数，请检查 config.json 或使用命令行参数。")

    query = build_query(topic, start_date, end_date)
    print(f"查询: {query}")

    collected, start = [], 0
    while len(collected) < max_res:
        size = min(page_size, max_res - len(collected))
        entries = fetch(query, start, size, delay)
        if not entries:
            break
        rows = [extract(e) for e in entries]
        collected.extend(rows)
        print(f"  start={start} +{len(rows)} = {len(collected)}")
        if len(entries) < size:
            break
        start += size
        time.sleep(delay)

    if args.split:
        stems = {c: list(filter(lambda r, c=c: r["category"] == c, collected))
                 for c in ("frontend", "backend", "audiollm")}
        stem = Path(out_name).stem
        for cat, rows in stems.items():
            p = out_dir / f"{stem}_{cat}.json"
            (save_json if out_fmt == "json" else save_csv)(rows, p)
            print(f"  {cat}: {len(rows)} -> {p}")
    else:
        p = out_dir / out_name
        (save_json if out_fmt == "json" else save_csv)(collected, p)
        print(f"完成: {len(collected)} 条 -> {p}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        sys.exit(str(e))
