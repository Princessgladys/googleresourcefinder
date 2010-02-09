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
import access
from calendar import timegm
import cgitb
from datetime import date as Date
from datetime import datetime as DateTime  # all DateTimes are always in UTC
from datetime import timedelta as TimeDelta
import gzip
from html import html_escape
import logging
import model
import os
import re
import simplejson
import sys

ROOT = os.path.dirname(__file__)

class Redirect(Exception):
    """Raise this exception to redirect to another page."""
    def __init__(self, url):
        self.url = url

class ErrorMessage(Exception):
    """Raise this exception to show an error message to the user."""
    def __init__(self, status, message):
        self.status = status
        self.message = message

def strip(text):
    return text.strip()

class Struct:
    pass

class Handler(webapp.RequestHandler):
    auto_params = {
        'cc': strip,
        'id': strip
    }

    def render(self, name, **values):
        self.write(webapp.template.render(os.path.join(ROOT, name), values))

    def write(self, text):
        self.response.out.write(text)

    def initialize(self, request, response):
        webapp.RequestHandler.initialize(self, request, response)
        for name in request.headers.keys():
            if name.lower().startswith('x-appengine'):
                logging.debug('%s: %s' % (name, request.headers[name]))
        self.auth = access.check_and_log(request, users.get_current_user())
        self.params = Struct()
        for param in self.auto_params:
            validator = self.auto_params[param]
            setattr(self.params, param, validator(request.get(param, '')))

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

def key_repr(key):
    levels = []
    while key:
        levels.insert(0, '%s %s' % (key.kind(), key.id() or repr(key.name())))
        key = key.parent()
    return '<Key: %s>' % '/'.join(levels)

def model_repr(model):
    if model.is_saved():
        key = model.key()
        return '<%s: %s>' % (key.kind(), key.id() or repr(key.name()))
    else:
        return '<%s: unsaved>' % model.kind()

db.Key.__repr__ = key_repr

db.Model.__repr__ = model_repr

def make_identifier(name):
    clean = re.sub('[^A-Za-z0-9]', ' ', name)
    return '_'.join(clean.lower().strip().split())

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

def to_posixtime(datetime):
    return timegm(datetime.utctimetuple()[:6])

def to_datetime(posixtime):
    return DateTime.utcfromtimestamp(posixtime)

def to_isotime(datetime):
    if isinstance(datetime, (int, float)):
        datetime = to_datetime(datetime)
    return datetime.isoformat() + 'Z'

def plural(n, singular='', plural='s'):
    if not isinstance(n, (int, float)):
        n = len(n)
    return [plural, singular][n == 1]

def run(*args, **kwargs):
    webapp.util.run_wsgi_app(webapp.WSGIApplication(*args, **kwargs))
