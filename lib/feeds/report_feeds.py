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

"""Support for Atom feed providers backed by the data store."""

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

import datetime
import tasks_external
import urllib
from crypto import sign, verify
from errors import ErrorMessage
from time_formats import from_rfc3339, to_rfc1123, to_rfc3339
from xmlutils import create_element, qualify, parse, serialize, write

HUB = 'http://pubsubhubbub.appspot.com'
ATOM_NS = 'http://www.w3.org/2005/Atom'
REPORT_NS = 'http://schemas.google.com/report/2010'
SPREADSHEETS_NS = 'http://schemas.google.com/spreadsheets/2006'


class ReportEntry(db.Model):
    """Entity representing one received or provided XML report entry.
    
    Each ReportEntry belongs to a local feed, identified by a 'feed_name',
    which is assumed to determine the URI of the feed served by this app.
    If the ReportEntry was copied from an external feed, it has a 'source_uri'.
    If the ReportEntry was created locally, its 'source_uri' is always ''."""
    feed_name = db.StringProperty(required=True)  # local feed name
    type_name = db.StringProperty(required=True)  # XML type in Clark notation
    subject_id = db.StringProperty(required=True)  # thing this report is about
    title = db.StringProperty()  # title or summary string
    author_uri = db.StringProperty(required=True)  # author identifier
    observed = db.DateTimeProperty(required=True)  # UTC timestamp
    arrived = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    content = db.TextProperty()  # serialized XML document
    source_uri = db.StringProperty(default='')  # URI of external source feed

    @staticmethod
    def get_latest_observed(feed_name, type_name, subject_id):
        """Gets the report entry with the given subject ID and latest observed
        time from the specified local feed."""
        return (ReportEntry.all().filter('feed_name =', feed_name)
                                 .filter('type_name =', type_name)
                                 .filter('subject_id =', subject_id)
                                 .order('-observed')).get()

    @staticmethod
    def get_latest_arrived(feed_name, source_uri=None, arrived_after=None,
                           limit=None):
        """Gets a list of entries from the given local feed in order of
        decreasing arrived time, with the given 'source_uri' if specified,
        with an arrived time greater than 'arrived_after' if specified,
        up to a maximum of 'limit' entries if specified."""
        query = (ReportEntry.all().filter('feed_name =', feed_name)
                                  .order('-arrived'))
        if source_uri is not None:  # source_uri='' filters to local entries
            query = query.filter('source_uri =', source_uri)
        if arrived_after:
            query = query.filter('arrived >', arrived_after)
        if limit is None:
            limit = 100
        return query.fetch(min(limit, 100))


def add_uri_prefixes(uri_prefixes):
    """Adds the namespace prefixes used by this module to a dictionary."""
    return dict([(ATOM_NS, 'atom'),
                 (REPORT_NS, 'report'),
                 (SPREADSHEETS_NS, 'gs')], **uri_prefixes)

def create_entry_element(entry, feed_uri):
    """Converts a ReportEntry entity into an Atom <entry> Element."""
    entry_id = '%s/%d' % (feed_uri, entry.key().id())
    author = create_element(
        (ATOM_NS, 'author'),
        create_element((ATOM_NS, 'uri'), entry.author_uri))
    if entry.author_uri.startswith('mailto:'):
        scheme, email = entry.author_uri.split(':', 1)
        author.append(create_element((ATOM_NS, 'email'), email))
    return create_element(
        (ATOM_NS, 'entry'),
        create_element((ATOM_NS, 'id'), entry_id),
        create_element((REPORT_NS, 'subject'), entry.subject_id),
        create_element((ATOM_NS, 'title'), entry.title),
        author,
        create_element((REPORT_NS, 'observed'), to_rfc3339(entry.observed)),
        create_element((ATOM_NS, 'updated'), to_rfc3339(entry.arrived)),
        create_element((REPORT_NS, 'content'),
                       parse(entry.content), type=entry.type_name),
        entry.source_uri and create_element(
            (ATOM_NS, 'source'),
            create_element((ATOM_NS, 'id'), entry.source_uri)))

def create_feed_element(entries, feed_uri, hub=None):
    """Constructs an Atom <feed> element containing the given report entries."""
    updated = None
    if entries:
        updated = entries[0].arrived
    else:
        updated = datetime.datetime.utcnow()
    elements = [
        create_element((ATOM_NS, 'id'), feed_uri),
        create_element((ATOM_NS, 'updated'), to_rfc3339(updated)),
        create_element((ATOM_NS, 'title'), feed_uri),
        hub and create_element((ATOM_NS, 'link'), rel='hub', href=hub)
    ]
    elements += [create_entry_element(entry, feed_uri) for entry in entries]
    return create_element((ATOM_NS, 'feed'), elements)

def write_entry(file, entry, feed_uri, uri_prefixes={}):
    """Writes an Atom <entry> for the given report entry to the given file."""
    entry_element = create_entry_element(entry, feed_uri)
    write(file, entry_element, add_uri_prefixes(uri_prefixes))

def write_feed(file, entries, feed_uri, uri_prefixes={}, hub=None):
    """Writes an Atom <feed> of the given report entries to the given file."""
    feed_element = create_feed_element(entries, feed_uri, hub)
    write(file, feed_element, add_uri_prefixes(uri_prefixes))

def notify_hub(feed_uri):
    """Notifies a PubSubHubbub hub of new content at a given feed URI."""
    tasks_external.add(HUB, {'hub.mode': 'publish', 'hub.url': feed_uri})

def check_request_etag(headers):
    """Determines etag, limit, arrived_after based on request headers."""
    # TODO: If reports A and B are written to different data centers,
    # and clock skew causes B to be written with an arrived time earlier
    # than A, after a subscriber has previously fetched the feed with A
    # as the latest item, then B will be missed on the next fetch.
    if 'if-none-match' in headers:
        try:
            etag = headers['If-None-Match'].strip().strip('"')
            timestamp, signature = etag.split('/')
            if verify('etag_key', timestamp, signature):
                return etag, None, from_rfc3339(timestamp)
        except (KeyError, ValueError):
            pass
    return None, 20, None

def create_response_etag(entries):
    """Constructs the ETag response header for the given report entries."""
    arrival_time = entries and entries[0].arrived or 0
    timestamp = to_rfc3339(arrival_time)
    return '"' + timestamp + '/' + sign('etag_key', timestamp) + '"'

def handle_feed_get(request, response, feed_name, uri_prefixes={}):
    """Handles a request for an Atom feed of XML report entries."""
    etag, limit, arrived_after = check_request_etag(request.headers)
    entries = ReportEntry.get_latest_arrived(
        feed_name, None, arrived_after, limit)

    response.headers['Content-Type'] = 'application/atom+xml'
    if entries:  # Deliver the new entries.
        response.headers['ETag'] = create_response_etag(entries)
        write_feed(response.out, entries, request.uri, uri_prefixes, hub=HUB)
    elif etag:  # If-None-Match was specified, and there was nothing new.
        response.set_status(304)
        response.headers['ETag'] = '"' + etag + '"'
    else:  # There are no entries in this feed.
        write_feed(response.out, entries, request.uri, uri_prefixes, hub=HUB)

def handle_entry_get(request, response, feed_name, uri_prefixes={}):
    """Handles a request for the Atom entry for an individual XML report."""
    try:
        feed_uri, entry_key = request_uri.rsplit('/', 1)
        id = int(entry_key)
    except ValueError:
        raise ErrorMessage(404, 'No such entry')
    entry = ReportEntry.get_by_id(id)
    if not entry or entry.feed_name != feed_name:
        raise ErrorMessage(404, 'No such entry')

    response.headers['Content-Type'] = 'application/atom+xml'
    response.headers['Last-Modified'] = to_rfc1123(entry.arrived)
    write_entry(response.out, entry, feed_uri, uri_prefixes)

def get_child(element, tag):
    """Gets a child element, or raises an HTTP 400 error if not found."""
    if isinstance(tag, tuple):
        tag = qualify(*tag)
    child = element.find(tag)
    if child is None:  # need "is None" because childless elements are false
        raise ErrorMessage(400, '%s contains no %s' % (element.tag, name))
    return child

def get_text(element, tag):
    """Gets the text of a child element, or '' if the element is missing."""
    if isinstance(tag, tuple):
        tag = qualify(*tag)
    return getattr(element.find(tag), 'text', '')

def create_report_entry(entry_element, feed_name, source_uri=None):
    """Converts an Atom <entry> Element into a ReportEntry entity."""
    # Get the Atom metadata.
    author_element = get_child(entry_element, (ATOM_NS, 'author'))
    author_uri = (get_text(author_element, (ATOM_NS, 'uri')) or
                  'mailto:' + get_text(author_element, (ATOM_NS, 'email')))
    title = get_text(entry_element, (ATOM_NS, 'title'))

    # Get the report metadata (subject ID and observed time).
    subject_id = get_child(entry_element, (REPORT_NS, 'subject')).text
    observed = from_rfc3339(
        get_child(entry_element, (REPORT_NS, 'observed')).text)

    # Get the content of the report.
    content_element = get_child(entry_element, (REPORT_NS, 'content'))
    type_name = content_element.attrib['type']
    enclosed_element = get_child(content_element, type_name)

    return ReportEntry(feed_name=feed_name,
                       type_name=type_name,
                       subject_id=subject_id,
                       title=title,
                       author_uri=author_uri,
                       observed=observed,
                       content=serialize(enclosed_element),
                       source_uri=source_uri or '')

def handle_feed_post(request, response, feed_name, set_source=False):
    """Handles a post of incoming entries, storing each entry as a report in
    the specified local feed.  If set_source is true, the posted feed must have
    an <id> element, which is set as the source_uri on each stored report."""
    entries = []
    try:
        feed_element = parse(request.body)
    except SyntaxError, e:
        raise ErrorMessage(400, str(e))
    if feed_element.tag != qualify(ATOM_NS, 'feed'):
        raise ErrorMessage(400, 'Incoming document is not an Atom feed')
    source_uri = set_source and get_child(feed_element, (ATOM_NS, 'id')).text
    for entry_element in feed_element.findall(qualify(ATOM_NS, 'entry')):
        entries.append(
            create_report_entry(entry_element, feed_name, source_uri))
    db.put(entries)
    return entries
