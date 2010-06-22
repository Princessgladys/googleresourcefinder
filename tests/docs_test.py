from selenium_test_case import SeleniumTestCase


class DocsTest(SeleniumTestCase):
    def test_map_loaded(self):
        self.open_path('/help')
        self.assert_text_present('Frequently Asked Questions')

        self.click_and_wait('link=Terms of Service')
        self.assert_text_present('Terms of Service for Google Resource Finder')

        self.click_and_wait('link=Privacy Policy')
        self.assert_text_present('Google Resource Finder Privacy Policy')
