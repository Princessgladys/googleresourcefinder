# Copyright 2010 Google Inc.
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

import utils
import django.utils.translation  # must be imported after utils

class Help(utils.Handler):
    def get(self):
        lang = django.utils.translation.get_language()
        self.render('locale/%s/help.html' % lang, params=self.params)

if __name__ == '__main__':
    utils.run([('/help', Help)], debug=True)
