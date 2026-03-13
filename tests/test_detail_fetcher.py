import unittest
from unittest.mock import Mock, patch

from scraper.detail_fetcher import HybridDetailFetcher


class HybridDetailFetcherTests(unittest.TestCase):
    def test_uses_http_result_when_html_is_usable(self):
        fetcher = HybridDetailFetcher(browser_fetcher=Mock())
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.encoding = "utf-8"
        response.apparent_encoding = "utf-8"
        response.text = "<html><body>" + ("a" * 800) + "</body></html>"

        with patch.object(fetcher.session, "get", return_value=response):
            html = fetcher.fetch("https://example.com")

        assert html is not None
        self.assertIn("<html>", html)
        assert fetcher.browser_fetcher is not None
        fetcher.browser_fetcher.get_page.assert_not_called()
        fetcher.close()

    def test_falls_back_to_browser_when_http_html_is_unusable(self):
        browser = Mock()
        browser.get_page.return_value = "<html><body>browser</body></html>"
        fetcher = HybridDetailFetcher(browser_fetcher=browser)
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html"}
        response.encoding = "utf-8"
        response.apparent_encoding = "utf-8"
        response.text = "访问过于频繁"

        with patch.object(fetcher.session, "get", return_value=response):
            html = fetcher.fetch("https://example.com")

        self.assertEqual(html, "<html><body>browser</body></html>")
        browser.get_page.assert_called_once()
        fetcher.close()

    def test_prefetch_http_returns_only_successful_results(self):
        fetcher = HybridDetailFetcher(browser_fetcher=Mock())

        def fake_http(url):
            if url.endswith("a"):
                return "<html>a</html>"
            return None

        with patch.object(fetcher, "_fetch_via_http", side_effect=fake_http):
            results = fetcher.prefetch_http(
                ["https://example.com/a", "https://example.com/b"],
                max_workers=2,
            )

        self.assertEqual(results, {"https://example.com/a": "<html>a</html>"})
        fetcher.close()


if __name__ == "__main__":
    unittest.main()
