# arxiv_paper_expert_liang

面向中文自然语言的 arXiv 论文研究与简报生成技能。

## 功能

- 按主题、时间范围抓取 arXiv 论文
- 自动将论文分为三类：Frontend（语音前端）、Backend（语音后端）、AudioLLM（音频大模型）
- 支持 JSON/CSV 格式输出
- 自动重试与速率限制处理

## 目录结构

```
scripts/
├── arxiv_fetch.py    # 论文抓取主脚本
results/              # 输出结果目录
config.json           # 默认配置文件
config_frontend.json  # Frontend 专用配置
config_backend.json   # Backend 专用配置
SKILL.md             # Cursor Skill 定义
```

## 快速开始

```bash
# 安装依赖
pip install requests feedparser beautifulsoup4

# 使用默认配置（搜索语音前端相关论文，2025-01-01 ~ 2026-04-01）
python scripts/arxiv_fetch.py

# 指定时间范围（2026 Q1）
python scripts/arxiv_fetch.py --start-date 2026-01-01 --end-date 2026-03-31 --max-results 600 --split

# 自定义主题
python scripts/arxiv_fetch.py --topic "diffusion model for speech" --start-date 2026-01-01 --end-date 2026-03-31
```

## 输出说明

使用 `--split` 参数时，输出三个文件：

- `results/*_frontend.json` — 语音前端：增强、分离、波束形成、去混响等
- `results/*_backend.json` — 语音后端：ASR、TTS、说话人识别、情感分析等
- `results/*_audiollm.json` — 音频大模型：LLM 用于语音/音频任务

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ARXIV_API_BASE` | `http://export.arxiv.org/api/query` | arXiv API 地址 |
| `ARXIV_CACHE_DIR` | `./cache` | 缓存目录 |
