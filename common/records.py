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

"""Data model and utiltiy functions for XML record storage."""

from google.appengine.ext import db
import xmlutils


class Record(db.Model):
    """Entity representing one received XML document."""
    feed = db.StringProperty(required=True)  # canonical URL for source feed
    type = db.StringProperty(required=True)  # XML type in Clark notation
    record_id = db.StringProperty(required=True)  # non-unique record ID
    title = db.StringProperty()  # title or summary string
    author_email = db.StringProperty(required=True)  # author identifier
    observation_time = db.DateTimeProperty(required=True)  # UTC timestamp
    arrival_time = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    content = db.TextProperty()  # XML document


class RecordType:
    def get_identifier(self, element):
        """Extracts the record_id string from an ElementTree element."""
        raise NotImplementedError

    def get_title(self, element):
        """Gets or fashions a descriptive title from an ElementTree element."""
        return ''

    def get_observation_time(self, element):
        """Extracts the observation time from an ElementTree element."""
        raise NotImplementedError


type_registry = {}

def register_type(type_name, record_type):
    type_registry[type_name] = record_type

def put_record(feed, author_email, element):
    record_type = type_registry[element.tag]
    Record(
        feed=feed,
        type=element.tag,
        record_id=record_type.get_identifier(element),
        title=record_type.get_title(element),
        author_email=author_email,
        observation_time=record_type.get_observation_time(element),
        content=xmlutils.serialize(element)
    ).put()

def get_latest_observed(type, record_id):
    query = (Record.all().filter('type =', type)
                         .filter('record_id =', record_id)
                         .order('-observation_time'))
    return query.get()

def get_latest_arrived(feed, limit=None, after_arrival_time=None):
    query = (Record.all().filter('feed =', feed)
                         .order('-arrival_time'))
    if after_arrival_time:
        query = query.filter('arrival_time >', after_arrival_time)
    return query.fetch(min(limit or 100, 100))
