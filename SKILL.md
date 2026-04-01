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
├── search.py      # 搜索功能：按主题/分类/时间搜索论文
├── extractor.py   # 信息提取：从搜索结果中提取元信息
├── analyzer.py    # AI 分析：调用 anan_01 agent 分析论文
└── summarizer.py  # 总结生成：整合信息生成结构化简报
```

## 典型使用触发

- 帮我找一下最近有关 XXX 的论文
- 最近一周有什么新的 LLM 论文？
- 2024年3月份关于强化学习的论文
- 帮我搜搜这个领域最近的工作

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

### 3. 分析阶段（analyzer.py）

调用 OpenClaw anan_01 agent 进行深度分析。

### 4. 总结阶段（summarizer.py）

生成结构化简报，包含：
- 论文概览
- 主题分布
- 关键发现
- 技术趋势
