#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
按主题和时间范围抓取 arXiv 论文信息。

支持两种运行方式：
1. 命令行参数（覆盖配置文件）：
   python arxiv_fetch.py --topic "diffusion model" --start-date "2026-01-01" --end-date "2026-03-31"

2. 配置文件（默认 config.json，与脚本同目录）：
   python arxiv_fetch.py

配置示例见 config.json，可自行修改 topic、日期范围等参数。

依赖：
pip install requests feedparser
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser
import requests

BASE_URL = "https://export.arxiv.org/api/query"

FRONTEND_KEYWORDS = [
    "speech enhancement", "noise reduction", "acoustic echo cancellation",
    "echo cancellation", "beamforming", "microphone array", "speech separation",
    "source separation", "dereverberation", "voice activity detection",
    "vad", "audio preprocessing", "feature extraction", "mel spectrogram",
    "mfcc", "asr front-end", "wake word", "keyword spotting", "bandwidth extension",
    "audio codec", "neural codec", "speech front-end", "audio front-end",
    "speech quality enhancement", "speech denoising", "denoising", "audio denoising",
    "speech dereverb", "room reverb", "acoustic beamforming", "speech beamforming",
    "endpointer", "voice purification", "speech representation",
    "room impulse response", "rir", "hrtf", "head-related",
    "ambisonics", "binaural", "spatial audio", "audio-visual segmentation",
    "audio deepfake detection", "deepfake detection",
    "filterbank", "fbank",
    "audio quality assessment", "mos score", "perceptual quality",
    "audio ssl", "self-supervised speech", "wav2vec", "hubert",
    "audio retrieval", "audio tagging", "sound event detection",
    "singing voice synthesis", "speech quality",
    "text-to-audio synthesis", "video-to-audio",
    "acoustic fault detection", "industrial fault",
    "speech segmentation", "phone classification",
    "gesture recognition", "gesture detection",
]

BACKEND_KEYWORDS = [
    "asr", "speech recognition", "speech synthesis",
    "tts", "text-to-speech", "voice conversion", "speaker verification",
    "speaker diarization", "emotion recognition", "prosody", "spoken language",
    "speech-to-text", "dialogue system", "speech emotion", "speaker embedding",
    "pitch tracking", "speech coding", "audio coding",
    "phonetic", "phoneme", "pronunciation", "stutter",
    "speech assessment", "pronunciation scoring", "language proficiency",
    "speech representation learning", "speech ssl",
    "groove", "music perception", "music generation",
    "dysarthric speech", "pathological speech", "clinical speech",
    "cough detection", "bowel sound",
    "articulatory", "vocal tract",
    "speech corpus", "speech dataset", "speech annotation",
    "speaker recognition", "voice cloning",
    "aphasic speech", "speech impairment",
    "rhythm", "rhythmic",
    "self-supervised speech model", "ssl model",
    "wav2vec", "hubert", "speech pretrained model",
    "language acquisition", "infant speech", "early language",
    "simultaneous speech-to-speech", "s2s translation",
]

AUDIOLLM_KEYWORDS = [
    # 明确的大型语言模型
    "large language model", "llm", "gpt-", "chatgpt",
    "multimodal llm", "audio language model",
    # 明确的音频 LLM 架构/任务
    "speech llm", "audio llm", "speech token", "semantic token",
    "speechlm", "audiogpt", "salmonn", "qwen-audio",
    # 明确的 LLM 训练/推理技术
    "rlhf", "dpo", "instruction tuning", "fine-tuning llm",
    "chain-of-thought", "cot reasoning", "reasoning chain",
    # 语音相关的 LLM 应用
    "llm-based asr", "llm for speech", "llm for audio",
    "llm-based tts", "llm-based speaker",
    # VLM / 视觉-语言模型（涉及音频时）
    "gpt-4o", "gpt-4-turbo", "claude", "gemini",
]


def _kw_hits(text: str, keywords: list) -> bool:
    for kw in keywords:
        if kw in text:
            return True
    return False


def classify_paper(title: str, summary: str) -> str:
    """
    三分类: frontend / backend / audiollm

    规则（优先级递减）：
      1. 标题或摘要含 audiollm 关键词 → audiollm
      2. 标题含 frontend 关键词（核心任务词：enhancement/separation/beamforming/dereverb）→ frontend
      3. 摘要含 frontend 核心任务词（且不在 backend 核心任务上下文中）→ frontend
      4. 其余 → backend
    """
    title_lower = title.lower()
    summary_lower = summary.lower()

    # 1. AudioLLM 优先
    if _kw_hits(title_lower, AUDIOLLM_KEYWORDS):
        return "audiollm"
    if _kw_hits(summary_lower, AUDIOLLM_KEYWORDS):
        return "audiollm"

    # 2. 标题含前端核心词 → 前端（无视摘要中的后端词）
    FE_TITLE_CORE = [
        "speech enhancement", "noise reduction", "echo cancellation",
        "beamforming", "speech separation", "source separation",
        "dereverberation", "dereverb", "voice activity detection",
        "vad", "keyword spotting", "wake word",
        "audio denoising", "speech denoising",
        "speech quality", "audio quality",
        "bandwidth extension", "endpointer",
        "speech front-end", "audio front-end",
    ]
    if _kw_hits(title_lower, FE_TITLE_CORE):
        return "frontend"

    # 3. 标题含前端工具词 → 看摘要是否在 backend 上下文中
    FE_TITLE_TOOLS = [
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
    ]
    if _kw_hits(title_lower, FE_TITLE_TOOLS):
        # 若摘要主要在讨论 backend 任务（asr/synthesis/emotion等），则归 backend
        BE_CONTEXT = [
            "speech recognition", "speech synthesis", "tts",
            "text-to-speech", "voice conversion",
            "speaker verification", "speaker diarization",
            "emotion recognition", "speech emotion",
            "phoneme", "phonetic", "pronunciation", "stutter",
            "dysarthric speech", "speech impairment", "clinical speech",
            "language acquisition", "infant speech",
            "simultaneous speech-to-speech",
        ]
        if _kw_hits(summary_lower, BE_CONTEXT):
            return "backend"
        return "frontend"

    # 4. 摘要含前端词（不考虑工具词）
    if _kw_hits(summary_lower, FE_TITLE_CORE):
        return "frontend"

    return "backend"
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")


def find_config() -> Path:
    """优先使用 --config 指定路径，否则依次查找：./config.json、../config.json（相对于脚本目录）"""
    return Path(DEFAULT_CONFIG)


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def parse_args(args: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch arXiv papers by topic and date range.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=find_config(),
        help="配置文件路径（默认：脚本目录的 ../config.json）",
    )
    parser.add_argument(
        "--topic",
        help='主题或 arXiv 查询表达式，例如 "diffusion model" 或 \'cat:cs.CL AND all:"llm"\'',
    )
    parser.add_argument(
        "--start-date",
        help='起始日期，格式 YYYY-MM-DD，例如 "2026-01-01"',
    )
    parser.add_argument(
        "--end-date",
        help='结束日期，格式 YYYY-MM-DD，例如 "2026-03-31"',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        help="最多抓取多少篇论文",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        help="每次请求多少条，建议不要太大",
    )
    parser.add_argument(
        "--output",
        help="输出文件名（不含路径，文件将保存到 results/ 目录下）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="输出格式，默认 json",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="是否将结果按前后端分成两个文件输出（frontend + backend）",
    )
    return parser.parse_args(args)


def resolve_output_dir(config_path: Path) -> Path:
    output_dir = config_path.parent / "results"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def resolve_config_value(key_path: str, config: Dict[str, Any], default: Any = None) -> Any:
    keys = key_path.split(".")
    val = config
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def validate_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"日期格式错误: {date_str}，应为 YYYY-MM-DD") from exc


def to_arxiv_submitted_date(dt: datetime, end_of_day: bool = False) -> str:
    if end_of_day:
        dt = dt.replace(hour=23, minute=59)
    else:
        dt = dt.replace(hour=0, minute=0)
    return dt.strftime("%Y%m%d%H%M")


def build_search_query(topic: str, start_date: str, end_date: str) -> str:
    start_dt = validate_date(start_date)
    end_dt = validate_date(end_date)

    if end_dt < start_dt:
        raise ValueError("end-date 不能早于 start-date")

    start_token = to_arxiv_submitted_date(start_dt, end_of_day=False)
    end_token = to_arxiv_submitted_date(end_dt, end_of_day=True)

    advanced_markers = ["all:", "ti:", "au:", "abs:", "cat:", "jr:", "co:", "rn:", "submittedDate:"]
    if any(marker in topic for marker in advanced_markers):
        topic_query = topic
    else:
        topic_query = f'all:"{topic}"'

    date_query = f"submittedDate:[{start_token} TO {end_token}]"
    return f"({topic_query}) AND {date_query}"


def fetch_page(
    search_query: str,
    start: int,
    page_size: int,
    base_delay: float = 3.0,
    max_retries: int = 5,
) -> feedparser.FeedParserDict:
    from urllib.parse import urlencode
    params = {
        "search_query": search_query,
        "start": start,
        "max_results": page_size,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    headers = {
        "User-Agent": "arxiv-topic-fetcher/1.0 (Python requests; contact: local-script)"
    }

    last_resp: Optional["requests.Response"] = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            last_resp = resp
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", base_delay * (2 ** attempt)))
                print(f"  ⚠️  429 请求受限，等待 {retry_after:.0f}s 后重试（第 {attempt + 1}/{max_retries} 次）...")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return feedparser.parse(resp.text)
        except requests.exceptions.RequestException as exc:
            if attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                print(f"  ⚠️  网络错误: {exc}，{wait:.0f}s 后重试（第 {attempt + 1}/{max_retries} 次）...")
                time.sleep(wait)
                continue
            raise

    # 所有重试均失败，最后一个响应转为异常
    if last_resp is not None:
        last_resp.raise_for_status()


def extract_entry(entry: Any) -> Dict[str, Any]:
    authors = ", ".join(author.name for author in getattr(entry, "authors", []))
    categories = ", ".join(tag["term"] for tag in getattr(entry, "tags", [])) if hasattr(entry, "tags") else ""

    pdf_url = ""
    for link in getattr(entry, "links", []):
        if getattr(link, "type", "") == "application/pdf":
            pdf_url = link.href
            break

    arxiv_id = entry.id.split("/abs/")[-1] if hasattr(entry, "id") else ""

    doi = ""
    for identifier in getattr(entry, "arxiv_identifiers", []):
        if identifier.startswith("doi:"):
            doi = identifier[4:]
            break
    if not doi:
        for link in getattr(entry, "links", []):
            if getattr(link, "title", "") == "doi":
                doi = getattr(link, "href", "").strip()
                break

    category = classify_paper(
        getattr(entry, "title", "").replace("\n", " ").strip(),
        getattr(entry, "summary", "").replace("\n", " ").strip(),
    )

    return {
        "arxiv_id": arxiv_id,
        "title": getattr(entry, "title", "").replace("\n", " ").strip(),
        "authors": authors,
        "published": getattr(entry, "published", ""),
        "updated": getattr(entry, "updated", ""),
        "summary": getattr(entry, "summary", "").replace("\n", " ").strip(),
        "primary_category": (
            getattr(entry, "arxiv_primary_category", {}).get("term", "")
            if hasattr(entry, "arxiv_primary_category")
            else ""
        ),
        "categories": categories,
        "entry_id": getattr(entry, "id", ""),
        "pdf_url": pdf_url,
        "doi": doi,
        "category": category,
    }


def save_to_json(rows: List[Dict[str, Any]], output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def save_to_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    if not rows:
        print("没有结果可写入。")
        return
    fieldnames = [
        "arxiv_id", "title", "authors", "published", "updated",
        "primary_category", "categories", "entry_id", "pdf_url", "doi", "category",
        "summary",
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    # 加载配置文件
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        # 没有配置文件时使用空配置，仅依赖命令行参数
        config = {}

    # 命令行参数覆盖配置文件
    topic = args.topic or resolve_config_value("search.topic", config)
    start_date = args.start_date or resolve_config_value("search.start_date", config)
    end_date = args.end_date or resolve_config_value("search.end_date", config)
    max_results = args.max_results or resolve_config_value("search.max_results", config, 100)
    page_size = args.page_size or resolve_config_value("search.page_size", config, 100)
    output_format = args.format
    output_filename = args.output or resolve_config_value("output.filename", config, "arxiv_results.json")

    if not topic:
        raise ValueError("未指定搜索主题。请在配置文件 config.json 的 search.topic 中设置，或使用 --topic 参数。")
    if not start_date or not end_date:
        raise ValueError("未指定日期范围。请在配置文件中设置 start_date / end_date，或使用 --start-date / --end-date 参数。")

    delay_seconds = resolve_config_value("request.delay_seconds", config, 3)

    output_dir = resolve_output_dir(args.config)
    output_filename = args.output or resolve_config_value("output.filename", config, "arxiv_results.json")

    search_query = build_search_query(topic, start_date, end_date)
    print(f"配置文件: {args.config}")
    print(f"使用的 arXiv 查询：")
    print(search_query)
    print("-" * 80)

    collected: List[Dict[str, Any]] = []
    start = 0

    while len(collected) < max_results:
        remaining = max_results - len(collected)
        current_page_size = min(page_size, remaining)

        print(f"正在抓取 start={start}, page_size={current_page_size} ...")
        feed = fetch_page(search_query, start, current_page_size, base_delay=delay_seconds)

        entries = getattr(feed, "entries", [])
        if not entries:
            print("没有更多结果。")
            break

        page_rows = [extract_entry(entry) for entry in entries]
        collected.extend(page_rows)

        print(f"本页抓取 {len(page_rows)} 条，累计 {len(collected)} 条。")

        if len(entries) < current_page_size:
            print("结果已经抓完。")
            break

        start += current_page_size
        time.sleep(delay_seconds)

    # --split 模式下按 category 分流输出
    if args.split:
        frontend_rows = [r for r in collected if r.get("category") == "frontend"]
        backend_rows  = [r for r in collected if r.get("category") == "backend"]
        audiollm_rows = [r for r in collected if r.get("category") == "audiollm"]

        stem = Path(output_filename).stem
        paths = {
            "frontend":  output_dir / f"{stem}_frontend.json",
            "backend":   output_dir / f"{stem}_backend.json",
            "audiollm":  output_dir / f"{stem}_audiollm.json",
        }

        for cat, rows in [("frontend", frontend_rows), ("backend", backend_rows), ("audiollm", audiollm_rows)]:
            if output_format == "json":
                save_to_json(rows, paths[cat])
            else:
                save_to_csv(rows, paths[cat])

        print(f"\n前端论文 {len(frontend_rows)} 条  -> {paths['frontend']}")
        print(f"后端论文 {len(backend_rows)} 条   -> {paths['backend']}")
        print(f"AudioLLM  {len(audiollm_rows)} 条  -> {paths['audiollm']}")
    else:
        output_path = output_dir / output_filename
        if output_format == "json":
            save_to_json(collected, output_path)
        else:
            save_to_csv(collected, output_path)
        print(f"\n完成，共保存 {len(collected)} 条到: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
