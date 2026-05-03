#!/usr/bin/env bash
# ════════════════════════════════════════════════════════
#  RAGStack — Unix/macOS one-click setup
#  Make executable: chmod +x setup.sh
#  Then run:        ./setup.sh
# ════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo " RAGStack Setup"
echo " ══════════════════════════════════════════════"
echo ""

# Prefer python3, fall back to python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo " ERROR: Python not found. Install Python 3.10+ from https://python.org"
    exit 1
fi

echo " Using: $($PYTHON --version)"
echo ""

"$PYTHON" "$SCRIPT_DIR/install.py" "$@"
