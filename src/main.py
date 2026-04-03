"""唯一入口"""
import sys

from src.cli import parse_args
from src.logger import setup_logger
from src.pipeline.runner import run_pipeline


def main():
    args = parse_args()
    logger = setup_logger()
    limit = 0 if args.full else args.limit

    logger.info(f"参数: query={args.query} | domain={args.domain} | limit={limit} | max_results={args.max_results}")

    try:
        run_pipeline(
            query=args.query,
            start_date=args.start_date,
            end_date=args.end_date,
            max_results=args.max_results,
            limit=limit,
            concurrency=args.concurrency,
            delay=args.delay,
            max_retries=args.max_retries,
            domain=args.domain,
        )
        logger.info("Pipeline 完成")
    except Exception as e:
        logger.error(f"Pipeline 失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
