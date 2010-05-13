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

"""Date and time format conversions."""

import datetime
import re
import rfc822

TIMESTAMP_RE = re.compile(
    r'^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?Z$')

def from_rfc3339(timestamp):
    """Converts a UTC timestamp in RFC 3339 format to a UTC datetime object."""
    match = TIMESTAMP_RE.match(timestamp)
    try:
        year, month, day, hour, minute, second = map(int, match.groups()[:6])
        micros = match.group(7) and int(float(match.group(7)) * 1000000) or 0
    except ValueError:
        raise ValueError('invalid timestamp format: %r' % timestamp)
    return datetime.datetime(year, month, day, hour, minute, second, micros)

def to_rfc3339(dt):
    """Formats a UTC datetime object as a UTC timestamp in RFC 3339 format."""
    return dt.isoformat() + 'Z'

def to_rfc1123(dt):
    """Formats a UTC datetime object as a GMT timestamp in RFC 1123 format."""
    delta = dt - datetime.datetime.utcfromtimestamp(0)
    return rfc822.formatdate(delta.days*86400 + delta.seconds)
