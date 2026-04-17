#!/usr/bin/env bash
# 监控守护：崩溃自动重启，限制重启频率防止疯狂循环
# 用法: ./run_monitor.sh   (Ctrl+C 优雅退出)
# 日志: monitor.log  (滚动追加，重启分隔行可grep "=== restart")

set -u
cd "$(dirname "$0")"

LOG=monitor.log
RESTART_DELAY=5          # 崩溃后等待秒数再拉起
MAX_RESTARTS_PER_MIN=4   # 每分钟最多重启次数（防火灾）
PIDFILE=/tmp/realtime_pet_monitor.pid

trap 'echo "🛑 收到退出信号，杀子进程"; [[ -f $PIDFILE ]] && kill "$(cat $PIDFILE)" 2>/dev/null; rm -f $PIDFILE; exit 0' INT TERM

# 重启时间戳环形缓冲
declare -a RESTART_TS=()

restart_count_last_min() {
    local now=$1; local cnt=0
    local kept=()
    for ts in "${RESTART_TS[@]}"; do
        if (( now - ts < 60 )); then
            kept+=("$ts"); ((cnt++))
        fi
    done
    RESTART_TS=("${kept[@]}")
    echo $cnt
}

attempt=0
while true; do
    ((attempt++))
    now=$(date +%s)
    cnt=$(restart_count_last_min "$now")
    if (( cnt >= MAX_RESTARTS_PER_MIN )); then
        echo "❌ 1分钟内已重启${cnt}次，超过限制 ${MAX_RESTARTS_PER_MIN}，等待60s..." | tee -a "$LOG"
        sleep 60
        RESTART_TS=()
        continue
    fi

    {
        echo ""
        echo "=== restart #$attempt @ $(date '+%Y-%m-%d %H:%M:%S') ==="
    } >> "$LOG"
    echo "🚀 启动监控 (尝试 #$attempt)"

    python -u realtime_pet_monitor.py >> "$LOG" 2>&1 &
    child_pid=$!
    echo $child_pid > "$PIDFILE"
    wait $child_pid
    rc=$?
    rm -f "$PIDFILE"

    RESTART_TS+=("$(date +%s)")

    if (( rc == 0 )); then
        echo "✅ 监控正常退出 (rc=0)，停止守护" | tee -a "$LOG"
        break
    fi

    # 信号识别
    if (( rc >= 128 )); then
        sig=$((rc - 128))
        echo "⚠️ 监控异常退出 rc=$rc (signal $sig)，${RESTART_DELAY}s 后重启..." | tee -a "$LOG"
    else
        echo "⚠️ 监控异常退出 rc=$rc，${RESTART_DELAY}s 后重启..." | tee -a "$LOG"
    fi
    sleep $RESTART_DELAY
done
