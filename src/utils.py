"""通用工具函数"""
import json
from pathlib import Path
from typing import Any, Optional, Union


def save_json(data: Any, path: Union[str, Path]) -> None:
    """将数据序列化到 JSON 文件（自动创建父目录）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Union[str, Path]) -> Optional[Any]:
    """从 JSON 文件加载数据，文件不存在时返回 None。"""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def truncate_text(text: str, max_chars: int = 50000) -> str:
    """截断过长的文本以控制 token 消耗。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... 内容已截断 ...]"
