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

"""Atom feed input and output."""

import datetime
import logging
import time_formats
import xmlutils

ATOM_NS = 'http://www.w3.org/2005/Atom'

def add_atom_prefix(uri_prefixes):
    """Adds an entry for the Atom namespace to a prefix dictionary."""
    return dict([(ATOM_NS, 'atom')], **uri_prefixes)

def create_entry(record):
    """Constructs an Element for an Atom entry for the given record."""
    atom_id = record.feed_id + '/' + str(record.key().id())
    return xmlutils.element('{%s}entry' % ATOM_NS,
        xmlutils.element('{%s}author' % ATOM_NS,
            xmlutils.element('{%s}email' % ATOM_NS, record.author_email)),
        xmlutils.element('{%s}id' % ATOM_NS, atom_id),
        xmlutils.element('{%s}title' % ATOM_NS, record.title),
        xmlutils.element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(record.arrived)),
        xmlutils.parse(record.content)
    )

def __create_feed(records, feed_id, hub=None):
    """Constructs an Element for an Atom feed containing the given records."""
    updated = None
    if records:
      updated = records[0].arrived
    else:
      updated = datetime.datetime.utcnow()
    elements = [
        xmlutils.element('{%s}title' % ATOM_NS, feed_id),
        xmlutils.element('{%s}id' % ATOM_NS, feed_id),
        xmlutils.element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(updated))
        ]
    if hub:
        elements.append(xmlutils.element('{%s}link' % ATOM_NS,
            {'rel': 'hub', 'href': hub}))
    elements.extend(map(create_entry, records))
    return xmlutils.element('{%s}feed' % ATOM_NS, elements)

def write_entry(file, record, uri_prefixes={}):
    """Writes an Atom entry for the given record to the given file."""
    xmlutils.write(file, create_entry(record), add_atom_prefix(uri_prefixes))

def write_feed(file, records, feed_id, uri_prefixes={}, hub=None):
    """Writes an Atom feed containing the given records to the given file."""


    feed = __create_feed(records, feed_id, hub)

    xmlutils.write(file, feed, add_atom_prefix(uri_prefixes))
