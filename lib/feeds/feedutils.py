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

"""Support for feed providers backed by the XML record store."""

import atom
import records
import time_formats
import urllib
from crypto import sign, verify
from errors import ErrorMessage
from xmlutils import qualify, parse

HUB = 'http://pubsubhubbub.appspot.com'
STATUS_NS = 'http://schemas.google.com/2010/status'

def notify_hub(feed_url):
    """Notifies a PubSubHubbub hub of new content."""
    data = urllib.urlencode({'hub.mode': 'publish', 'hub.url': feed_url})
    file = urllib.urlopen(HUB, data)
    file.read()
    file.close()

def check_request_etag(headers):
    """Determines etag, limit, arrived_after based on request headers."""
    # TODO: If records A and B are written to different data centers,
    # and clock skew causes B to be written with an arrival_time earlier
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
    """Constructs the ETag response header for the given records."""
    arrival_time = latest and latest[0].arrived or 0
    timestamp = time_formats.to_rfc3339(arrival_time)
    return '"' + timestamp + '/' + sign('etag_key', timestamp) + '"'

def handle_feed_get(request, response, feed_id, uri_prefixes={}):
    """Handles a request for an Atom feed of XML records."""
    etag, limit, arrived_after = check_request_etag(request.headers)
    latest = records.get_latest_arrived(feed_id, limit, arrived_after)

    response.headers['Content-Type'] = 'application/atom+xml'
    if latest:  # Deliver the new entries.
        response.headers['ETag'] = create_response_etag(latest)
        atom.write_feed(response.out, latest, feed_id, uri_prefixes, hub=HUB)
    elif etag:  # If-None-Match was specified, and there was nothing new.
        response.set_status(304)
        response.headers['ETag'] = '"' + etag + '"'
    else:  # There are no entries in this feed.
        atom.write_feed(response.out, latest, feed_id, uri_prefixes, hub=HUB)

def handle_entry_get(request, response, feed_id, entry_id, uri_prefixes={}):
    """Handles a request for the Atom entry for an individual XML record."""
    try:
        id = int(entry_id)
    except ValueError:
        raise ErrorMessage(404, 'No such entry')
    record = records.Record.get_by_id(id)
    if not record or record.feed_id != feed_id:
        raise ErrorMessage(404, 'No such entry')

    response.headers['Content-Type'] = 'application/atom+xml'
    response.headers['Last-Modified'] = \
        time_formats.to_rfc1123(record.arrived)
    atom.write_entry(response.out, record, uri_prefixes)

def get_child(element, name, ns=None):
    """Gets an element, or raises an HTTP 400 error if not found."""
    if ns:
        name = qualify(ns, name)
    child = element.find(name)
    # Elements without children are false, so we have to compare with None.
    if child is None:
        raise ErrorMessage(400, '%s contains no %s' % (element.tag, name))
    return child

def get_optional_text(element, name, ns=None):
    """Gets the text of a child element, or '' if the element is missing."""
    if ns:
        name = qualify(ns, name)
    child = element.find(name)
    # Elements without children are false, so we have to compare with None.
    if child is None:
        return ''
    return child.text

def handle_feed_post(request, response):
    """Handles a post of incoming entries from PubSubHubbub."""
    posted_records = []
    try:
        feed = parse(request.body)
    except SyntaxError, e:
        raise ErrorMessage(400, str(e))
    if feed.tag != qualify(atom.ATOM_NS, 'feed'):
        raise ErrorMessage(400, 'Incoming document is not an Atom feed')
    feed_id = get_child(feed, 'id', atom.ATOM_NS)
    for entry in feed.findall(qualify(atom.ATOM_NS, 'entry')):
        # Get the Atom metadata.
        entry_id = get_child(entry, 'id', atom.ATOM_NS)
        author = get_child(entry, 'author', atom.ATOM_NS)
        email = get_child(author, 'email', atom.ATOM_NS)
        title = get_optional_text(entry, 'title', atom.ATOM_NS)

        # Get the status report metadata (subject ID and observed time).
        subject = get_child(entry, 'subject', STATUS_NS)
        observed = time_formats.from_rfc3339(
            get_child(entry, 'observed', STATUS_NS).text)

        # Get the content of the status report.
        report = get_child(entry, 'report', STATUS_NS)
        content = get_child(report, report.attrib.get('type'))

        # Store the record.
        posted_records.append(records.put_record(
            feed_id.text, email.text, title, subject.text, observed, content))
    notify_hub(feed_id.text)
    return posted_records

