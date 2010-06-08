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

from utils import *
from html import *

class Scan(Handler):
    def get(self):
        self.write('''
<!doctype html public "-//W3C//HTML 4.01 Transitional//EN">
<link rel=stylesheet href="static/style.css">
<style>td, th { padding-left: 4px; }</style>
''')
        country_codes = [country.key().name() for country in Country.all()]
        if self.request.get('cc'):
            country_codes = [self.request.get('cc')]
        for cc in sorted(country_codes):
            country = get(None, Country, cc)
            counts = {'version': 0, 'base': 0,
                      'dump': 0, 'dumps': 0, 'supplies': 0}
            self.write('''
<table cellpadding=0 cellspacing=0 class="list">
<tr><td colspan=6>%s</td></tr>
<tr>
  <th class="index">timestamp</th>
  <th>version</th>
  <th>base</th>
  <th>dump</th>
  <th>dumps</th>
  <th>supplies</th>
</tr>''' % html_repr(country))
            for version in Version.all().ancestor(country).order('-timestamp'):
                self.write('''
<tr>
  <td class="index">%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
</tr>''' % (
    html_repr(version.timestamp, leaf=1, depth=0),
    html_repr(version, leaf=1, depth=0),
    html_repr(version.base, leaf=1, depth=0),
    html_repr(version.dump, leaf=0, depth=0),
    html_repr(version.dumps, leaf=0, depth=0),
    len(version.supplies)
))
                counts['version'] += (not not version)
                counts['base'] += (not not version.base)
                counts['dump'] += (not not version.dump)
                counts['dumps'] += (not not version.dumps)
                counts['supplies'] += (not not version.supplies)
            self.write('''
<tr>
  <th>counts</th>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
</tr>''' % (
    counts['version'],
    counts['base'],
    counts['dump'],
    counts['dumps'],
    counts['supplies']
))
            self.write('</table>')

if __name__ == '__main__':
    run([('/scan', Scan)], debug=True)
