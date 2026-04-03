"""LLM 论文分析服务"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

from src.config import load_config
from src.logger import setup_logger
from src.utils import load_json, save_json, truncate_text

logger = setup_logger()


class AnalysisMode:
    DETAILED = "detailed"


DETAILED_PROMPT = """

请仔细阅读以下论文，给出**有态度**的深度分析。

## 论文信息

**标题：** {title}

**作者：** {authors}

**原文摘要：**
{summary}

**正文内容：**
{content}

---

## 分析要求

请按以下结构输出（**全部用中文**，每个模块都要求**先给结论、再展开分析**）：

### 1. 一句话总结（必填）
用**一句话**概括这篇论文的核心价值。这句话要足够犀利，让人一眼就知道这篇论文在解决什么问题。

### 2. 研究动机
**结论先行：** 这篇论文要解决什么问题？
**展开分析：** 为什么这个问题重要但还没被很好解决？现有的方法有什么根本性缺陷？

### 3. 核心亮点（3-5个）
每个亮点用以下格式：
- **亮点描述**：具体的创新或贡献
- **金句点评**：一句话点出这个亮点的意义或反直觉之处

### 4. 反直觉发现（非共识观点）
这是最重要的模块！列出论文中**打破常规认知**的发现或观点：
- 哪些结论与直觉相悖？
- 哪些方法违背了领域内的"共识"？
- 作者提出了哪些"异端邪说"？
每个发现都要解释**为什么它反直觉**。

### 5. 关键技术或方法
**结论先行：** 核心技术是什么？
**展开分析：** 为什么这个技术有效？背后的原理是什么？与其他方法的关键区别在哪？

### 6. 实验结果
**结论先行：** 核心结果是什么（提升多少）？
**展开分析：** 实验设置如何？结果是否 solid？有没有 cherry-picking 的嫌疑？

### 7. 论文的局限性/缺陷
**不要客气！** 大胆指出论文的问题：
- 方法层面的缺陷
- 实验不够 solid 的地方
- 适用范围有限的地方
- 作者自己没意识到的盲点

### 8. 论文结论
**结论先行：** 作者的核心结论是什么？
**价值判断：** 这个结论可信吗？有多大的影响力？

### 9. 适用场景
**结论先行：** 这篇论文适合用在什么场景？
**边界条件：** 在什么情况下可能不 work？

### 10. 犀利点评（可选）
用一段话给这篇论文打一个"分数"或"一句话评价"。
"""

DETAILED_OUTPUT_SCHEMA = """请按以下 JSON 格式输出（只输出 JSON，不要有其他内容）：

{
  "一句话总结": "...",
  "研究动机": {"结论": "...", "展开": "..."},
  "核心亮点": [{"描述": "...", "金句": "..."}, ...],
  "反直觉发现": [{"发现": "...", "为何反直觉": "..."}, ...],
  "关键技术": {"结论": "...", "展开": "..."},
  "实验结果": {"结论": "...", "展开": "..."},
  "局限性/缺陷": ["缺陷1", "缺陷2", ...],
  "论文结论": {"结论": "...", "价值判断": "..."},
  "适用场景": {"结论": "...", "边界条件": "..."},
  "犀利点评": "..."
}
"""


def load_llm_config() -> dict:
    return load_config()["llm"]


def create_client(cfg: dict) -> OpenAI:
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def build_prompt(paper: dict) -> str:
    title = paper.get("title", "Unknown Title")
    authors = paper.get("authors", [])
    if isinstance(authors, list):
        authors_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
    else:
        authors_str = str(authors)
    summary = paper.get("summary", paper.get("abstract", ""))
    content = paper.get("content", "")

    return (
        DETAILED_PROMPT.format(
            title=title,
            authors=authors_str,
            summary=summary or "（无摘要）",
            content=truncate_text(content, max_chars=50000),
        )
        + "\n\n"
        + DETAILED_OUTPUT_SCHEMA
    )


def parse_analysis_result(text: str) -> dict:
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            text = json_match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        result: dict = {"error": "JSON 解析失败（可能截断）"}
        fields = [
            "一句话总结", "研究动机", "核心亮点", "反直觉发现",
            "关键技术", "实验结果", "局限性/缺陷", "论文结论",
            "适用场景", "犀利点评",
        ]
        for field in fields:
            pattern = rf'"{field}"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                result[field] = match.group(1).replace('\\"', '"').replace('\\n', '\n')
            else:
                pattern = rf'"{field}"\s*:\s*\{{([^}}]*)\}}'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    result[field] = match.group(1)
        return result


async def analyze_paper_async(
    client: OpenAI,
    paper: dict,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    arxiv_id = paper.get("arxiv_id", "unknown")
    title = paper.get("title", "Unknown Title")

    prompt = build_prompt(paper)

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        result_text = response.choices[0].message.content.strip()
        usage = response.usage

        analysis = parse_analysis_result(result_text)

        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "category": paper.get("category", "unknown"),
            "published": paper.get("published", ""),
            "analysis": analysis,
            "model_used": model,
            "tokens_used": usage.total_tokens if usage else 0,
            "raw_response": result_text,
        }

    except Exception as e:
        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "category": paper.get("category", "unknown"),
            "published": paper.get("published", ""),
            "error": str(e),
            "model_used": model,
        }


class AnalysisState:
    """管理分析状态，支持断点续传和增量写入。"""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.results: list = []
        self.done_ids: set = set()
        self._load()

    def _load(self) -> None:
        if self.output_path.exists():
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.results = data
                    self.done_ids = {r.get("arxiv_id") for r in data if r.get("arxiv_id")}
                    logger.info(f"已加载 {len(self.results)} 条历史记录（断点续传）")
            except (json.JSONDecodeError, OSError):
                pass

    def is_done(self, arxiv_id: str) -> bool:
        return arxiv_id in self.done_ids

    def add(self, result: dict) -> None:
        self.results.append(result)
        self.done_ids.add(result.get("arxiv_id", ""))
        self._save()

    def _save(self) -> None:
        self.output_path.write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def total_done(self) -> int:
        return len(self.results)


async def run_batch(
    client: OpenAI,
    papers: list,
    state: AnalysisState,
    model: str,
    max_tokens: int,
    temperature: float,
    concurrency: int,
    delay: float,
    max_retries: int = 3,
) -> None:
    pending = [
        (i, p) for i, p in enumerate(papers)
        if not state.is_done(p.get("arxiv_id", ""))
    ]
    total = len(papers)
    remaining = len(pending)

    if remaining == 0:
        logger.info(f"全部 {total} 篇论文已完成，无需重复分析")
        return

    logger.info(f"共 {total} 篇论文，已完成 {state.total_done} 篇，待分析 {remaining} 篇")
    logger.info(f"并发数: {concurrency}，请求间隔: {delay}s，重试次数: {max_retries}")

    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(idx: int, paper: dict, attempt: int = 1) -> tuple:
        async with semaphore:
            arxiv_id = paper.get("arxiv_id", f"unknown_{idx}")
            title_short = paper.get("title", "Unknown")[:60]
            prefix = f"[{idx + 1}/{total}]"
            if attempt > 1:
                prefix = f"[{idx + 1}/{total}] (重试 {attempt})"

            logger.info(f"{prefix} {arxiv_id} - {title_short}...")

            result = await analyze_paper_async(
                client=client,
                paper=paper,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if "error" in result:
                logger.warning(f"  x 失败: {result['error']}")
                return idx, result, False
            else:
                logger.info(f"  v 完成 (tokens: {result.get('tokens_used', 0)})")
                return idx, result, True

    tasks = [process_one(i, paper) for i, paper in pending]
    first_pass = await asyncio.gather(*tasks, return_exceptions=True)

    failed: list = []
    for item in first_pass:
        if isinstance(item, Exception):
            continue
        idx, result, success = item
        if success:
            state.add(result)
        else:
            failed.append((idx, papers[idx]))

    for attempt in range(2, max_retries + 1):
        if not failed:
            break
        logger.info(f"\n--- 重试第 {attempt} 轮 ({len(failed)} 篇失败) ---")
        retry_tasks = [process_one(idx, paper, attempt) for idx, paper in failed]
        retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)

        failed = []
        for item in retry_results:
            if isinstance(item, Exception):
                continue
            idx, result, success = item
            if not success:
                failed.append((idx, papers[idx]))
            else:
                state.add(result)

        if failed and delay > 0:
            await asyncio.sleep(delay)

    for idx, paper in failed:
        arxiv_id = paper.get("arxiv_id", f"unknown_{idx}")
        state.add({
            "arxiv_id": arxiv_id,
            "title": paper.get("title", "Unknown"),
            "error": "最终失败（已达最大重试次数）",
            "model_used": model,
        })

    logger.info(f"分析完成，共 {state.total_done} 篇论文已保存到 {state.output_path}")


def analyze_papers(
    input_path: str | Path = "results/arxiv_results_content.json",
    output_path: Optional[str | Path] = None,
    limit: Optional[int] = 3,
    concurrency: int = 5,
    delay: float = 1.0,
    max_retries: int = 3,
) -> None:
    """
    对论文进行 LLM 详细分析，支持断点续传和增量写入。
    """
    cfg = load_llm_config()

    papers = load_json(input_path)
    if not papers:
        raise FileNotFoundError(f"{input_path} 不存在或为空")

    if limit:
        papers = papers[:limit]

    if output_path is None:
        input_p = Path(input_path)
        output_path = input_p.parent / f"{input_p.stem}_analysis.json"

    out_path = Path(output_path)
    state = AnalysisState(out_path)
    client = create_client(cfg)

    max_tokens = cfg.get("max_tokens", 4096)

    asyncio.run(run_batch(
        client=client,
        papers=papers,
        state=state,
        model=cfg["model"],
        max_tokens=max_tokens,
        temperature=cfg.get("temperature", 0.7),
        concurrency=concurrency,
        delay=delay,
        max_retries=max_retries,
    ))
