from selenium_test_case import SeleniumTestCase
import unittest

class DocsTestCase(SeleniumTestCase):
    def test_map_loaded(self):
        self.open_path('/help')
        self.wait_for_load()
        self.assertTrue(self.is_text_present('Frequently Asked Questions'))

        self.click('link=Terms of Service')
        self.wait_for_load()
        self.assertTrue(self.is_text_present(
            'Terms of Service for Google Resource Finder'))

        self.click('link=Google Resource Finder Privacy Policy')
        self.wait_for_load()
        self.assertTrue(self.is_text_present('Google Privacy Policy'))

if __name__ == "__main__":
    unittest.main()
