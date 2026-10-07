#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo " TURTLEBOT3 HUMBLE — EXACT REBUILD"
echo "============================================================"

[[ -f /opt/ros/humble/setup.bash ]] || {
    echo "[FAIL] ROS 2 Humble not installed"
    exit 1
}

set +u
source /opt/ros/humble/setup.bash
set -u

export TURTLEBOT3_MODEL=burger

for cmd in git colcon rosdep python3; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "[FAIL] command missing: $cmd"
        exit 1
    }
done

# PyQt5 is needed for true key-release events.
if ! python3 - <<'PY' >/dev/null 2>&1
from PyQt5.QtWidgets import QApplication
PY
then
    echo "[INFO] installing python3-pyqt5"
    sudo apt-get update
    sudo apt-get install -y python3-pyqt5
fi

clone_locked()
{
    local name="$1"
    local line branch commit url dest actual

    line="$(
        awk -F '\t' -v name="$name" \
            'NR>1 && $1==name {print $0}' \
            UPSTREAM_LOCK.tsv
    )"

    [[ -n "$line" ]] || {
        echo "[FAIL] lock missing: $name"
        exit 1
    }

    branch="$(printf '%s\n' "$line" | cut -f2)"
    commit="$(printf '%s\n' "$line" | cut -f3)"
    url="$(printf '%s\n' "$line" | cut -f4)"
    dest="src/$name"

    if [[ ! -d "$dest/.git" ]]; then
        echo "[INFO] cloning $name"
        git clone --branch "$branch" "$url" "$dest"
    fi

    if [[ -n "$(git -C "$dest" status --porcelain)" ]]; then
        echo "[FAIL] local upstream tree is dirty: $dest"
        git -C "$dest" status --short
        exit 1
    fi

    git -C "$dest" fetch origin "$branch"
    git -C "$dest" checkout --detach "$commit"

    actual="$(git -C "$dest" rev-parse HEAD)"
    [[ "$actual" == "$commit" ]] || {
        echo "[FAIL] SHA mismatch: $name"
        exit 1
    }

    echo "[PASS] $name @ $commit"
}

clone_locked turtlebot3
clone_locked turtlebot3_msgs
clone_locked turtlebot3_simulations

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    echo
    echo "[FAIL] rosdep not initialized"
    echo "Run once:"
    echo "  sudo rosdep init"
    echo "  rosdep update"
    exit 1
fi

rosdep update

# Deliberately avoid turtlebot3_gazebo / Gazebo Classic dependencies.
rosdep install \
    --from-paths \
        src/turtlebot3_msgs \
        src/turtlebot3/turtlebot3_description \
        src/turtlebot3/turtlebot3_node \
        src/turtlebot3/turtlebot3_bringup \
        src/turtlebot3/turtlebot3_teleop \
        src/turtlebot3_simulations/turtlebot3_fake_node \
        src/custom/tb3_deadman_teleop \
    --ignore-src \
    --rosdistro humble \
    -r \
    -y

rm -rf build install log

colcon build \
    --symlink-install \
    --allow-overriding turtlebot3_msgs turtlebot3_node \
    --packages-select \
        turtlebot3_msgs \
        turtlebot3_description \
        turtlebot3_node \
        turtlebot3_bringup \
        turtlebot3_teleop \
        turtlebot3_fake_node \
        tb3_deadman_teleop

echo
echo "============================================================"
echo " BUILD COMPLETE"
echo "============================================================"
echo
echo "Next:"
echo "  ./verify.sh"
echo "  ./run.sh"
