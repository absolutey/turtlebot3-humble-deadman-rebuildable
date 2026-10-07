#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

LOG="$(mktemp)"
PID=""

cleanup()
{
    if [[ -n "$PID" ]] \
       && [[ -d "/proc/$PID" ]]
    then
        kill -KILL "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi

    rm -f "$LOG"
}

trap cleanup EXIT

[[ -f "$ROOT/install/setup.bash" ]] || {
    echo "[FAIL] repository is not built"
    exit 1
}

set +u
source /opt/ros/humble/setup.bash
source "$ROOT/install/setup.bash"
set -u

export TURTLEBOT3_MODEL=burger
export QT_QPA_PLATFORM=offscreen

EXE="$(
    ros2 pkg prefix tb3_deadman_teleop
)/lib/tb3_deadman_teleop/deadman_teleop"

[[ -x "$EXE" ]] || {
    echo "[FAIL] executable missing: $EXE"
    exit 1
}

is_live_non_zombie()
{
    local pid="$1"
    local stat

    [[ -r "/proc/$pid/stat" ]] || return 1

    stat="$(
        awk '{print $3}' "/proc/$pid/stat" 2>/dev/null \
        || true
    )"

    [[ -n "$stat" ]] || return 1
    [[ "$stat" != "Z" ]]
}

echo "============================================================"
echo " DEAD-MAN TRUE ONE-SHOT LIFECYCLE TEST"
echo "============================================================"

"$EXE" >"$LOG" 2>&1 &
PID=$!

for second in 1 2 3; do
    sleep 1

    if ! is_live_non_zombie "$PID"; then
        echo "[FAIL] premature startup exit"
        echo "before_seconds=$second"
        cat "$LOG"
        exit 1
    fi
done

echo "[PASS] stays alive for >=3 seconds"

START_NS="$(date +%s%N)"

kill -INT "$PID"

EXITED=0

for _ in $(seq 1 20); do
    if ! is_live_non_zombie "$PID"; then
        EXITED=1
        break
    fi

    sleep 0.1
done

END_NS="$(date +%s%N)"

if [[ "$EXITED" -ne 1 ]]; then
    echo "[FAIL] did not exit within 2 seconds after one SIGINT"
    echo
    cat "$LOG"
    exit 1
fi

set +e
wait "$PID"
RC=$?
set -e

PID=""

ELAPSED_MS="$(
    python3 - "$START_NS" "$END_NS" <<'PY'
import sys

start = int(sys.argv[1])
end = int(sys.argv[2])

print(
    (end - start) // 1_000_000
)
PY
)"

BAD="$(
    grep -E \
        'RCLError|publisher.s context is invalid|Traceback|SIGKILL' \
        "$LOG" \
        || true
)"

if [[ -n "$BAD" ]]; then
    echo "[FAIL] lifecycle error found in output"
    echo "$BAD"
    echo
    cat "$LOG"
    exit 1
fi

echo "[PASS] exactly one SIGINT accepted"
echo "[PASS] exit <=2 seconds"
echo "[PASS] no RCLError"
echo "[PASS] no traceback"
echo "[PASS] no SIGKILL escalation"
echo "shutdown_ms=$ELAPSED_MS"
echo "exit_code=$RC"
echo
echo "[PASS] TRUE ONE-SHOT NODE SHUTDOWN"
