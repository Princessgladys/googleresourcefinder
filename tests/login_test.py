from selenium_test_case import SeleniumTestCase
import unittest


class LoginTest(SeleniumTestCase):
    def test_map_loaded(self):
        assert self.login('/')
        self.assert_element('map')


if __name__ == "__main__":
    unittest.main()
