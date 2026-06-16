# Real Data Smoke

阶段 G 用于验证真实 BaoStock 数据链路是否端到端可跑。默认输出到 `data/real_smoke/`，不会覆盖前端 `src/data/`。

## 运行

```bash
./scripts/run_baostock_smoke.sh
```

默认参数：

```text
SMOKE_START=2024-01-01
SMOKE_END=2024-03-29
SMOKE_MAX_CODES=5
SMOKE_CODE_OFFSET=0
SMOKE_DB=data/real_smoke/baostock_smoke.sqlite
SMOKE_ACCOUNT_ID=paper-real-smoke
```

可覆盖：

```bash
SMOKE_START=2024-01-01 SMOKE_END=2024-06-28 SMOKE_MAX_CODES=10 ./scripts/run_baostock_smoke.sh
```

如果 30 只以上同步遇到 BaoStock 网络超时，按批次跑：

```bash
SMOKE_MAX_CODES=10 SMOKE_CODE_OFFSET=0 ./scripts/run_baostock_smoke.sh
SMOKE_MAX_CODES=10 SMOKE_CODE_OFFSET=10 ./scripts/run_baostock_smoke.sh
SMOKE_MAX_CODES=10 SMOKE_CODE_OFFSET=20 ./scripts/run_baostock_smoke.sh
```

## 输出

```text
data/real_smoke/baostock_smoke.sqlite
data/real_smoke/dataStatus.json
data/real_smoke/stockPool.json
data/real_smoke/signalReport.json
data/real_smoke/marketRisk.json
data/real_smoke/simulationReport.json
data/real_smoke/simulationAccount.json
data/real_smoke/runLog.json
data/real_smoke/summary.json
```

## 通过标准

- `runLog.json` 最新状态为 `success`
- `dataStatus.json` 的 `qualityIssueCount` 为 0
- `dataStatus.json` 的 `coverageRate` 接近或等于 100%
- `dataStatus.json` 的 `missingBarCount` 为 0，或能解释为停牌/退市/数据源缺失
- `daily_bar` 有真实记录
- `stockPool.json` 有股票池记录
- `simulationAccount.json` 能正常生成

## 提升到前端展示

确认 smoke 结果没问题后，可以用正式脚本更新 `src/data/`：

```bash
PAPER_SOURCE=baostock PAPER_START=2024-01-01 PAPER_END=2024-03-29 PAPER_MAX_CODES=5 ./scripts/run_paper_daily.sh
```
