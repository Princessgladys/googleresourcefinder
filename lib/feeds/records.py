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
    """Entity representing one received or provided XML document entry."""
    feed_id = db.StringProperty(required=True)  # URI of parent feed
    type_name = db.StringProperty(required=True)  # XML type in Clark notation
    subject_id = db.StringProperty(required=True)  # thing this record is about
    title = db.StringProperty()  # title or summary string
    author_email = db.StringProperty(required=True)  # author identifier
    observed = db.DateTimeProperty(required=True)  # UTC timestamp
    arrived = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    content = db.TextProperty()  # serialized XML document 


def put_record(feed_id, author_email, title, subject_id, observed, element):
    """Stores an XML Element as a record."""
    record = Record(
        feed_id=feed_id,
        type_name=element.tag,
        subject_id=subject_id,
        title=title,
        author_email=author_email,
        observed=observed,
        content=xmlutils.serialize(element))
    record.put()
    return record

def get_latest_observed(type_name, record_id):
    """Gets the record with the given record ID and latest observed time."""
    return (Record.all().filter('type_name =', type_name)
                        .filter('record_id =', record_id)
                        .order('-observed')).get()

def get_latest_arrived(feed_id, limit=None, arrived_after=None):
    """Gets a list of records in the given feed in order of decreasing
    arrived time, with an arrived time greater than 'arrived_after' if
    specified, up to a maximum of 'limit' records if specified."""
    query = (Record.all().filter('feed_id =', feed_id)
                         .order('-arrived'))
    if arrived_after:
        query = query.filter('arrived >', arrived_after)
    return query.fetch(min(limit or 100, 100))
