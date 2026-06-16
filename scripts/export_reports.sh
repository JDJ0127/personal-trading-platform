#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

cli data-status --db "$TRADING_DB" --output src/data/dataStatus.json --source-name "${PAPER_SOURCE:-BaoStock}"
cli simulation-account --db "$TRADING_DB" --account-id "$PAPER_ACCOUNT_ID" --output src/data/simulationAccount.json
cli simulation-plan --db "$TRADING_DB" --account-id "$PAPER_ACCOUNT_ID" --output src/data/simulationReport.json
cli run-log --db "$TRADING_DB" --output src/data/runLog.json

echo "Frontend reports exported."
