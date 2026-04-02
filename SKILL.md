---
name: arxiv-paper-expert
description: 面向中文自然语言的语音与音频深度学习 arXiv 论文检索、整理、分析与简报生成技能。用于处理“最近几天语音有什么新论文”“帮我整理 speech/audio/TTS/ASR/语音增强/语音分离/说话人/AudioLLM 方向论文”“给我一版最近语音论文的浓缩总结”这类请求；适合围绕 speech、audio、voice、TTS、ASR、speech enhancement、speech separation、speaker、audio deepfake、audio language model 等主题，执行搜索、全文抓取、LLM 分析、Markdown/HTML 报告生成，以及执行后摘要回复。
---

# arxiv-paper-expert

用于整理**语音相关深度学习论文**，尤其是最近几天 / 最近一周 / 指定时间范围内的 arXiv 新论文。

## 典型触发

- 帮我看最近几天语音有什么新论文
- 帮我整理最近一周 speech / audio / TTS / ASR 论文
- 最近 AudioLLM 有什么新工作
- 帮我生成一版语音论文简报
- 把这批语音相关论文做成 HTML 和 Markdown

## 默认范围

优先把这个 skill 理解为：**语音、音频、说话人、语音生成、语音理解、AudioLLM 相关深度学习论文整理器**。

常见主题包括：
- speech
- audio
- voice
- TTS / text-to-speech
- ASR / speech recognition
- speech enhancement
- speech separation
- speaker / diarization / verification
- audio deepfake
- audio language model / speech LLM

## 执行流程

按下面顺序执行：

1. **搜索论文**
   - 默认使用 `scripts/run_pipeline.sh`
   - 典型命令：`bash scripts/run_pipeline.sh --step all --days 3 --full`
   - 若只需搜索：`bash scripts/run_pipeline.sh --step fetch --days 7`

2. **抓取全文**
   - 默认读取：`results/arxiv_results.json`
   - 生成：`results/arxiv_results_content.json`

3. **做 LLM 分析**
   - 默认读取：`results/arxiv_results_content.json`
   - 生成：`results/arxiv_results_content_analysis.json`

4. **生成报告**
   - 默认读取：`results/arxiv_results_content_analysis.json`
   - 生成：
     - `results/arxiv_results_content_report.md`
     - `results/arxiv_results_content_report.html`

5. **执行后必须收尾**
   - 读取本次新生成的 Markdown 报告
   - 提炼一版可直接发送给用户的浓缩总结
   - 附上自己的简短评价
   - 通过消息告知用户，不要只说“文件已生成”

## 执行后默认回复模板

完成一次标准执行后，默认按下面结构回复，除非用户明确要求别的格式：

```markdown
已完成最近 N 天 / 指定时间范围的语音相关论文整理。

**产出文件**
- Markdown: `results/arxiv_results_content_report.md`
- HTML: `results/arxiv_results_content_report.html`

**本次范围**
- 时间范围：...
- 论文总数：...
- 分类分布：frontend X / backend Y / audiollm Z

**浓缩版结论**
- 最值得优先看的 3-5 篇：...
- 这一批论文的共同趋势：...
- 哪些更偏方法创新，哪些更偏工程整合：...

**我的评价**
- 用 3-6 句话给出判断，不要只复述报告内容。
- 可以直接说：这批论文整体偏扎实 / 偏热闹 / 偏生成 / 偏安全 / 偏工程。
- 如果有明显最值得追踪的方向，也直接点出来。
```

回复风格要求：
- 先给结果，再给判断
- 默认简洁，不写流水账
- 不要只说“文件已生成”
- 尽量给出明确偏好和取舍，而不是平均用力地罗列

## “最值得看”默认筛选标准

当你需要从一批论文里挑出“最值得优先看”的 3-5 篇时，默认按下面标准排序和判断：

### 优先项

- **方法新意优先于纯工程堆料**
  - 如果一篇论文只是把已有模块重新拼装、主要靠堆参数、堆数据或堆训练技巧提分，应降低优先级
  - 如果一篇论文提出了新的问题建模方式、结构设计、训练视角、分析框架或评估思路，应提高优先级

- **跨方向迁移价值高的优先**
  - 不只看它在单一 benchmark 上是否有效，还要看它的方法能否迁移到其他语音任务、音频任务或多模态任务
  - 对 speech / audio / AudioLLM / 安全 / 生成 / 表征学习都可能有启发的方法，应优先推荐

- **对语音主线问题有结构性推进的优先**
  - 例如在 ASR、TTS、增强、分离、说话人建模、音频理解、音频安全等主线问题上，给出了明确的结构改进或范式改进
  - 如果只是对已有主线做边角优化，优先级应更低

### 降权项

- **单纯刷指标但缺少洞察的降权**
  - 如果论文主要卖点只是“某个 benchmark 上又涨了几点”，但看不出为什么有效、也没有新的分析或可迁移的设计，应降权
  - 如果实验做得很满但核心思想薄弱，也不要因为表格好看就优先推荐

### 结果表达要求

在给“最值得看”推荐时，不要只列标题。要顺带说明：
- 为什么它值得优先看
- 它更偏方法创新、结构创新、问题定义创新，还是只是工程整合
- 它是否可能影响其他方向，而不只是当前子任务

## 输出与覆盖规则

默认输出都写入 `results/`，并且**直接覆盖同名文件**：

- `results/arxiv_results.json`
- `results/arxiv_results_content.json`
- `results/arxiv_results_content_analysis.json`
- `results/arxiv_results_content_report.md`
- `results/arxiv_results_content_report.html`

含义：
- 下次执行会覆盖这次结果
- 对于“最近 N 天”的滚动追踪，这是合理默认行为
- 如果需要保留历史快照，应手动另存一份

## 关键脚本

- `scripts/arxiv_fetch.py`：搜索论文
- `scripts/arxiv_content.py`：抓取全文（HTML 优先，PDF 回退）
- `scripts/paper_analyzer.py`：LLM 分析
- `scripts/generate_report.py`：生成 Markdown / HTML 报告
- `scripts/run_pipeline.sh`：串联完整流程

## 注意事项

- 默认优先给用户一版**浓缩摘要 + 个人评价**，文件路径放在前面或后面都可以
- 如果用户明确只要文件，再简化回复
- 如果分析阶段发现旧文件干扰，应坚持使用本次流程生成的 `results/arxiv_results_content*.json`
- 如果用户问“下次会不会覆盖结果”，答案是：**会，默认覆盖同名 results 文件**
