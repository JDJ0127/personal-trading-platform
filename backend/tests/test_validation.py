from datetime import date
from unittest import TestCase

from trading_platform.data.validation import validate_daily_bar
from trading_platform.models import DailyBar


class ValidationTest(TestCase):
    def test_validate_daily_bar_rejects_invalid_ohlc(self) -> None:
        bar = DailyBar(
            trade_date=date(2026, 6, 1),
            ts_code="300308.SZ",
            open=10,
            high=9,
            low=8,
            close=10,
            pre_close=9.8,
            volume=100,
            amount=1000,
        )

        issues = validate_daily_bar(bar)

        self.assertTrue(any(issue.message == "high is below open or close" for issue in issues))
