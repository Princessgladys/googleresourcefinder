import datetime
import os
import re
import selenium
import time
import unittest

from google.appengine.api import memcache, users

import cache
import scrape
from model import Account, MinimalSubject, Subject, db


class Struct:
    """A plain container for attributes: like a dictionary but more concise."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


# Configuration profiles for Selenium testing.
CONFIGS = {
    'local': Struct(
        base_url='http://localhost:8081',
        user_name='test@example.com',
        login_form='//form[@action="/_ah/login"]',
        login_email='//input[@id="email"]',
        login_submit='//input[@id="submit-login"]',
        timeout=30
    ),
    'dev': Struct(
        base_url='http://resourcemapper.appspot.com',
        user_name='test@example.com',
        password='',
        login_form='//form[@id="gaia_loginform"]',
        login_email='//input[@id="Email"]',
        login_password='//input[@id="Passwd"]',
        login_submit='//input[@id="signIn"]',
        timeout=30
    )
}


class Regex:
    """A wrapper for a regular expression that shows the original regex
    in its representation, to make test failures easier to understand."""

    def __init__(self, regex):
        """Compiles the given regular expression, allowing '.' to match
        any character including newline."""
        self.regex = regex
        self.re = re.compile(regex, re.DOTALL)

    def __repr__(self):
        return '<Regex %s>' % self.regex

    def match(self, target):
        """Returns True if the ENTIRE target string matches this regex."""
        # The 'match' method only anchors at the beginning, not the end,
        # so we additionally check that we matched all the way to the end.
        match = self.re.match(target)
        return match and match.end() == len(target)


def match(expected_string_or_regex, actual_string):
    """Returns True if the actual_string entirely matches the expected
    string or regular expression."""
    if isinstance(expected_string_or_regex, Regex):
        return expected_string_or_regex.match(actual_string)
    else:
        return actual_string == expected_string_or_regex


class SeleniumTestCase(unittest.TestCase, selenium.selenium):
    def setUp(self):
        # Select a test config based on the TEST_CONFIG environment variable.
        config_name = os.environ.get('TEST_CONFIG', '')
        if config_name not in CONFIGS:
            raise Exception('TEST_CONFIG must be one of: %r' % CONFIGS.keys())
        self.config = CONFIGS[config_name]

        # Start up Selenium.
        selenium.selenium.__init__(
            self, 'localhost', 4444, '*chrome', 'https://www.google.com/')
        self.start()

    def tearDown(self):
        # Hitting any page with flush=yes will flush the appserver's caches.
        s = scrape.Session()
        s.go(self.config.base_url + '/help?flush=yes')

        # Shut down Selenium.
        self.stop()

    def login(self, path=None):
        """Navigates to the given path, logging in if necessary, and waits for
        the page to load.  Use this method to load the first page in a test.
        Returns True if a login form appeared and was submitted."""
        if path is not None:
            self.open_path(path)
        if self.is_element_present(self.config.login_form):
            self.type(self.config.login_email, self.config.user_name)
            if 'password' in self.config:
                self.type(self.config.login_password, self.config.password)
            self.click(self.config.login_submit)
            self.wait_for_load()
            return True
        return False

    # ---------------------------------------- datastore convenience methods

    def set_default_permissions(self, actions):
        """Sets the permissions for the special 'default' account."""
        Account(key_name='default', actions=actions).put()
        cache.DEFAULT_ACCOUNT.flush()

    def delete_default_account(self):
        """Deletes the special 'default' account."""
        account = Account.get_by_key_name('default')
        if account:
            account.delete()
        cache.DEFAULT_ACCOUNT.flush()

    def put_account(self, **properties):
        """Stores a test Account with the specified properties.  (By default,
        the e-mail address is determined by the test configuration.)"""
        account = Account(email=self.config.user_name)
        for key, value in properties.items():
            setattr(account, key, value)
        account.put()

    def delete_account(self):
        """Deletes the test Account."""
        account = Account.all().filter('email =', self.config.user_name).get()
        if account:
            account.delete()

    def put_subject(self, subdomain, subject_name, type='hospital',
                    observed=None, email='test@example.com',
                    nickname='nickname_foo', affiliation='affiliation_foo',
                    comment='comment_foo', **attribute_values):
        """Stores a Subject and its corresponding MinimalSubject."""
        key_name = subdomain + ':' + subject_name
        subject = Subject(key_name=key_name, type=type)
        if observed is None:
            observed = datetime.datetime.now()
        user = users.User(email)
        for key, value in attribute_values.items():
            subject.set_attribute(
                key, value, observed, user, nickname, affiliation, comment)
        subject.put()
        minimal = MinimalSubject(subject, key_name=key_name, type=type)
        for key, value in attribute_values.items():
            minimal.set_attribute(key, value)
        minimal.put()

    def delete_subject(self, subdomain, subject_name):
        """Deletes a Subject and all its child entities from the datastore."""
        subject = Subject.get(subdomain, subject_name)
        children = db.Query(keys_only=True).ancestor(subject).fetch(200)
        while children:
            db.delete(children)
            children = db.Query(keys_only=True).ancestor(subject).fetch(200)
        db.delete(subject)

    # ----------------------------------------- Selenium convenience methods

    def open_path(self, path):
        """Navigates to a given path under the server's base URL, then
        waits for the page to load."""
        self.open(self.config.base_url + path) 

    def get_status_code(self, path):
        """Navigates to a given path and returns the HTTP status code."""
        # Sadly, Selenium always raises a generic Exception -- we have to
        # parse the text of the error message to get the status code.
        try:
            self.open_path(path)
        except Exception, e:
            match = re.match(r'.*Response_Code = (\d+)', str(e))
            if match:
                return int(match.group(1))
        return 200

    def wait_for_load(self):
        """Waits for a page to load, timing out after 30 seconds."""
        self.wait_for_page_to_load(str(self.config.timeout * 1000))

    def wait_until(self, function, *args, **kwargs):
        """Waits until the given function (called with the given arguments and
        keyword arguments) returns a true value, timing out after 30 seconds."""
        start = time.time()
        while not function(*args, **kwargs):
            if time.time() - start > 30:
                self.fail('Timed out: %r %r %r' % (function, args, kwargs))
            time.sleep(0.2)

    def wait_for_element(self, locator):
        """Waits until the given element is present."""
        # For some reason, this wait doesn't always work unless we do it twice.
        self.wait_until(self.is_element_present, locator)
        self.wait_until(self.is_element_present, locator)

    def click_and_wait(self, locator):
        """Clicks a link that is supposed to load a page, then waits for the
        page to finish loading."""
        self.click(locator)
        self.wait_for_load()

    def click_and_wait_for_new_window(self, link_id):
        """Clicks a link that is supposed to open a new window, waits for the
        new window to load, and switches to the new window for subsequent
        Selenium commands."""
        self.click('id=%s' % link_id)
        self.select_window('_blank')
        self.wait_for_load()

    def is_not_visible(self, locator):
        """Returns true if an element is missing or not visible. Useful with
        wait_until."""
        return (not self.is_element_present(locator) or
                not self.is_visible(locator))

    def assert_element(self, locator):
        """Asserts that the given element is present."""
        self.assertTrue(self.is_element_present(locator),
            'Element %s is unexpectedly missing' % locator)

    def assert_no_element(self, locator):
        """Asserts that the given element is not present."""
        self.assertFalse(self.is_element_present(locator),
            'Element %s is unexpectedly present' % locator)

    def assert_text(self, string_or_regex, locator):
        """Asserts that the text of the given element entirely matches the
        given string or regular expression."""
        text = self.get_text(locator)
        self.assertTrue(
            match(string_or_regex, text),
            'Element %s: actual text %r does not match %r' %
            (locator, text, string_or_regex))

    def assert_no_text(self, string_or_regex, locator):
        """Asserts that the text of the given element does not contain the
        given string or regular expression."""
        text = self.get_text(locator)
        self.assertFalse(
            match(string_or_regex, text),
            'Element %s: actual text %r does match %r' %
            (locator, text, string_or_regex))

    def assert_value(self, string_or_regex, locator):
        """Asserts that the entire value of the given element exactly matches
        the given string, or matches the given regular expression."""
        value = self.get_value(locator)
        self.assertTrue(
            match(string_or_regex, value),
            'Element %s: actual value %r does not match %r' %
            (locator, value, string_or_regex))

    def assert_text_present(self, string):
        """Asserts that the given text is present somewhere on the page."""
        self.assertTrue(
            self.is_text_present(string),
            'Expected text %r is not present on page %s' %
            (string, self.get_location())
        )

    def assert_text_not_present(self, string):
        """Asserts that the given text is not present anywhere on the page."""
        self.assertFalse(
            self.is_text_present(string),
            'Unexpected text %r is present on page %s' %
            (string, self.get_location())
        )
