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

"""Support for Atom feed providers backed by the XML report store."""

from google.appengine.ext import db

import datetime
import reports
import time_formats
import urllib
from crypto import sign, verify
from errors import ErrorMessage
from xmlutils import element, qualify, parse, write

HUB = 'http://pubsubhubbub.appspot.com'
ATOM_NS = 'http://www.w3.org/2005/Atom'
REPORT_NS = 'http://schemas.google.com/report/2010'
SPREADSHEETS_NS = 'http://schemas.google.com/spreadsheets/2006'

def add_uri_prefixes(uri_prefixes):
    """Adds the namespace prefixes used by this module to a dictionary."""
    return dict([(ATOM_NS, 'atom'), (REPORT_NS, 'report'),
                 (SPREADSHEETS_NS, 'gs')], **uri_prefixes)

def create_entry(report, feed_uri):
    """Constructs an Atom <entry> Element containing the given report."""
    entry_id = '%s/%d' % (feed_uri, report.key().id())
    author = element('{%s}author' % ATOM_NS,
        element('{%s}uri' % ATOM_NS, report.author_uri))
    if report.author_uri.startswith('mailto:'):
        author.append(element(
            '{%s}email' % ATOM_NS, report.author_uri.split(':', 1)[1]))
    return element('{%s}entry' % ATOM_NS,
        element('{%s}id' % ATOM_NS, entry_id),
        element('{%s}subject' % REPORT_NS, report.subject_id),
        element('{%s}title' % ATOM_NS, report.title),
        author,
        element('{%s}observed' % REPORT_NS,
            time_formats.to_rfc3339(report.observed)),
        element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(report.arrived)),
        element('{%s}content' % REPORT_NS,
            {'type': '%s' % report.type_name},
            parse(report.content)),
        report.source_uri and element('{%s}source' % ATOM_NS,
            element('{%s}id' % ATOM_NS, report.source_uri)))

def create_feed(reports, feed_uri, hub=None):
    """Constructs an Atom <feed> element containing the given reports."""
    updated = None
    if reports:
        updated = reports[0].arrived
    else:
        updated = datetime.datetime.utcnow()
    elements = [
        element('{%s}id' % ATOM_NS, feed_uri),
        element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(updated)),
        element('{%s}title' % ATOM_NS, feed_uri),
    ]
    if hub:
        elements.append(element('{%s}link' % ATOM_NS,
            {'rel': 'hub', 'href': hub}))
    elements += [create_entry(report, feed_uri) for report in reports]
    return element('{%s}feed' % ATOM_NS, elements)

def write_entry(file, report, feed_uri, uri_prefixes={}):
    """Writes an Atom entry for the given report to the given file."""
    entry = create_entry(report, feed_uri)
    write(file, entry, add_uri_prefixes(uri_prefixes))

def write_feed(file, reports, feed_uri, uri_prefixes={}, hub=None):
    """Writes an Atom feed containing the given reports to the given file."""
    feed = create_feed(reports, feed_uri, hub)
    write(file, feed, add_uri_prefixes(uri_prefixes))

def notify_hub(feed_uri):
    """Notifies a PubSubHubbub hub of new content at a given feed URI."""
    data = urllib.urlencode({'hub.mode': 'publish', 'hub.url': feed_uri})
    file = urllib.urlopen(HUB, data)
    file.read()
    file.close()

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
                return etag, None, time_formats.from_rfc3339(timestamp)
        except (KeyError, ValueError):
            pass
    return None, 20, None

def create_response_etag(latest):
    """Constructs the ETag response header for the given reports."""
    arrival_time = latest and latest[0].arrived or 0
    timestamp = time_formats.to_rfc3339(arrival_time)
    return '"' + timestamp + '/' + sign('etag_key', timestamp) + '"'

def handle_feed_get(request, response, feed_name, uri_prefixes={}):
    """Handles a request for an Atom feed of XML reports."""
    etag, limit, arrived_after = check_request_etag(request.headers)
    latest = reports.get_latest_arrived(feed_name, None, arrived_after, limit)

    response.headers['Content-Type'] = 'application/atom+xml'
    if latest:  # Deliver the new entries.
        response.headers['ETag'] = create_response_etag(latest)
        write_feed(response.out, latest, request.uri, uri_prefixes, hub=HUB)
    elif etag:  # If-None-Match was specified, and there was nothing new.
        response.set_status(304)
        response.headers['ETag'] = '"' + etag + '"'
    else:  # There are no entries in this feed.
        write_feed(response.out, latest, request.uri, uri_prefixes, hub=HUB)

def handle_entry_get(request, response, feed_name, uri_prefixes={}):
    """Handles a request for the Atom entry for an individual XML report."""
    try:
        feed_uri, entry_key = request_uri.rsplit('/', 1)
        id = int(entry_key)
    except ValueError:
        raise ErrorMessage(404, 'No such entry')
    report = reports.XmlReport.get_by_id(id)
    if not report or report.feed_name != feed_name:
        raise ErrorMessage(404, 'No such entry')

    response.headers['Content-Type'] = 'application/atom+xml'
    response.headers['Last-Modified'] = time_formats.to_rfc1123(report.arrived)
    write_entry(response.out, report, feed_uri, uri_prefixes)

def get_child(element, name, ns=None):
    """Gets a child element, or raises an HTTP 400 error if not found."""
    if ns:
        name = qualify(ns, name)
    child = element.find(name)
    if child is None:  # need "is None" because childless elements are false
        raise ErrorMessage(400, '%s contains no %s' % (element.tag, name))
    return child

def get_text(element, name, ns=None):
    """Gets the text of a child element, or '' if the element is missing."""
    if ns:
        name = qualify(ns, name)
    return getattr(element.find(name), 'text', '')

def handle_feed_post(request, response, feed_name):
    """Handles a post of incoming entries, storing each entry as a report in
    the specified local feed, and using the feed-level <id> element as the
    source_uri of each stored report."""
    reports = []
    try:
        feed = parse(request.body)
    except SyntaxError, e:
        raise ErrorMessage(400, str(e))
    if feed.tag != qualify(ATOM_NS, 'feed'):
        raise ErrorMessage(400, 'Incoming document is not an Atom feed')
    source_uri = get_child(feed, 'id', ATOM_NS).text
    for entry in feed.findall(qualify(ATOM_NS, 'entry')):
        reports.append(create_report_from_entry(entry, feed_name, source_uri))
    db.put(reports)
    return reports

def create_report_from_entry(entry, feed_name, source_uri=None):
    """Converts an XML entry element into a XmlReport entity."""
    # Get the Atom metadata.
    author = get_child(entry, 'author', ATOM_NS)
    author_uri = (get_text(author, 'uri', ATOM_NS) or
                  'mailto:' + get_text(author, 'email', ATOM_NS))
    title = get_text(entry, 'title', ATOM_NS)

    # Get the report metadata (subject ID and observed time).
    subject_id = get_child(entry, 'subject', REPORT_NS).text
    observed = time_formats.from_rfc3339(
        get_child(entry, 'observed', REPORT_NS).text)

    # Get the content of the report.
    content = get_child(entry, 'content', REPORT_NS)
    element = get_child(content, content.attrib.get('type'))

    # Create the report entity.
    return reports.create_report(
        feed_name, subject_id, title, author_uri, observed, element, source_uri)
