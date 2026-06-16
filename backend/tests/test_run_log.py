from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.simulation.run_log import finish_pipeline_run, start_pipeline_run, write_run_log_report


class RunLogTest(TestCase):
    def test_pipeline_run_log_records_status_and_exports_json(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "run.sqlite")
            run_id = start_pipeline_run(store, "paper-pipeline", "sample", "paper-main", date(2026, 6, 8))
            finish_pipeline_run(
                store,
                run_id,
                "success",
                {
                    "stockCount": 2,
                    "signalCount": 1,
                    "plannedOrderCount": 1,
                    "blockedOrderCount": 0,
                    "orderCount": 1,
                    "fillCount": 1,
                },
            )
            report = write_run_log_report(store, Path(tmpdir) / "runLog.json")

            self.assertEqual(report["summary"]["runCount"], 1)
            self.assertEqual(report["summary"]["latestStatus"], "success")
            self.assertEqual(report["runs"][0]["runId"], run_id)
            self.assertEqual(report["runs"][0]["fillCount"], 1)
