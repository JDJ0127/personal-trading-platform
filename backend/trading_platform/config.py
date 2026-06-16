from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TradingConfig:
    initial_cash: float = 500_000.0
    max_drawdown_limit: float = 0.15
    max_positions: int = 5
    min_position_weight: float = 0.10
    max_position_weight: float = 0.20
    max_portfolio_weight: float = 0.60
    lot_size: int = 100
    commission_rate: float = 0.00025
    min_commission: float = 5.0
    stamp_tax_rate: float = 0.0005
    transfer_fee_rate: float = 0.00001
    slippage_bps: float = 5.0


DEFAULT_CONFIG = TradingConfig()


@dataclass(frozen=True)
class AppConfig:
    tushare_token: str | None = None
    trading_db: Path = Path("data/trading.sqlite")
    sample_data_dir: Path = Path("backend/sample_data")
    universe_file: Path = Path("config/universe_core.csv")
    backtest_output: Path = Path("src/data/backtestResult.json")
    stability_output: Path = Path("src/data/stabilityReport.json")
    portfolio_output: Path = Path("src/data/portfolioReport.json")
    data_status_output: Path = Path("src/data/dataStatus.json")
    stock_pool_output: Path = Path("src/data/stockPool.json")
    signal_output: Path = Path("src/data/signalReport.json")
    market_risk_output: Path = Path("src/data/marketRisk.json")
    simulation_output: Path = Path("src/data/simulationReport.json")
    simulation_account_output: Path = Path("src/data/simulationAccount.json")
    run_log_output: Path = Path("src/data/runLog.json")
    news_output: Path = Path("src/data/newsReport.json")
    default_start: str | None = None
    default_end: str | None = None


def load_dotenv(path: str | Path = ".env") -> None:
    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_app_config(dotenv_path: str | Path = ".env") -> AppConfig:
    load_dotenv(dotenv_path)
    return AppConfig(
        tushare_token=os.environ.get("TUSHARE_TOKEN") or None,
        trading_db=Path(os.environ.get("TRADING_DB", "data/trading.sqlite")),
        sample_data_dir=Path(os.environ.get("SAMPLE_DATA_DIR", "backend/sample_data")),
        universe_file=Path(os.environ.get("UNIVERSE_FILE", "config/universe_core.csv")),
        backtest_output=Path(os.environ.get("BACKTEST_OUTPUT", "src/data/backtestResult.json")),
        stability_output=Path(os.environ.get("STABILITY_OUTPUT", "src/data/stabilityReport.json")),
        portfolio_output=Path(os.environ.get("PORTFOLIO_OUTPUT", "src/data/portfolioReport.json")),
        data_status_output=Path(os.environ.get("DATA_STATUS_OUTPUT", "src/data/dataStatus.json")),
        stock_pool_output=Path(os.environ.get("STOCK_POOL_OUTPUT", "src/data/stockPool.json")),
        signal_output=Path(os.environ.get("SIGNAL_OUTPUT", "src/data/signalReport.json")),
        market_risk_output=Path(os.environ.get("MARKET_RISK_OUTPUT", "src/data/marketRisk.json")),
        simulation_output=Path(os.environ.get("SIMULATION_OUTPUT", "src/data/simulationReport.json")),
        simulation_account_output=Path(os.environ.get("SIMULATION_ACCOUNT_OUTPUT", "src/data/simulationAccount.json")),
        run_log_output=Path(os.environ.get("RUN_LOG_OUTPUT", "src/data/runLog.json")),
        news_output=Path(os.environ.get("NEWS_OUTPUT", "src/data/newsReport.json")),
        default_start=os.environ.get("BACKTEST_START") or None,
        default_end=os.environ.get("BACKTEST_END") or None,
    )
