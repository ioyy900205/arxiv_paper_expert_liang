"""配置加载"""
import json
from pathlib import Path
from typing import Any, Optional

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_config_cache: Optional[dict] = None


def load_config(force_reload: bool = False) -> dict:
    """加载 config.json，缓存结果避免重复读取。"""
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache
    if not CONFIG_PATH.exists():
        _config_cache = {}
        return _config_cache
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _config_cache = json.load(f)
    return _config_cache


def resolve(cfg: dict, key: str, default: Any = None) -> Any:
    """按点分路径从 config 字典中取值。"""
    for k in key.split("."):
        if isinstance(cfg, dict) and k in cfg:
            cfg = cfg[k]
        else:
            return default
    return cfg
