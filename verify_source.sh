#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo " TURTLEBOT3 SOURCE INTEGRITY VERIFY"
echo "============================================================"

sha256sum -c SOURCE_SHA256.txt

if git ls-files | grep -E '(^|/)__pycache__/|\.py[co]$' >/dev/null; then
    echo "[FAIL] generated Python cache is tracked by Git"
    git ls-files | grep -E '(^|/)__pycache__/|\.py[co]$'
    exit 1
fi

echo "[PASS] source SHA256 manifest"
echo "[PASS] no tracked Python cache"
