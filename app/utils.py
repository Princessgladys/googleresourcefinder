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
from google.appengine.ext import db
from google.appengine.ext import webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util

import StringIO
from calendar import timegm
import cgi
import cgitb
import config
from datetime import date as Date
from datetime import datetime as DateTime  # all DateTimes are always in UTC
from datetime import timedelta as TimeDelta
from feeds.errors import ErrorMessage, Redirect
import gzip
from html import html_escape
import logging
import model
import os
import re
import simplejson
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

# TODO(shakusa) Add these back in post-v1
HIDDEN_ATTRIBUTE_NAMES = ['region_id', 'district_id', 'commune_id',
                          'commune_code', 'sante_id']

def strip(text):
    return text.strip()

def validate_yes(text):
    return (text.lower() == 'yes') and 'yes' or ''

def validate_float(text):
    try:
        return float(text)
    except ValueError:
        return None

def get_message(version, namespace, name):
    message = model.Message.all().ancestor(version).filter(
        'namespace =', namespace).filter('name =', name).get()
    django_locale = django.utils.translation.to_locale(
        django.utils.translation.get_language())
    return message and getattr(message, django_locale) or name

class Struct:
    pass

class Handler(webapp.RequestHandler):
    auto_params = {
        'cc': strip,
        'facility_name': strip,
        'print': validate_yes,
        'embed': validate_yes,
        'lat': validate_float,
        'lon': validate_float,
        'rad': validate_float,
        'lang': strip,
    }

    def require_logged_in_user(self):
        """Redirect to login in case there is no user"""
        if not self.user:
            raise Redirect(users.create_login_url(self.request.uri))

    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.write(webapp.template.render(os.path.join(ROOT, path), params))

    def write(self, text):
        self.response.out.write(text)

    def initialize(self, request, response):
        webapp.RequestHandler.initialize(self, request, response)
        self.user = users.get_current_user()
        logging.info('user: %s' % (self.user and
                                   self.user.email() or 'anonymous'))
        for name in request.headers.keys():
            if name.lower().startswith('x-appengine'):
                logging.debug('%s: %s' % (name, request.headers[name]))
        self.params = Struct()
        for param in self.auto_params:
            validator = self.auto_params[param]
            setattr(self.params, param, validator(request.get(param, '')))
        # Activate localization.
        self.select_locale()

        # Provide the non-localized URL of the current page.
        self.params.url_no_lang = set_url_param(self.request.url, 'lang', None)
        if '?' not in self.params.url_no_lang:
          self.params.url_no_lang += '?'

        self.params.languages = config.LANGUAGES

    def select_locale(self):
        """Detect and activate the appropriate locale.  The 'lang' query
           parameter has priority, then the rflang cookie, then the
           default setting."""
        # self.param.lang will use dashes (fr-CA), which is more common
        # externally, but django wants underscores (fr_CA). If you need
        # that version, use django.utils.translation.get_language()
        self.params.lang = (self.params.lang or
            self.request.cookies.get('django_language', None) or
            settings.LANGUAGE_CODE)
        # Check for and potentially convert an alternate language code
        self.params.lang = config.ALTERNATE_LANG_CODES.get(
            self.params.lang, self.params.lang)
        self.response.headers.add_header(
            'Set-Cookie', 'django_language=%s' % self.params.lang)
        django.utils.translation.activate(self.params.lang.replace('-', '_'))
        self.response.headers.add_header('Content-Language', self.params.lang)

    def handle_exception(self, exception, debug_mode):
        if isinstance(exception, Redirect):
            self.redirect(exception.url)
        elif isinstance(exception, ErrorMessage):
            self.error(exception.status)
            self.response.clear()
            self.render('templates/error.html', message=exception.message)
        else:
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

def get_latest_version(cc):
    country = get(None, model.Country, cc)
    versions = model.Version.all().ancestor(country).order('-timestamp')
    if versions.count():
        return versions[0]

def fetch(cc, url, payload=None, previous_data=None):
    country = get(None, model.Country, cc)
    method = (payload is None) and urlfetch.GET or urlfetch.POST
    response = urlfetch.fetch(url, payload, method, deadline=10)
    data = response.content
    logging.info('utils.py: received %d bytes of data' % len(data))
    if data == previous_data:
        return None
    dump = model.Dump(country, source=url, data=data)
    dump.put()
    return dump

def load(loader, dump):
    logging.info('load started')
    version = model.Version(dump.parent(), dump=dump)
    version.put()
    logging.info('new version: %r' % version)
    loader.put_dump(version, decompress(dump.data))
    logging.info('load finished: %r' % version)
    return version

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

def set_url_param(url, param, value):
  """This modifies a URL, setting the given param to the specified value.  This
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

def plural(n, singular='', plural='s'):
    if not isinstance(n, (int, float)):
        n = len(n)
    return [plural, singular][n == 1]

def run(*args, **kwargs):
    webapp.util.run_wsgi_app(webapp.WSGIApplication(*args, **kwargs))
