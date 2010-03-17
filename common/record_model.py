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

"""The data model for XML record storage."""

from google.appengine.ext import db

class Record(db.Model):
    """Entity representing one received XML document."""
    feed = db.StringProperty(required=True)  # canonical URL for source feed
    type = db.StringProperty(required=True)  # XML type in Clark notation
    record_id = db.StringProperty(required=True)  # non-unique record ID
    author_email = db.StringProperty(required=True)  # author identifier
    observation_time = db.DateTimeProperty(required=True)  # UTC timestamp
    arrival_time = db.DateTimeProperty(auto_now=True)  # UTC timestamp
    content = db.TextProperty()  # XML document
