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

from google.appengine.api import users
from google.appengine.ext import db
from datetime import date as Date
from datetime import datetime as DateTime

def html_escape(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;')

def span(text, klass):
    return '<span class="%s">%s</span>' % (klass, html_escape(text))

def leaf_html_repr(key):
    kind_repr = span(key.kind(), 'kind') + ' '
    if key.id() is not None:
        return kind_repr + span(key.id(), 'id')
    else:
        return kind_repr + span(key.name(), 'name')

def key_html_repr(key):
    result = leaf_html_repr(key)
    while key.parent():
        key = key.parent()
        result = leaf_html_repr(key) + span('/', 'separator') + result
    return '<span class="path">%s</span>' % result

def html_repr(value, depth=1, leaf=0):
    key_repr = leaf and leaf_html_repr or key_html_repr
    if isinstance(value, db.Model) and depth:
        rows = ['<tr><td colspan=2>%s</td></tr>' % key_repr(value.key())]
        for name in (sorted(value.properties().keys()) +
                     sorted(value.dynamic_properties())):
            value_repr = html_repr(getattr(value, name), depth - 1, leaf)
            rows.append('<tr><td class="property">%s</td>' % name +
                        '<td class="value">%s</td></tr>' % value_repr)
        return ('<table cellpadding=0 cellspacing=0 class="entity">%s</table>'
                % ''.join(rows))
    if isinstance(value, db.Model):
        return key_repr(value.key())
    if isinstance(value, list):
        rows = []
        for i in range(len(value)):
            rows.append('<tr><td class="index">%d</td>' % i +
                        '<td class="item">%s</td></tr>' %
                        html_repr(value[i], depth, leaf))
        return ('<table cellpadding=0 cellspacing=0 class="list">%s</table>'
                % ''.join(rows))
    if isinstance(value, db.Key):
        return html_repr(db.get(value), depth, leaf)
    if isinstance(value, users.User):
        return 'User(%r)' % value.email()
    if isinstance(value, (db.ByteString, db.Category, db.Email, db.Link,
                          db.PhoneNumber, db.PostalAddress, db.Rating)):
        return '%s(%r)' % (value.__class__.__name__, value)
    if isinstance(value, (db.Blob, db.Text)):
        return '%s(%r..., len=%d)' % (
            value.__class__.__name__, value[:20], len(value))
    if isinstance(value, db.GeoPt):
        return 'GeoPt(%g, %g)' % (value.lat, value.lon)
    if isinstance(value, db.IM):
        return 'IM(%r, %r)' % (value.protocol, value.address)
    if isinstance(value, (Date, DateTime)):
        return span(value.isoformat() + 'Z', 'date')
    if value is None:
        return span('None', 'none')
    return html_escape(repr(value))
