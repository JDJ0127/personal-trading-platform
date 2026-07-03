#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

cli data-status --db "$TRADING_DB" --output src/data/dataStatus.json --source-name "${PAPER_SOURCE:-BaoStock}"
cli simulation-account --db "$TRADING_DB" --account-id "$PAPER_ACCOUNT_ID" --output src/data/simulationAccount.json
cli simulation-plan --db "$TRADING_DB" --account-id "$PAPER_ACCOUNT_ID" --output src/data/simulationReport.json
cli run-log --db "$TRADING_DB" --output src/data/runLog.json

TRADE_DATE="$(python3 - <<'PY'
import json
from pathlib import Path
path = Path("src/data/dataStatus.json")
print(json.loads(path.read_text(encoding="utf-8"))["summary"]["latestTradeDate"] if path.exists() else "")
PY
)"

if [[ -n "$TRADE_DATE" && "${PAPER_SOURCE:-baostock}" == "baostock" ]]; then
  cli index-quotes --trade-date "$TRADE_DATE" --output src/data/indexQuotes.json --retry "$PAPER_RETRY"
fi

if [[ -n "$TRADE_DATE" ]]; then
  cli news-events --trade-date "$TRADE_DATE" --output src/data/newsReport.json
fi

echo "Frontend reports exported."
