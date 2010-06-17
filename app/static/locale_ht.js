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

  //i18n: Label for every item in a list.
  messages.ALL = "Tout";

  //i18n: Date at a given time (example: Jan 21, 2010 at 14:32 UTC-4)
  messages.DATE_AT_TIME = "${DATE} a ${TIME}";

  //i18n: Local date format (example: Jan 21, 2010)
  messages.DATE_FORMAT_MEDIUM = "${MONTH} ${DAY}, ${YEAR}";

  //i18n: Displaying markers on a map for facilities within RADIUS_MILES
  //i18n: miles of a location
  messages.DISPLAYING_FACILITIES_IN_RANGE = "Ekpoze etablisman nan ${RADIUS_MILES} mil";

  //i18n: Displaying markers on a map for the NUM_FACILITIES closest to a 
  //i18n: location
  messages.DISPLAYING_CLOSEST_N_FACILITIES = "Ekspoze ${NUM_FACILITIES} etablisman ki pi pre";

  //i18n: A distance (example: 3.11 miles (5 km))
  messages.DISTANCE = "${MILES} mil (${KM} kilom\u00e8t)";

  //i18n: Meaning: administrative division
  messages.DISTRICT = "Distri";

  //i18n: Error message for required field.
  messages.ERROR_FIELD_IS_REQUIRED = "Dom\u00e8n sa obligatwa.";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_INVALID = "Latitd dwe ant -90 ak 90";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_MUST_BE_NUMBER = "Latitd dwe yon nimewo";

  //i18n: Error message for not loading facility information successfully
  messages.ERROR_LOADING_FACILITY_INFORMATION = "Er\u00e8 transp\u00f2te etablisman enf\u00f2masyon.";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_INVALID = "Lonjitd dwe ant -180 ak 180";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_MUST_BE_NUMBER = "Lonjitd dwe yon nimewo";

  //i18n: Error message for a value that is not a number
  messages.ERROR_VALUE_MUST_BE_NUMBER = "Val\u00e8 dwe yon nimewo";

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE = "${NUM_FACILITIES} Etablisman nan ${RADIUS_MILES} mil";

  //i18n: A place that provides a particular service
  messages.FACILITY = "Etablisman";

  //i18n: Proper name of an ID for a healthcare facility defined by the
  //i18n: Pan-American Health Organization, no translation necessary.
  messages.FACILITY_PCODE = "PCode:";

  //i18n: Proper name of an ID for a healthcare facility, no translation
  //i18n: necessary.
  messages.HEALTHC_ID = "ID HealthC:";

  //i18n: Message indicating loading hospital information
  messages.LOADING = "Transp\u00f2te...";

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS = "Janvye, Fevriye, Mas, Avril, Me, Jen, jiy\u00e8, Out, septanm, Okt\u00f2b, Novanm, Desanm".split(' ');

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS = "Kabann disponib/total";

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION = "t ${PHONE}";

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP = "Premyeman chwazi yon lopital ki nan b\u00f2 goch la. L\u00e8 sa a enprimant la pral enprime yon lis lopital soti nan z\u00f2n ou ye a";

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP = "Enprime yon list lopital nan l\u00f2d distans de ${FACILITY_NAME}";

  //i18n: Message indicating hospital information has been saved
  messages.SAVED = "Nou anrejistre chanjman ou";

  //i18n: Message indicating saving hospital information
  messages.SAVING = "Anrejistre...";

  //i18n: work done by someone that benefits another
  messages.SERVICES = "S\u00e8vis";

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW = "Ekspoze:";

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE = "${HOURS}: ${MINUTES} ${ZONE}";

  //i18n: Label indicating a record was updated
  messages.UPDATED = "Remete an fonksyon";

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
