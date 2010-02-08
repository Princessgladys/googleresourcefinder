#!/usr/bin/python2.5
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

"""Simple KML parser for placemarks."""

__author__ = 'Ka-Ping Yee <ping@zesty.ca>'

import re
import xml.sax
import xml.sax.handler

def strip(content):
    return content.strip()

def single_line(content):
    return ' '.join(content.split())

def parse_coordinates(content):
    return map(float, content.strip().split(','))

INVALID_IMG_RE = re.compile(r'''<img[^>]*src=["']https?://[^.]+?/.*?["'].*?>''')

def clean_html(content):
    if '<' in content:
        return INVALID_IMG_RE.sub('', content)
    else:
        return content.replace('\n', '<br>').strip()

class Handler(xml.sax.handler.ContentHandler):
    field_for_tag = {
        'name': 'name',
        'coordinates': 'location',
        'description': 'comment'
    }

    parser_for_field = {
        'name': single_line,
        'location': parse_coordinates,
        'comment': clean_html,
    }

    def __init__(self):
        self.tags = []
        self.record = {}
        self.records = []

    def startElement(self, name, attrs):
        self.tags.append(name)
        if name == 'Placemark':
            self.record = {}

    def endElement(self, name):
        assert self.tags.pop() == name
        if name == 'Placemark':
            for field in self.record:
                parser = self.parser_for_field[field]
                self.record[field] = parser(self.record[field])
            self.records.append(self.record)

    def characters(self, content):
        field = self.field_for_tag.get(self.tags[-1], None)
        if field:
            self.record.setdefault(field, '')
            self.record[field] += content


def parse_file(kml_file):
    handler = Handler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.parse(kml_file)
    return handler.records
