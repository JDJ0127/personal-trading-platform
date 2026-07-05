from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import date, datetime, time
from pathlib import Path

from trading_platform.models import (
    DailyBar,
    FactorValue,
    LimitPrice,
    MinuteBar,
    RealtimeQuote,
    Signal,
    SignalType,
    StockBasic,
    StockPoolEntry,
    Suspension,
    TradeCalendar,
)


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists stock_basic (
                  ts_code text primary key,
                  symbol text not null,
                  name text not null,
                  exchange text not null,
                  market text not null,
                  list_date text not null,
                  delist_date text,
                  is_hs text,
                  status text not null
                );

                create table if not exists daily_bar (
                  trade_date text not null,
                  ts_code text not null,
                  open real not null,
                  high real not null,
                  low real not null,
                  close real not null,
                  pre_close real not null,
                  volume real not null,
                  amount real not null,
                  pct_chg real not null,
                  adj_factor real not null,
                  primary key (trade_date, ts_code)
                );

                create table if not exists minute_bar (
                  trade_time text not null,
                  ts_code text not null,
                  interval text not null,
                  open real not null,
                  high real not null,
                  low real not null,
                  close real not null,
                  volume real not null,
                  amount real not null,
                  adjust text not null,
                  source text not null,
                  primary key (trade_time, ts_code, interval, adjust)
                );

                create table if not exists realtime_quote (
                  quote_time text not null,
                  ts_code text not null,
                  name text not null,
                  price real not null,
                  open real not null,
                  high real not null,
                  low real not null,
                  pre_close real not null,
                  volume real not null,
                  amount real not null,
                  pct_chg real not null,
                  source text not null,
                  primary key (quote_time, ts_code, source)
                );

                create table if not exists limit_price (
                  trade_date text not null,
                  ts_code text not null,
                  up_limit real not null,
                  down_limit real not null,
                  limit_type text not null,
                  primary key (trade_date, ts_code)
                );

                create table if not exists suspension (
                  trade_date text not null,
                  ts_code text not null,
                  suspend_type text not null,
                  reason text,
                  primary key (trade_date, ts_code, suspend_type)
                );

                create table if not exists trade_calendar (
                  cal_date text not null,
                  exchange text not null,
                  is_open integer not null,
                  pretrade_date text,
                  primary key (cal_date, exchange)
                );

                create table if not exists stock_pool (
                  trade_date text not null,
                  ts_code text not null,
                  name text not null,
                  industry text not null,
                  is_pass integer not null,
                  filter_reasons text not null,
                  listed_days integer not null,
                  close real,
                  amount real,
                  avg_amount real,
                  primary key (trade_date, ts_code)
                );

                create table if not exists factor_value (
                  trade_date text not null,
                  ts_code text not null,
                  factor_name text not null,
                  factor_value real not null,
                  factor_score real not null,
                  primary key (trade_date, ts_code, factor_name)
                );

                create table if not exists signal (
                  signal_date text not null,
                  trade_date text not null,
                  ts_code text not null,
                  signal_type text not null,
                  score real not null,
                  target_weight real not null,
                  reason text not null,
                  primary key (signal_date, trade_date, ts_code, signal_type)
                );

                create table if not exists simulation_account (
                  account_id text primary key,
                  account_name text not null,
                  mode text not null,
                  strategy_name text not null,
                  initial_cash real not null,
                  total_asset real not null,
                  cash real not null,
                  market_value real not null,
                  cumulative_return real not null,
                  max_drawdown real not null,
                  position_count integer not null,
                  last_trade_date text,
                  status text not null,
                  created_at text not null,
                  updated_at text not null
                );

                create table if not exists simulation_order (
                  account_id text not null,
                  order_id text not null,
                  trade_date text not null,
                  ts_code text not null,
                  side text not null,
                  order_price real not null,
                  order_quantity integer not null,
                  filled_quantity integer not null,
                  avg_fill_price real not null,
                  status text not null,
                  reject_reason text not null,
                  primary key (account_id, order_id)
                );

                create table if not exists simulation_fill (
                  account_id text not null,
                  fill_id text not null,
                  trade_date text not null,
                  ts_code text not null,
                  side text not null,
                  quantity integer not null,
                  price real not null,
                  commission real not null,
                  stamp_tax real not null,
                  transfer_fee real not null,
                  primary key (account_id, fill_id)
                );

                create table if not exists simulation_position (
                  account_id text not null,
                  trade_date text not null,
                  ts_code text not null,
                  name text not null,
                  industry text not null,
                  quantity integer not null,
                  available_quantity integer not null,
                  cost_price real not null,
                  market_price real not null,
                  market_value real not null,
                  weight real not null,
                  unrealized_pnl real not null,
                  unrealized_pnl_pct real not null,
                  stop_price real not null,
                  holding_days integer not null,
                  primary key (account_id, ts_code)
                );

                create table if not exists simulation_equity_curve (
                  account_id text not null,
                  trade_date text not null,
                  total_asset real not null,
                  cash real not null,
                  market_value real not null,
                  daily_return real not null,
                  cumulative_return real not null,
                  drawdown real not null,
                  max_drawdown real not null,
                  position_count integer not null,
                  total_weight real not null,
                  primary key (account_id, trade_date)
                );

                create table if not exists pipeline_run (
                  run_id text primary key,
                  workflow text not null,
                  source text not null,
                  account_id text,
                  trade_date text,
                  status text not null,
                  started_at text not null,
                  finished_at text,
                  duration_ms integer,
                  stock_count integer not null default 0,
                  signal_count integer not null default 0,
                  planned_order_count integer not null default 0,
                  blocked_order_count integer not null default 0,
                  order_count integer not null default 0,
                  fill_count integer not null default 0,
                  error_message text not null default ''
                );

                create index if not exists idx_daily_bar_code_date
                  on daily_bar (ts_code, trade_date);
                create index if not exists idx_minute_bar_code_time
                  on minute_bar (ts_code, trade_time);
                create index if not exists idx_realtime_quote_code_time
                  on realtime_quote (ts_code, quote_time desc);
                create index if not exists idx_simulation_fill_date
                  on simulation_fill (account_id, trade_date);
                create index if not exists idx_simulation_order_date
                  on simulation_order (account_id, trade_date);
                create index if not exists idx_pipeline_run_started
                  on pipeline_run (started_at desc);
                """
            )

    def upsert_stock_basic(self, rows: Iterable[StockBasic]) -> int:
        payload = [
            (
                row.ts_code,
                row.symbol,
                row.name,
                row.exchange,
                row.market,
                row.list_date.isoformat(),
                row.delist_date.isoformat() if row.delist_date else None,
                row.is_hs,
                row.status,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into stock_basic values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(ts_code) do update set
                  symbol=excluded.symbol,
                  name=excluded.name,
                  exchange=excluded.exchange,
                  market=excluded.market,
                  list_date=excluded.list_date,
                  delist_date=excluded.delist_date,
                  is_hs=excluded.is_hs,
                  status=excluded.status
                """,
                payload,
            )
        return len(payload)

    def upsert_daily_bars(self, rows: Iterable[DailyBar]) -> int:
        payload = [
            (
                row.trade_date.isoformat(),
                row.ts_code,
                row.open,
                row.high,
                row.low,
                row.close,
                row.pre_close,
                row.volume,
                row.amount,
                row.pct_chg,
                row.adj_factor,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into daily_bar values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, ts_code) do update set
                  open=excluded.open,
                  high=excluded.high,
                  low=excluded.low,
                  close=excluded.close,
                  pre_close=excluded.pre_close,
                  volume=excluded.volume,
                  amount=excluded.amount,
                  pct_chg=excluded.pct_chg,
                  adj_factor=excluded.adj_factor
                """,
                payload,
            )
        return len(payload)

    def upsert_minute_bars(self, rows: Iterable[MinuteBar]) -> int:
        payload = [
            (
                row.trade_time.isoformat(timespec="seconds"),
                row.ts_code,
                row.interval,
                row.open,
                row.high,
                row.low,
                row.close,
                row.volume,
                row.amount,
                row.adjust,
                row.source,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into minute_bar values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_time, ts_code, interval, adjust) do update set
                  open=excluded.open,
                  high=excluded.high,
                  low=excluded.low,
                  close=excluded.close,
                  volume=excluded.volume,
                  amount=excluded.amount,
                  source=excluded.source
                """,
                payload,
            )
        return len(payload)

    def upsert_realtime_quotes(self, rows: Iterable[RealtimeQuote]) -> int:
        payload = [
            (
                row.quote_time.isoformat(timespec="seconds"),
                row.ts_code,
                row.name,
                row.price,
                row.open,
                row.high,
                row.low,
                row.pre_close,
                row.volume,
                row.amount,
                row.pct_chg,
                row.source,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into realtime_quote values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(quote_time, ts_code, source) do update set
                  name=excluded.name,
                  price=excluded.price,
                  open=excluded.open,
                  high=excluded.high,
                  low=excluded.low,
                  pre_close=excluded.pre_close,
                  volume=excluded.volume,
                  amount=excluded.amount,
                  pct_chg=excluded.pct_chg
                """,
                payload,
            )
        return len(payload)

    def upsert_limit_prices(self, rows: Iterable[LimitPrice]) -> int:
        payload = [
            (row.trade_date.isoformat(), row.ts_code, row.up_limit, row.down_limit, row.limit_type)
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into limit_price values (?, ?, ?, ?, ?)
                on conflict(trade_date, ts_code) do update set
                  up_limit=excluded.up_limit,
                  down_limit=excluded.down_limit,
                  limit_type=excluded.limit_type
                """,
                payload,
            )
        return len(payload)

    def upsert_suspensions(self, rows: Iterable[Suspension]) -> int:
        payload = [(row.trade_date.isoformat(), row.ts_code, row.suspend_type, row.reason) for row in rows]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into suspension values (?, ?, ?, ?)
                on conflict(trade_date, ts_code, suspend_type) do update set
                  reason=excluded.reason
                """,
                payload,
            )
        return len(payload)

    def upsert_trade_calendar(self, rows: Iterable[TradeCalendar]) -> int:
        payload = [
            (
                row.cal_date.isoformat(),
                row.exchange,
                1 if row.is_open else 0,
                row.pretrade_date.isoformat() if row.pretrade_date else None,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into trade_calendar values (?, ?, ?, ?)
                on conflict(cal_date, exchange) do update set
                  is_open=excluded.is_open,
                  pretrade_date=excluded.pretrade_date
                """,
                payload,
            )
        return len(payload)

    def upsert_stock_pool(self, rows: Iterable[StockPoolEntry]) -> int:
        payload = [
            (
                row.trade_date.isoformat(),
                row.ts_code,
                row.name,
                row.industry,
                1 if row.is_pass else 0,
                "|".join(row.filter_reasons),
                row.listed_days,
                row.close,
                row.amount,
                row.avg_amount,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into stock_pool values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, ts_code) do update set
                  name=excluded.name,
                  industry=excluded.industry,
                  is_pass=excluded.is_pass,
                  filter_reasons=excluded.filter_reasons,
                  listed_days=excluded.listed_days,
                  close=excluded.close,
                  amount=excluded.amount,
                  avg_amount=excluded.avg_amount
                """,
                payload,
            )
        return len(payload)

    def upsert_factor_values(self, rows: Iterable[FactorValue]) -> int:
        payload = [
            (row.trade_date.isoformat(), row.ts_code, row.factor_name, row.factor_value, row.factor_score)
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into factor_value values (?, ?, ?, ?, ?)
                on conflict(trade_date, ts_code, factor_name) do update set
                  factor_value=excluded.factor_value,
                  factor_score=excluded.factor_score
                """,
                payload,
            )
        return len(payload)

    def upsert_signals(self, rows: Iterable[Signal]) -> int:
        payload = [
            (
                row.signal_date.isoformat(),
                row.trade_date.isoformat(),
                row.ts_code,
                row.signal_type.value,
                row.score,
                row.target_weight,
                row.reason,
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                insert into signal values (?, ?, ?, ?, ?, ?, ?)
                on conflict(signal_date, trade_date, ts_code, signal_type) do update set
                  score=excluded.score,
                  target_weight=excluded.target_weight,
                  reason=excluded.reason
                """,
                payload,
            )
        return len(payload)

    def load_daily_bars(self, start: date | None = None, end: date | None = None) -> list[DailyBar]:
        query = "select * from daily_bar"
        params: list[str] = []
        clauses: list[str] = []
        if start:
            clauses.append("trade_date >= ?")
            params.append(start.isoformat())
        if end:
            clauses.append("trade_date <= ?")
            params.append(end.isoformat())
        if clauses:
            query += " where " + " and ".join(clauses)
        query += " order by trade_date, ts_code"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            DailyBar(
                trade_date=date.fromisoformat(row["trade_date"]),
                ts_code=row["ts_code"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                pre_close=row["pre_close"],
                volume=row["volume"],
                amount=row["amount"],
                pct_chg=row["pct_chg"],
                adj_factor=row["adj_factor"],
            )
            for row in rows
        ]

    def load_minute_bars(self, start: date | None = None, end: date | None = None) -> list[MinuteBar]:
        query = "select * from minute_bar"
        params: list[str] = []
        clauses: list[str] = []
        if start:
            clauses.append("trade_time >= ?")
            params.append(start.isoformat())
        if end:
            clauses.append("trade_time <= ?")
            params.append(datetime.combine(end, time(23, 59, 59)).isoformat())
        if clauses:
            query += " where " + " and ".join(clauses)
        query += " order by trade_time, ts_code"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            MinuteBar(
                trade_time=datetime.fromisoformat(row["trade_time"]),
                ts_code=row["ts_code"],
                interval=row["interval"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                amount=row["amount"],
                adjust=row["adjust"],
                source=row["source"],
            )
            for row in rows
        ]

    def load_realtime_quotes(self) -> list[RealtimeQuote]:
        with self.connect() as conn:
            rows = conn.execute("select * from realtime_quote order by quote_time desc, ts_code").fetchall()
        return [
            RealtimeQuote(
                quote_time=datetime.fromisoformat(row["quote_time"]),
                ts_code=row["ts_code"],
                name=row["name"],
                price=row["price"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                pre_close=row["pre_close"],
                volume=row["volume"],
                amount=row["amount"],
                pct_chg=row["pct_chg"],
                source=row["source"],
            )
            for row in rows
        ]

    def load_stock_basic(self) -> list[StockBasic]:
        with self.connect() as conn:
            rows = conn.execute("select * from stock_basic order by ts_code").fetchall()
        return [
            StockBasic(
                ts_code=row["ts_code"],
                symbol=row["symbol"],
                name=row["name"],
                exchange=row["exchange"],
                market=row["market"],
                list_date=date.fromisoformat(row["list_date"]),
                delist_date=date.fromisoformat(row["delist_date"]) if row["delist_date"] else None,
                is_hs=row["is_hs"] or "",
                status=row["status"],
            )
            for row in rows
        ]

    def load_stock_pool(self, trade_date: date | None = None) -> list[StockPoolEntry]:
        params: list[str] = []
        query = "select * from stock_pool"
        if trade_date:
            query += " where trade_date = ?"
            params.append(trade_date.isoformat())
        query += " order by is_pass desc, ts_code"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            StockPoolEntry(
                trade_date=date.fromisoformat(row["trade_date"]),
                ts_code=row["ts_code"],
                name=row["name"],
                industry=row["industry"],
                is_pass=bool(row["is_pass"]),
                filter_reasons=tuple(reason for reason in row["filter_reasons"].split("|") if reason),
                listed_days=row["listed_days"],
                close=row["close"],
                amount=row["amount"],
                avg_amount=row["avg_amount"],
            )
            for row in rows
        ]

    def load_factor_values(self, trade_date: date | None = None) -> list[FactorValue]:
        params: list[str] = []
        query = "select * from factor_value"
        if trade_date:
            query += " where trade_date = ?"
            params.append(trade_date.isoformat())
        query += " order by trade_date, ts_code, factor_name"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            FactorValue(
                trade_date=date.fromisoformat(row["trade_date"]),
                ts_code=row["ts_code"],
                factor_name=row["factor_name"],
                factor_value=row["factor_value"],
                factor_score=row["factor_score"],
            )
            for row in rows
        ]

    def load_signals(self, signal_date: date | None = None) -> list[Signal]:
        params: list[str] = []
        query = "select * from signal"
        if signal_date:
            query += " where signal_date = ?"
            params.append(signal_date.isoformat())
        query += " order by score desc, ts_code"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            Signal(
                signal_date=date.fromisoformat(row["signal_date"]),
                trade_date=date.fromisoformat(row["trade_date"]),
                ts_code=row["ts_code"],
                signal_type=SignalType(row["signal_type"]),
                score=row["score"],
                target_weight=row["target_weight"],
                reason=row["reason"],
            )
            for row in rows
        ]

    def load_limit_prices(self) -> dict[tuple[date, str], LimitPrice]:
        with self.connect() as conn:
            rows = conn.execute("select * from limit_price").fetchall()
        return {
            (date.fromisoformat(row["trade_date"]), row["ts_code"]): LimitPrice(
                trade_date=date.fromisoformat(row["trade_date"]),
                ts_code=row["ts_code"],
                up_limit=row["up_limit"],
                down_limit=row["down_limit"],
                limit_type=row["limit_type"],
            )
            for row in rows
        }

    def load_suspensions(self) -> set[tuple[date, str]]:
        with self.connect() as conn:
            rows = conn.execute("select trade_date, ts_code from suspension where suspend_type = 'suspend'").fetchall()
        return {(date.fromisoformat(row["trade_date"]), row["ts_code"]) for row in rows}

    def table_status(self) -> list[dict[str, object]]:
        specs = [
            ("stock_basic", None),
            ("trade_calendar", "cal_date"),
            ("daily_bar", "trade_date"),
            ("minute_bar", "trade_time"),
            ("realtime_quote", "quote_time"),
            ("limit_price", "trade_date"),
            ("suspension", "trade_date"),
            ("stock_pool", "trade_date"),
            ("factor_value", "trade_date"),
            ("signal", "signal_date"),
            ("simulation_account", "last_trade_date"),
            ("simulation_order", "trade_date"),
            ("simulation_fill", "trade_date"),
            ("simulation_position", "trade_date"),
            ("simulation_equity_curve", "trade_date"),
            ("pipeline_run", "trade_date"),
        ]
        with self.connect() as conn:
            result: list[dict[str, object]] = []
            for table_name, date_column in specs:
                count = conn.execute(f"select count(*) as count from {table_name}").fetchone()["count"]
                latest_date = None
                if date_column:
                    row = conn.execute(f"select max({date_column}) as latest_date from {table_name}").fetchone()
                    latest_date = row["latest_date"]
                result.append({"table": table_name, "recordCount": count, "latestDate": latest_date})
            return result
