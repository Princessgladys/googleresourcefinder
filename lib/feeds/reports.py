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

"""Data model and utility functions for storage of XML reports."""

from google.appengine.ext import db
import xmlutils


class XmlReport(db.Model):
    """Entity representing one received or provided XML report entry.
    
    Each XmlReport belongs to a local feed, identified by a 'feed_name', which
    is assumed to determine the URI of the containing feed served by this app.
    XmlReports that are copied from other feeds also have a 'source_uri'."""
    feed_name = db.StringProperty(required=True)  # local feed name
    type_name = db.StringProperty(required=True)  # XML type in Clark notation
    subject_id = db.StringProperty(required=True)  # thing this report is about
    title = db.StringProperty()  # title or summary string
    author_uri = db.StringProperty(required=True)  # author identifier
    observed = db.DateTimeProperty(required=True)  # UTC timestamp
    arrived = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    content = db.TextProperty()  # serialized XML document
    source_uri = db.StringProperty(default='')  # URI of source feed


def create_report(feed_name, subject_id, title, author_uri, observed, element,
                  source_uri=''):
    """Wraps an Element as an XmlReport belonging to a specified local feed."""
    return XmlReport(
        feed_name=feed_name,
        type_name=element.tag,
        subject_id=subject_id,
        title=title,
        author_uri=author_uri,
        observed=observed,
        content=xmlutils.serialize(element),
        source_uri=source_uri)

def put_report(*args):
    """Stores an Element as an XmlReport belonging to a specified local feed."""
    report = create_report(*args)
    report.put()
    return report

def get_latest_observed(feed_name, type_name, subject_id):
    """Gets the report with the given subject ID and latest observed time
    from the specified local feed."""
    return (XmlReport.all().filter('feed_name =', feed_name)
                           .filter('type_name =', type_name)
                           .filter('subject_id =', subject_id)
                        .order('-observed')).get()

def get_latest_arrived(feed_name, source_uri=None, arrived_after=None,
                       limit=None):
    """Gets a list of reports from the given local feed in order of decreasing
    arrived time, with the given 'source_uri' if specified, with an arrived
    time greater than 'arrived_after' if specified, up to a maximum of 'limit'
    reports if specified."""
    query = XmlReport.all().filter('feed_name =', feed_name).order('-arrived')
    if source_uri:
        query = query.filter('source_uri =', source_uri)
    if arrived_after:
        query = query.filter('arrived >', arrived_after)
    if limit is None:
        limit = 100
    return query.fetch(min(limit, 100))
