#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

mkdir -p "$REPLAY_OUTPUT_DIR"

ARGS=(
  paper-replay
  --db "$TRADING_DB"
  --start "$REPLAY_START"
  --end "$REPLAY_END"
  --account-id "$REPLAY_ACCOUNT_ID"
  --account-name "$REPLAY_ACCOUNT_NAME"
  --source-name "$REPLAY_SOURCE_NAME"
  --account-output "$REPLAY_OUTPUT_DIR/simulationAccount.json"
  --data-status-output "$REPLAY_OUTPUT_DIR/dataStatus.json"
  --stock-pool-output "$REPLAY_OUTPUT_DIR/stockPool.json"
  --signal-output "$REPLAY_OUTPUT_DIR/signalReport.json"
  --market-risk-output "$REPLAY_OUTPUT_DIR/marketRisk.json"
  --simulation-output "$REPLAY_OUTPUT_DIR/simulationReport.json"
  --news-output "$REPLAY_OUTPUT_DIR/newsReport.json"
  --run-log-output "$REPLAY_OUTPUT_DIR/runLog.json"
)

if [[ "$REPLAY_RESET_ACCOUNT" != "0" ]]; then
  ARGS+=(--reset-account)
fi

cli "${ARGS[@]}"

if [[ "$REPLAY_EXPORT_FRONTEND" != "0" ]]; then
  mkdir -p "$REPLAY_FRONTEND_DIR"
  cp "$REPLAY_OUTPUT_DIR"/*.json "$REPLAY_FRONTEND_DIR"/
  echo "Frontend replay JSON refreshed: $REPLAY_FRONTEND_DIR"
fi

echo "Paper replay completed. Outputs: $REPLAY_OUTPUT_DIR"
