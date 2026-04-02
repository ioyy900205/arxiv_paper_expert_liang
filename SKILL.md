---
name: arxiv_paper_expert
description: 面向中文自然语言的 arXiv 论文研究技能。用于把"看看最近有什么新论文""帮我找一下某个主题的论文""最近一周 XX 领域有哪些新工作"这类请求，转成可执行的论文搜索、信息提取与简要分析流程。
author: liang
version: 0.1.0
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
  - name: ARXIV_CACHE_DIR
    default: ./cache
    description: 缓存目录
network_access: true
---

# arxiv_paper_expert

面向中文自然语言的 arXiv 论文研究与简报生成技能。

## What this skill is for

使用这个 skill 的典型场景：

- 找某个时间段内的某个主题论文 list
- 找某个时间点/时间段内某个领域的新论文
- 对一批论文做信息提取和整理
- 调用 AI（anan_01 agent）对论文做深度分析
- 生成结构化论文简报

## 模块架构

```
scripts/
├── arxiv_fetch.py       # 搜索功能：按主题/分类/时间搜索论文
├── arxiv_content.py     # 内容抓取：HTML 优先 + PDF 回退获取正文
├── paper_analyzer.py    # LLM 分析：调用 MiniMax API 分析论文
├── test_llm.py          # LLM 测试：快速验证 API Key 可用性
└── ...
```

## 典型使用触发

- 帮我找一下最近有关 XXX 的论文
- 最近一周有什么新的 LLM 论文？
- 2024年3月份关于强化学习的论文
- 帮我搜搜这个领域最近的工作
- 帮我分析一下这批论文（投喂给 LLM）
- 帮我生成论文简报

## 工作流程

### 1. 搜索阶段（search.py）

支持三种搜索方式：

| 方式 | 说明 | 实现 |
|------|------|------|
| 主题搜索 | 按关键词搜索 | arXiv API query 参数 |
| 分类浏览 | 按分类浏览最近论文 | 抓取 arxiv.org/list/{cat}/recent |
| 组合搜索 | 分类 + 关键词 + 时间 | API 参数组合 |

时间表达支持：
- 自然语言：`"最近一周"` → `(today-7, today)`
- 绝对日期：`"2024年3月"` → `(2024-03-01, 2024-03-31)`
- 时间窗口：`"2024年3月前后"` → `(2024-02-15, 2024-03-15)`

### 2. 提取阶段（extractor.py）

从搜索结果中提取：
- 标题 (title)
- 作者 (authors)
- 摘要 (abstract)
- 分类 (categories)
- 发表日期 (published)
- arXiv ID
- PDF 链接
- 更新日期 (updated)

### 2.1 内容抓取（arxiv_content.py）

通过 `arxiv_content.py` 获取论文全文，策略如下：

| 来源 | 优先级 | 备注 |
|------|--------|------|
| HTML 版本 | 高 | `https://arxiv.org/html/{id}` |
| PDF 版本 | 低（回退） | 当 HTML 不存在时自动使用 |

输出 JSON 每条记录增加三个字段：
- `content` — 正文纯文本
- `html_url` — 实际来源 URL（HTML 或 PDF）
- `content_source` — 来源标识（`html` / `pdf` / `none`）

正文末尾的参考文献节会被自动去除（通过关键词 `References`、`Bibliography`、`Acknowledgment` 检测）。

```bash
# 处理前 3 条
python scripts/arxiv_content.py results/arxiv_results.json

# 指定条数
python scripts/arxiv_content.py results/arxiv_results.json -n 10 -o results/content.json

# 全量处理
python scripts/arxiv_content.py results/arxiv_results.json --full
```

依赖：`pip install requests beautifulsoup4 pdfminer.six`

### 3. 分析阶段（paper_analyzer.py）

通过 `paper_analyzer.py` 调用 MiniMax LLM 对论文进行深度分析。

**配置：** 在 `config.json` 的 `llm` 节配置 API Key 和模型。

#### 分析模式

默认情况下所有类型都使用**详细分析**。

在 `config.json` 的 `analysis.type_modes` 配置：

```json
"analysis": {
  "default_mode": "detailed",
  "type_modes": {
    "frontend": "detailed",   // 语音前端：详细分析
    "backend": "concise",     // 语音后端：精简分析
    "audiollm": "concise"     // AudioLLM：精简分析
  }
}
```

#### 输出字段

**详细模式输出：**

| 字段 | 说明 |
|------|------|
| 一句话总结 | 300字以内的中文概括 |
| 核心亮点 | 3-5个 bullet points |
| 反直觉的发现 | 论文中出人意料的发现 |
| 论文的局限性/缺陷 | 不足和可改进之处 |
| 论文结论 | 作者的主要结论 |
| 研究动机/解决的问题 | 背景和动机 |
| 关键技术或方法 | 核心技术 |
| 实验结果摘要 | 实验设置和结果 |
| 适用场景/应用前景 | 实际应用价值 |
| 与相关工作的对比 | 横向对比 |

**精简模式输出：**

| 字段 | 说明 |
|------|------|
| 一句话总结 | 精辟、通俗的一句话概括 |

#### 使用示例

```bash
# 默认详细分析前 3 条
python scripts/paper_analyzer.py results/content_test.json

# 精简分析前 5 条（一句话总结）
python scripts/paper_analyzer.py results/content_test.json -n 5 --concise

# 全量精简分析
python scripts/paper_analyzer.py results/content_test.json --full --concise

# 按类型选择模式
python scripts/paper_analyzer.py results/content_test.json --type frontend  # 详细
python scripts/paper_analyzer.py results/content_test.json --type backend   # 精简

# 指定输出路径
python scripts/paper_analyzer.py results/content_test.json -o results/analysis.json

# 调整并发和间隔
python scripts/paper_analyzer.py results/content_test.json -n 10 -c 5 --delay 0.5

# 失败重试次数
python scripts/paper_analyzer.py results/content_test.json --max-retries 3
```

依赖：`pip install openai`

### 4. 总结阶段（summarizer.py）

生成结构化简报，包含：
- 论文概览
- 主题分布
- 关键发现
- 技术趋势
