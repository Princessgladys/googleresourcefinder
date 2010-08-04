# Copyright 2009-2010 by Ka-Ping Yee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util

import StringIO
import access
import cache
from calendar import timegm
import cgi
import cgitb
import config
from datetime import date as Date
from datetime import datetime as DateTime  # all DateTimes are always in UTC
from datetime import timedelta as TimeDelta
from feeds.crypto import get_secret
from feeds.errors import ErrorMessage, Redirect
import gzip
from html import html_escape
import logging
import model
import os
import pickle
import re
import sys
import unicodedata
import urllib
import urlparse

ROOT = os.path.dirname(__file__)

# Set up localization.
from django.conf import settings
try:
    settings.configure()
except:
    pass
settings.LANGUAGE_CODE = 'en'
settings.USE_I18N = True
settings.LOCALE_PATHS = (os.path.join(ROOT, 'locale'),)
import django.utils.translation
# We use lazy translation in this file because the locale isn't set until the
# Handler is initialized.
from django.utils.translation import gettext_lazy as _

# Attributes exported to CSV that should currently remain hidden from the
# info window bubble and edit view.
# TODO(shakusa) Un-hide these post-v1 when view/edit support is better
HIDDEN_ATTRIBUTE_NAMES = ['accuracy', 'region_id', 'district_id', 'commune_id',
                          'commune_code', 'sante_id']

def fetch_all(query):
    """Gets all the results of a query as efficiently as possible.  If the
    query's results were previously obtained, they are reused."""
    if not hasattr(query, 'results'):
        # Calling fetch() is faster than iterating one by one.  'limit' can
        # be arbitrarily large, but 'offset' cannot exceed 1000 -- so we
        # only get one attempt.  We assume less than a million results.
        query.results = query.fetch(1000000)
    return query.results

def strip(text):
    return text.strip()

def validate_yes(text):
    return (text.lower() in ['y', 'yes']) and 'yes' or ''

def validate_action(text):
    return text in access.ACTIONS and text

def validate_float(text):
    try:
        return float(text)
    except ValueError:
        return None

def get_lang():
    """Gets the current Django language code (a lowercase language code
    followed by an optional hyphen and lowercase subcode)."""
    return django.utils.translation.get_language()

def get_locale(lang=None):
    """Gets the current Django locale code (a lowercase two-letter language
    code followed by an optional underscore and uppercase country code),
    or converts the specified Django language code to a locale code."""
    return django.utils.translation.to_locale(lang or get_lang())

def get_message(namespace, name, locale=''):
    """Gets a translated message (in the current language)."""
    message = cache.MESSAGES.get((namespace, name))
    return message and getattr(message, locale or get_locale()) or name

def split_key_name(entity):
    """Splits the key_name of a Subject or SubjectType entity into the
    subdomain and the subject name, or the subdomain and the type name."""
    return entity.key().name().split(':', 1)

class Struct:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Handler(webapp.RequestHandler):
    auto_params = {
        'embed': validate_yes,
        'flush': validate_yes,
        'subject_name': strip,  # without the subdomain (it would be redundant)
        'subject_type': strip,  # without the subdomain (it would be redundant)
        'lang': strip,  # a Django language code (e.g. 'en', 'fr-ca', 'pt-br')
        'lat': validate_float,
        'lon': validate_float,
        'print': validate_yes,
        'rad': validate_float,
        'action': validate_action,
    }

    def require_action_permitted(self, action):
        """Returns if and only if the given action is allowed.  Otherwise,
        aborts with an error message or redirection to the login page."""
        if access.check_action_permitted(self.account, self.subdomain, action):
            return
        self.require_logged_in_user()  # if not logged in, offer login page
        logging.info('utils.py: unauthorized edit attempt')
        #i18n: Error message
        raise ErrorMessage(403, _('Unauthorized user.'))

    def require_logged_in_user(self):
        """Redirect to login in case there is no user"""
        if not self.user:
            raise Redirect(users.create_login_url(self.request.uri))

    def render(self, path, **params):
        """Renders the template at the given path with the given parameters
        to response.out."""
        self.write(self.render_to_string(path, **params))

    def render_to_string(self, path, **params):
        """Renders the template at the given path with the given parameters
           to a string that is returned."""
        return webapp.template.render(os.path.join(ROOT, path), params)

    def write(self, text):
        self.response.out.write(text)

    def initialize(self, request, response, user_for_test=None):
        """Performs common initialization steps for all requests (subdomain
        selection, language selection, query parameter validation)."""
        webapp.RequestHandler.initialize(self, request, response)

        self.user = user_for_test or users.get_current_user()
        self.account = access.check_and_log(request, self.user)
        for name in request.headers.keys():
            if name.lower().startswith('x-appengine'):
                logging.debug('%s: %s' % (name, request.headers[name]))

        # Determine the subdomain.
        self.subdomain = ''
        levels = self.request.headers.get('Host', '').split('.')
        if levels[-2:] == ['appspot', 'com'] and len(levels) >= 4:
            # foo.resource-finder.appspot.com -> subdomain 'foo'
            # bar.kpy.latest.resource-finder.appspot.com -> subdomain 'bar'
            self.subdomain = levels[0]
        # The 'subdomain' query parameter always overrides the hostname.
        self.subdomain = self.request.get('subdomain', self.subdomain)

        # To be safe, we purge the in-memory portion of MinimalSubjectCache
        # before each request to be sure we don't see stale data.
        if self.subdomain:
            cache.MINIMAL_SUBJECTS[self.subdomain].flush_local()

        # Validate the query parameters and collect the validated values.
        self.params = Struct()
        for param in self.auto_params:
            validator = self.auto_params[param]
            setattr(self.params, param, validator(request.get(param, '')))

        # Flush all caches if "flush=yes" was set.
        if self.params.flush:
            cache.flush_all()

        # Activate the appropriate language.
        self.select_lang()

        # Provide the language-independent URL of the current page.
        self.params.url_no_lang = set_url_param(self.request.url, 'lang', None)
        if '?' not in self.params.url_no_lang:
            self.params.url_no_lang += '?'

        # Provide the list of available languages.
        self.params.languages = config.LANGUAGES

        # Provide the Google Analytics account ID.
        self.params.analytics_id = get_secret('analytics_id')

    def select_lang(self):
        """Detect and activate the appropriate language.  The 'lang' query
           parameter has priority, then the 'django_language' cookie, then the
           default language in settings."""
        # lang will be a Django language code: all lowercase, with a dash
        # between the language and optional region (e.g. 'en', 'fr-ca').
        lang = (
            self.params.lang or
            self.request.cookies.get('django_language', None) or
            self.account and self.account.locale or
            settings.LANGUAGE_CODE
        ).replace('_', '-').lower()

        # Check for and potentially convert an alternate language code.
        if lang not in dict(config.LANGUAGES):
            lang = config.LANG_FALLBACKS.get(lang, settings.LANGUAGE_CODE)

        # Store the language settings in params.lang and params.maps_lang.
        self.params.lang = lang
        self.params.maps_lang = config.MAPS_LANG_FALLBACKS.get(lang, lang)

       # change account locale if necessary
        if self.account and lang != self.account.locale:
            self.account.locale = lang
            db.put(self.account)

        # Activate the selected language.
        django.utils.translation.activate(lang)
        self.response.headers.add_header(
            'Set-Cookie', 'django_language=%s' % lang)
        self.response.headers.add_header('Content-Language', lang)

    def get_subdomain_root(self, subdomain):
        """Gets the URL to the main page for a subdomain."""
        host = self.request.headers['Host']
        levels = host.split('.')
        if levels[-2:] == ['appspot', 'com']:
            if len(levels) >= 5:  # kpy.latest.resource-finder.appspot.com
                return 'http://%s.%s/' % (subdomain, '.'.join(levels[-5:]))
            elif len(levels) >= 3:  # resource-finder.appspot.com
                return 'http://%s.%s/' % (subdomain, '.'.join(levels[-3:]))
        return 'http://%s/?subdomain=%s' % (host, subdomain)

    def get_url(self, path, **params):
        """Constructs a relative URL for a given path and query parameters,
        preserving the current 'subdomain' parameter if there is one."""
        if self.request.get('subdomain'):
            params['subdomain'] = self.request.get('subdomain')
        if params:
            path += ('?' in path and '&' or '?') + urlencode(params)
        return path

    def handle_exception(self, exception, debug_mode):
        """Handles an exception thrown by a handler method."""
        if isinstance(exception, Redirect):  # redirection
            self.redirect(exception.url)
        elif isinstance(exception, ErrorMessage):  # user-facing error message
            self.error(exception.status)
            self.response.clear()
            self.render('templates/error.html', message=exception.message,
                        subdomain=self.subdomain)
        else:  # unexpected error
            self.error(500)
            logging.exception(exception)
            if debug_mode:
                self.response.clear()
                self.write(cgitb.html(sys.exc_info()))

def make_name(text):
    text = re.sub(r'[ -]+', '_', text.strip())
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in decomposed if re.match(r'\w', ch)).lower()

def get(parent, Kind, kn):
    entity = Kind.get_by_key_name(kn, parent=parent)
    if entity is None:
        raise KeyError('no %s has key=%s parent=%r' % (Kind.kind(), kn, parent))
    return entity

def get_base(entity):
    if isinstance(entity, db.Key):
        entity = db.get(entity)
    while entity.base:
        entity = entity.base
    return entity

def fetch(url, payload=None, previous_data=None):
    method = (payload is None) and urlfetch.GET or urlfetch.POST
    response = urlfetch.fetch(url, payload, method, deadline=10)
    data = response.content
    logging.info('utils.py: received %d bytes of data' % len(data))
    if data == previous_data:
        return None
    dump = model.Dump(source=url, data=data)
    dump.put()
    return dump

def format(value, localize=False):
    """Formats values in a way that is suitable to display to a user.
    If 'localize' is true, the value is treated as a localizable message key or
    list of message keys to be looked up in the 'attribute_value' namespace."""
    if localize:
        if isinstance(value, list):
            value = [get_message('attribute_value', item) for item in value]
        else:
            value = get_message('attribute_value', value)
    if isinstance(value, unicode):
        return value.encode('utf-8')
    if isinstance(value, str) and value != '':
        return value.replace('\n', ' ')
    if isinstance(value, list) and value != []:
        return ', '.join(value).encode('utf-8')
    if isinstance(value, DateTime):
        return to_local_isotime(value.replace(microsecond=0))
    if isinstance(value, db.GeoPt):
        latitude = u'%.4f\u00b0 %s' % (
            abs(value.lat), value.lat >= 0 and 'N' or 'S')
        longitude = u'%.4f\u00b0 %s' % (
            abs(value.lon), value.lon >= 0 and 'E' or 'W')
        return (latitude + ', ' + longitude).encode('utf-8')
    if isinstance (value, bool):
        return value and format(_('Yes')) or format(_('No'))
    return value_or_dash(value)

def get_last_updated_time(s):
    subdomain, subject_name = split_key_name(s)
    st = cache.SUBJECT_TYPES[subdomain][s.type]
    return max(s.get_observed(name) for name in st.attribute_names if
               s.get_observed(name))

def decompress(data):
    file = gzip.GzipFile(fileobj=StringIO.StringIO(data))
    try:
        return file.read()
    except IOError:
        return data

def export(Kind):
    results = ''
    for entity in Kind.all():
        fields = []
        for key in entity.properties():
            if key != 'timestamp':
                fields.append('%s=%r' % (key, getattr(entity, key)))
        results += '%s(%s).put()\n' % (Kind.__name__, ', '.join(fields))
    return results

def to_utf8(string):
    """If Unicode, encode to UTF-8; if 8-bit string, leave unchanged."""
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string

def urlencode(params):
    """Apply UTF-8 encoding to any Unicode strings in the parameter dict.
    Leave 8-bit strings alone.  (urllib.urlencode doesn't support Unicode.)"""
    keys = params.keys()
    keys.sort()  # Sort the keys to get canonical ordering
    return urllib.urlencode([
        (to_utf8(key), to_utf8(params[key]))
        for key in keys if isinstance(params[key], basestring)])

def url_pickle(data):
    """Serializes a Python object into a 7-bit string.  Use this to pass Python
    objects through query parameters.  The webob.Request decodes query params
    as Unicode strings, so regular pickles will run into encoding problems."""
    return pickle.dumps(data).decode('latin-1').encode('utf-7')

def url_unpickle(data):
    """Deserializes a Python object that was serialized with url_pickle."""
    return pickle.loads(data.decode('utf-7').encode('latin-1'))

def set_url_param(url, param, value):
    """Modifies a URL, setting the given param to the specified value.  This
    may add the param or override an existing value, or, if the value is None,
    it will remove the param.  Note that value must be a basestring and can't be
    an int, for example."""
    url_parts = list(urlparse.urlparse(url))
    params = dict(cgi.parse_qsl(url_parts[4]))
    if value is None:
        if param in params:
            del(params[param])
    else:
        params[param] = value
    url_parts[4] = urlencode(params)
    return urlparse.urlunparse(url_parts)

def to_posixtime(datetime):
    return timegm(datetime.utctimetuple()[:6])

def to_datetime(posixtime):
    return DateTime.utcfromtimestamp(posixtime)

def to_isotime(datetime):
    if isinstance(datetime, (int, float)):
        datetime = to_datetime(datetime)
    return datetime.isoformat() + 'Z'

def to_local_isotime(utc_datetime, clear_ms=False):
    # TODO(shakusa) Use local timezone instead of hard-coding Haitian time
    if clear_ms:
      utc_datetime = utc_datetime.replace(microsecond=0)
    utc_datetime = utc_datetime - TimeDelta(hours=5)
    return utc_datetime.isoformat(' ') + ' -05:00'

def to_local_isotime_day(time):
    isotime = to_local_isotime(time)
    return isotime[:isotime.find(' ')]

def to_unicode(value):
    """Converts the given value to unicode. Django does not do this
       automatically when fetching translations."""
    if isinstance(value, unicode):
        return value
    elif isinstance(value, str):
        return value.decode('utf-8')
    elif value is not None:
        return str(value).decode('utf-8')
    else:
        return u''

def value_or_dash(value):
    """Converts the given value to a unicode dash if the value does
    not exist and does not equal 0."""
    if not value and value != 0:
        return u'\u2013'.encode('utf-8')
    return value

def can_edit(account, subdomain, attribute):
    """Returns True if the user can edit the given attribute."""
    return not attribute.edit_action or access.check_action_permitted(
        account, subdomain, attribute.edit_action)

def order_and_format_updates(updates, subject_type, locale, format_function,
                             attr_index='attribute'):
    """Orders attribute updates in the same order specified by
    subject_type.attribute_names, in the given locale."""
    updates_by_name = dict((update[attr_index], update) for update in updates)
    formatted_attrs = []
    for name in subject_type.attribute_names:
        if name in updates_by_name:
            formatted_attrs.append(
                format_function(updates_by_name[name], locale))
    return formatted_attrs

def run(*args, **kwargs):
    webapp.util.run_wsgi_app(webapp.WSGIApplication(*args, **kwargs))
