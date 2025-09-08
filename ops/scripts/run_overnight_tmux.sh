#!/usr/bin/env bash
set -euo pipefail
SESSION="alice_overnight"
tmux new-session -d -s "$SESSION" "make overnight-8h"
echo "[tmux] running in session $SESSION. Attach: tmux attach -t $SESSION"