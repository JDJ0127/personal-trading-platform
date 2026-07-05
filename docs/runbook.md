# Runbook

## 第一次运行

```bash
cp .env.example .env
./scripts/check_all.sh
./scripts/run_sample.sh
./scripts/start_frontend.sh
```

## 跑 BaoStock 模拟盘

先做小样本真实数据 smoke：

```bash
./scripts/run_baostock_smoke.sh
./scripts/write_smoke_report.sh
```

确认 `docs/real_data_smoke_result.md` 里状态为 `success` 后，再跑正式每日模拟盘：

```bash
PAPER_SOURCE=baostock ./scripts/run_paper_daily.sh
```

如果是首次同步，建议指定起始日期：

```bash
PAPER_SOURCE=baostock PAPER_START=2025-01-01 ./scripts/run_paper_daily.sh
```

需要快速验证链路时，显式关闭全市场并限制代码数量：

```bash
PAPER_SOURCE=baostock PAPER_ALL_STOCK=0 PAPER_MAX_CODES=30 ./scripts/run_paper_daily.sh
```

如果数据库已有行情，后续可直接增量：

```bash
PAPER_SOURCE=baostock ./scripts/run_paper_daily.sh
```

如果要重跑历史区间，关闭增量：

```bash
PAPER_INCREMENTAL=0 PAPER_START=2024-01-01 PAPER_END=2024-03-29 PAPER_TRADE_DATE=2024-03-29 ./scripts/run_paper_daily.sh
```

## 区间模拟盘回放

回放用于检查连续多日账户推进、权益曲线、订单计划和运行日志。它只复用数据库已有行情，不会联网同步：

```bash
TRADING_DB=data/baostock_frontend.sqlite REPLAY_START=2024-03-25 REPLAY_END=2024-03-29 ./scripts/run_paper_replay.sh
```

默认输出：

```text
data/paper_replay/simulationAccount.json
data/paper_replay/stockPool.json
data/paper_replay/signalReport.json
data/paper_replay/marketRisk.json
data/paper_replay/simulationReport.json
data/paper_replay/runLog.json
```

默认会同步到 `src/data/paperReplay/` 供前端“回放验证”页面展示。如果只想保留后端归档，不刷新前端回放页：

```bash
REPLAY_EXPORT_FRONTEND=0 ./scripts/run_paper_replay.sh
```

如果想保留同一回放账户的历史状态，设置：

```bash
REPLAY_RESET_ACCOUNT=0 ./scripts/run_paper_replay.sh
```

## 前端数据刷新

如果数据库已有数据，只想重新导出前端 JSON：

```bash
./scripts/export_reports.sh
```

数据中心会展示行情覆盖率、覆盖股票数、覆盖交易日、缺失行情数量。覆盖率低于预期时，先查看“缺失日期”和“缺失股票”，再决定是否重跑同步。

## 常见问题

### BaoStock 网络失败

使用重试和失败跳过：

```bash
PAPER_RETRY=3 ./scripts/run_paper_daily.sh
```

脚本默认会给 BaoStock 使用：

```text
--incremental --retry "$PAPER_RETRY" --continue-on-error
```

### 页面数据不是最新

先重新导出报告：

```bash
./scripts/export_reports.sh
```

再重启前端：

```bash
./scripts/start_frontend.sh
```

### 检查系统是否健康

```bash
./scripts/check_all.sh
```

### 查看运行日志

前端进入“报告日志”，或直接查看：

```bash
python3 -m json.tool src/data/runLog.json
```

回放日志默认查看：

```bash
python3 -m json.tool data/paper_replay/runLog.json
```

## 推荐日常流程

1. 开盘前或收盘后同步数据：

   ```bash
   ./scripts/run_paper_daily.sh
   ```

2. 启动前端查看：

   ```bash
   ./scripts/start_frontend.sh
   ```

3. 重点看：

   - 数据中心
   - 风控中心
   - 模拟交易
   - 持仓组合
   - 报告日志
