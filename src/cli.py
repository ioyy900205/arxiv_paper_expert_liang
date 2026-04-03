"""命令行参数解析"""
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="ArXiv Paper Expert - 唯一入口")
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="ArXiv 搜索 query（可覆盖 config.json）",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="搜索开始日期 YYYY-MM-DD（可覆盖 config.json）",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="搜索结束日期 YYYY-MM-DD（可覆盖 config.json）",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="最大搜索论文数（默认 200）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="单次分析论文数（默认 3，0 = 全部）",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="LLM 并发请求数（默认 5）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="请求间隔秒数（默认 1.0）",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="单篇最大重试次数（默认 3）",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="分析全部论文（等同于 --limit 0）",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        choices=["speech", "quant", "both"],
        help="检索领域：speech（语音/音频，默认）/ quant（金融量化）/ both（两个都检）",
    )
    return parser.parse_args()
