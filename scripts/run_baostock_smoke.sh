#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

mkdir -p "$SMOKE_OUTPUT_DIR"

cli paper-pipeline \
  --source baostock \
  --db "$SMOKE_DB" \
  --start "$SMOKE_START" \
  --end "$SMOKE_END" \
  --trade-date "$SMOKE_END" \
  --universe-file "$UNIVERSE_FILE" \
  --code-offset "$SMOKE_CODE_OFFSET" \
  --max-codes "$SMOKE_MAX_CODES" \
  --retry "$PAPER_RETRY" \
  --continue-on-error \
  --account-id "$SMOKE_ACCOUNT_ID" \
  --account-name "真实数据烟测账户" \
  --account-output "$SMOKE_OUTPUT_DIR/simulationAccount.json" \
  --data-status-output "$SMOKE_OUTPUT_DIR/dataStatus.json" \
  --stock-pool-output "$SMOKE_OUTPUT_DIR/stockPool.json" \
  --signal-output "$SMOKE_OUTPUT_DIR/signalReport.json" \
  --market-risk-output "$SMOKE_OUTPUT_DIR/marketRisk.json" \
  --simulation-output "$SMOKE_OUTPUT_DIR/simulationReport.json" \
  --news-output "$SMOKE_OUTPUT_DIR/newsReport.json" \
  --run-log-output "$SMOKE_OUTPUT_DIR/runLog.json"

python3 - <<'PY'
import json
from pathlib import Path

root = Path("data/real_smoke")
status = json.loads((root / "dataStatus.json").read_text(encoding="utf-8"))
account = json.loads((root / "simulationAccount.json").read_text(encoding="utf-8"))
signals = json.loads((root / "signalReport.json").read_text(encoding="utf-8"))
run_log = json.loads((root / "runLog.json").read_text(encoding="utf-8"))

summary = {
    "latestTradeDate": status["summary"]["latestTradeDate"],
    "totalRecords": status["summary"]["totalRecords"],
    "qualityIssueCount": status["summary"]["qualityIssueCount"],
    "barStockCount": status["summary"].get("barStockCount", 0),
    "barTradeDayCount": status["summary"].get("barTradeDayCount", 0),
    "expectedBarCount": status["summary"].get("expectedBarCount", 0),
    "actualBarCount": status["summary"].get("actualBarCount", 0),
    "missingBarCount": status["summary"].get("missingBarCount", 0),
    "coverageRate": status["summary"].get("coverageRate", 0),
    "signalCount": signals["summary"]["signalCount"],
    "accountId": account["account"]["accountId"],
    "totalAsset": account["account"]["totalAsset"],
    "positionCount": account["summary"]["positionCount"],
    "latestRunStatus": run_log["summary"]["latestStatus"],
}
(root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY

echo "BaoStock smoke completed. Outputs: $SMOKE_OUTPUT_DIR"
