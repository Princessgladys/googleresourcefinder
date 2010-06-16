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

from cron import Job, Timestamp

import cron
import datetime
import unittest

class CronTest(unittest.TestCase):
    def setUp(self):
        self.job1 = Job(description='test', url='http://www.google.com/',
                        payload='', method='GET', months=[],
                        days_of_month=[datetime.datetime.now().day],
                        weekdays=[],
                        hours_of_day=[datetime.datetime.now().hour],
                        minutes_of_hour=[datetime.datetime.now().minute])

        self.job2 = Job(description='test', url='http://www.google.com/',
                        payload='', method='GET', months=[], 
                        days_of_month=[datetime.datetime.now().day+1],
                        weekdays=[],
                        hours_of_day=[datetime.datetime.now().hour+1],
                        minutes_of_hour=[datetime.datetime.now().minute+1])
        
        self.now = datetime.datetime.utcnow()
        Timestamp(key_name='cron',
                  timestamp=self.now-datetime.timedelta(0, 0, 0, 0, 3)).put()
    
    def test_get_datetimes(self):
        times = cron.get_datetimes()
        assert len(times) == 3
        for i in range(len(times)):
            assert times[i].minute == self.now.minute-len(times)+i+1
    
    def test_job_should_run(self):
        assert cron.job_should_run(self.job1, datetime.datetime.now()) == True
        assert cron.job_should_run(self.job2, datetime.datetime.now()) == False
    
    def test_make_task_name(self):
        assert cron.make_task_name('foo') == 'foo'
        assert cron.make_task_name('foo! \t\n!BAR37') == 'foo---BAR37'
