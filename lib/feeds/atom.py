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

"""Input and output of reports in Atom feeds."""

import datetime
import logging
import time_formats
import xmlutils

ATOM_NS = 'http://www.w3.org/2005/Atom'
REPORT_NS = 'http://schemas.google.com/2010/report'

def add_atom_prefix(uri_prefixes):
    """Adds an entry for the Atom namespace to a prefix dictionary."""
    return dict([(ATOM_NS, 'atom'), (REPORT_NS, 'report')], **uri_prefixes)

def create_entry(report):
    """Constructs an Element for an Atom entry for the given report."""
    atom_id = report.feed_id + '/' + str(report.key().id())
    author = xmlutils.element('{%s}author' % ATOM_NS,
        xmlutils.element('{%s}uri' % ATOM_NS, report.author_uri))
    if report.author_uri.startswith('mailto:'):
        author.append(xmlutils.element(
            '{%s}email' % ATOM_NS, report.author_uri.split(':', 1)[1]))
    return xmlutils.element('{%s}entry' % ATOM_NS,
        xmlutils.element('{%s}id' % ATOM_NS, atom_id),
        author,
        xmlutils.element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(report.arrived)),
        xmlutils.element('{%s}title' % ATOM_NS, report.title),
        xmlutils.element('{%s}subject' % REPORT_NS, report.subject_id),
        xmlutils.element('{%s}observed' % REPORT_NS,
            time_formats.to_rfc3339(report.observed)),
        xmlutils.element('{%s}report' % REPORT_NS,
            {'type': '%s' % report.type_name},
            xmlutils.parse(report.content))
    )

def create_feed(reports, feed_id, hub=None):
    """Constructs an Element for an Atom feed containing the given reports."""
    updated = None
    if reports:
        updated = reports[0].arrived
    else:
        updated = datetime.datetime.utcnow()
    elements = [
        xmlutils.element('{%s}id' % ATOM_NS, feed_id),
        xmlutils.element('{%s}updated' % ATOM_NS,
            time_formats.to_rfc3339(updated)),
        xmlutils.element('{%s}title' % ATOM_NS, feed_id),
    ]
    if hub:
        elements.append(xmlutils.element('{%s}link' % ATOM_NS,
            {'rel': 'hub', 'href': hub}))
    elements.extend(map(create_entry, reports))
    return xmlutils.element('{%s}feed' % ATOM_NS, elements)

def write_entry(file, report, uri_prefixes={}):
    """Writes an Atom entry for the given report to the given file."""
    xmlutils.write(file, create_entry(report), add_atom_prefix(uri_prefixes))

def write_feed(file, reports, feed_id, uri_prefixes={}, hub=None):
    """Writes an Atom feed containing the given reports to the given file."""
    feed = create_feed(reports, feed_id, hub)
    xmlutils.write(file, feed, add_atom_prefix(uri_prefixes))
