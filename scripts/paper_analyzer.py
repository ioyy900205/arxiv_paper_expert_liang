#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 LLM 对 arXiv 论文进行深度分析，输出结构化的论文理解报告。

依赖：pip install openai
配置：config.json 中的 llm 节

用法：
  python scripts/paper_analyzer.py results/content_test.json              # 分析前 3 条
  python scripts/paper_analyzer.py results/content_test.json -n 5        # 分析前 5 条
  python scripts/paper_analyzer.py results/content_test.json --full      # 全量分析
  python scripts/paper_analyzer.py results/content_test.json -o results/analysis.json
  python scripts/paper_analyzer.py results/content_test.json --full     # 断点续传（自动跳过已分析）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

# ---------------------------------------------------------------
# 配置
# ---------------------------------------------------------------

ANALYSIS_PROMPT = """你是一位犀利、有观点的 AI 论文评审专家。请仔细阅读以下论文，给出**有态度**的深度分析。

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
用一段话给这篇论文打一个"分数"或"一句话评价"。可以包含：
- 与同类工作的最大差距
- 最值得借鉴的地方
- 最值得警惕的地方
"""

OUTPUT_SCHEMA = """请按以下 JSON 格式输出（只输出 JSON，不要有其他内容）：

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


# ---------------------------------------------------------------
# LLM 客户端
# ---------------------------------------------------------------

def load_llm_config() -> dict:
    """从 config.json 加载 LLM 配置。"""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)["llm"]


def create_client(cfg: dict) -> OpenAI:
    """创建 LLM 客户端。"""
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def truncate_text(text: str, max_chars: int = 50000) -> str:
    """截断过长的文本以控制 token 消耗。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... 内容已截断 ...]"


# ---------------------------------------------------------------
# 论文分析
# ---------------------------------------------------------------

def build_prompt(paper: dict) -> str:
    """构建单篇论文的分析 prompt。"""
    arxiv_id = paper.get("arxiv_id", "unknown")
    title = paper.get("title", "Unknown Title")
    authors = paper.get("authors", [])
    if isinstance(authors, list):
        authors = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
    summary = paper.get("summary", paper.get("abstract", ""))
    content = paper.get("content", "")

    prompt = ANALYSIS_PROMPT.format(
        title=title,
        authors=authors,
        summary=summary or "（无摘要）",
        content=truncate_text(content, max_chars=50000),
    )
    prompt += "\n\n" + OUTPUT_SCHEMA
    return prompt


def parse_analysis_result(text: str) -> dict:
    """从 LLM 输出中解析 JSON 分析结果。"""
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
        return {"error": "JSON 解析失败", "raw_text": text[:2000]}


async def analyze_paper_async(
    client: OpenAI,
    paper: dict,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    """
    异步调用 LLM 分析单篇论文。
    """
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
            "analysis": analysis,
            "model_used": model,
            "tokens_used": usage.total_tokens if usage else 0,
            "raw_response": result_text,
        }

    except Exception as e:
        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "error": str(e),
            "model_used": model,
        }


# ---------------------------------------------------------------
# 状态管理（断点续传 + 增量输出）
# ---------------------------------------------------------------

class AnalysisState:
    """
    管理分析状态，支持断点续传和增量写入。
    """

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.results: list[dict] = []
        self.done_ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        """从已有输出文件加载已完成状态。"""
        if self.output_path.exists():
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.results = data
                    self.done_ids = {r.get("arxiv_id") for r in data if r.get("arxiv_id")}
                    print(f"已加载 {len(self.results)} 条历史记录（断点续传）")
            except (json.JSONDecodeError, OSError):
                pass

    def is_done(self, arxiv_id: str) -> bool:
        """检查论文是否已分析过。"""
        return arxiv_id in self.done_ids

    def add(self, result: dict) -> None:
        """添加分析结果并立即写入文件。"""
        self.results.append(result)
        self.done_ids.add(result.get("arxiv_id", ""))
        self._save()

    def _save(self) -> None:
        """增量写入：每次追加覆盖完整文件。"""
        self.output_path.write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    @property
    def total_done(self) -> int:
        return len(self.results)


# ---------------------------------------------------------------
# 并发批量处理
# ---------------------------------------------------------------

async def run_batch(
    client: OpenAI,
    papers: list[dict],
    state: AnalysisState,
    model: str,
    max_tokens: int,
    temperature: float,
    concurrency: int,
    delay: float,
) -> None:
    """
    并发分析论文，支持断点续传和增量输出。
    """
    # 过滤掉已完成的
    pending = [p for p in papers if not state.is_done(p.get("arxiv_id", ""))]
    total = len(papers)
    remaining = len(pending)

    if remaining == 0:
        print(f"全部 {total} 篇论文已完成，无需重复分析")
        return

    print(f"共 {total} 篇论文，已完成 {state.total_done} 篇，待分析 {remaining} 篇")
    print(f"并发数: {concurrency}，请求间隔: {delay}s")
    print("-" * 50)

    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(idx: int, paper: dict) -> tuple[int, dict]:
        async with semaphore:
            arxiv_id = paper.get("arxiv_id", f"unknown_{idx}")
            title = paper.get("title", "Unknown")[:60]
            print(f"[{idx+1}/{total}] {arxiv_id} - {title}...")

            result = await analyze_paper_async(
                client=client,
                paper=paper,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if "error" in result:
                print(f"  ✗ 失败: {result['error']}")
            else:
                print(f"  ✓ 完成 (tokens: {result.get('tokens_used', 0)})")

            # 增量写入
            state.add(result)

            # 并发请求间适当延迟
            if delay > 0:
                await asyncio.sleep(delay)

            return idx, result

    # 创建所有任务
    tasks = [
        process_with_semaphore(i, paper)
        for i, paper in enumerate(papers)
        if not state.is_done(paper.get("arxiv_id", ""))
    ]

    # 并发执行
    await asyncio.gather(*tasks, return_exceptions=True)

    print("-" * 50)
    print(f"分析完成，共 {state.total_done} 篇论文已保存到 {state.output_path}")


def run(
    input_path: Path,
    output_path: Optional[Path] = None,
    limit: Optional[int] = None,
    concurrency: int = 3,
    delay: float = 1.0,
) -> None:
    """
    入口函数。
    """
    # 加载配置
    cfg = load_llm_config()

    # 加载论文数据
    papers = json.loads(input_path.read_text(encoding="utf-8"))
    if limit:
        papers = papers[:limit]

    # 确定输出路径
    out_path = output_path or input_path.parent / f"{input_path.stem}_analysis.json"

    # 创建状态管理
    state = AnalysisState(out_path)

    # 创建客户端
    client = create_client(cfg)

    # 运行
    asyncio.run(run_batch(
        client=client,
        papers=papers,
        state=state,
        model=cfg["model"],
        max_tokens=cfg.get("max_tokens", 4096),
        temperature=cfg.get("temperature", 0.7),
        concurrency=concurrency,
        delay=delay,
    ))


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="使用 LLM 分析 arXiv 论文，输出结构化报告（支持断点续传 + 并发）"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="results/content_test.json",
        help="输入 JSON 文件（包含论文数据）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=3,
        help="最多分析多少篇论文（默认 3）",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="分析全部论文（忽略 -n）",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=3,
        help="并发请求数（默认 3）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="每次请求间隔秒数（默认 1.0）",
    )
    args = parser.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.output) if args.output else None,
        limit=None if args.full else args.limit,
        concurrency=args.concurrency,
        delay=args.delay,
    )
