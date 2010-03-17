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

import record_model
import xmlutils

class RecordType:
    def get_identifier(self, element):
        """Extracts the record_id string from an ElementTree element."""
        raise NotImplementedError

    def get_observation_time(self, element):
        """Extracts the observation time from an ElementTree element."""
        raise NotImplementedError

type_registry = {}

def register_type(type_name, record_type):
    type_registry[type_name] = record_type

prefix_registry = {}

def register_prefix(prefix, namespace):
    prefix_registry[namespace] = prefix

def put_record(feed, element):
    record_model.Record(
        feed=feed,
        type=element.tag,
        record_id=type_registry[type].get_identifier(element),
        observation_time=type_registry[type].get_observation_time(element),
        content=xmlutils.tostring(element)
    ).put()

def get_latest_observed(type, record_id):
    query = (record_model.Record.all().filter('type =', type)
                                      .filter('record_id =', record_id)
                                      .order('-observation_time'))
    return query.get()

def get_latest_arrived(type, record_id, limit=None, min_arrival_time=None):
    query = (record_model.Record.all().filter('type =', type)
                                      .filter('record_id =', record_id)
                                      .order('-arrival_time'))
    return query.fetch(min(limit or 100, 100))
