#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

ARGS=(
  paper-pipeline
  --source "$PAPER_SOURCE"
  --db "$TRADING_DB"
  --universe-file "$UNIVERSE_FILE"
  --account-id "$PAPER_ACCOUNT_ID"
  --account-name "$PAPER_ACCOUNT_NAME"
  --account-output src/data/simulationAccount.json
  --data-status-output src/data/dataStatus.json
  --stock-pool-output src/data/stockPool.json
  --signal-output src/data/signalReport.json
  --market-risk-output src/data/marketRisk.json
  --simulation-output src/data/simulationReport.json
  --news-output src/data/newsReport.json
  --run-log-output src/data/runLog.json
)

if [[ "$PAPER_SOURCE" == "sample" ]]; then
  ARGS+=(--data-dir "$SAMPLE_DATA_DIR")
else
  ARGS+=(--retry "$PAPER_RETRY" --continue-on-error --max-codes "$PAPER_MAX_CODES")
  if [[ "$PAPER_INCREMENTAL" != "0" ]]; then
    ARGS+=(--incremental)
  fi
fi

if [[ -n "${PAPER_START:-}" ]]; then
  ARGS+=(--start "$PAPER_START")
elif [[ "$PAPER_SOURCE" != "sample" && -n "$BACKTEST_START" ]]; then
  ARGS+=(--start "$BACKTEST_START")
fi

if [[ -n "${PAPER_END:-}" ]]; then
  ARGS+=(--end "$PAPER_END")
elif [[ -n "$BACKTEST_END" ]]; then
  ARGS+=(--end "$BACKTEST_END")
fi

if [[ -n "${PAPER_TRADE_DATE:-}" ]]; then
  ARGS+=(--trade-date "$PAPER_TRADE_DATE")
fi

if [[ -n "${PAPER_CODES:-}" ]]; then
  ARGS+=(--codes "$PAPER_CODES")
fi

cli "${ARGS[@]}"

echo "Paper daily pipeline completed."
