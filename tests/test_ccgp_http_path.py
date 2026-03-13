import unittest
from unittest.mock import Mock, patch

from scraper.ccgp_bxsearcher import BxSearchParams, CCGPBxSearcher


class CCGPHttpPathTests(unittest.TestCase):
    def test_search_uses_http_results_without_browser_page(self):
        searcher = CCGPBxSearcher(page=None)
        html = """
        <html><body>
          <ul class="vT-srch-result-list-bid">
            <li>
              <a href="/cggg/test1.htm">测试公告一</a>
              <span>2026-03-13 | 采购人：甲单位 | 代理机构：乙机构</span>
            </li>
          </ul>
        </body></html>
        """

        with patch.object(
            searcher, "_fetch_search_page_http", side_effect=[html, "<html></html>"]
        ):
            results = searcher.search(BxSearchParams(kw="智能"), max_pages=2)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "测试公告一")
        self.assertEqual(results[0]["buyer_name"], "甲单位")
        self.assertEqual(results[0]["agent_name"], "乙机构")
        searcher.close()

    def test_search_falls_back_to_browser_when_first_http_page_unavailable(self):
        page = Mock()
        page.goto.return_value = None
        page.evaluate.return_value = ""
        page.content.return_value = """
        <html><body>
          <ul class="vT-srch-result-list-bid">
            <li><a href="/cggg/test2.htm">测试公告二</a><span>2026-03-14</span></li>
          </ul>
        </body></html>
        """
        page.query_selector.return_value = None

        searcher = CCGPBxSearcher(page=page)
        with patch.object(searcher, "_fetch_search_page_http", return_value=None):
            results = searcher.search(BxSearchParams(kw="智能"), max_pages=1)

        self.assertEqual(len(results), 1)
        page.goto.assert_called_once()
        searcher.close()


if __name__ == "__main__":
    unittest.main()
