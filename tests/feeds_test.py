from scrape_test_case import ScrapeTestCase


class FeedsTest(ScrapeTestCase):
    def test_empty_feed(self):
        doc = self.s.go('http://localhost:8081/feeds/foo?subdomain=haiti')
        assert doc.first('atom:feed')
