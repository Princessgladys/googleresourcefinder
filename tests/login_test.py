from selenium_test_case import SeleniumTestCase


class LoginTest(SeleniumTestCase):
    def test_map_loaded(self):
        self.assertTrue(self.login('/'))
        self.assertTrue(self.is_element_present('map'))
