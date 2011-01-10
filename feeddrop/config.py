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
