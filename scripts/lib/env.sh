#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LOCAL_NODE_DIR=""
if compgen -G "$ROOT_DIR/.tools/node-*/bin" > /dev/null; then
  LOCAL_NODE_DIR="$(find "$ROOT_DIR/.tools" -maxdepth 2 -type d -path "*/bin" | sort | tail -n 1)"
  export PATH="$LOCAL_NODE_DIR:$PATH"
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

TRADING_DB="${TRADING_DB:-data/trading.sqlite}"
SAMPLE_DATA_DIR="${SAMPLE_DATA_DIR:-backend/sample_data}"
UNIVERSE_FILE="${UNIVERSE_FILE:-config/universe_core.csv}"
BACKTEST_START="${BACKTEST_START:-2025-01-01}"
BACKTEST_END="${BACKTEST_END:-}"
PAPER_ACCOUNT_ID="${PAPER_ACCOUNT_ID:-paper-main}"
PAPER_ACCOUNT_NAME="${PAPER_ACCOUNT_NAME:-模拟盘主账户}"
PAPER_MAX_CODES="${PAPER_MAX_CODES:-30}"
PAPER_SOURCE="${PAPER_SOURCE:-baostock}"
PAPER_RETRY="${PAPER_RETRY:-2}"
PAPER_INCREMENTAL="${PAPER_INCREMENTAL:-1}"
REPLAY_OUTPUT_DIR="${REPLAY_OUTPUT_DIR:-data/paper_replay}"
REPLAY_FRONTEND_DIR="${REPLAY_FRONTEND_DIR:-src/data/paperReplay}"
REPLAY_START="${REPLAY_START:-2024-03-25}"
REPLAY_END="${REPLAY_END:-2024-03-29}"
REPLAY_ACCOUNT_ID="${REPLAY_ACCOUNT_ID:-paper-replay}"
REPLAY_ACCOUNT_NAME="${REPLAY_ACCOUNT_NAME:-模拟盘回放账户}"
REPLAY_RESET_ACCOUNT="${REPLAY_RESET_ACCOUNT:-1}"
REPLAY_SOURCE_NAME="${REPLAY_SOURCE_NAME:-Replay}"
REPLAY_EXPORT_FRONTEND="${REPLAY_EXPORT_FRONTEND:-1}"
SMOKE_DB="${SMOKE_DB:-data/real_smoke/baostock_smoke.sqlite}"
SMOKE_OUTPUT_DIR="${SMOKE_OUTPUT_DIR:-data/real_smoke}"
SMOKE_START="${SMOKE_START:-2024-01-01}"
SMOKE_END="${SMOKE_END:-2024-03-29}"
SMOKE_MAX_CODES="${SMOKE_MAX_CODES:-5}"
SMOKE_CODE_OFFSET="${SMOKE_CODE_OFFSET:-0}"
SMOKE_ACCOUNT_ID="${SMOKE_ACCOUNT_ID:-paper-real-smoke}"

FRONTEND_PORT="${FRONTEND_PORT:-5173}"

cli() {
  python3 -m trading_platform.cli.main "$@"
}
