from selenium_test_case import SeleniumTestCase
import unittest


class DocsTest(SeleniumTestCase):
    def test_map_loaded(self):
        self.open_path('/help')
        self.wait_for_load()
        self.assert_text('Frequently Asked Questions', '//h1')
        self.assert_element('//h1[.="Frequently Asked Questions"]')

        self.click('link=Terms of Service')
        self.wait_for_load()
        self.assert_text('Terms of Service for Google Resource Finder', '//h1')

        self.click('link=Google Resource Finder Privacy Policy')
        self.wait_for_load()
        self.assert_text('Google Privacy Policy', '//h1')


if __name__ == "__main__":
    unittest.main()
