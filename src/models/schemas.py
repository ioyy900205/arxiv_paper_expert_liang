"""数据结构定义"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: str
    published: str
    summary: str
    primary_category: str
    categories: str
    pdf_url: str
    category: str  # frontend / backend / audiollm / quant / other
    updated: str = ""
    entry_id: str = ""
    doi: str = ""
    content: Optional[str] = None
    analysis: Optional[dict] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Paper":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})
