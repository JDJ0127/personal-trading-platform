import argparse
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.cli.main import run_ingest, run_paper_pipeline, run_paper_replay


class PaperPipelineTest(TestCase):
    def test_run_paper_pipeline_exports_daily_account_reports(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            args = argparse.Namespace(
                source="sample",
                data_dir=Path("backend/sample_data"),
                db=root / "paper.sqlite",
                token=None,
                start=None,
                end=date(2026, 6, 8),
                trade_date=None,
                ts_code=None,
                codes=None,
                universe_file=Path("config/universe_core.csv"),
                code_offset=0,
                max_codes=None,
                all_stock=False,
                skip_sync=False,
                skip_stock_basic=False,
                adjustflag="2",
                timeout=20.0,
                account_id="paper-test",
                account_name="测试模拟账户",
                account_output=root / "simulationAccount.json",
                data_status_output=root / "dataStatus.json",
                stock_pool_output=root / "stockPool.json",
                signal_output=root / "signalReport.json",
                market_risk_output=root / "marketRisk.json",
                simulation_output=root / "simulationReport.json",
                news_output=root / "newsReport.json",
                run_log_output=root / "runLog.json",
            )

            run_paper_pipeline(args)
            account = json.loads(args.account_output.read_text(encoding="utf-8"))
            run_log = json.loads(args.run_log_output.read_text(encoding="utf-8"))

            self.assertEqual(account["account"]["accountId"], "paper-test")
            self.assertEqual(account["account"]["lastTradeDate"], "2026-06-08")
            self.assertEqual(run_log["summary"]["latestStatus"], "success")
            self.assertEqual(run_log["runs"][0]["workflow"], "paper-pipeline")
            self.assertTrue(args.data_status_output.exists())
            self.assertTrue(args.signal_output.exists())
            self.assertTrue(args.simulation_output.exists())

    def test_run_paper_replay_advances_account_across_date_range(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "paper.sqlite"
            run_ingest(argparse.Namespace(data_dir=Path("backend/sample_data"), db=db_path))
            args = argparse.Namespace(
                db=db_path,
                start=date(2026, 6, 3),
                end=date(2026, 6, 8),
                account_id="paper-replay-test",
                account_name="测试回放账户",
                reset_account=True,
                source_name="SampleReplay",
                account_output=root / "simulationAccount.json",
                data_status_output=root / "dataStatus.json",
                stock_pool_output=root / "stockPool.json",
                signal_output=root / "signalReport.json",
                market_risk_output=root / "marketRisk.json",
                simulation_output=root / "simulationReport.json",
                news_output=root / "newsReport.json",
                run_log_output=root / "runLog.json",
            )

            run_paper_replay(args)
            account = json.loads(args.account_output.read_text(encoding="utf-8"))
            run_log = json.loads(args.run_log_output.read_text(encoding="utf-8"))
            market_risk = json.loads(args.market_risk_output.read_text(encoding="utf-8"))

            self.assertEqual(account["account"]["accountId"], "paper-replay-test")
            self.assertEqual(account["account"]["lastTradeDate"], "2026-06-08")
            self.assertGreaterEqual(account["summary"]["equityPointCount"], 4)
            self.assertEqual(market_risk["tradeDate"], "2026-06-08")
            self.assertEqual(run_log["summary"]["latestStatus"], "success")
            self.assertEqual(run_log["runs"][0]["workflow"], "paper-replay")
