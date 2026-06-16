from unittest import TestCase

from trading_platform.news.rules import build_news_report


class NewsRulesTest(TestCase):
    def test_build_news_report_maps_sample_events(self) -> None:
        report = build_news_report()

        self.assertEqual(report["summary"]["eventCount"], 3)
        self.assertEqual(report["summary"]["positiveCount"], 2)
        self.assertEqual(report["summary"]["negativeCount"], 1)
        self.assertEqual(report["events"][0]["sector"], "算力、数据中心")
        self.assertEqual(report["events"][2]["sentiment"], "negative")

