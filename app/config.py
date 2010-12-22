#!/usr/bin/python2.5
# Copyright 2009-2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Application-wide configuration settings.
from google.appengine.ext import db
import random, simplejson

# List of language codes supported for each subdomain
LANGS_BY_SUBDOMAIN = {'haiti': ('en', 'fr', 'ht', 'es-419'),
                      'pakistan': ('en', 'ur')}

SUBDOMAIN_LIST_FOOTERS = {'haiti': 'blank.html',
                          'pakistan': 'blank.html'}

# List of languages that appear in the language menu, as (code, name) pairs.
LANGUAGES = (('en', 'English'),
             ('fr', u'Fran\u00e7ais'), # French
             ('ht', u'Krey\u00f2l'), # Kreyol
             ('es-419', u'Espa\u00F1ol'), # Spanish (Latin American)
             ('ur', u'\u0627\u0631\u062F\u0648') # Urdu
            )

# A map from unavailable languages to the best available fallback languages.
LANG_FALLBACKS = {'es': 'es-419'}

# Google Maps is not available in all languages.  This maps from unavailable
# languages to the best available fallback language.
MAPS_LANG_FALLBACKS = {'ht': 'fr'}

# English-only Resource Finder discussion board, monitored by Google
DISCUSSION_BOARD = 'https://sites.google.com/site/resourcefinderdiscussion/'

# Google feedback form, translated to other languages
FEEDBACK_FORM = 'http://www.google.com/support/fluvaccinefinder/bin/' + \
                'request.py?hl=%(lang)s&contact_type=do_resource'

# Links to feedback / discussion sites
FEEDBACK_URLS_BY_LANG = {
    'en': DISCUSSION_BOARD,
    'es-419': FEEDBACK_FORM % {'lang': 'es-419'},
    'fr': FEEDBACK_FORM % {'lang': 'fr'},
    'ht': FEEDBACK_FORM % {'lang': 'ht'},
    'ur': DISCUSSION_BOARD
}


class ConfigEntry(db.Model):
    """An application configuration setting, identified by its key_name."""
    value = db.StringProperty(default='')


def get(name, default=None):
    """Gets a configuration setting."""
    config = ConfigEntry.get_by_key_name(name)
    if config:
        return simplejson.loads(config.value)
    return default


def get_or_generate(name):
    """Gets a configuration setting, or sets it to a random 32-byte value
    encoded in hexadecimal if it doesn't exist.  Use this function when you
    need a persistent cryptographic secret unique to the application."""
    random_hex = ''.join('%02x' % random.randrange(256) for i in range(32))
    ConfigEntry.get_or_insert(key_name=name, value=simplejson.dumps(random_hex))
    return get(name)


def set(**kwargs):
    """Sets configuration settings."""
    for name, value in kwargs.items():
        ConfigEntry(key_name=name, value=simplejson.dumps(value)).put()
