# arxiv_paper_expert_liang

面向中文自然语言的 arXiv 论文研究与简报生成技能。支持搜索、下载、分析论文，并生成结构化的分析报告。

## 功能特性

- **论文搜索**: 按主题、分类、时间范围搜索 arXiv 论文
- **全文抓取**: 自动从 arXiv 获取论文全文（HTML 优先，PDF 回退）
- **LLM 分析**: 调用 MiniMax LLM 对论文进行深度分析
- **报告生成**: 生成 HTML 和 Markdown 格式的分析报告
- **自动化流水线**: 一键执行完整的论文研究流程

## 目录结构

```
arxiv_paper_expert_liang/
├── config.json              # 唯一配置文件
├── requirements.txt         # Python 依赖
├── README.md
├── SKILL.md                 # Cursor 技能说明
├── scripts/
│   ├── arxiv_fetch.py       # 论文搜索与抓取
│   ├── arxiv_content.py     # 论文全文抓取（HTML/PDF）
│   ├── paper_analyzer.py    # LLM 论文分析
│   ├── generate_report.py    # 报告生成（HTML/Markdown）
│   ├── run_pipeline.sh      # 完整流水线脚本
│   └── test_llm.py          # LLM API 测试
└── results/                 # 输出目录
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
    "topic": "cat:cs.SD AND (all:\"speech enhancement\" OR ti:\"speech\" ...)",
    "start_date": "2025-01-01",
    "end_date": "2026-04-01",
    "max_results": 200
  }
}
```

### 3. 执行流水线

```bash
# 完整流程（搜索 → 抓取 → 分析 → 报告）
bash scripts/run_pipeline.sh

# 仅搜索最近 7 天论文
bash scripts/run_pipeline.sh --step fetch --days 7

# 仅抓取全文
bash scripts/run_pipeline.sh --step content

# 分析前 10 篇论文
bash scripts/run_pipeline.sh --step analyze -n 10

# 断点续传
bash scripts/run_pipeline.sh --step analyze --resume
```

## 各脚本说明

### arxiv_fetch.py - 论文搜索

按主题、分类和时间范围搜索 arXiv 论文。

```bash
python scripts/arxiv_fetch.py                          # 使用默认配置
python scripts/arxiv_fetch.py --days 30                 # 最近 30 天
python scripts/arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split
```

**功能特点：**
- 自动分页获取
- 429 限流自动等待重试
- 三分类：frontend（语音前端）/ backend（语音后端）/ audiollm（音频大模型）
- 支持 `--split` 输出三个分类文件

### arxiv_content.py - 全文抓取

从 arXiv 获取论文全文，提取为纯文本。

```bash
python scripts/arxiv_content.py results/arxiv_results.json -n 3   # 前 3 篇
python scripts/arxiv_content.py results/arxiv_results.json --full # 全部
python scripts/arxiv_content.py results/arxiv_results.json --full --delay 1.0
```

**功能特点：**
- HTML 优先（可复制文本），PDF 回退
- 自动版本回退（当前版本不可用时尝试其他版本）
- 移除参考文献和致谢
- 保留章节结构

### paper_analyzer.py - LLM 分析

调用 LLM 对论文进行深度分析，输出结构化的分析结果。

```bash
python scripts/paper_analyzer.py results/content_test.json -n 5      # 分析 5 篇
python scripts/paper_analyzer.py results/content_test.json --full    # 全量分析
python scripts/paper_analyzer.py results/content_test.json --concise # 精简模式
```

**分析模式：**
- **详细分析**: 10+ 个维度的深度评审（一句话总结、研究动机、核心亮点、反直觉发现、关键技术、实验结果、局限性、论文结论、适用场景、犀利点评）
- **精简分析**: 一句话总结

**输出字段：**

| 字段 | 说明 |
|------|------|
| 一句话总结 | 核心价值概括 |
| 研究动机 | 要解决的问题和重要性 |
| 核心亮点 | 3-5 个创新点 |
| 反直觉发现 | 打破常规认知的结论 |
| 关键技术 | 核心技术原理 |
| 实验结果 | 实验设置和结果 |
| 局限性/缺陷 | 不足和改进方向 |
| 论文结论 | 作者的核心结论 |
| 适用场景 | 应用场景和边界条件 |
| 犀利点评 | 综合评价 |

**断点续传：** 自动跳过已分析的论文，中断后可继续

### generate_report.py - 报告生成

将分析结果生成为 HTML 和 Markdown 格式的报告。

```bash
python scripts/generate_report.py
```

**输出：**
- `results/paper_analysis_report.html` - 浅色主题 HTML 报告
- `results/paper_analysis_report.md` - 带目录的 Markdown 报告

**HTML 报告特点：**
- 分类颜色标签
- 目录导航
- 响应式设计
- 回到顶部按钮

### run_pipeline.sh - 完整流水线

一键执行完整的论文研究流程。

```bash
bash scripts/run_pipeline.sh                    # 完整流程
bash scripts/run_pipeline.sh --step fetch        # 仅搜索
bash scripts/run_pipeline.sh --step content      # 仅抓取
bash scripts/run_pipeline.sh --step analyze      # 仅分析
bash scripts/run_pipeline.sh --full              # 全量分析
bash scripts/run_pipeline.sh --days 30           # 最近 30 天
bash scripts/run_pipeline.sh --resume            # 断点续传
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整流水线                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. arxiv_fetch.py                                              │
│     输入: config.json                                            │
│     输出: results/arxiv_results.json                              │
│           ↓                                                      │
│  2. arxiv_content.py                                            │
│     输入: results/arxiv_results.json                              │
│     输出: results/content_*.json                                  │
│           ↓                                                      │
│  3. paper_analyzer.py                                           │
│     输入: results/content_*.json                                  │
│     输出: results/analysis_*.json                                 │
│           ↓                                                      │
│  4. generate_report.py                                          │
│     输入: results/analysis_*.json                                 │
│     输出: paper_analysis_report.html                              │
│           paper_analysis_report.md                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

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

### content_*.json

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

### analysis_*.json

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

### config.json 搜索配置

```json
{
  "search": {
    "topic": "arXiv 查询语句（支持 all:, ti:, au:, cat:, submittedDate:）",
    "start_date": "开始日期（YYYY-MM-DD）",
    "end_date": "结束日期（YYYY-MM-DD）",
    "max_results": 200,
    "page_size": 100
  }
}
```

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
    "audiollm": ["llm", "gpt-", "multimodal llm", ...]
  }
}
```

**分类优先级：** audiollm > frontend > backend

## 依赖

```
requests>=2.28.0
feedparser>=6.0.0
beautifulsoup4>=4.11.0
pdfminer.six>=20221105
openai>=1.0.0
```

## License

MIT
