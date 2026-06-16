# Personal Trading Platform

个人 A 股量化交易平台 MVP。1.0 目标是接入低成本真实数据，运行模拟盘，验证策略收益的可靠性和稳定性，不进行真实交易。

## 当前能力

- BaoStock 免费行情同步，支持增量、重试、单票失败跳过
- 数据覆盖率检查：股票数、交易日数、应有/实际行情、缺失行情明细
- 股票池、因子信号、市场风控、模拟订单计划
- 模拟盘账户持久化：账户、订单、成交、持仓、权益曲线
- 每日模拟盘任务流 `paper-pipeline`
- 区间模拟盘回放 `paper-replay`，用于验证多日稳定性
- 前端仪表盘读取生成的 JSON 报告
- 运行日志 `pipeline_run` 和 `runLog.json`

## 快速开始

安装前端依赖后，运行一次样例流程：

```bash
./scripts/run_sample.sh
./scripts/start_frontend.sh
```

打开：

```text
http://localhost:5173/
```

## 每日模拟盘

默认使用 `.env` 或 `.env.example` 里的路径。推荐先复制配置：

```bash
cp .env.example .env
```

运行 BaoStock 增量模拟盘：

```bash
./scripts/run_paper_daily.sh
```

常用环境变量：

```bash
PAPER_SOURCE=baostock
PAPER_MAX_CODES=30
PAPER_START=2025-01-01
PAPER_END=2026-06-16
PAPER_TRADE_DATE=2026-06-16
PAPER_ACCOUNT_ID=paper-main
PAPER_INCREMENTAL=1
```

示例：

```bash
PAPER_SOURCE=baostock PAPER_MAX_CODES=60 ./scripts/run_paper_daily.sh
```

历史区间重跑时关闭增量：

```bash
PAPER_INCREMENTAL=0 PAPER_START=2024-01-01 PAPER_END=2024-03-29 PAPER_TRADE_DATE=2024-03-29 ./scripts/run_paper_daily.sh
```

## 区间模拟盘回放

数据库已有行情后，可以用独立账户回放一段历史交易日：

```bash
REPLAY_START=2024-03-25 REPLAY_END=2024-03-29 ./scripts/run_paper_replay.sh
```

默认输出到 `data/paper_replay/`，不会覆盖前端 `src/data/`。常用环境变量：

```bash
TRADING_DB=data/baostock_frontend.sqlite
REPLAY_OUTPUT_DIR=data/paper_replay
REPLAY_ACCOUNT_ID=paper-replay
REPLAY_RESET_ACCOUNT=1
```

脚本默认也会同步一份只读 JSON 到 `src/data/paperReplay/`，前端左侧菜单“回放验证”会读取这份数据。

## 检查与构建

```bash
./scripts/check_all.sh
./scripts/build_frontend.sh
```

`check_all.sh` 会运行后端单元测试、前端构建和 CLI 冒烟检查。

## 常用脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/run_sample.sh` | 跑样例数据 pipeline，并刷新前端 JSON |
| `scripts/run_baostock_smoke.sh` | 跑 BaoStock 真实数据 smoke，输出到 `data/real_smoke/` |
| `scripts/run_paper_daily.sh` | 跑每日模拟盘任务流 |
| `scripts/run_paper_replay.sh` | 跑区间模拟盘回放，输出到 `data/paper_replay/` |
| `scripts/export_reports.sh` | 从数据库重新导出前端 JSON |
| `scripts/start_frontend.sh` | 启动 Vite 前端 |
| `scripts/build_frontend.sh` | 构建前端 |
| `scripts/check_all.sh` | 测试和构建总检查 |

## 真实数据 Smoke

先用独立目录验证 BaoStock 链路，不覆盖前端主数据：

```bash
./scripts/run_baostock_smoke.sh
./scripts/write_smoke_report.sh
```

结果查看：

```text
data/real_smoke/summary.json
docs/real_data_smoke_result.md
```

## 目录说明

```text
backend/                  后端数据、策略、回测、模拟盘代码
backend/sample_data/       CSV 样例数据
config/universe_core.csv   核心股票池配置
src/                       React 前端
src/data/                  前端消费的 JSON 报告
data/                      本地 SQLite 和验证输出
scripts/                   日常运行脚本
docs/                      运行手册和上线清单
```

## 重要说明

当前系统只用于模拟盘验证，不会连接券商或执行真实交易。策略结果不构成投资建议。
