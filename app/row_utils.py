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

from feedlib import time_formats, xml_utils
from feedlib.report_feeds import REPORT_NS, SPREADSHEETS_NS
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

def serialize_to_elements(values, comments={}):
    """Returns a list of <gs:field> elements for the given values and comments
    (both are dictionaries keyed on attribute names)."""
    fields = []
    for name in values:
        fields.append(xml_utils.create_element(
            (SPREADSHEETS_NS, 'field'),
            serialize(name, values[name]),
            name in comments and {'comment': comments[name]} or None))
    return fields

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
        return string.upper() == u'TRUE'
    if type == 'multi':
        return string.split(',')
    if type == 'geopt':
        return db.GeoPt(*map(float, string.split(',')))

def parse_from_elements(parent):
    """Parses all the <gs:field> elements that are children of the given
    element, returning a dictionary of values and a dictionary of comments."""
    values = {}
    comments = {}
    for field in parent.findall(xml_utils.qualify(SPREADSHEETS_NS, 'field')):
        name = field.attrib['name']
        values[name] = parse(name, field.text)
        comments[name] = field.get(xml_utils.qualify(REPORT_NS, 'comment'))
    return values, comments
