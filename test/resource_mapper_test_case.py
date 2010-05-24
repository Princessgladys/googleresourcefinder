from selenium import selenium
import os
import time
import unittest

ENV_OPTIONS = {
    'local': {
        'base_url': 'http://localhost:8080',
        'is_local': True, 
        'user_name': 'test@example.com',
        'login_form': '//form[@action="/_ah/login"]',
        'login_email': '//input[@id="email"]',
        'login_submit': '//input[@id="submit-login"]'
    }, 
    'dev': {
        'base_url': 'http://resourcemapper.appspot.com',
        'is_local': False, 
        'user_name': 'test@example.com',
        'password': '',
        'login_form': '//form[@id="gaia_loginform"]',
        'login_email': '//input[@id="Email"]',
        'login_password': '//input[@id="Passwd"]',
        'login_submit': '//input[@id="signIn"]'
    } 
} 

class ResourceMapperTestCase(unittest.TestCase):         
    def setUp(self):
        self.initEnvironment()
        self.verificationErrors = []
        self.s = selenium('localhost', 4444, '*chrome', 
                          'https://www.google.com/')
        self.s.start()

    def tearDown(self):
        self.s.stop()
        self.assertEqual([], self.verificationErrors)
    
    def login(self, path):
        """Attempts to open the given path, logging in if necessary.  Use
        this method to load the first page in a test.  Returns True if the
        login form was submitted, or False if no login form appeared."""
        self.open_path(path)
        if self.s.is_element_present(self.environment['login_form']):
            self.s.type(self.environment['login_email'],
                        self.environment['user_name'])
            if not self.environment['is_local']:
                self.s.type(self.environment['login_password'],
                            self.environment['password'])
            self.s.click(self.environment['login_submit'])
            self.s.wait_for_page_to_load('30000')
            return True
        return False

    def initEnvironment(self):
        if not os.environ.has_key('env'):
            raise Exception('Please specify environment env = {local, dev}')
        envType = os.environ['env']
        self.environment = ENV_OPTIONS[envType]

    def open_path(self, path):
        """Navigates to a given path under the server's base URL."""
        self.s.open(self.environment['base_url'] + path) 

    def wait_for_load(self):
        """Waits for a page to load, timing out after 30 seconds."""
        self.s.wait_for_page_to_load('30000')

    def wait_until(self, function, *args, **kwargs):
        """Waits until the given function (called with the given arguments and
        keyword arguments) returns a true value, timing out after 30 seconds."""
        start = time.time()
        while not function(*args, **kwargs):
            if time.time() - start > 30:
                self.fail('timed out: %r %r %r' % (function, args, kwargs))
            time.sleep(0.2)

    def wait_for_element(self, locator):
       self.wait_until(self.s.is_element_present, locator)

    def assert_element(self, locator):
       self.assertTrue(self.s.is_element_present(locator))

    def assert_no_element(self, locator):
       self.assertFalse(self.s.is_element_present(locator))

    def assert_text(self, text, locator):
       self.assertEquals(text, self.s.get_text(locator))

    def assert_value(self, value, locator):
       self.assertEquals(value, self.s.get_value(locator))
