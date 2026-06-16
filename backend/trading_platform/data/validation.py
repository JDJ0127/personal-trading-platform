from __future__ import annotations

from dataclasses import dataclass

from trading_platform.models import DailyBar


@dataclass(frozen=True)
class ValidationIssue:
    table: str
    key: str
    message: str


def validate_daily_bar(bar: DailyBar) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    key = f"{bar.trade_date.isoformat()}:{bar.ts_code}"

    if bar.high < max(bar.open, bar.close):
        issues.append(ValidationIssue("daily_bar", key, "high is below open or close"))
    if bar.low > min(bar.open, bar.close):
        issues.append(ValidationIssue("daily_bar", key, "low is above open or close"))
    if min(bar.open, bar.high, bar.low, bar.close, bar.pre_close) <= 0:
        issues.append(ValidationIssue("daily_bar", key, "price must be positive"))
    if bar.volume < 0:
        issues.append(ValidationIssue("daily_bar", key, "volume cannot be negative"))
    if bar.amount < 0:
        issues.append(ValidationIssue("daily_bar", key, "amount cannot be negative"))
    if bar.adj_factor <= 0:
        issues.append(ValidationIssue("daily_bar", key, "adj_factor must be positive"))

    return issues


def validate_daily_bars(bars: list[DailyBar]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[tuple[str, str]] = set()

    for bar in bars:
        duplicate_key = (bar.trade_date.isoformat(), bar.ts_code)
        if duplicate_key in seen:
            issues.append(ValidationIssue("daily_bar", ":".join(duplicate_key), "duplicate daily bar"))
        seen.add(duplicate_key)
        issues.extend(validate_daily_bar(bar))

    return issues

