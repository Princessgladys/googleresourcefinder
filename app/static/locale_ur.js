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

  //i18n: Label to add a facility
  messages.ADD = "\u0627\u0636\u0627\u0641\u06c1 \u06a9\u0631\u06cc";

  //i18n: Label for every item in a list.
  messages.ALL = "\u0633\u0628\u06be\u06cc";

  //i18n: Label for a cancel link
  messages.CANCEL = "\u0645\u0646\u0633\u0648\u062e \u06a9\u0631\u06cc\u06ba";

  //i18n: Message explaining how to place a new subject on the map
  messages.CLICK_TO_ADD_SUBJECT = "\u067e\u0631 \u06a9\u0644\u06a9 \u06a9\u0631\u06cc\u06ba \u0646\u0642\u0634\u06d2 \u067e\u0631 \u0627\u06cc\u06a9 \u062c\u06af\u06c1 \u0627\u06cc\u06a9 \u0646\u0626\u06cc \u0633\u06c1\u0648\u0644\u062a \u06a9\u06d2 \u0644\u0626\u06d2 \u0645\u0627\u0631\u06a9\u0631 \u062c\u06af\u06c1";

  //i18n: Date at a given time (example: Jan 21, 2010 at 14:32 UTC-4)
  messages.DATE_AT_TIME = "${DATE} \u067e\u0631 ${TIME}";

  //i18n: Local date format (example: Jan 21, 2010)
  messages.DATE_FORMAT_MEDIUM = "${MONTH} ${DAY}\u060c ${YEAR}";

  //i18n: Displaying markers on a map for facilities within RADIUS_MILES
  //i18n: miles of a location
  messages.DISPLAYING_FACILITIES_IN_RANGE = "${RADIUS_MILES} \u0645\u06cc\u0644 \u06a9\u06d2 \u0627\u0646\u062f\u0631 \u06a9\u06cc \u0633\u06c1\u0648\u0644\u06cc\u0627\u062a \u062f\u06a9\u06be\u0627 \u0631\u06c1\u0627 \u06c1\u06d2";

  //i18n: Displaying markers on a map for the NUM_FACILITIES closest to a 
  //i18n: location
  messages.DISPLAYING_CLOSEST_N_FACILITIES = "${NUM_FACILITIES} \u0642\u0631\u06cc\u0628 \u062a\u0631\u06cc\u0646 \u0633\u06c1\u0648\u0644\u06cc\u0627\u062a \u062f\u06a9\u06be\u0627 \u0631\u06c1\u0627 \u06c1\u06d2";

  //i18n: A distance (example: 3.11 miles (5 km))
  messages.DISTANCE = "${MILES} \u0645\u06cc\u0644 (${KM} \u06a9\u0644\u0648\u0645\u06cc\u0679\u0631)";

  //i18n: Meaning: administrative division
  messages.DISTRICT = "\u0636\u0644\u0639";

  //i18n: Notifies user how to add latitude and longitude values.
  messages.EDIT_LATITUDE_LONGITUDE = "\u0622\u067e \u0641\u0627\u0631\u0645 \u0621 \u062a\u0631\u0645\u06cc\u0645 \u0645\u06cc\u06ba \u0627\u06cc\u06a9 \u0637\u0648\u0644 \u0628\u0644\u062f \u0627\u0648\u0631 \u0639\u0631\u0636 \u0628\u0644\u062f \u06a9\u06d2 \u0634\u0627\u0645\u0644 \u06a9\u0631 \u0633\u06a9\u062a\u06d2 \u06c1\u06cc\u06ba";

  //i18n: Saved message; e-mail subscription has been saved
  messages.EMAIL_SUBSCRIPTION_SAVED = "\u0622\u067e \u06a9\u0648 \u0627\u0633 \u0633\u06c1\u0648\u0644\u062a \u06a9\u06cc\u0644\u0626\u06d2 ${FREQUENCY} \u0627\u06cc \u0645\u06cc\u0644 \u062a\u0627\u0632\u06c1 \u06a9\u0627\u0631\u06cc\u0627\u06ba \u0645\u0648\u0635\u0648\u0644 \u06c1\u0648\u06ba \u06af\u06cc\u06d4 \u0631\u06a9\u0646\u06cc\u062a \u06a9\u06cc \u062a\u0631\u062a\u06cc\u0628\u0627\u062a \u0628\u062f\u0644\u0646\u06d2 \u06a9\u06cc\u0644\u0626\u06d2 ${START_LINK}\u062a\u0631\u062a\u06cc\u0628\u0627\u062a${END_LINK} \u06a9\u0627 \u0635\u0641\u062d\u06c1 \u0627\u0633\u062a\u0639\u0645\u0627\u0644 \u06a9\u0631\u06cc\u06ba\u06d4";

  //i18n: Eror message, shown when an error occurs.
  messages.ERROR = "\u0627\u06cc\u06a9 \u063a\u0644\u0637\u06cc \u0648\u0627\u0642\u0639 \u06c1\u0648\u06af\u0626\u06cc \u06c1\u06d2\u06d4 \u0628\u0631\u0627\u06c1 \u06a9\u0631\u0645 \u0628\u0639\u062f \u0645\u06cc\u06ba \u062f\u0648\u0628\u0627\u0631\u06c1 \u0622\u0632\u0645\u0627\u0626\u06cc\u06ba\u06d4";

  //i18n: Error message for required field.
  messages.ERROR_FIELD_IS_REQUIRED = "\u0641\u06cc\u0644\u0688 \u0645\u0637\u0644\u0648\u0628 \u06c1\u06d2\u06d4";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_INVALID = "\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062f -90 \u0627\u0648\u0631 90 \u06a9\u06d2 \u062f\u0631\u0645\u06cc\u0627\u0646 \u06c1\u0648\u0646\u0627 \u0686\u0627\u06c1\u06cc\u06d2\u06d4";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_MUST_BE_NUMBER = "\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062f \u0627\u06cc\u06a9 \u0639\u062f\u062f \u06c1\u0648\u0646\u0627 \u0686\u0627\u06c1\u06cc\u06d2\u06d4";

  //i18n: Error message for not loading edit form successfully
  messages.ERROR_LOADING_EDIT_FORM = "\u062a\u0631\u0645\u06cc\u0645\u06cc \u0641\u0627\u0631\u0645 \u0644\u0648\u0688 \u06a9\u0631\u0646\u06d2 \u0645\u06cc\u06ba \u063a\u0644\u0637\u06cc\u06d4";

  //i18n: Error message for not loading facility information successfully
  messages.ERROR_LOADING_FACILITY_INFORMATION = "\u0633\u06c1\u0648\u0644\u062a \u06a9\u06cc \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0644\u0648\u0688 \u06a9\u0631\u0646\u06d2 \u0645\u06cc\u06ba \u063a\u0644\u0637\u06cc\u06d4";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_INVALID = "\u0637\u0648\u0644 \u0627\u0644\u0628\u0644\u062f -180 \u0627\u0648\u0631 180 \u06a9\u06d2 \u062f\u0631\u0645\u06cc\u0627\u0646 \u06c1\u0648\u0646\u0627 \u0686\u0627\u06c1\u06cc\u06d2\u06d4";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_MUST_BE_NUMBER = "\u0637\u0648\u0644 \u0627\u0644\u0628\u0644\u062f \u0627\u06cc\u06a9 \u0639\u062f\u062f \u06c1\u0648\u0646\u0627 \u0686\u0627\u06c1\u06cc\u06d2\u06d4";

  //i18n: Error message for not saving facility information successfully
  messages.ERROR_SAVING_FACILITY_INFORMATION = "\u0633\u06c1\u0648\u0644\u062a \u06a9\u06cc \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0645\u062d\u0641\u0648\u0638 \u06a9\u0631\u0646\u06d2 \u0645\u06cc\u06ba \u063a\u0644\u0637\u06cc\u06d4";

  //i18n: Error message for a value that is not a number
  messages.ERROR_VALUE_MUST_BE_NUMBER = "\u0642\u062f\u0631 \u0644\u0627\u0632\u0645\u06cc \u0637\u0648\u0631 \u067e\u0631 \u0639\u062f\u062f \u06c1\u0648\u0646\u06cc \u0686\u0627\u06c1\u06cc\u06d2\u06d4";

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE = "${NUM_FACILITIES} \u0633\u06c1\u0648\u0644\u06cc\u0627\u062a ${RADIUS_MILES} \u0645\u06cc\u0644 \u06a9\u06d2 \u0627\u0646\u062f\u0631";

  //i18n: A place that provides a particular service
  messages.FACILITY = "\u0633\u06c1\u0648\u0644\u062a";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Haiti ministry of health (MSPP); no translation necessary.
  messages.PCODE = "PCode";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Pan-American Health Organization; no translation necessary.
  messages.HEALTHC_ID = "HealthC ID";

  //i18n: Message indicating loading hospital information
  messages.LOADING = "\u0644\u0648\u0688 \u06c1\u0648\u0631\u06c1\u0627 \u06c1\u06d2...";

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS = "\u062c\u0646\u0648\u0631\u06cc \u0641\u0631\u0648\u0631\u06cc \u0645\u0627\u0631\u0686 \u0627\u067e\u0631\u06cc\u0644 \u0645\u0626\u06cc \u062c\u0648\u0646 \u062c\u0648\u0644\u0627\u0626\u06cc \u0627\u06af\u0633\u062a \u0633\u062a\u0645\u0628\u0631 \u0627\u06a9\u062a\u0648\u0628\u0631 \u0646\u0648\u0645\u0628\u0631 \u062f\u0633\u0645\u0628\u0631".split(' ');

  //i18n: Label for a new subject
  messages.NEW_SUBJECT = "\u0646\u0626\u06cc \u0633\u06c1\u0648\u0644";

  //i18n: Notification for a facility with missing location information.
  messages.NO_LOCATION_ENTERED = "\u062f\u0627\u062e\u0644 \u06cc\u06c1 \u0633\u06c1\u0648\u0644\u062a \u06a9\u0633\u06cc \u062c\u06af\u06c1 \u0627\u0628\u06be\u06cc \u062a\u06a9 \u0646\u06c1\u06cc\u06ba \u06c1\u06d2";

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS = "\u06a9\u06be\u0644\u0627 / \u06a9\u0644 \u0628\u0633\u062a\u0631";

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION = "\u0635\u0641\u062d\u06c1 ${PHONE}";

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP = "\u0633\u0628 \u0633\u06d2 \u067e\u06c1\u0644\u06d2 \u0628\u0627\u0626\u06cc\u06ba \u0633\u0645\u062a \u06a9\u06cc \u0641\u06c1\u0631\u0633\u062a \u0633\u06d2 \u0627\u06cc\u06a9 \u06c1\u0633\u067e\u062a\u0627\u0644 \u0645\u0646\u062a\u062e\u0628 \u06a9\u0631\u06cc\u06ba\u06d4 \u067e\u06be\u0631 \u067e\u0631\u0646\u0679 \u0622\u067e \u06a9\u06d2 \u0627\u0646\u062a\u062e\u0627\u0628 \u0633\u06d2 \u062f\u0648\u0631\u06cc \u06a9\u06d2 \u0644\u062d\u0627\u0637 \u0633\u06d2 \u06c1\u0633\u067e\u062a\u0627\u0644\u0648\u06ba \u06a9\u06cc \u0641\u06c1\u0631\u0633\u062a \u067e\u0631\u0646\u0679 \u06a9\u0631\u06d2 \u06af\u0627\u06d4";

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP = "${FACILITY_NAME} \u0633\u06d2 \u062f\u0648\u0631\u06cc \u06a9\u06d2 \u0644\u062d\u0627\u0638 \u0633\u06d2 \u06c1\u0633\u067e\u062a\u0627\u0644\u0648\u06ba \u06a9\u06cc \u0641\u06c1\u0631\u0633\u062a \u067e\u0631\u0646\u0679 \u06a9\u0631\u06cc\u06ba";

  //i18n: Message indicating hospital information has been saved
  messages.SAVED = "\u0622\u067e \u06a9\u06cc \u062a\u0631\u0645\u06cc\u0645 \u0645\u062d\u0641\u0648\u0638 \u06c1\u0648\u06af\u0626\u06cc \u06c1\u06d2";

  //i18n: Message indicating saving hospital information
  messages.SAVING = "\u0645\u062d\u0641\u0648\u0638 \u06c1\u0648 \u0631\u06c1\u0627 \u06c1\u06d2...";

  //i18n: work done by someone that benefits another
  messages.SERVICES = "\u062e\u062f\u0645\u0627\u062a";

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW = "\u062f\u06a9\u06be\u0627\u0626\u06cc\u06ba";

  //i18n: Message explaining how to add a latitude and longitude to a facility.
  messages.SIGN_IN_TO_EDIT_LOCATION = "${START_LINK}\u0633\u0627\u0626\u0646 \u0627\u0646${END_LINK} \u0641\u0627\u0631\u0645 \u0645\u06cc\u06ba \u062a\u0631\u0645\u06cc\u0645 \u06a9\u0631\u06cc\u06ba \u0627\u0648\u0631 \u0627\u06cc\u06a9 \u0637\u0648\u0644 \u0628\u0644\u062f \u0627\u0648\u0631 \u0639\u0631\u0636 \u0628\u0644\u062f \u06a9\u06d2 \u0646\u0642\u0627\u0637 \u06a9\u0627 \u0627\u0636\u0627\u0641\u06c1 \u062f\u06cc\u06a9\u06be\u0646\u06d2 \u06a9\u06d2 \u0644\u0626\u06d2.";

  //i18n: Label to subscribe from a subject
  messages.SUBSCRIBE_TO_UPDATES = "\u0627\u06cc \u0645\u06cc\u0644 \u062a\u0627\u0632\u06c1 \u06a9\u0627\u0631\u06cc\u0648\u06ba \u06a9\u06cc \u0631\u06a9\u0646\u06cc\u062a \u062d\u0627\u0635\u0644 \u06a9\u0631\u06cc\u06ba";

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE = "${HOURS}:${MINUTES} ${ZONE}";

  //i18n: Label to unsubscribe to a subject
  messages.UNSUBSCRIBE = "\u0631\u06a9\u0646\u06cc\u062a \u062e\u062a\u0645 \u06a9\u0631\u06cc\u06ba";

  //i18n: Message indicating the user is unsubscribed
  messages.UNSUBSCRIBED = "\u0631\u06a9\u0646\u06cc\u062a \u062e\u062a\u0645 \u06a9\u0631\u06cc\u06ba\u06d4";

  //i18n: Label indicating a record was updated
  messages.UPDATED = "\u062a\u062c\u062f\u06cc\u062f \u0634\u062f\u06c1";

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
