#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ -f "$ROOT/install/setup.bash" ]] || {
    echo "[FAIL] install/setup.bash missing; run ./rebuild.sh first"
    exit 1
}

set +u
source /opt/ros/humble/setup.bash
source "$ROOT/install/setup.bash"
set -u

export TURTLEBOT3_MODEL=burger

echo "============================================================"
echo " TURTLEBOT3 REBUILDABLE SOURCE VERIFY"
echo "============================================================"

FAIL=0

for pkg in \
    turtlebot3_msgs \
    turtlebot3_description \
    turtlebot3_node \
    turtlebot3_bringup \
    turtlebot3_teleop \
    turtlebot3_fake_node \
    tb3_deadman_teleop
do
    prefix="$(ros2 pkg prefix "$pkg" 2>/dev/null || true)"

    if [[ -n "$prefix" ]]; then
        echo "[PASS] $pkg -> $prefix"
    else
        echo "[FAIL] $pkg"
        FAIL=1
    fi
done

if ros2 pkg executables tb3_deadman_teleop \
    | grep -qE '^tb3_deadman_teleop[[:space:]]+deadman_teleop$'
then
    echo "[PASS] deadman executable"
else
    echo "[FAIL] deadman executable"
    FAIL=1
fi

share="$(ros2 pkg prefix tb3_deadman_teleop --share)"

for file in \
    "$share/launch/hostsafe_fake_deadman.launch.py" \
    "$share/rviz/tb3_deadman.rviz"
do
    if [[ -f "$file" ]]; then
        echo "[PASS] $file"
    else
        echo "[FAIL] missing: $file"
        FAIL=1
    fi
done

python3 -m py_compile \
    "$ROOT/src/custom/tb3_deadman_teleop/tb3_deadman_teleop/deadman_teleop.py"

echo "[PASS] Python syntax"

if grep -qE '^[[:space:]]*Keep:[[:space:]]*1[[:space:]]*$' \
    "$ROOT/src/custom/tb3_deadman_teleop/rviz/tb3_deadman.rviz"
then
    echo "[PASS] RViz Odometry Keep=1 present"
else
    echo "[FAIL] RViz Keep=1 not found"
    FAIL=1
fi

echo

if [[ "$FAIL" -eq 0 ]]; then
    echo "[PASS] REBUILDABLE TURTLEBOT3 BASIC SOURCE"
else
    echo "[FAIL] SOURCE VERIFY"
    exit 1
fi
