#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

cli pipeline \
  --source sample \
  --data-dir "$SAMPLE_DATA_DIR" \
  --db "$TRADING_DB" \
  --output src/data/backtestResult.json \
  --stability-output src/data/stabilityReport.json \
  --portfolio-output src/data/portfolioReport.json \
  --account-id "$PAPER_ACCOUNT_ID" \
  --account-output src/data/simulationAccount.json \
  --data-status-output src/data/dataStatus.json \
  --stock-pool-output src/data/stockPool.json \
  --signal-output src/data/signalReport.json \
  --market-risk-output src/data/marketRisk.json \
  --simulation-output src/data/simulationReport.json \
  --news-output src/data/newsReport.json

cli run-log --db "$TRADING_DB" --output src/data/runLog.json

echo "Sample pipeline completed."
