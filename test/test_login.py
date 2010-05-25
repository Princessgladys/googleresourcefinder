from resource_mapper_test_case import ResourceMapperTestCase
import unittest

class LoginTestCase(ResourceMapperTestCase):
    def test_map_loaded(self):
        self.assertTrue(self.login('/'))
        self.assertTrue(self.s.is_element_present('map'))

if __name__ == "__main__":
    unittest.main()
