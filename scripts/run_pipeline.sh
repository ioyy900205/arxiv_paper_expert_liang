#!/bin/bash
# =============================================================================
# arxiv_paper_expert - 完整流水线
#
# 用途：自动化执行 arXiv 论文研究的完整流程
#       搜索 → 抓取全文 → LLM 分析 → 生成最终报告
#
# 用法：
#   bash scripts/run_pipeline.sh                    # 完整流程（使用 config.json 配置）
#   bash scripts/run_pipeline.sh --step fetch        # 仅搜索阶段
#   bash scripts/run_pipeline.sh --step content      # 仅抓取全文
#   bash scripts/run_pipeline.sh --step analyze      # 仅 LLM 分析
#   bash scripts/run_pipeline.sh --step all          # 完整流程
#   bash scripts/run_pipeline.sh -n 10               # 分析前 10 篇
#   bash scripts/run_pipeline.sh --resume            # 断点续传（跳过已分析）
#
# 依赖：
#   pip install -r requirements.txt
#   # 或
#   pip install requests feedparser beautifulsoup4 pdfminer.six openai
#
# 配置：config.json
# =============================================================================

set -euo pipefail

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 默认配置
STEP="${STEP:-all}"           # all | fetch | content | analyze
LIMIT="${LIMIT:-3}"           # 分析的论文数量（默认 3，--full 时忽略）
CONCURRENCY="${CONCURRENCY:-5}"  # LLM 并发数
DELAY="${DELAY:-1.0}"         # 请求间隔（秒）
RESUME="${RESUME:-false}"     # 断点续传
DAYS="${DAYS:-7}"             # 搜索最近 N 天

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --step)
            STEP="$2"
            shift 2
            ;;
        -n|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -c|--concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --resume)
            RESUME="true"
            shift
            ;;
        --full)
            LIMIT="full"
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --step <stage>    执行阶段: all|fetch|content|analyze|report"
            echo "  -n <num>          分析论文数量（默认 3）"
            echo "  --full            分析全部论文"
            echo "  -c <num>          LLM 并发数（默认 5）"
            echo "  --delay <sec>     请求间隔（默认 1.0 秒）"
            echo "  --days <num>      搜索最近 N 天论文（默认 7）"
            echo "  --resume          断点续传"
            echo "  --help, -h        显示此帮助"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# 辅助函数
# =============================================================================

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

separator() {
    echo ""
    echo "============================================"
    echo "$*"
    echo "============================================"
}

check_dependencies() {
    log "检查依赖..."
    local missing=()
    # 注意：beautifulsoup4 的导入名是 bs4
    local pkg_map="beautifulsoup4:bs4:pdfminer.six:pdfminer"
    for pkg in requests feedparser bs4 pdfminer openai; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            # 映射回显示名
            case $pkg in
                bs4) missing+=("beautifulsoup4") ;;
                pdfminer) missing+=("pdfminer.six") ;;
                *) missing+=("$pkg") ;;
            esac
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "缺少依赖: ${missing[*]}"
        echo "请运行: pip install ${missing[*]}"
        exit 1
    fi
    log "依赖检查通过"
}

# =============================================================================
# 阶段 1: 搜索论文
# =============================================================================

run_fetch() {
    separator "阶段 1: 搜索论文（最近 $DAYS 天）"

    # 检查 config.json 是否存在
    if [[ ! -f config.json ]]; then
        echo "错误: config.json 不存在"
        echo "请先创建 config.json，参考 README.md 中的配置示例"
        exit 1
    fi

    log "执行 arxiv_fetch.py..."
    python3 scripts/arxiv_fetch.py --days "$DAYS"

    local results_file="results/arxiv_results.json"
    if [[ -f $results_file ]]; then
        local count=$(python3 -c "import json; print(len(json.load(open('$results_file'))))")
        log "搜索完成: $count 篇论文保存到 $results_file"
    fi
}

# =============================================================================
# 阶段 2: 抓取全文
# =============================================================================

run_content() {
    separator "阶段 2: 抓取论文全文"

    local input_file="results/arxiv_results.json"

    if [[ ! -f $input_file ]]; then
        echo "错误: $input_file 不存在，请先运行搜索阶段"
        exit 1
    fi

    # 计算可用论文数量
    local total=$(python3 -c "import json; print(len(json.load(open('$input_file'))))")
    log "待处理论文: $total 篇"

    log "执行 arxiv_content.py（抓取全文）..."
    python3 scripts/arxiv_content.py "$input_file" --full --delay 3.0

    local output_file="${input_file%.json}_content.json"
    if [[ -f $output_file ]]; then
        local count=$(python3 -c "import json; print(len(json.load(open('$output_file'))))")
        local with_content=$(python3 -c "import json; print(sum(1 for p in json.load(open('$output_file')) if p.get('content')))")
        log "全文抓取完成: $count 篇（$with_content 篇有正文内容）"
    fi
}

# =============================================================================
# 阶段 3: LLM 分析
# =============================================================================

run_analyze() {
    separator "阶段 3: LLM 分析论文"

    local input_file="results/arxiv_results_content.json"

    if [[ ! -f $input_file ]]; then
        echo "错误: 未找到内容文件: $input_file"
        echo "请先运行全文抓取阶段，生成与本次搜索对应的 content 文件"
        exit 1
    fi

    # 计算可用论文数量
    local total=$(python3 -c "import json; print(len(json.load(open('$input_file'))))")
    local with_content=$(python3 -c "import json; print(sum(1 for p in json.load(open('$input_file')) if p.get('content')))")
    log "待分析论文: $total 篇（$with_content 篇有正文内容）"

    # 确定分析数量
    local analyze_cmd=""
    if [[ "$LIMIT" == "full" ]]; then
        analyze_cmd="--full"
        log "将分析全部论文（--full）"
    else
        analyze_cmd="-n $LIMIT"
        log "将分析前 $LIMIT 篇论文"
    fi

    # 确定输出文件（与 results/arxiv_results_content.json 对应）
    local output_file="results/arxiv_results_content_analysis.json"

    log "执行 paper_analyzer.py..."
    log "输出文件: $output_file"

    python3 scripts/paper_analyzer.py "$input_file" \
        -o "$output_file" \
        $analyze_cmd \
        -c "$CONCURRENCY" \
        --delay "$DELAY"

    if [[ -f $output_file ]]; then
        local count=$(python3 -c "import json; print(len(json.load(open('$output_file'))))")
        local success=$(python3 -c "import json; print(sum(1 for p in json.load(open('$output_file')) if not p.get('error')))")
        log "LLM 分析完成: $count 篇（$success 篇成功）"
        log "结果保存在: $output_file"
    fi
}

# =============================================================================
# 断点续传模式
# =============================================================================

run_resume() {
    separator "断点续传模式"

    local input_file="results/arxiv_results_content.json"
    local latest_analysis="results/arxiv_results_content_analysis.json"

    if [[ ! -f $input_file ]]; then
        echo "错误: $input_file 不存在"
        exit 1
    fi

    if [[ ! -f "$latest_analysis" ]]; then
        echo "错误: 未找到历史分析文件: $latest_analysis"
        echo "请先运行一次完整分析"
        exit 1
    fi

    local count=$(python3 -c "import json; print(len(json.load(open('$latest_analysis'))))")
    log "找到历史分析: $latest_analysis ($count 篇)"

    # 确定分析数量
    local analyze_cmd=""
    if [[ "$LIMIT" == "full" ]]; then
        analyze_cmd="--full"
    else
        analyze_cmd="-n $LIMIT"
    fi

    log "执行 paper_analyzer.py（断点续传）..."
    python3 scripts/paper_analyzer.py "$input_file" \
        -o "$latest_analysis" \
        $analyze_cmd \
        -c "$CONCURRENCY" \
        --delay "$DELAY"
}

# =============================================================================
# 阶段 4: 生成报告
# =============================================================================

run_report() {
    separator "阶段 4: 生成分析报告"

    local analysis_file="results/arxiv_results_content_analysis.json"

    if [[ ! -f "$analysis_file" ]]; then
        echo "错误: 未找到分析结果文件: $analysis_file"
        echo "请先运行 LLM 分析阶段"
        exit 1
    fi

    log "执行 generate_report.py..."
    log "输入文件: $analysis_file"

    python3 scripts/generate_report.py "$analysis_file"

    log "报告生成完成"
}

# =============================================================================
# 主流程
# =============================================================================

main() {
    log "开始 arXiv 论文研究流水线"
    log "配置: STEP=$STEP, LIMIT=$LIMIT, CONCURRENCY=$CONCURRENCY, DELAY=$DELAY"

    check_dependencies

    case "$STEP" in
        all)
            run_fetch
            run_content
            run_analyze
            run_report
            ;;
        fetch)
            run_fetch
            ;;
        content)
            run_content
            ;;
        analyze)
            if [[ "$RESUME" == "true" ]]; then
                run_resume
            else
                run_analyze
            fi
            ;;
        report)
            run_report
            ;;
        *)
            echo "错误: 未知的步骤 '$STEP'"
            echo "可用选项: all, fetch, content, analyze, report"
            exit 1
            ;;
    esac

    separator "流水线完成"
    log "所有任务已完成"
}

main "$@"
