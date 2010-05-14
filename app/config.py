#!/usr/bin/python2.5
# Copyright 2009-2010 by Steve Hakusa
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

# Application-wide configuration settings.

# List of languages that appear in the language menu, as (code, name) pairs.
LANGUAGES = [('en', 'English'),
             ('fr', u'Fran\u00e7ais'), # French
             #('ht', u'Krey\u00f2l'), # Kreyol
             ('es-419', u'Espa\u00F1ol'), # Spanish (Latin American)
             ]

# Mapping of alternate language code to internal representation
ALTERNATE_LANG_CODES = { 'es': 'es-419', }