"""arXiv 论文搜索服务"""
from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests

from src.config import load_config, resolve
from src.logger import setup_logger
from src.utils import save_json

BASE_URL = "https://export.arxiv.org/api/query"

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

_KW: dict = _DEFAULT_KW
logger = setup_logger()


def _hits(text: str, kws: list) -> bool:
    return any(kw in text for kw in kws)


def classify_paper(title: str, summary: str) -> str:
    """五分类: audiollm / quant / frontend / backend / other（优先级递减）"""
    tl, sl = title.lower(), summary.lower()
    fe = _KW.get("frontend", {})
    be = _KW.get("backend", {})
    al = _KW.get("audiollm", [])
    qu = _KW.get("quant", {})

    fe_tc = fe.get("title_core", _DEFAULT_KW["frontend"]["title_core"])
    fe_tt = fe.get("title_tools", _DEFAULT_KW["frontend"]["title_tools"])
    fe_sc = fe.get("summary_core", _DEFAULT_KW["frontend"]["summary_core"])
    be_ct = be.get("context", [])

    # 1. audiollm 最高优先级
    if _hits(tl, al) or _hits(sl, al):
        return "audiollm"

    # 2. quant
    qu_tc = qu.get("title_core", [])
    qu_ta = qu.get("title_ai", [])
    qu_sc = qu.get("summary_core", [])
    if _hits(tl, qu_tc) or _hits(tl, qu_ta) or _hits(sl, qu_sc):
        return "quant"

    # 3. frontend
    if _hits(tl, fe_tc):
        return "frontend"
    if _hits(tl, fe_tt):
        return "backend" if _hits(sl, be_ct) else "frontend"
    if _hits(sl, fe_sc):
        return "frontend"

    # 4. 其他
    return "other"


_DOMAIN_TOPICS = {
    "speech": "(cat:eess.AS OR cat:eess.SP OR cat:cs.SD) AND (all:\"speech\" OR all:\"audio\" OR all:\"voice\" OR all:\"TTS\" OR all:\"ASR\" OR all:\"speech enhancement\" OR all:\"speech separation\" OR all:\"speech recognition\" OR all:\"speech synthesis\" OR all:\"speaker verification\" OR all:\"speaker diarization\" OR all:\"text-to-speech\" OR all:\"voice conversion\" OR all:\"speech generation\" OR all:\"audio deepfake\" OR all:\"speech LLM\" OR all:\"audio language model\")",
    "quant": "(cat:q-fin.CP OR cat:q-fin.GN OR cat:q-fin.PM OR cat:q-fin.RM OR cat:q-fin.ST OR cat:q-fin.TR) AND (all:\"quantitative\" OR all:\"algorithmic\" OR all:\"portfolio\" OR all:\"risk\" OR all:\"trading\" OR all:\"finance\" OR all:\"market\" OR all:\"stock\" OR all:\"volatility\" OR all:\"option\")",
}


def _resolve_topic(cfg: dict, domain: str, explicit_query: Optional[str]) -> str:
    """根据 domain 配置解析出实际搜索 query。优先级：explicit_query > config.topic > domain 模板。"""
    if explicit_query is not None:
        return explicit_query

    topic_cfg = resolve(cfg, "search.topic")
    if isinstance(topic_cfg, dict):
        domains = [d.strip() for d in domain.split(",")]
        parts = []
        for d in domains:
            t = _DOMAIN_TOPICS.get(d)
            if not t:
                raise ValueError(f"未知的 domain: {d}，支持的值为: speech, quant, both")
            parts.append(f"({t})")
        return " OR ".join(parts) if len(parts) > 1 else parts[0]

    # 向后兼容：config.topic 为字符串
    return topic_cfg or _DOMAIN_TOPICS.get(domain.split(",")[0].strip(), _DOMAIN_TOPICS["speech"])


def build_query(topic: str, start: str, end: str) -> str:
    """构建带日期范围的 arXiv 查询语句。"""
    sd = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    ed = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if ed < sd:
        raise ValueError("end_date 不能早于 start_date")

    def fmt(dt, last: bool = False) -> str:
        return dt.strftime("%Y%m%d") + ("2359" if last else "0000")

    markers = ["all:", "ti:", "au:", "cat:", "submittedDate:"]
    q = topic if any(m in topic for m in markers) else f'all:"{topic}"'
    return f"({q}) AND submittedDate:[{fmt(sd)} TO {fmt(ed, True)}]"


def fetch(query: str, start: int, size: int, delay: float) -> list:
    """向 arXiv API 发请求，返回 entry 列表。"""
    params = {
        "search_query": query,
        "start": start,
        "max_results": size,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{BASE_URL}?{requests.compat.urlencode(params)}"
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "arxiv-fetch/1.0"})
            if r.status_code == 429:
                t = float(r.headers.get("Retry-After", delay * 2 ** attempt))
                logger.warning(f"429 rate limit, sleeping {t:.0f}s")
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
    """从单个 entry 提取结构化字段。"""
    authors = ", ".join(a.name for a in getattr(entry, "authors", []))
    cats = ", ".join(t["term"] for t in getattr(entry, "tags", []))
    pdf = next(
        (l.href for l in getattr(entry, "links", []) if l.get("type") == "application/pdf"),
        "",
    )
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

    def clean(v: str) -> str:
        return getattr(entry, v, "").replace("\n", " ").strip()

    return {
        "arxiv_id": entry.id.split("/abs/")[-1],
        "title": clean("title"),
        "authors": authors,
        "published": clean("published"),
        "updated": clean("updated"),
        "summary": clean("summary"),
        "primary_category": (
            getattr(entry, "arxiv_primary_category", {}).get("term", "")
            if hasattr(entry, "arxiv_primary_category") else ""
        ),
        "categories": cats,
        "entry_id": entry.id,
        "pdf_url": pdf,
        "doi": doi,
        "category": classify_paper(clean("title"), clean("summary")),
    }


def _save_csv(rows: list, path: Path) -> None:
    if not rows:
        return
    fields = [
        "arxiv_id", "title", "authors", "published", "updated",
        "primary_category", "categories", "entry_id", "pdf_url", "doi", "category", "summary",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fetch_arxiv(
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: Optional[int] = None,
    topic: Optional[str] = None,
    split: bool = False,
    domain: Optional[str] = None,
) -> list:
    """
    搜索 arXiv 论文并返回列表，同时也写入 results/arxiv_results.json。

    搜索范围由 domain 参数决定（支持 speech / quant / both）：
      - speech:  语音/音频/说话人相关
      - quant:  金融量化 AI
      - both:   speech OR quant（同时检索两个领域）
    优先级顺序：query > topic（兼容旧参数名），
    domain 决定默认 topic 来源（仅在 query/topic 均未指定时生效）。

    日期优先从 start_date / end_date 取，否则从 config.json 读取。
    """
    global _KW
    cfg = load_config()
    _KW = cfg.get("keywords", _DEFAULT_KW)

    dom = domain or resolve(cfg, "search.domain", "speech")
    q = _resolve_topic(cfg, dom, query or topic)
    if not q:
        raise ValueError("必须提供 query 或 topic 参数，或在 config.json 中设置 search.topic")

    start = start_date or resolve(cfg, "search.start_date")
    end = end_date or resolve(cfg, "search.end_date")
    if not start or not end:
        raise ValueError(
            "必须提供 start_date 和 end_date，或在 config.json 中设置 search.start_date / search.end_date"
        )

    size = max_results or resolve(cfg, "search.max_results", 200)
    page_size = resolve(cfg, "search.page_size", 100)
    delay = resolve(cfg, "request.delay_seconds", 3)

    full_query = build_query(q, start, end)
    logger.info(f"查询: {full_query}")

    collected: list = []
    offset = 0
    while len(collected) < size:
        batch = min(page_size, size - len(collected))
        entries = fetch(full_query, offset, batch, delay)
        if not entries:
            break
        rows = [extract(e) for e in entries]
        collected.extend(rows)
        logger.info(f"  start={offset} +{len(rows)} = {len(collected)}")
        if len(entries) < batch:
            break
        offset += batch
        time.sleep(delay)

    out_dir = Path(__file__).parent.parent.parent / "results"
    out_dir.mkdir(exist_ok=True)

    if split:
        stems = {
            c: [r for r in collected if r["category"] == c]
            for c in ("frontend", "backend", "audiollm", "quant", "other")
        }
        for cat, rows in stems.items():
            p = out_dir / f"arxiv_results_{cat}.json"
            save_json(rows, p)
            logger.info(f"  {cat}: {len(rows)} -> {p}")
    else:
        out_path = out_dir / "arxiv_results.json"
        save_json(collected, out_path)
        logger.info(f"完成: {len(collected)} 条 -> {out_path}")

    return collected
