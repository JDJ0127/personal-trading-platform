from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from trading_platform.backtest.broker import SimulatedBroker
from trading_platform.backtest.comparison import write_strategy_comparison
from trading_platform.backtest.engine import BacktestEngine
from trading_platform.backtest.export import build_frontend_backtest_report
from trading_platform.backtest.portfolio_report import write_portfolio_report
from trading_platform.backtest.stability import write_stability_report
from trading_platform.config import DEFAULT_CONFIG, load_app_config
from trading_platform.data.baostock_provider import BaoStockSession
from trading_platform.data.csv_provider import CsvDataProvider, parse_date
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.data.status import write_data_status_report
from trading_platform.data.tushare_provider import TushareClient, TushareDataProvider
from trading_platform.data.validation import validate_daily_bars
from trading_platform.news.rules import write_news_report
from trading_platform.risk.market_risk import write_market_risk_report
from trading_platform.simulation.account import (
    persist_backtest_account,
    reset_simulation_account,
    run_daily_simulation,
    write_simulation_account_report,
)
from trading_platform.simulation.planner import write_simulation_report
from trading_platform.simulation.run_log import collect_paper_metrics, finish_pipeline_run, start_pipeline_run, write_run_log_report
from trading_platform.strategies.factor_signals import generate_factor_signals_from_store, write_signal_report
from trading_platform.universe.config import load_universe_codes, merge_universe_codes
from trading_platform.strategies.optimized_trend import OptimizedTrendStrategy
from trading_platform.strategies.simple_trend import SimpleTrendStrategy
from trading_platform.universe.stock_pool import build_stock_pool_from_store, write_stock_pool_report


def build_parser() -> argparse.ArgumentParser:
    app_config = load_app_config()
    parser = argparse.ArgumentParser(prog="trading-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="load CSV files into a local SQLite database")
    ingest.add_argument("--data-dir", type=Path, default=app_config.sample_data_dir)
    ingest.add_argument("--db", type=Path, default=app_config.trading_db)
    ingest.set_defaults(func=run_ingest)

    validate = subparsers.add_parser("validate", help="validate local CSV market data")
    validate.add_argument("--data-dir", type=Path, default=app_config.sample_data_dir)
    validate.set_defaults(func=run_validate)

    data_status = subparsers.add_parser("data-status", help="export SQLite data status for the frontend")
    data_status.add_argument("--db", type=Path, default=app_config.trading_db)
    data_status.add_argument("--output", type=Path, default=app_config.data_status_output)
    data_status.add_argument("--source-name", default="Tushare")
    data_status.set_defaults(func=run_data_status)

    stock_pool = subparsers.add_parser("stock-pool", help="generate stock pool and export frontend JSON")
    stock_pool.add_argument("--db", type=Path, default=app_config.trading_db)
    stock_pool.add_argument("--trade-date", type=parse_date)
    stock_pool.add_argument("--output", type=Path, default=app_config.stock_pool_output)
    stock_pool.set_defaults(func=run_stock_pool)

    factor_signal = subparsers.add_parser("factor-signal", help="generate factors, signals, and frontend JSON")
    factor_signal.add_argument("--db", type=Path, default=app_config.trading_db)
    factor_signal.add_argument("--trade-date", type=parse_date)
    factor_signal.add_argument("--output", type=Path, default=app_config.signal_output)
    factor_signal.set_defaults(func=run_factor_signal)

    market_risk = subparsers.add_parser("market-risk", help="export market regime and risk JSON")
    market_risk.add_argument("--db", type=Path, default=app_config.trading_db)
    market_risk.add_argument("--trade-date", type=parse_date)
    market_risk.add_argument("--output", type=Path, default=app_config.market_risk_output)
    market_risk.set_defaults(func=run_market_risk)

    simulation = subparsers.add_parser("simulation-plan", help="export simulation order plan JSON")
    simulation.add_argument("--db", type=Path, default=app_config.trading_db)
    simulation.add_argument("--account-id", default="paper-main")
    simulation.add_argument("--trade-date", type=parse_date)
    simulation.add_argument("--output", type=Path, default=app_config.simulation_output)
    simulation.set_defaults(func=run_simulation_plan)

    news = subparsers.add_parser("news-events", help="export rule-based policy/news JSON")
    news.add_argument("--output", type=Path, default=app_config.news_output)
    news.set_defaults(func=run_news_events)

    sync_tushare = subparsers.add_parser("sync-tushare", help="sync Tushare Pro data into SQLite")
    sync_tushare.add_argument("--db", type=Path, default=app_config.trading_db)
    sync_tushare.add_argument("--token", default=app_config.tushare_token)
    sync_tushare.add_argument("--start", required=app_config.default_start is None, type=parse_date, default=_optional_config_date(app_config.default_start))
    sync_tushare.add_argument("--end", required=app_config.default_end is None, type=parse_date, default=_optional_config_date(app_config.default_end))
    sync_tushare.add_argument("--ts-code", help="optional single stock code, for example 600000.SH")
    sync_tushare.add_argument("--skip-stock-basic", action="store_true", help="skip stock_basic refresh")
    sync_tushare.set_defaults(func=run_sync_tushare)

    sync_baostock = subparsers.add_parser("sync-baostock", help="sync BaoStock free market data into SQLite")
    sync_baostock.add_argument("--db", type=Path, default=app_config.trading_db)
    sync_baostock.add_argument("--start", type=parse_date, default=_optional_config_date(app_config.default_start))
    sync_baostock.add_argument("--end", type=parse_date, default=_optional_config_date(app_config.default_end), help="defaults to today when omitted")
    sync_baostock.add_argument("--codes", help="comma-separated stock codes, for example 600030.SH,300308.SZ")
    sync_baostock.add_argument("--universe-file", type=Path, default=app_config.universe_file, help="CSV file with a ts_code column")
    sync_baostock.add_argument("--code-offset", type=int, default=0, help="skip the first N merged universe codes")
    sync_baostock.add_argument("--max-codes", type=int, help="limit synced codes after merging --universe-file and --codes")
    sync_baostock.add_argument("--all-stock", action="store_true", help="sync all listed stocks from BaoStock")
    sync_baostock.add_argument("--skip-stock-basic", action="store_true", help="skip stock_basic refresh")
    sync_baostock.add_argument("--adjustflag", default="2", choices=["1", "2", "3"], help="BaoStock adjustment flag: 1 back, 2 front, 3 none")
    sync_baostock.add_argument("--timeout", type=float, default=20.0, help="socket timeout seconds for BaoStock requests")
    sync_baostock.add_argument("--incremental", action="store_true", help="start from the day after the latest daily_bar in SQLite")
    sync_baostock.add_argument("--retry", type=int, default=1, help="retry count per BaoStock history request")
    sync_baostock.add_argument("--continue-on-error", action="store_true", help="skip failed symbols instead of aborting the whole sync")
    sync_baostock.set_defaults(func=run_sync_baostock)

    backtest = subparsers.add_parser("backtest", help="run the sample trend strategy")
    backtest.add_argument("--data-dir", type=Path, help="CSV directory; used when --db is not provided")
    backtest.add_argument("--db", type=Path, default=app_config.trading_db, help="SQLite database path")
    backtest.add_argument("--start", type=parse_date, default=_optional_config_date(app_config.default_start))
    backtest.add_argument("--end", type=parse_date, default=_optional_config_date(app_config.default_end))
    backtest.add_argument("--json", action="store_true", help="print machine-readable result summary")
    backtest.add_argument("--strategy", choices=["simple_trend_v0", "optimized_trend_v1"], default="simple_trend_v0")
    backtest.add_argument("--output", type=Path, default=app_config.backtest_output, help="write frontend backtest report JSON to this path")
    backtest.add_argument("--stability-output", type=Path, default=app_config.stability_output, help="write stability report JSON to this path")
    backtest.add_argument("--portfolio-output", type=Path, default=app_config.portfolio_output, help="write portfolio report JSON to this path")
    backtest.add_argument("--account-id", default="paper-main", help="simulation account id to persist backtest results into")
    backtest.add_argument("--account-output", type=Path, default=app_config.simulation_account_output, help="write persisted simulation account JSON to this path")
    backtest.set_defaults(func=run_backtest)

    pipeline = subparsers.add_parser("pipeline", help="run data load, backtest, and frontend JSON export")
    pipeline.add_argument("--source", choices=["sample", "tushare", "baostock"], default="sample")
    pipeline.add_argument("--data-dir", type=Path, default=app_config.sample_data_dir)
    pipeline.add_argument("--db", type=Path, default=app_config.trading_db)
    pipeline.add_argument("--token", default=app_config.tushare_token)
    pipeline.add_argument("--start", type=parse_date, default=_optional_config_date(app_config.default_start))
    pipeline.add_argument("--end", type=parse_date, default=_optional_config_date(app_config.default_end))
    pipeline.add_argument("--ts-code", help="optional single stock code for Tushare sync")
    pipeline.add_argument("--codes", help="comma-separated stock codes for BaoStock sync")
    pipeline.add_argument("--universe-file", type=Path, default=app_config.universe_file, help="CSV file with a ts_code column for BaoStock sync")
    pipeline.add_argument("--code-offset", type=int, default=0, help="skip the first N merged universe codes")
    pipeline.add_argument("--max-codes", type=int, help="limit synced codes after merging --universe-file and --codes")
    pipeline.add_argument("--all-stock", action="store_true", help="sync all listed BaoStock stocks")
    pipeline.add_argument("--skip-sync", action="store_true", help="skip data sync and reuse the existing SQLite database")
    pipeline.add_argument("--skip-stock-basic", action="store_true", help="skip stock_basic refresh for remote data sources")
    pipeline.add_argument("--adjustflag", default="2", choices=["1", "2", "3"], help="BaoStock adjustment flag")
    pipeline.add_argument("--timeout", type=float, default=20.0, help="socket timeout seconds for BaoStock requests")
    pipeline.add_argument("--incremental", action="store_true")
    pipeline.add_argument("--retry", type=int, default=1)
    pipeline.add_argument("--continue-on-error", action="store_true")
    pipeline.add_argument("--strategy", choices=["simple_trend_v0", "optimized_trend_v1"], default="simple_trend_v0")
    pipeline.add_argument("--output", type=Path, default=app_config.backtest_output)
    pipeline.add_argument("--stability-output", type=Path, default=app_config.stability_output)
    pipeline.add_argument("--portfolio-output", type=Path, default=app_config.portfolio_output)
    pipeline.add_argument("--data-status-output", type=Path, default=app_config.data_status_output)
    pipeline.add_argument("--stock-pool-output", type=Path, default=app_config.stock_pool_output)
    pipeline.add_argument("--signal-output", type=Path, default=app_config.signal_output)
    pipeline.add_argument("--market-risk-output", type=Path, default=app_config.market_risk_output)
    pipeline.add_argument("--simulation-output", type=Path, default=app_config.simulation_output)
    pipeline.add_argument("--account-id", default="paper-main")
    pipeline.add_argument("--account-output", type=Path, default=app_config.simulation_account_output)
    pipeline.add_argument("--news-output", type=Path, default=app_config.news_output)
    pipeline.set_defaults(func=run_pipeline)

    validate_baostock = subparsers.add_parser("validate-baostock", help="run a BaoStock validation pipeline into data/validation outputs")
    validate_baostock.add_argument("--start", required=app_config.default_start is None, type=parse_date, default=_optional_config_date(app_config.default_start))
    validate_baostock.add_argument("--end", required=app_config.default_end is None, type=parse_date, default=_optional_config_date(app_config.default_end))
    validate_baostock.add_argument("--universe-file", type=Path, default=app_config.universe_file)
    validate_baostock.add_argument("--codes", help="extra comma-separated stock codes")
    validate_baostock.add_argument("--code-offset", type=int, default=0, help="skip the first N merged universe codes")
    validate_baostock.add_argument("--max-codes", type=int, help="limit synced codes for faster smoke validation")
    validate_baostock.add_argument("--strategy", choices=["simple_trend_v0", "optimized_trend_v1"], default="optimized_trend_v1")
    validate_baostock.add_argument("--skip-sync", action="store_true", help="reuse output-dir/baostock_validation.sqlite without syncing")
    validate_baostock.add_argument("--timeout", type=float, default=20.0)
    validate_baostock.add_argument("--output-dir", type=Path, default=Path("data/validation"))
    validate_baostock.set_defaults(func=run_validate_baostock)

    compare = subparsers.add_parser("compare-strategies", help="compare two stability report JSON files")
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--optimized", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    compare.set_defaults(func=run_compare_strategies)

    account_export = subparsers.add_parser("simulation-account", help="export a persisted simulation account JSON")
    account_export.add_argument("--db", type=Path, default=app_config.trading_db)
    account_export.add_argument("--account-id", default="paper-main")
    account_export.add_argument("--output", type=Path, default=app_config.simulation_account_output)
    account_export.set_defaults(func=run_simulation_account)

    paper_run = subparsers.add_parser("paper-run", help="advance a persisted simulation account for one trade date")
    paper_run.add_argument("--db", type=Path, default=app_config.trading_db)
    paper_run.add_argument("--trade-date", type=parse_date, required=True)
    paper_run.add_argument("--account-id", default="paper-main")
    paper_run.add_argument("--account-name", default="模拟盘主账户")
    paper_run.add_argument("--output", type=Path, default=app_config.simulation_account_output)
    paper_run.set_defaults(func=run_paper_run)

    paper_pipeline = subparsers.add_parser("paper-pipeline", help="run the daily paper trading workflow")
    paper_pipeline.add_argument("--source", choices=["sample", "tushare", "baostock"], default="sample")
    paper_pipeline.add_argument("--data-dir", type=Path, default=app_config.sample_data_dir)
    paper_pipeline.add_argument("--db", type=Path, default=app_config.trading_db)
    paper_pipeline.add_argument("--token", default=app_config.tushare_token)
    paper_pipeline.add_argument("--start", type=parse_date, default=_optional_config_date(app_config.default_start))
    paper_pipeline.add_argument("--end", type=parse_date, default=_optional_config_date(app_config.default_end))
    paper_pipeline.add_argument("--trade-date", type=parse_date, help="paper account execution date; defaults to --end or latest daily_bar date")
    paper_pipeline.add_argument("--ts-code", help="optional single stock code for Tushare sync")
    paper_pipeline.add_argument("--codes", help="comma-separated stock codes for BaoStock sync")
    paper_pipeline.add_argument("--universe-file", type=Path, default=app_config.universe_file)
    paper_pipeline.add_argument("--code-offset", type=int, default=0)
    paper_pipeline.add_argument("--max-codes", type=int)
    paper_pipeline.add_argument("--all-stock", action="store_true")
    paper_pipeline.add_argument("--skip-sync", action="store_true")
    paper_pipeline.add_argument("--skip-stock-basic", action="store_true")
    paper_pipeline.add_argument("--adjustflag", default="2", choices=["1", "2", "3"])
    paper_pipeline.add_argument("--timeout", type=float, default=20.0)
    paper_pipeline.add_argument("--incremental", action="store_true")
    paper_pipeline.add_argument("--retry", type=int, default=1)
    paper_pipeline.add_argument("--continue-on-error", action="store_true")
    paper_pipeline.add_argument("--account-id", default="paper-main")
    paper_pipeline.add_argument("--account-name", default="模拟盘主账户")
    paper_pipeline.add_argument("--account-output", type=Path, default=app_config.simulation_account_output)
    paper_pipeline.add_argument("--data-status-output", type=Path, default=app_config.data_status_output)
    paper_pipeline.add_argument("--stock-pool-output", type=Path, default=app_config.stock_pool_output)
    paper_pipeline.add_argument("--signal-output", type=Path, default=app_config.signal_output)
    paper_pipeline.add_argument("--market-risk-output", type=Path, default=app_config.market_risk_output)
    paper_pipeline.add_argument("--simulation-output", type=Path, default=app_config.simulation_output)
    paper_pipeline.add_argument("--news-output", type=Path, default=app_config.news_output)
    paper_pipeline.add_argument("--run-log-output", type=Path, default=app_config.run_log_output)
    paper_pipeline.set_defaults(func=run_paper_pipeline)

    paper_replay = subparsers.add_parser("paper-replay", help="replay a paper account over a historical date range")
    paper_replay.add_argument("--db", type=Path, default=app_config.trading_db)
    paper_replay.add_argument("--start", type=parse_date, required=True)
    paper_replay.add_argument("--end", type=parse_date, required=True)
    paper_replay.add_argument("--account-id", default="paper-replay")
    paper_replay.add_argument("--account-name", default="模拟盘回放账户")
    paper_replay.add_argument("--reset-account", action="store_true")
    paper_replay.add_argument("--source-name", default="Replay")
    paper_replay.add_argument("--account-output", type=Path, default=app_config.simulation_account_output)
    paper_replay.add_argument("--data-status-output", type=Path, default=app_config.data_status_output)
    paper_replay.add_argument("--stock-pool-output", type=Path, default=app_config.stock_pool_output)
    paper_replay.add_argument("--signal-output", type=Path, default=app_config.signal_output)
    paper_replay.add_argument("--market-risk-output", type=Path, default=app_config.market_risk_output)
    paper_replay.add_argument("--simulation-output", type=Path, default=app_config.simulation_output)
    paper_replay.add_argument("--news-output", type=Path, default=app_config.news_output)
    paper_replay.add_argument("--run-log-output", type=Path, default=app_config.run_log_output)
    paper_replay.set_defaults(func=run_paper_replay)

    run_log = subparsers.add_parser("run-log", help="export pipeline run logs JSON")
    run_log.add_argument("--db", type=Path, default=app_config.trading_db)
    run_log.add_argument("--output", type=Path, default=app_config.run_log_output)
    run_log.add_argument("--limit", type=int, default=30)
    run_log.set_defaults(func=run_run_log)
    return parser


def run_ingest(args: argparse.Namespace) -> None:
    provider = CsvDataProvider(args.data_dir)
    bars = provider.load_daily_bars()
    issues = validate_daily_bars(bars)
    if issues:
        for issue in issues:
            print(f"{issue.table} {issue.key}: {issue.message}")
        raise SystemExit(1)

    store = SQLiteStore(args.db)
    store.initialize()
    counts = {
        "stock_basic": store.upsert_stock_basic(provider.load_stock_basic()),
        "trade_calendar": store.upsert_trade_calendar(provider.load_trade_calendar()),
        "daily_bar": store.upsert_daily_bars(bars),
        "limit_price": store.upsert_limit_prices(provider.load_limit_prices()),
        "suspension": store.upsert_suspensions(provider.load_suspensions()),
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2))


def run_validate(args: argparse.Namespace) -> None:
    provider = CsvDataProvider(args.data_dir)
    issues = validate_daily_bars(provider.load_daily_bars())
    if not issues:
        print("validation passed")
        return
    for issue in issues:
        print(f"{issue.table} {issue.key}: {issue.message}")
    raise SystemExit(1)


def run_data_status(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    store.initialize()
    report = write_data_status_report(store, args.output, args.source_name)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def run_stock_pool(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    entries = build_stock_pool_from_store(store, args.trade_date)
    store.upsert_stock_pool(entries)
    report = write_stock_pool_report(entries, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def run_factor_signal(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    store.initialize()
    factors, signals = generate_factor_signals_from_store(store, args.trade_date)
    factor_count = store.upsert_factor_values(factors)
    signal_count = store.upsert_signals(signals)
    report = write_signal_report(store, args.output, args.trade_date)
    print(json.dumps({"factor_value": factor_count, "signal": signal_count, "report": report["summary"]}, ensure_ascii=False, indent=2))


def run_market_risk(args: argparse.Namespace) -> None:
    report = write_market_risk_report(SQLiteStore(args.db), args.output, getattr(args, "trade_date", None))
    print(json.dumps({"tradeDate": report["tradeDate"], "market": report["market"], "risk": report["risk"]}, ensure_ascii=False, indent=2))


def run_simulation_plan(args: argparse.Namespace) -> None:
    report = write_simulation_report(
        SQLiteStore(args.db),
        args.output,
        getattr(args, "account_id", "paper-main"),
        getattr(args, "trade_date", None),
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def run_news_events(args: argparse.Namespace) -> None:
    report = write_news_report(args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def run_sync_tushare(args: argparse.Namespace) -> None:
    if not args.token:
        raise SystemExit("Tushare token is required. Pass --token or set TUSHARE_TOKEN.")

    provider = TushareDataProvider(TushareClient(args.token))
    stock_basic = [] if args.skip_stock_basic else provider.load_stock_basic()
    trade_calendar = provider.load_trade_calendar(args.start, args.end)
    daily_bars = provider.load_daily_bars(args.start, args.end, args.ts_code)
    issues = validate_daily_bars(daily_bars)
    if issues:
        for issue in issues:
            print(f"{issue.table} {issue.key}: {issue.message}")
        raise SystemExit(1)

    limit_prices = provider.load_limit_prices(args.start, args.end, args.ts_code)
    suspensions = provider.load_suspensions(args.start, args.end, args.ts_code)

    store = SQLiteStore(args.db)
    store.initialize()
    counts = {
        "stock_basic": store.upsert_stock_basic(stock_basic),
        "trade_calendar": store.upsert_trade_calendar(trade_calendar),
        "daily_bar": store.upsert_daily_bars(daily_bars),
        "limit_price": store.upsert_limit_prices(limit_prices),
        "suspension": store.upsert_suspensions(suspensions),
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2))


def run_sync_baostock(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    store.initialize()
    start, end = _resolve_baostock_sync_dates(store, args.start, args.end, getattr(args, "incremental", False))
    sync_start = _incremental_start(store, start, end) if getattr(args, "incremental", False) else start

    requested_codes = [] if args.all_stock else _select_codes(_requested_baostock_codes(args.codes, args.universe_file), args.code_offset, args.max_codes)
    with BaoStockSession(timeout=args.timeout) as provider:
        if args.all_stock:
            stock_basic = [] if args.skip_stock_basic else provider.load_stock_basic(end)
            codes = _resolve_baostock_codes(requested_codes, args.all_stock, stock_basic, store)
        else:
            codes = _resolve_baostock_codes(requested_codes, args.all_stock, [], store)
            stock_basic = [] if args.skip_stock_basic else provider.load_stock_basic(end, codes)
        if not codes:
            raise SystemExit("BaoStock sync requires --codes, --all-stock, or existing stock_basic rows in the database.")

        if sync_start > end:
            trade_calendar = []
            daily_bars = []
        else:
            trade_calendar = provider.load_trade_calendar(sync_start, end)
            daily_bars = provider.load_daily_bars(
                sync_start,
                end,
                codes,
                args.adjustflag,
                retries=getattr(args, "retry", 1),
                continue_on_error=getattr(args, "continue_on_error", False),
            )
        issues = validate_daily_bars(daily_bars)
        if issues:
            for issue in issues:
                print(f"{issue.table} {issue.key}: {issue.message}")
            raise SystemExit(1)

        limit_prices = provider.load_limit_prices(sync_start, end, codes)
        suspensions = provider.load_suspensions(sync_start, end, codes)

    counts = {
        "stock_basic": store.upsert_stock_basic(stock_basic),
        "trade_calendar": store.upsert_trade_calendar(trade_calendar),
        "daily_bar": store.upsert_daily_bars(daily_bars),
        "limit_price": store.upsert_limit_prices(limit_prices),
        "suspension": store.upsert_suspensions(suspensions),
        "sync_start": sync_start.isoformat(),
        "sync_end": end.isoformat(),
        "requested_codes": len(codes),
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2))


def run_backtest(args: argparse.Namespace) -> None:
    stock_basic = []
    store = None
    if args.data_dir:
        provider = CsvDataProvider(args.data_dir)
        stock_basic = provider.load_stock_basic()
        bars = [
            bar
            for bar in provider.load_daily_bars()
            if _inside_range(bar.trade_date, args.start, args.end)
        ]
        broker = SimulatedBroker(
            DEFAULT_CONFIG,
            {(row.trade_date, row.ts_code): row for row in provider.load_limit_prices()},
            {(row.trade_date, row.ts_code) for row in provider.load_suspensions() if row.suspend_type == "suspend"},
        )
    elif args.db:
        store = SQLiteStore(args.db)
        store.initialize()
        stock_basic = store.load_stock_basic()
        bars = store.load_daily_bars(args.start, args.end)
        broker = SimulatedBroker(DEFAULT_CONFIG, store.load_limit_prices(), store.load_suspensions())
    else:
        raise SystemExit("either --data-dir or --db is required")

    issues = validate_daily_bars(bars)
    if issues:
        for issue in issues:
            print(f"{issue.table} {issue.key}: {issue.message}")
        raise SystemExit(1)

    engine = BacktestEngine(bars, _build_strategy(args.strategy), broker)
    result = engine.run()
    frontend_report = build_frontend_backtest_report(result, DEFAULT_CONFIG)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(frontend_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stability_report = write_stability_report(result, args.stability_output) if args.stability_output else None
    if args.portfolio_output:
        write_portfolio_report(result, bars, stock_basic, args.portfolio_output)
    if args.account_output:
        if store is None:
            store = SQLiteStore(args.db or Path("data/trading.sqlite"))
        persist_backtest_account(store, result, bars, stock_basic, args.account_id)
        write_simulation_account_report(store, args.account_id, args.account_output)

    summary = {
        "strategy": result.strategy_name,
        "initial_cash": result.initial_cash,
        "final_asset": round(result.final_asset, 2),
        "cumulative_return": round(result.cumulative_return, 4),
        "max_drawdown": round(result.max_drawdown, 4),
        "win_rate": round(result.win_rate, 4),
        "orders": result.order_count,
        "fills": result.fill_count,
        "snapshots": len(result.snapshots),
        "monthly_win_rate": stability_report["summary"]["monthlyWinRate"] if stability_report else None,
        "winning_months": stability_report["summary"]["winningMonthCount"] if stability_report else None,
        "losing_months": stability_report["summary"]["losingMonthCount"] if stability_report else None,
    }
    if args.json:
        print(json.dumps(frontend_report if args.output is None else summary, ensure_ascii=False, indent=2))
        return
    print(f"策略: {summary['strategy']}")
    print(f"期末资产: {summary['final_asset']}")
    print(f"累计收益: {summary['cumulative_return']:.2%}")
    print(f"最大回撤: {summary['max_drawdown']:.2%}")
    print(f"订单/成交: {summary['orders']}/{summary['fills']}")


def run_pipeline(args: argparse.Namespace) -> None:
    if args.skip_sync:
        print("step 1/8: skip data sync and reuse SQLite database")
    elif args.source == "sample":
        ingest_args = argparse.Namespace(data_dir=args.data_dir, db=args.db)
        print("step 1/8: ingest sample CSV data")
        run_ingest(ingest_args)
    elif args.source == "tushare":
        if not args.start or not args.end:
            raise SystemExit("pipeline --source tushare requires --start and --end, or BACKTEST_START/BACKTEST_END in .env")
        sync_args = argparse.Namespace(
            db=args.db,
            token=args.token,
            start=args.start,
            end=args.end,
            ts_code=args.ts_code,
            skip_stock_basic=args.skip_stock_basic,
        )
        print("step 1/8: sync Tushare data")
        run_sync_tushare(sync_args)
    else:
        sync_args = argparse.Namespace(
            db=args.db,
            start=args.start,
            end=args.end,
            codes=args.codes,
            universe_file=args.universe_file,
            code_offset=args.code_offset,
            max_codes=args.max_codes,
            all_stock=args.all_stock,
            skip_stock_basic=args.skip_stock_basic,
            adjustflag=args.adjustflag,
            timeout=args.timeout,
            incremental=args.incremental,
            retry=args.retry,
            continue_on_error=args.continue_on_error,
        )
        print("step 1/8: sync BaoStock data")
        run_sync_baostock(sync_args)

    print("step 2/8: generate stock pool")
    run_stock_pool(argparse.Namespace(db=args.db, trade_date=args.end, output=args.stock_pool_output))
    print("step 3/8: generate factor signals")
    run_factor_signal(argparse.Namespace(db=args.db, trade_date=args.end, output=args.signal_output))
    print("step 4/8: export market and risk JSON")
    run_market_risk(argparse.Namespace(db=args.db, trade_date=args.end, output=args.market_risk_output))
    print("step 5/8: export simulation plan JSON")
    run_simulation_plan(argparse.Namespace(db=args.db, account_id=args.account_id, trade_date=args.end, output=args.simulation_output))
    print("step 6/8: export news event JSON")
    run_news_events(argparse.Namespace(output=args.news_output))
    print("step 7/8: run backtest and export frontend JSON")
    backtest_args = argparse.Namespace(
        data_dir=None,
        db=args.db,
        start=args.start,
        end=args.end,
        json=True,
        output=args.output,
        stability_output=args.stability_output,
        portfolio_output=args.portfolio_output,
        account_id=args.account_id,
        account_output=args.account_output,
        strategy=args.strategy,
    )
    run_backtest(backtest_args)
    print("step 8/8: export data status JSON")
    run_data_status(argparse.Namespace(db=args.db, output=args.data_status_output, source_name=_data_source_name(args.source)))


def run_validate_baostock(args: argparse.Namespace) -> None:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline_args = argparse.Namespace(
        source="baostock",
        data_dir=None,
        db=output_dir / "baostock_validation.sqlite",
        token=None,
        start=args.start,
        end=args.end,
        ts_code=None,
        codes=args.codes,
        universe_file=args.universe_file,
        code_offset=args.code_offset,
        max_codes=args.max_codes,
        all_stock=False,
        skip_sync=args.skip_sync,
        skip_stock_basic=False,
        adjustflag="2",
        strategy=args.strategy,
        timeout=args.timeout,
        incremental=False,
        retry=1,
        continue_on_error=False,
        output=output_dir / "backtestResult.json",
        stability_output=output_dir / "stabilityReport.json",
        portfolio_output=output_dir / "portfolioReport.json",
        account_id="paper-main",
        account_output=output_dir / "simulationAccount.json",
        data_status_output=output_dir / "dataStatus.json",
        stock_pool_output=output_dir / "stockPool.json",
        signal_output=output_dir / "signalReport.json",
        market_risk_output=output_dir / "marketRisk.json",
        simulation_output=output_dir / "simulationReport.json",
        news_output=output_dir / "newsReport.json",
    )
    run_pipeline(pipeline_args)


def run_compare_strategies(args: argparse.Namespace) -> None:
    report = write_strategy_comparison(args.baseline, args.optimized, args.output)
    print(json.dumps({"verdict": report["verdict"], "period": report["period"], "metrics": report["metrics"]}, ensure_ascii=False, indent=2))


def run_simulation_account(args: argparse.Namespace) -> None:
    report = write_simulation_account_report(SQLiteStore(args.db), args.account_id, args.output)
    print(json.dumps({"account": report["account"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


def run_paper_run(args: argparse.Namespace) -> None:
    report = run_daily_simulation(
        SQLiteStore(args.db),
        args.trade_date,
        account_id=args.account_id,
        account_name=args.account_name,
        output=args.output,
    )
    print(json.dumps({"account": report["account"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


def run_paper_pipeline(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    store.initialize()
    initial_trade_date = args.trade_date or args.end or _latest_trade_date(store)
    run_id = start_pipeline_run(store, "paper-pipeline", args.source, args.account_id, initial_trade_date)
    try:
        _run_source_sync(args, prefix="paper step 1/8")
        trade_date = args.trade_date or args.end or _latest_trade_date(store)
        if trade_date is None:
            raise SystemExit("paper-pipeline requires --trade-date, --end, or existing daily_bar rows in SQLite.")

        print("paper step 2/8: generate stock pool")
        run_stock_pool(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.stock_pool_output))
        print("paper step 3/8: generate factor signals")
        run_factor_signal(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.signal_output))
        print("paper step 4/8: export market and risk JSON")
        run_market_risk(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.market_risk_output))
        print("paper step 5/8: export simulation plan JSON")
        run_simulation_plan(argparse.Namespace(db=args.db, account_id=args.account_id, trade_date=trade_date, output=args.simulation_output))
        simulation_report = json.loads(Path(args.simulation_output).read_text(encoding="utf-8")) if args.simulation_output.exists() else {"summary": {}}
        print("paper step 6/8: advance paper account")
        run_paper_run(
            argparse.Namespace(
                db=args.db,
                trade_date=trade_date,
                account_id=args.account_id,
                account_name=args.account_name,
                output=args.account_output,
            )
        )
        print("paper step 7/9: export news event JSON")
        run_news_events(argparse.Namespace(output=args.news_output))
        print("paper step 8/9: export data status JSON")
        run_data_status(argparse.Namespace(db=args.db, output=args.data_status_output, source_name=_data_source_name(args.source)))
        metrics = collect_paper_metrics(store, args.account_id, trade_date)
        metrics["plannedOrderCount"] = simulation_report.get("summary", {}).get("plannedOrderCount", 0)
        metrics["blockedOrderCount"] = simulation_report.get("summary", {}).get("blockedOrderCount", 0)
        finish_pipeline_run(store, run_id, "success", metrics)
        print("paper step 9/9: export run log JSON")
        write_run_log_report(store, args.run_log_output)
    except Exception as exc:
        finish_pipeline_run(store, run_id, "failed", error_message=str(exc))
        write_run_log_report(store, args.run_log_output)
        raise


def run_paper_replay(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.db)
    store.initialize()
    run_id = start_pipeline_run(store, "paper-replay", args.source_name, args.account_id, args.end)
    try:
        if args.reset_account:
            reset_simulation_account(store, args.account_id)
        trade_dates = _trade_dates_between(store, args.start, args.end)
        if not trade_dates:
            raise SystemExit("paper-replay found no daily_bar rows in the requested date range.")

        last_simulation_report = {"summary": {}}
        for index, trade_date in enumerate(trade_dates, start=1):
            print(f"replay {index}/{len(trade_dates)} {trade_date}: generate stock pool")
            run_stock_pool(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.stock_pool_output))
            print(f"replay {index}/{len(trade_dates)} {trade_date}: generate factor signals")
            run_factor_signal(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.signal_output))
            print(f"replay {index}/{len(trade_dates)} {trade_date}: export market risk")
            run_market_risk(argparse.Namespace(db=args.db, trade_date=trade_date, output=args.market_risk_output))
            print(f"replay {index}/{len(trade_dates)} {trade_date}: export simulation plan")
            run_simulation_plan(
                argparse.Namespace(
                    db=args.db,
                    account_id=args.account_id,
                    trade_date=trade_date,
                    output=args.simulation_output,
                )
            )
            if args.simulation_output.exists():
                last_simulation_report = json.loads(args.simulation_output.read_text(encoding="utf-8"))
            print(f"replay {index}/{len(trade_dates)} {trade_date}: advance paper account")
            run_paper_run(
                argparse.Namespace(
                    db=args.db,
                    trade_date=trade_date,
                    account_id=args.account_id,
                    account_name=args.account_name,
                    output=args.account_output,
                )
            )

        run_news_events(argparse.Namespace(output=args.news_output))
        run_data_status(argparse.Namespace(db=args.db, output=args.data_status_output, source_name=args.source_name))
        metrics = collect_paper_metrics(store, args.account_id, trade_dates[-1])
        metrics["plannedOrderCount"] = last_simulation_report.get("summary", {}).get("plannedOrderCount", 0)
        metrics["blockedOrderCount"] = last_simulation_report.get("summary", {}).get("blockedOrderCount", 0)
        metrics["replayTradeDays"] = len(trade_dates)
        finish_pipeline_run(store, run_id, "success", metrics)
        write_run_log_report(store, args.run_log_output)
    except Exception as exc:
        finish_pipeline_run(store, run_id, "failed", error_message=str(exc))
        write_run_log_report(store, args.run_log_output)
        raise


def run_run_log(args: argparse.Namespace) -> None:
    report = write_run_log_report(SQLiteStore(args.db), args.output, args.limit)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def _inside_range(value: date, start: date | None, end: date | None) -> bool:
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def _optional_config_date(value: str | None) -> date | None:
    return parse_date(value) if value else None


def _data_source_name(source: str) -> str:
    return {"sample": "CSV样例", "tushare": "Tushare", "baostock": "BaoStock"}.get(source, source)


def _run_source_sync(args: argparse.Namespace, prefix: str) -> None:
    if args.skip_sync:
        print(f"{prefix}: skip data sync and reuse SQLite database")
        return
    if args.source == "sample":
        print(f"{prefix}: ingest sample CSV data")
        run_ingest(argparse.Namespace(data_dir=args.data_dir, db=args.db))
        return
    if args.source == "tushare":
        if not args.start or not args.end:
            raise SystemExit("Tushare sync requires --start and --end, or BACKTEST_START/BACKTEST_END in .env")
        print(f"{prefix}: sync Tushare data")
        run_sync_tushare(
            argparse.Namespace(
                db=args.db,
                token=args.token,
                start=args.start,
                end=args.end,
                ts_code=args.ts_code,
                skip_stock_basic=args.skip_stock_basic,
            )
        )
        return
    print(f"{prefix}: sync BaoStock data")
    run_sync_baostock(
        argparse.Namespace(
            db=args.db,
            start=args.start,
            end=args.end,
            codes=args.codes,
            universe_file=args.universe_file,
            code_offset=args.code_offset,
            max_codes=args.max_codes,
            all_stock=args.all_stock,
            skip_stock_basic=args.skip_stock_basic,
            adjustflag=args.adjustflag,
            timeout=args.timeout,
            incremental=args.incremental,
            retry=args.retry,
            continue_on_error=args.continue_on_error,
        )
    )


def _latest_trade_date(store: SQLiteStore) -> date | None:
    bars = store.load_daily_bars()
    return max((bar.trade_date for bar in bars), default=None)


def _trade_dates_between(store: SQLiteStore, start: date, end: date) -> list[date]:
    if start > end:
        raise SystemExit("paper-replay requires --start to be earlier than or equal to --end.")
    return sorted({bar.trade_date for bar in store.load_daily_bars(start, end)})


def _incremental_start(store: SQLiteStore, start: date, end: date) -> date:
    latest = _latest_trade_date(store)
    if latest is None:
        return start
    next_date = latest + timedelta(days=1)
    if next_date > end:
        return end + timedelta(days=1)
    return max(start, next_date)


def _resolve_baostock_sync_dates(store: SQLiteStore, start: date | None, end: date | None, incremental: bool) -> tuple[date, date]:
    resolved_end = end or date.today()
    if start:
        return start, resolved_end
    latest = _latest_trade_date(store)
    if incremental and latest:
        return latest + timedelta(days=1), resolved_end
    raise SystemExit("BaoStock sync requires --start unless --incremental can infer it from existing daily_bar rows.")


def _build_strategy(name: str):
    if name == "optimized_trend_v1":
        return OptimizedTrendStrategy(max_positions=DEFAULT_CONFIG.max_positions)
    return SimpleTrendStrategy(max_positions=DEFAULT_CONFIG.max_positions)


def _parse_codes(codes_arg: str | None) -> list[str]:
    return [code.strip() for code in codes_arg.split(",") if code.strip()] if codes_arg else []


def _requested_baostock_codes(codes_arg: str | None, universe_file: Path | None) -> list[str]:
    file_codes = load_universe_codes(universe_file) if universe_file and universe_file.exists() else []
    return merge_universe_codes(file_codes, _parse_codes(codes_arg))


def _select_codes(codes: list[str], offset: int, max_codes: int | None) -> list[str]:
    if offset < 0:
        raise SystemExit("--code-offset must be greater than or equal to 0")
    sliced = codes[offset:]
    if max_codes is None:
        return sliced
    if max_codes <= 0:
        raise SystemExit("--max-codes must be greater than 0")
    return sliced[:max_codes]


def _resolve_baostock_codes(codes: list[str], all_stock: bool, stock_basic: list, store: SQLiteStore) -> list[str]:
    if codes:
        return codes
    if all_stock:
        return [stock.ts_code for stock in stock_basic if stock.status == "L" and stock.market != "指数"]
    return [stock.ts_code for stock in store.load_stock_basic() if stock.status == "L" and stock.market != "指数"]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
