---
name: arxiv_paper_expert
description: 面向中文自然语言的 arXiv 论文研究技能。用于把"看看最近有什么新论文""帮我找一下某个主题的论文""最近一周 XX 领域有哪些新工作"这类请求，转成可执行的论文搜索、信息提取与简要分析流程。
author: liang
version: 1.0.0
requirements:
  python: 3.8+
  packages:
    - requests
    - feedparser
    - beautifulsoup4
    - pdfminer.six
    - openai
environment_variables:
  - name: ARXIV_API_BASE
    default: http://export.arxiv.org/api/query
    description: arXiv API 地址
network_access: true
---

# arxiv_paper_expert

面向中文自然语言的 arXiv 论文研究与简报生成技能。

## What this skill is for

使用这个 skill 的典型场景：

- 找某个时间段内的某个主题论文列表
- 找某个时间点/时间段内某个领域的新论文
- 对一批论文做信息提取和整理
- 调用 LLM 对论文做深度分析
- 生成结构化论文简报

## 模块架构

```
scripts/
├── arxiv_fetch.py       # 论文搜索：按主题/分类/时间搜索
├── arxiv_content.py     # 全文抓取：HTML 优先 + PDF 回退
├── paper_analyzer.py    # LLM 分析：调用 MiniMax API 分析论文
├── generate_report.py   # 报告生成：HTML/Markdown 格式报告
├── run_pipeline.sh       # 完整流水线：一键执行全部
└── test_llm.py          # LLM 测试：快速验证 API Key 可用性
```

## 典型使用触发

- 帮我找一下最近有关 XXX 的论文
- 最近一周有什么新的 LLM 论文？
- 2024年3月份关于强化学习的论文
- 帮我搜搜这个领域最近的工作
- 帮我分析一下这批论文
- 帮我生成论文简报

## 工作流程

### 完整流水线（推荐）

```bash
# 进入项目目录
cd arxiv_paper_expert_liang

# 完整流程：搜索 → 抓取 → 分析 → 报告
bash scripts/run_pipeline.sh

# 仅搜索最近 7 天论文
bash scripts/run_pipeline.sh --step fetch --days 7

# 仅抓取全文
bash scripts/run_pipeline.sh --step content

# 分析前 10 篇论文
bash scripts/run_pipeline.sh --step analyze -n 10

# 断点续传（跳过已分析）
bash scripts/run_pipeline.sh --step analyze --resume

# 分析全部论文
bash scripts/run_pipeline.sh --step analyze --full
```

### 阶段 1：搜索论文（arxiv_fetch.py）

按主题、分类和时间范围搜索 arXiv 论文。

```bash
python scripts/arxiv_fetch.py --days 30                    # 最近 30 天
python scripts/arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split
```

**功能特点：**
- 自动分页获取
- 429 限流自动等待重试
- 三分类：frontend（语音前端）/ backend（语音后端）/ audiollm（音频大模型）
- 支持 `--split` 输出三个分类文件

### 阶段 2：全文抓取（arxiv_content.py）

从 arXiv 获取论文全文，提取为纯文本。

```bash
python scripts/arxiv_content.py results/arxiv_results.json -n 3   # 前 3 篇
python scripts/arxiv_content.py results/arxiv_results.json --full # 全部
```

**功能特点：**
- HTML 优先（可复制文本），PDF 回退
- 自动版本回退（当前版本不可用时尝试其他版本）
- 移除参考文献和致谢
- 保留章节结构

### 阶段 3：LLM 分析（paper_analyzer.py）

调用 LLM 对论文进行深度分析，输出结构化的分析结果。

```bash
python scripts/paper_analyzer.py results/arxiv_results_content.json -n 5      # 分析 5 篇
python scripts/paper_analyzer.py results/arxiv_results_content.json --full    # 全量分析
python scripts/paper_analyzer.py results/arxiv_results_content.json --concise # 精简模式
```

**分析模式：**
- **详细分析**：10+ 个维度的深度评审（一句话总结、研究动机、核心亮点、反直觉发现、关键技术、实验结果、局限性、论文结论、适用场景、犀利点评）
- **精简分析**：一句话总结

**断点续传：** 自动跳过已分析的论文，中断后可继续

### 阶段 4：报告生成（generate_report.py）

将分析结果生成为 HTML 和 Markdown 格式的报告。

```bash
python scripts/generate_report.py
```

**输出：**
- `results/paper_analysis_report.html` - 浅色主题 HTML 报告
- `results/paper_analysis_report.md` - 带目录的 Markdown 报告

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
    "mode": "detailed",
    "model_used": "MiniMax-M2.7-highspeed",
    "tokens_used": 12345
  }
]
```

## 配置说明

### config.json

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
    "topic": "cat:cs.SD AND (all:\"speech enhancement\" OR ...)",
    "start_date": "2025-01-01",
    "end_date": "2026-04-01",
    "max_results": 200
  }
}
```

## 依赖

```
requests>=2.28.0
feedparser>=6.0.0
beautifulsoup4>=4.11.0
pdfminer.six>=20221105
openai>=1.0.0
```
