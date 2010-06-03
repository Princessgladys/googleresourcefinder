# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for cron.py."""

from feeds.xmlutils import Struct

import cron
import datetime
import unittest

JOB1 = Struct()
JOB1.description = 'test'
JOB1.url = 'http://www.google.com/'
JOB1.payload = {}
JOB1.method ='GET'
JOB1.months = []
JOB1.days_of_month = [datetime.datetime.now().day]
JOB1.weekdays = []
JOB1.hours_of_day = [datetime.datetime.now().hour]
JOB1.minutes_of_hour = [datetime.datetime.now().minute]
    
JOB2 = Struct()
JOB2.months = []
JOB2.days_of_month = [datetime.datetime.now().day + 1]
JOB2.isoweekday = []
JOB2.hours_of_day = [datetime.datetime.now().hour + 1]
JOB2.minutes_of_hour = [datetime.datetime.now().minute + 1]

class CronTest(unittest.TestCase):
    def test_check_time(self):
        assert cron.job_should_run(JOB1, datetime.datetime.now()) == True
        assert cron.job_should_run(JOB2, datetime.datetime.now()) == False
