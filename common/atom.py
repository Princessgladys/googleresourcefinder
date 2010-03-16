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

import time_formats
import xmlutils

ATOM_NS = 'http://www.w3.org/2005/Atom'

def add_atom_prefix(uri_prefixes):
    """Adds an entry for the Atom namespace to a prefix dictionary."""
    return dict([(ATOM_NS, 'atom')], **uri_prefixes)

def create_entry(record):
    """Constructs an Element for an Atom entry for the given record."""
    atom_id = record.feed + '/' + str(record.key().id())
    return xmlutils.element('{%s}entry' % ATOM_NS,
        xmlutils.element('{%s}author' % ATOM_NS,
            xmlutils.element('{%s}email' % ATOM_NS, record.author_email)),
        xmlutils.element('{%s}id' % ATOM_NS, atom_id),
        xmlutils.element('{%s}title' % ATOM_NS, record.title),
        xmlutils.element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(record.arrival_time)),
        xmlutils.parse(record.content)
    )

def create_feed(records):
    """Constructs an Element for an Atom feed containing the given records."""
    return xmlutils.element('{%s}feed' % ATOM_NS, map(create_entry, records))

def write_entry(file, record, uri_prefixes={}):
    """Writes an Atom entry for the given record to the given file."""
    xmlutils.write(file, create_entry(record), add_atom_prefix(uri_prefixes))

def write_feed(file, records, uri_prefixes={}):
    """Writes an Atom feed containing the given records to the given file."""
    xmlutils.write(file, create_feed(records), add_atom_prefix(uri_prefixes))
