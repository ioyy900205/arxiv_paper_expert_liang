# arxiv_paper_expert_liang

面向中文自然语言的 arXiv 论文研究与简报生成技能。支持语音/音频和金融量化两大领域的论文搜索、下载、分析，并生成结构化的分析报告。

## 功能特性

- **论文搜索**: 按主题、分类、时间范围搜索 arXiv 论文
- **全文抓取**: 自动从 arXiv 获取论文全文（HTML 优先，PDF 回退）
- **LLM 分析**: 调用 MiniMax LLM 对论文进行深度分析
- **报告生成**: 生成 HTML 和 Markdown 格式的分析报告
- **自动化流水线**: 一键执行完整的论文研究流程
- **多领域支持**: 语音/音频深度学习 + 金融量化 AI

## 目录结构

```
arxiv_paper_expert_liang/
├── SKILL.md                 # OpenClaw/Cursor 技能说明
├── README.md
├── config.json              # 唯一配置文件（LLM、搜索参数、分类关键词）
├── requirements.txt         # Python 依赖
├── logs/                    # 日志输出目录（自动创建）
├── results/                 # 输出目录
│   ├── arxiv_results.json              # 搜索结果
│   ├── arxiv_results_content.json      # 全文抓取结果
│   ├── arxiv_results_content_analysis.json  # LLM 分析结果
│   ├── arxiv_results_content_report.html     # HTML 报告
│   └── arxiv_results_content_report.md      # Markdown 报告
└── src/                     # 唯一入口
    ├── main.py              # 固定入口：python -m src
    ├── cli.py               # 参数解析
    ├── config.py            # 配置读取
    ├── logger.py            # 日志
    ├── utils.py             # 通用工具
    ├── pipeline/runner.py   # Pipeline 编排
    ├── services/
    │   ├── arxiv_fetcher.py    # 论文搜索
    │   ├── content_extractor.py # 全文抓取
    │   ├── paper_analyzer.py    # LLM 分析
    │   └── report_generator.py  # 报告生成
    └── models/schemas.py    # 数据结构
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整流水线                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. arxiv_fetch.py                                              │
│     输入: config.json（设置 start_date 和 end_date）               │
│     输出: results/arxiv_results.json                              │
│           ↓                                                      │
│  2. arxiv_content.py                                            │
│     输入: results/arxiv_results.json                              │
│     输出: results/arxiv_results_content.json                      │
│           ↓                                                      │
│  3. paper_analyzer.py                                           │
│     输入: results/arxiv_results_content.json                      │
│     输出: results/arxiv_results_content_analysis.json             │
│           ↓                                                      │
│  4. generate_report.py                                          │
│     输入: results/arxiv_results_content_analysis.json             │
│     输出: results/arxiv_results_content_report.html               │
│           results/arxiv_results_content_report.md                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.json`：

```json
{
  "llm": {
    "provider": "minimax",
    "api_key": "your-api-key",
    "base_url": "https://api.minimax.chat/v1",
    "model": "MiniMax-M2.7-highspeed",
    "max_tokens": 16384,
    "temperature": 0.7
  },
  "search": {
    "domain": "speech",
    "topic": {
      "speech": "(cat:eess.AS OR ...) AND (all:\"speech\" OR all:\"audio\" ...)",
      "quant": "(cat:q-fin.CP OR ...) AND (all:\"quantitative\" OR ...)"
    },
    "start_date": "2026-04-01",
    "end_date": "2026-04-03",
    "max_results": 200
  }
}
```

**domain 配置说明：**

| 值 | 检索范围 |
|----|----------|
| `speech` | 语音/音频（默认） |
| `quant` | 金融量化 AI |
| `both` | 两个领域同时检索 |

### 3. 执行流水线

统一入口：`python -m src`（src/main.py）

```bash
# 默认流程（使用 config.json 中的日期范围）
python -m src

# 命令行覆盖日期范围
python -m src --start-date 2026-04-01 --end-date 2026-04-03

# 指定搜索 query
python -m src --query "cat:cs.SD AND all:\"speech enhancement\""

# 分析全部论文（默认只分析前 3 篇）
python -m src --full
```

## CLI 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--query` | config.json | 搜索 query（覆盖 config） |
| `--domain` | config.json | 检索领域：speech（默认）/ quant / both |
| `--start-date` | config.json | 搜索开始日期 (YYYY-MM-DD) |
| `--end-date` | config.json | 搜索结束日期 (YYYY-MM-DD) |
| `--max-results` | 200 | 最大搜索论文数 |
| `--limit` | 3 | 单次分析论文数（0 = 全部） |
| `--concurrency` | 5 | LLM 并发请求数 |
| `--delay` | 1.0 | 请求间隔（秒） |
| `--max-retries` | 3 | 单篇最大重试次数 |
| `--full` | false | 分析全部论文（等同于 `--limit 0`） |

## 服务模块（内部使用）

各服务模块通过 `src/pipeline/runner.py` 编排，也可独立测试：

| 模块 | 文件 | 功能 |
|------|------|------|
| 论文搜索 | `src/services/arxiv_fetcher.py` | 按 query / 日期搜索 arXiv |
| 全文抓取 | `src/services/content_extractor.py` | HTML 优先 + PDF 回退 |
| LLM 分析 | `src/services/paper_analyzer.py` | 深度分析 + 断点续传 |
| 报告生成 | `src/services/report_generator.py` | Markdown + HTML 双格式 |

流程产物（按顺序）：

| 阶段 | 文件 | 说明 |
|------|------|------|
| 搜索 | `results/arxiv_results.json` | 原始搜索结果 |
| 全文 | `results/arxiv_results_content.json` | HTML/PDF 提取文本 |
| 分析 | `results/arxiv_results_content_analysis.json` | LLM 结构化分析 |
| 报告 | `results/arxiv_results_content_report.html` | 可交互 HTML 报告 |
| 报告 | `results/arxiv_results_content_report.md` | Markdown 报告 |

## 输出文件格式

### arxiv_results.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "authors": "作者1, 作者2",
    "published": "2026-04-01",
    "summary": "摘要...",
    "primary_category": "cs.SD",
    "categories": "cs.SD, eess.AS",
    "pdf_url": "https://arxiv.org/pdf/...",
    "category": "frontend"
  }
]
```

### arxiv_results_content.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "authors": "作者1, 作者2",
    "content": "论文全文内容...",
    "html_url": "https://arxiv.org/html/...",
    "content_source": "html",
    "used_arxiv_id": "2604.01155v1"
  }
]
```

### arxiv_results_content_analysis.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "category": "frontend",
    "published": "2026-04-01T00:00:00Z",
    "analysis": {
      "一句话总结": "...",
      "研究动机": {"结论": "...", "展开": "..."},
      "核心亮点": [{"描述": "...", "金句": "..."}, ...],
      "反直觉发现": [{"发现": "...", "为何反直觉": "..."}, ...],
      "关键技术": {"结论": "...", "展开": "..."},
      "实验结果": {"结论": "...", "展开": "..."},
      "局限性/缺陷": ["...", "..."],
      "论文结论": {"结论": "...", "价值判断": "..."},
      "适用场景": {"结论": "...", "边界条件": "..."},
      "犀利点评": "..."
    },
    "model_used": "MiniMax-M2.7-highspeed",
    "tokens_used": 12345
  }
]
```

## 配置说明

### config.json 搜索配置

```json
{
  "search": {
    "domain": "speech",
    "topic": { ... },
    "start_date": "开始日期（YYYY-MM-DD）",
    "end_date": "结束日期（YYYY-MM-DD）",
    "max_results": 200,
    "page_size": 100
  }
}
```

**domain 配置：**

| 值 | 检索范围 |
|----|----------|
| `speech` | 语音/音频/eess（默认） |
| `quant` | 金融量化/q-fin |
| `both` | 两个领域同时检索 |

> **命令行参数优先级高于 config.json**：`python -m src --domain quant` 会覆盖 `config.json` 中的 `domain` 设置。

### config.json 分类关键词

```json
{
  "keywords": {
    "frontend": {
      "title_core": ["speech enhancement", "beamforming", ...],
      "title_tools": ["mel spectrogram", "mfcc", ...],
      "summary_core": ["speech enhancement", ...]
    },
    "backend": {
      "context": ["speech recognition", "tts", ...]
    },
    "audiollm": ["llm", "gpt-", "multimodal llm", ...],
    "quant": {
      "title_core": ["quantitative trading", "portfolio optimization", ...],
      "title_ai": ["reinforcement learning trading", "deep learning finance", ...],
      "summary_core": ["quantitative finance", "finrl", ...]
    }
  }
}
```

**分类优先级：** audiollm > quant > frontend > backend

## 依赖

```
requests>=2.28.0
feedparser>=6.0.0
beautifulsoup4>=4.11.0
pdfminer.six>=20221105
openai>=1.0.0
python-dateutil>=2.8.0
```

## License

MIT
