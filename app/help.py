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

class Help(utils.Handler):
    def get(self):
        locale = utils.get_locale()
        self.render('locale/%s/help.html' % locale, params=self.params)


# The email update help pages below [the base help file, the documentation,
# and the reference] are currently available only in English.
class EmailHelp(utils.Handler):
    def get(self):
        self.render('locale/en/help_email.html', params=self.params)


class EmailHelpDocumentation(utils.Handler):
    def get(self):
        self.render('locale/en/help_email_documentation.html',
                    params=self.params)


class EmailHelpReference(utils.Handler):
    def get(self):
        self.render('locale/en/help_email_reference.html', params=self.params)


if __name__ == '__main__':
    utils.run([
        ('/help', Help),
        ('/help/email', EmailHelp),
        ('/help/email/documentation', EmailHelpDocumentation),
        ('/help/email/reference', EmailHelpReference)
    ], debug=True)
