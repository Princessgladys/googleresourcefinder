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

import cron
import datetime
import unittest

class CronTest(unittest.TestCase):
    def setUp(self):
        self.time = datetime.datetime(2010, 06, 16, 12, 30, 37)
        self.job1 = cron.Job(description='test', url='http://www.google.com/',
                             payload='', method='GET', months=[],
                             days_of_month=[self.time.day],
                             weekdays=[],
                             hours_of_day=[self.time.hour],
                             minutes_of_hour=[self.time.minute])

        self.job2 = cron.Job(description='test', url='http://www.google.com/',
                             payload='', method='GET', months=[], 
                             days_of_month=[self.time.day + 1],
                             weekdays=[],
                             hours_of_day=[self.time.hour + 1],
                             minutes_of_hour=[self.time.minute + 1])
        
        timestamp = self.time - datetime.timedelta(minutes=3)
        cron.Timestamp(key_name='cron', timestamp=timestamp).put()
        
    def test_get_datetimes(self):
        times = cron.get_datetimes(self.time)
        assert len(times) == 3
        for i in range(len(times)):
            assert times[i].minute == self.time.minute - 2 + i
        
    def test_job_should_run(self):
        assert cron.job_should_run(self.job1, self.time) == True
        assert cron.job_should_run(self.job2, self.time) == False

    def test_make_task_name(self):
        assert cron.make_task_name('foo') == 'foo'
        assert cron.make_task_name('foo! \t\n!BAR37') == 'foo---BAR37'
