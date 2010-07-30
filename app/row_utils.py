# Copyright 2010 Google Inc.
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

"""Serialization of attribute values to and from gs:field contents."""

from feedlib import time_formats
from google.appengine.ext import db
import model

def serialize(attribute_name, value):
    """Serializes a given attribute value to a Unicode string."""
    type = model.Attribute.get_by_key_name(attribute_name).type
    if type in ['str', 'text', 'contact', 'choice']:
        return value
    if type == 'date':
        return time_formats.to_rfc3339(value)
    if type in ['int', 'float']:
        return unicode(value)
    if type == 'bool':
        return value and u'TRUE' or u'FALSE'
    if type == 'multi':
        return u','.join(value)
    if type == 'geopt':
        return unicode(value.lat) + ',' + unicode(value.lon)

def parse(attribute_name, string):
    """Parses a Unicode string into an attribute value."""
    type = model.Attribute.get_by_key_name(attribute_name).type
    if type in ['str', 'text', 'contact', 'choice']:
        return string
    if type == 'date':
        return time_formats.from_rfc3339(string)
    if type == 'int':
        return int(string)
    if type == 'float':
        return float(string)
    if type == 'bool':
        return string == u'TRUE'
    if type == 'multi':
        return string.split(',')
    if type == 'geopt':
        return db.GeoPt(*map(float, string.split(',')))
