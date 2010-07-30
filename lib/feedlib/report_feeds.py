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
import logging
import pickle
import tasks_external
import urllib
from crypto import sign, verify
from errors import ErrorMessage
from time_formats import from_rfc3339, to_rfc1123, to_rfc3339
from xml_utils import create_element, qualify, parse, serialize, write

HUB = 'http://pubsubhubbub.appspot.com'
HUB = 'http://localhost:8888'
ATOM_NS = 'http://www.w3.org/2005/Atom'
REPORT_NS = 'http://schemas.google.com/report/2010'
SPREADSHEETS_NS = 'http://schemas.google.com/spreadsheets/2006'


class ReportEntry(db.Model):
    """Entity representing one received or provided XML report entry.
    Each ReportEntry belongs to a local feed, identified by a 'feed_name',
    which is assumed to determine the URI of the feed served by this app.

    Original (locally created) report entries have a numeric key().id() from
    which the Atom entry ID is generated, and always have 'external_entry_id'
    and 'external_feed_id' set to ''.
    
    Clones of externally created entries have a key().name() formed by
    pickling the tuple (feed_name, entry_id), and have non-empty values for
    'external_entry_id' and 'external_feed_id'."""
    feed_name = db.StringProperty(required=True)  # local feed name
    title = db.StringProperty(default='')  # title or summary string
    arrived = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    author_uri = db.StringProperty(required=True)  # author identifier
    subject_id = db.StringProperty(required=True)  # thing this report is about
    observed = db.DateTimeProperty(required=True)  # UTC timestamp
    type_name = db.StringProperty(required=True)  # XML type in Clark notation
    content = db.TextProperty(default='')  # serialized XML document
    external_entry_id = db.StringProperty(default='')  # external Atom entry ID
    external_feed_id = db.StringProperty(default='')  # external Atom feed ID

    @staticmethod
    def get_latest_observed(feed_name, type_name, subject_id):
        """Gets the report entry with the given subject ID and latest observed
        time from the specified local feed."""
        return (ReportEntry.all().filter('feed_name =', feed_name)
                                 .filter('type_name =', type_name)
                                 .filter('subject_id =', subject_id)
                                 .order('-observed')).get()

    @staticmethod
    def get_latest_arrived(feed_name, external_feed_id=None,
                           arrived_after=None, limit=None):
        """Gets a list of entries from the given local feed in order of
        decreasing arrived time, with the given 'external_feed_id' if
        specified, with an arrived time greater than 'arrived_after' if
        specified, up to a maximum of 'limit' entries if specified."""
        query = (ReportEntry.all().filter('feed_name =', feed_name)
                                  .order('-arrived'))
        if external_feed_id is not None:
            query = query.filter('external_feed_id =', external_feed_id)
        if arrived_after:
            query = query.filter('arrived >', arrived_after)
        if limit is None:
            limit = 100
        return query.fetch(min(limit, 100))

    @staticmethod
    def create_original(feed_name, title, author_uri, subject_id, observed,
                        type_name, content):
        # The datastore chooses a new numeric entity ID.
        return ReportEntry(feed_name=feed_name,
                           type_name=type_name,
                           subject_id=subject_id,
                           title=title,
                           author_uri=author_uri,
                           observed=observed,
                           content=content)

    @staticmethod
    def create_clone(feed_name, title, author_uri, subject_id, observed,
                     type_name, content, external_entry_id, external_feed_id):
        key_name = pickle.dumps((feed_name, external_entry_id))
        return ReportEntry(key_name=key_name,
                           feed_name=feed_name,
                           title=title,
                           author_uri=author_uri,
                           subject_id=subject_id,
                           observed=observed,
                           type_name=type_name,
                           content=content,
                           external_entry_id=external_entry_id,
                           external_feed_id=external_feed_id)

    def get_entry_id(self, feed_uri):
        """Gets the Atom entry ID for this entry, given its parent feed URI."""
        return self.external_entry_id or '%s/%d' % (feed_uri, self.key().id())

def add_uri_prefixes(uri_prefixes):
    """Adds the namespace prefixes used by this module to a dictionary."""
    return dict([(ATOM_NS, 'atom'),
                 (REPORT_NS, 'report'),
                 (SPREADSHEETS_NS, 'gs')], **uri_prefixes)

def create_entry_element(entry, feed_uri):
    """Converts a ReportEntry entity into an Atom <entry> Element."""
    author = create_element(
        (ATOM_NS, 'author'),
        create_element((ATOM_NS, 'uri'), entry.author_uri))
    if entry.author_uri.startswith('mailto:'):
        scheme, email = entry.author_uri.split(':', 1)
        author.append(create_element((ATOM_NS, 'email'), email))
    return create_element(
        (ATOM_NS, 'entry'),
        create_element((ATOM_NS, 'id'), entry.get_entry_id(feed_uri)),
        entry.external_feed_id and create_element(
            (ATOM_NS, 'source'),
            create_element((ATOM_NS, 'id'), entry.external_feed_id)),
        create_element((ATOM_NS, 'title'), entry.title),
        create_element((ATOM_NS, 'updated'), to_rfc3339(entry.arrived)),
        author,
        create_element((REPORT_NS, 'subject'), entry.subject_id),
        create_element((REPORT_NS, 'observed'), to_rfc3339(entry.observed)),
        create_element((REPORT_NS, 'content'),
                       parse(entry.content), type=entry.type_name))

def create_feed_element(entries, feed_uri, hub=None):
    """Constructs an Atom <feed> element containing the given report entries."""
    updated = None
    if entries:
        updated = entries[0].arrived
    else:
        updated = datetime.datetime.utcnow()
    elements = [
        create_element((ATOM_NS, 'id'), feed_uri),
        create_element((ATOM_NS, 'title'), feed_uri),
        create_element((ATOM_NS, 'updated'), to_rfc3339(updated)),
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
        raise ErrorMessage(400, '%s contains no %s' % (element.tag, tag))
    return child

def get_text(element, tag):
    """Gets the text of a child element, or '' if the element is missing."""
    if isinstance(tag, tuple):
        tag = qualify(*tag)
    return getattr(element.find(tag), 'text', '')

def create_report_entry(entry_element, feed_name, external_feed_id=None):
    """Converts an Atom <entry> Element into a ReportEntry entity.  If
    'external_feed_id' is specified, the resulting entity is considered a
    clone: the entity gets the specified external_feed_id, and the entry
    element must contain an <id> which becomes the entity's external_entry_id.
    Otherwise, the entity is stored as an original, with no external_feed_id
    or external_entry_id."""
    # Get the Atom metadata.
    title = get_text(entry_element, (ATOM_NS, 'title'))
    author_element = get_child(entry_element, (ATOM_NS, 'author'))
    author_uri = (get_text(author_element, (ATOM_NS, 'uri')) or
                  'mailto:' + get_text(author_element, (ATOM_NS, 'email')))

    # Get the report metadata (subject ID and observed time).
    subject_id = get_child(entry_element, (REPORT_NS, 'subject')).text
    observed = from_rfc3339(
        get_child(entry_element, (REPORT_NS, 'observed')).text)

    # Get the content of the report.
    content_element = get_child(entry_element, (REPORT_NS, 'content'))
    type_name = content_element.attrib['type']
    enclosed_element = get_child(content_element, type_name)

    if external_feed_id:
        external_entry_id = get_child(entry_element, (ATOM_NS, 'id')).text
        return ReportEntry.create_clone(
            feed_name, title, author_uri, subject_id, observed, type_name,
            serialize(enclosed_element), external_entry_id, external_feed_id)
    else:
        return ReportEntry.create_original(
            feed_name, title, author_uri, subject_id, observed, type_name,
            serialize(enclosed_element))

def handle_feed_post(request, response, feed_name, store_as_original=False):
    """Handles a post of incoming entries, storing each entry as a report in
    the specified local feed.  By default, the entries are assumed to belong
    to an external feed, and the posted feed must contain an <id> element,
    which determines the external_feed_id of the stored entries.  If
    'store_as_original' is true, the entries are stored as originals, with no
    external_entry_id or external_feed_id."""
    entries = []
    try:
        feed_element = parse(request.body)
    except SyntaxError, e:
        raise ErrorMessage(400, str(e))
    if feed_element.tag != qualify(ATOM_NS, 'feed'):
        raise ErrorMessage(400, 'Incoming document is not an Atom feed')
    if store_as_original:
        external_feed_id = None
    else:
        external_feed_id = get_child(feed_element, (ATOM_NS, 'id')).text
    for entry_element in feed_element.findall(qualify(ATOM_NS, 'entry')):
        # To avoid duplicates, ignore entries that came from this app.
        entry_id = get_text(entry_element, (ATOM_NS, 'id'))
        if not entry_id.startswith(request.host_url + '/'):
            entries.append(create_report_entry(
                entry_element, feed_name, external_feed_id))

    # If there are new reports to add, store them and notify the hub.
    if entries:
        db.put(entries)
        for entry in entries:
            logging.info('Stored entry: ' + entry.get_entry_id(request.uri))
        notify_hub(request.uri)
    return entries
