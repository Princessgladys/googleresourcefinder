/*
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
*/

/**
 * @fileoverview Message definitions for translation.
 */

locale = function() {
  var messages = {};

  messages.CALL_FOR_AVAILABILITY =
      'Please call for availability information';

  messages.DATE_AT_TIME =
      '${DATE} at ${TIME}';

  messages.DISPLAYING_FACILITIES_IN_RANGE =
      'Displaying facilities within ${RADIUS_MILES} miles';

  messages.DISPLAYING_CLOSEST_N_FACILITIES =
      'Displaying ${NUM_FACILITIES} closest facilities';

  messages.DISTANCE =
      '${MILES} miles (${KM} km)';

  messages.EDIT_LINK_HTML =
      HTML('${LINK_START}Edit this record${LINK_END}');

  messages.FACILITIES_IN_RANGE =
      '${NUM_FACILITIES} Facilities within ${RADIUS_MILES} miles';

  messages.GEOLOCATION_HTML =
      HTML('Latitude: ${LATITUDE}<br>Longitude: ${LONGITUDE}');

  // Month indices run from 0 to 11 (Jan to Dec)
  messages.MONTH_ABBRS =
      'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');

  messages.NO =
      'No';

  messages.PRINT_DISABLED_TOOLTIP =
      'First select a hospital from the list on the left. Then Print will ' +
      'print a list of hospitals in order of distance from your selection.';

  messages.PRINT_ENABLED_TOOLTIP =
      'Print a list of hospitals in order of distance from ${FACILITY_NAME}';

  messages.REQUEST_EDIT_ACCESS_HTML =
      HTML('${LINK_START}Request edit access${LINK_END}');

  messages.SIGN_IN_TO_EDIT =
      'Please sign in to edit';

  messages.YES =
      'Yes';

  function message_renderer(name) {
    return function (params) {
      return render(messages[name], params);
    };
  }

  function array_message_renderer(name, index) {
    return function (params) {
      return render(messages[name][index], params);
    };
  }

  locale = {};
  for (var name in messages) {
    if (messages[name].constructor === Array) {
      locale[name] = [];
      for (var i = 0; i < messages[name].length; i++) {
        locale[name][i] = array_message_renderer(name, i);
      }
    } else {
      locale[name] = message_renderer(name);      
    }
  }
  return locale;
}();
