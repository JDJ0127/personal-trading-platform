import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.config import load_app_config


class ConfigTest(TestCase):
    def test_load_app_config_reads_dotenv_without_overriding_environment(self) -> None:
        with TemporaryDirectory() as tmpdir:
            dotenv = Path(tmpdir) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "TUSHARE_TOKEN=from_file",
                        "TRADING_DB=data/from_file.sqlite",
                        "BACKTEST_OUTPUT=src/data/from_file.json",
                    ]
                ),
                encoding="utf-8",
            )

            keys = ["TUSHARE_TOKEN", "TRADING_DB", "BACKTEST_OUTPUT"]
            previous = {key: os.environ.get(key) for key in keys}
            os.environ["TUSHARE_TOKEN"] = "from_env"
            try:
                config = load_app_config(dotenv)
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

        self.assertEqual(config.tushare_token, "from_env")
        self.assertEqual(config.trading_db, Path("data/from_file.sqlite"))
        self.assertEqual(config.backtest_output, Path("src/data/from_file.json"))
