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

"""Common exception classes."""

class ErrorMessage(Exception):
    """Raise this exception to show an error message to the user."""
    def __init__(self, status, message):
        self.status = status
        self.message = message

    def __str__(self):
        return 'ErrorMessage(%r, %r)' % (self.status, self.message)

class Redirect(Exception):
    """Raise this exception to redirect to another page."""
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return 'Redirect(%r)' % self.url
