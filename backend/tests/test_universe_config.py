from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.universe.config import load_universe_codes, merge_universe_codes


class UniverseConfigTest(TestCase):
    def test_load_universe_codes_filters_disabled_and_dedupes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "ts_code,name,enabled\n"
                "600030.SH,中信证券,1\n"
                "300308.SZ,中际旭创,true\n"
                "600030.SH,重复,1\n"
                "000001.SZ,平安银行,0\n",
                encoding="utf-8",
            )

            codes = load_universe_codes(path)

            self.assertEqual(codes, ["600030.SH", "300308.SZ"])

    def test_load_universe_codes_requires_ts_code_column(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("code,name\n600030.SH,中信证券\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_universe_codes(path)

    def test_merge_universe_codes_keeps_order(self) -> None:
        codes = merge_universe_codes(["600030.SH", "300308.SZ"], ["300308.SZ", "000001.SZ"])

        self.assertEqual(codes, ["600030.SH", "300308.SZ", "000001.SZ"])

    def test_default_core_universe_has_validation_scale(self) -> None:
        root = Path(__file__).resolve().parents[2]
        codes = load_universe_codes(root / "config" / "universe_core.csv")

        self.assertGreaterEqual(len(codes), 50)
        self.assertIn("600030.SH", codes)
        self.assertIn("300750.SZ", codes)
