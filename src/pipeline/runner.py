"""Pipeline 编排"""
from pathlib import Path
from typing import Optional

from src.config import load_config, resolve
from src.logger import setup_logger
from src.services.arxiv_fetcher import fetch_arxiv
from src.services.content_extractor import fetch_content
from src.services.paper_analyzer import analyze_papers
from src.services.report_generator import generate_report

logger = setup_logger()


def run_pipeline(
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: int = 200,
    limit: int = 3,
    concurrency: int = 5,
    delay: float = 1.0,
    max_retries: int = 3,
    domain: Optional[str] = None,
) -> None:
    """
    完整流水线：搜索 → 抓取全文 → LLM 分析 → 生成报告。

    各中间结果自动复用：
      - results/arxiv_results.json              （搜索结果）
      - results/arxiv_results_content.json      （全文）
      - results/arxiv_results_content_analysis.json（分析）
      - results/arxiv_results_content_report.html/.md（报告）
    """
    results_dir = Path(__file__).parent.parent.parent / "results"

    logger.info("=== 阶段 1/4: 搜索论文 ===")
    fetch_arxiv(
        query=query,
        start_date=start_date,
        end_date=end_date,
        max_results=max_results,
        domain=domain,
    )

    input_path = results_dir / "arxiv_results.json"
    if not input_path.exists():
        logger.warning(f"{input_path} 不存在，跳过后续阶段")
        return

    logger.info("=== 阶段 2/4: 抓取全文 ===")
    fetch_content(input_path=input_path, limit=None, delay=3.0)

    input_path = results_dir / "arxiv_results_content.json"
    if not input_path.exists():
        logger.warning(f"{input_path} 不存在，跳过分析阶段")
        return

    logger.info("=== 阶段 3/4: LLM 分析 ===")
    analyze_papers(
        input_path=input_path,
        limit=None if limit == 0 else limit,
        concurrency=concurrency,
        delay=delay,
        max_retries=max_retries,
    )

    input_path = results_dir / "arxiv_results_content_analysis.json"
    if not input_path.exists():
        logger.warning(f"{input_path} 不存在，跳过报告生成")
        return

    logger.info("=== 阶段 4/4: 生成报告 ===")
    cfg = load_config()
    sd = start_date or resolve(cfg, "search.start_date", "")
    ed = end_date or resolve(cfg, "search.end_date", "")
    date_range_str = f"{sd} ~ {ed}" if sd and ed else None
    generate_report(input_path=input_path, output_dir=results_dir, date_range_str=date_range_str)

    logger.info("=== Pipeline 完成 ===")
