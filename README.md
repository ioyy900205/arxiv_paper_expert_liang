# arxiv_paper_expert_liang

面向中文自然语言的 arXiv 论文研究与简报生成技能。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 1. 抓取论文（默认 2025-01-01 ~ 2026-04-01，语音相关主题）
python scripts/arxiv_fetch.py

# 2. 获取论文全文（HTML 优先，PDF 回退）
python scripts/arxiv_content.py results/arxiv_results.json --full

# 3. 使用 LLM 分析论文
python scripts/paper_analyzer.py results/content_test.json -n 5

# 测试 LLM API
python scripts/test_llm.py
```

## 目录结构

```
scripts/
├── arxiv_fetch.py       # 论文搜索与抓取
├── arxiv_content.py     # 论文全文抓取（HTML/PDF）
├── paper_analyzer.py    # LLM 论文分析
├── test_llm.py          # LLM API 测试
results/                 # 输出目录
config.json               # 唯一配置文件
requirements.txt         # Python 依赖
README.md
SKILL.md                 # 技能说明文档
```

## 工作流程

```
arxiv_fetch.py      →  arxiv_results.json    # 论文元信息
     ↓
arxiv_content.py    →  content_test.json     # 论文全文
     ↓
paper_analyzer.py   →  *_analysis.json       # LLM 分析结果
```

## config.json

所有配置集中在 `config.json` 一个文件里：

```json
{
  "llm": {
    "provider": "minimax",
    "api_key": "your-api-key",
    "base_url": "https://api.minimax.chat/v1",
    "model": "MiniMax-M2.7-highspeed",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "search": {
    "topic": "cat:cs.SD AND (all:\"speech enhancement\" ...)",
    "start_date": "2025-01-01",
    "end_date": "2026-04-01",
    "max_results": 200,
    "page_size": 100
  },
  "output": { "format": "json", "filename": "arxiv_results.json" },
  "request": { "delay_seconds": 3 }
}
```

## 主要功能

### 1. 论文搜索 (arxiv_fetch.py)

```bash
# 默认配置搜索
python scripts/arxiv_fetch.py

# 指定时间和数量
python scripts/arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split
```

### 2. 全文抓取 (arxiv_content.py)

自动从 arXiv 获取论文全文，优先使用 HTML 格式（可复制文本），失败时自动回退到 PDF。

```bash
# 分析前 3 条
python scripts/arxiv_content.py results/arxiv_results.json

# 全量抓取
python scripts/arxiv_content.py results/arxiv_results.json --full

# 调整请求间隔
python scripts/arxiv_content.py results/arxiv_results.json --full --delay 1.0
```

**功能特点：**
- HTML 优先，PDF 回退
- 自动重试（429 限流时等待后重试）
- 版本回退（当前版本不可用时尝试其他版本）
- 参考文献清理

### 3. LLM 分析 (paper_analyzer.py)

调用 LLM 对论文进行深度分析，输出结构化的分析结果。

```bash
# 分析前 5 条
python scripts/arxiv_analyzer.py results/content_test.json -n 5

# 全量分析
python scripts/arxiv_analyzer.py results/content_test.json --full

# 指定输出路径
python scripts/arxiv_analyzer.py results/content_test.json -o results/analysis.json
```

**输出字段：**

| 字段 | 说明 |
|------|------|
| 中文摘要 | 300字以内的中文概括 |
| 核心亮点 | 3-5个 bullet points |
| 反直觉的发现 | 论文中出人意料的发现 |
| 论文的局限性/缺陷 | 不足和可改进之处 |
| 论文结论 | 作者的主要结论 |
| 研究动机/解决的问题 | 背景和动机 |
| 关键技术或方法 | 核心技术 |
| 实验结果摘要 | 实验设置和结果 |
| 适用场景/应用前景 | 实际应用价值 |
| 与相关工作的对比 | 横向对比 |

## 输出文件

### arxiv_results.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要...",
    "categories": ["cs.SD", "eess.AS"],
    "published_date": "2026-04-01",
    "html_url": "https://arxiv.org/abs/...",
    "pdf_url": "https://arxiv.org/pdf/..."
  }
]
```

### content_test.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "content": "论文全文内容...",
    "html_url": "https://arxiv.org/html/...",
    "content_source": "html",
    "used_arxiv_id": "2604.01155v1"
  }
]
```

### *_analysis.json

```json
[
  {
    "arxiv_id": "2604.01155v1",
    "title": "论文标题",
    "analysis": {
      "中文摘要": "...",
      "核心亮点": ["...", "..."],
      "反直觉的发现": "...",
      "论文的局限性/缺陷": "...",
      "论文结论": "...",
      "研究动机/解决的问题": "...",
      "关键技术或方法": "...",
      "实验结果摘要": "...",
      "适用场景/应用前景": "...",
      "与相关工作的对比": "..."
    }
  }
]
```
