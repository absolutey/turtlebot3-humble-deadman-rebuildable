#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ -f "$ROOT/install/setup.bash" ]] || {
    echo "[FAIL] not built; run ./rebuild.sh first"
    exit 1
}

set +u
source /opt/ros/humble/setup.bash
source "$ROOT/install/setup.bash"
set -u

export TURTLEBOT3_MODEL=burger

exec ros2 launch \
    tb3_deadman_teleop \
    hostsafe_fake_deadman.launch.py
