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
from crypto import sign, verify
from errors import ErrorMessage
from xmlutils import qualify, parse


def check_request_etag(headers):
    """Determines etag, limit, after_arrival_time based on request headers."""
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
    arrival_time = latest and latest[0].arrival_time or 0
    timestamp = time_formats.to_rfc3339(arrival_time)
    return '"' + timestamp + '/' + sign('etag_key', timestamp) + '"'

def handle_feed_get(request, response, feed_id, uri_prefixes={}):
    """Handles a request for an Atom feed of XML records."""
    etag, limit, after_arrival_time = check_request_etag(request.headers)
    latest = records.get_latest_arrived(feed_id, limit, after_arrival_time)

    response.headers['Content-Type'] = 'application/atom+xml'
    if latest:  # Deliver the new entries.
        response.headers['ETag'] = create_response_etag(latest)
        atom.write_feed(response.out, latest, uri_prefixes)
    elif etag:  # If-None-Match was specified, and there was nothing new.
        response.set_status(304)
        response.headers['ETag'] = '"' + etag + '"'
    else:  # There are no entries in this feed.
        atom.write_feed(response.out, latest, uri_prefixes)

def handle_entry_get(request, response, feed_id, entry_id, uri_prefixes={}):
    """Handles a request for the Atom entry for an individual XML record."""
    try:
        id = int(entry_id)
    except ValueError:
        raise ErrorMessage(404, _('No such entry'))
    record = records.Record.get_by_id(id)
    if not record or record.feed_id != feed_id:
        raise ErrorMessage(404, _('No such entry'))

    response.headers['Content-Type'] = 'application/atom+xml'
    response.headers['Last-Modified'] = \
        time_formats.to_rfc1123(record.arrival_time)
    atom.write_entry(response.out, record, uri_prefixes)

def get_child(element, name, error_message):
    """Gets an Atom element, or raises an HTTP 400 error if not found."""
    child = element.find(qualify(atom.ATOM_NS, name))
    if child is None:
        raise ErrorMessage(400, error_message)
    return child

def handle_feed_post(request, response):
    """Handles a post of incoming entries from PubSubHubbub."""
    try:
        feed = parse(request.body)
    except SyntaxError, e:
        raise ErrorMessage(400, str(e))
    if feed.tag != qualify(atom.ATOM_NS, 'feed'):
        raise ErrorMessage(400, _('Incoming document is not an Atom feed'))
    feed_id = get_child(feed, 'id', 'feed has no id')
    for entry in feed.findall(qualify(atom.ATOM_NS, 'entry')):
        entry_id = get_child(entry, 'id', _('entry has no id'))
        author = get_child(entry, 'author', _('entry %r has no author') % entry_id)
        email = get_child(author, 'email', _('entry %r has no email') % entry_id)
        for child in entry.getchildren():
            if not child.tag.startswith('{%s}' % atom.ATOM_NS):
                try:
                    records.put_record(feed_id.text, email.text, child)
                except TypeError, e:
                    raise ErrorMessage(400, str(e))
                break
        else:
            raise ErrorMessage(400, _('entry %r contains no XML document'))


if __name__ == '__main__':
    run([(r'/feeds/([^/]+)', Feed),
         (r'/feeds/([^/]+)/([^/]+)', Entry)])
