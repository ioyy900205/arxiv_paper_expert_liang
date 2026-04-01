# arxiv_paper_expert_liang

面向中文自然语言的 arXiv 论文研究与简报生成技能。

## 快速开始

```bash
pip install requests feedparser beautifulsoup4

# 默认配置（2025-01-01 ~ 2026-04-01，语音相关主题）
python scripts/arxiv_fetch.py

# 抓取 2026 Q1 论文
python scripts/arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split
```

## 目录结构

```
scripts/
├── arxiv_fetch.py   # 论文抓取脚本
results/             # 输出目录
config.json          # 唯一配置文件（含搜索参数和分类关键词）
README.md
```

## config.json

所有配置集中在 `config.json` 一个文件里：

```json
{
  "search": {
    "topic": "cat:cs.SD AND (all:\"speech enhancement\" ...)",
    "start_date": "2025-01-01",
    "end_date": "2026-04-01",
    "max_results": 200,
    "page_size": 100
  },
  "output": { "format": "json", "filename": "arxiv_results.json" },
  "request": { "delay_seconds": 3 },
  "keywords": {
    "frontend": { ... },
    "backend":  { ... },
    "audiollm": [...]
  }
}
```

关键词说明：

| 节 | 字段 | 作用 |
|----|------|------|
| `frontend.title_core` | 标题匹配 | 直接归为 frontend |
| `frontend.title_tools` | 标题匹配 | 摘要含 `backend.context` → backend，否则 → frontend |
| `frontend.summary_core` | 摘要匹配 | 归为 frontend |
| `backend.context` | 摘要匹配 | 用于排除 title_tools 的误判 |
| `audiollm` | 标题或摘要匹配 | 最高优先级，归为 audiollm |

## 输出

使用 `--split` 时生成三个文件：

- `results/*_frontend.json` — 语音前端（增强、分离、波束形成、去混响等）
- `results/*_backend.json` — 语音后端（ASR、TTS、说话人识别、情感等）
- `results/*_audiollm.json` — 音频大模型（LLM 用于语音/音频任务）
