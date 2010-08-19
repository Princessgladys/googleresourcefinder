import scrape
import unittest


class ScrapeTestCase(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.s = scrape.Session()
