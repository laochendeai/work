import unittest
from urllib.parse import parse_qs, urlparse

from scraper.ccgp_bxsearcher import BxSearchParams, CCGPBxSearcher


class CCGPBxSearcherUrlTests(unittest.TestCase):
    def test_build_url_maps_query_params_for_single_source_ccgp(self):
        searcher = CCGPBxSearcher(page=None)
        url = searcher.build_url(
            BxSearchParams(
                kw="智能",
                search_type="fulltext",
                bid_sort="central",
                pin_mu="engineering",
                bid_type="中标公告",
                time_type="custom",
                start_date="2026-03-01",
                end_date="2026-03-13",
            ),
            page_index=3,
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "search.ccgp.gov.cn")
        self.assertEqual(parsed.path, "/bxsearch")
        self.assertEqual(params["kw"], ["智能"])
        self.assertEqual(params["searchtype"], ["2"])
        self.assertEqual(params["bidSort"], ["1"])
        self.assertEqual(params["pinMu"], ["2"])
        self.assertEqual(params["bidType"], ["7"])
        self.assertEqual(params["timeType"], ["6"])
        self.assertEqual(params["start_time"], ["2026:03:01"])
        self.assertEqual(params["end_time"], ["2026:03:13"])
        self.assertEqual(params["page_index"], ["3"])
        self.assertEqual(params["dbselect"], ["bidx"])

    def test_build_url_requires_dates_for_custom_time(self):
        searcher = CCGPBxSearcher(page=None)
        with self.assertRaises(ValueError):
            searcher.build_url(
                BxSearchParams(
                    kw="智能",
                    time_type="custom",
                )
            )


if __name__ == "__main__":
    unittest.main()
