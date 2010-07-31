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

"""Configuration settings for unit tests.  Import this before utils."""

from feedlib import fake_config

fake_config.use_fake_config(
    hub='https://pubsubhubbub.appspot.com',
    languages=u'en:English|fr:Fran\xe7ais|ht:Krey\xf2l|es-419:Espa\xf1ol',
    lang_fallbacks='es:es-419',
    maps_lang_fallbacks='ht:fr',
    hidden_attribute_names=
        'accuracy region_id district_id commune_id commune_code sante_id')
