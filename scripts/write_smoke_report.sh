#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

mkdir -p "$SMOKE_OUTPUT_DIR"

python3 - <<'PY'
import json
from pathlib import Path

root = Path("data/real_smoke")
out = Path("docs/real_data_smoke_result.md")

def load(name):
    return json.loads((root / name).read_text(encoding="utf-8"))

summary = load("summary.json")
status = load("dataStatus.json")
signals = load("signalReport.json")
risk = load("marketRisk.json")
account = load("simulationAccount.json")
run_log = load("runLog.json")

tables = {item["table"]: item for item in status["tables"]}
lines = [
    "# Real Data Smoke Result",
    "",
    f"- 最新交易日: {summary['latestTradeDate']}",
    f"- 运行状态: {summary['latestRunStatus']}",
    f"- 数据质量问题: {summary['qualityIssueCount']}",
    f"- 覆盖股票数: {summary.get('barStockCount', 0)}",
    f"- 覆盖交易日: {summary.get('barTradeDayCount', 0)}",
    f"- 行情覆盖率: {summary.get('coverageRate', 0):.2%}",
    f"- 缺失行情: {summary.get('missingBarCount', 0)}",
    f"- 总记录数: {summary['totalRecords']}",
    f"- 日线记录: {tables.get('daily_bar', {}).get('recordCount', 0)}",
    f"- 股票池记录: {tables.get('stock_pool', {}).get('recordCount', 0)}",
    f"- 信号数量: {signals['summary']['signalCount']}",
    f"- 买入/观察: {signals['summary'].get('buyCount', 0)} / {signals['summary'].get('watchCount', 0)}",
    f"- 市场状态: {risk['market']['state']} ({risk['market']['score']}/5)",
    f"- 风控状态: {risk['risk']['state']}",
    f"- 账户: {account['account']['accountId']}",
    f"- 总资产: {account['account']['totalAsset']}",
    f"- 持仓数: {account['summary']['positionCount']}",
    f"- 订单/成交: {account['summary']['orderCount']} / {account['summary']['fillCount']}",
    "",
    "## Latest Run",
    "",
]

if run_log["runs"]:
    run = run_log["runs"][0]
    lines.extend([
        f"- workflow: {run['workflow']}",
        f"- source: {run['source']}",
        f"- startedAt: {run['startedAt']}",
        f"- durationMs: {run['durationMs']}",
        f"- error: {run['errorMessage'] or '--'}",
    ])

out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out)
PY
