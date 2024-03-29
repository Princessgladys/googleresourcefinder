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
  messages.ADD =
      'Add';

  //i18n: Label for every item in a list.
  messages.ALL =
      'All';

  //i18n: Label for a cancel link
  messages.CANCEL =
      'Cancel';

  //i18n: Message explaining how to place a new subject on the map
  messages.CLICK_TO_ADD_SUBJECT =
      'Click a location on the map to place the marker for a new facility.';

  //i18n: Date at a given time (example: Jan 21, 2010 at 14:32 UTC-4)
  messages.DATE_AT_TIME =
      '${DATE} at ${TIME}';

  //i18n: Local date format (example: Jan 21, 2010)
  messages.DATE_FORMAT_MEDIUM =
      '${MONTH} ${DAY}, ${YEAR}';

  //i18n: Displaying markers on a map for facilities within RADIUS_MILES
  //i18n: miles of a location
  messages.DISPLAYING_FACILITIES_IN_RANGE =
      'Displaying facilities within ${RADIUS_MILES} miles';

  //i18n: Displaying markers on a map for the NUM_FACILITIES closest to a 
  //i18n: location
  messages.DISPLAYING_CLOSEST_N_FACILITIES =
      'Displaying ${NUM_FACILITIES} closest facilities';

  //i18n: A distance (example: 3.11 miles (5 km))
  messages.DISTANCE =
      '${MILES} miles (${KM} km)';

  //i18n: Meaning: administrative division
  messages.DISTRICT =
      'District';

  //i18n: Notifies user how to add latitude and longitude values.
  messages.EDIT_LATITUDE_LONGITUDE =
      'You can add a latitude and longitude in the edit form.';

  //i18n: Saved message; e-mail subscription has been saved
  messages.EMAIL_SUBSCRIPTION_SAVED =
      'You will receive ${FREQUENCY} email updates for this facility. Use the ${START_LINK}Settings${END_LINK} page to change subscription settings.';

  //i18n: Eror message, shown when an error occurs.
  messages.ERROR =
      'An error has occurred. Please try again later.';

  //i18n: Error message for required field.
  messages.ERROR_FIELD_IS_REQUIRED =
      'Field is required.';

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_INVALID =
      'Latitude must be between -90 and 90.';

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_MUST_BE_NUMBER =
      'Latitude must be a number.';

  //i18n: Error message for not loading edit form successfully
  messages.ERROR_LOADING_EDIT_FORM =
      'Error loading edit form.';

  //i18n: Error message for not loading facility information successfully
  messages.ERROR_LOADING_FACILITY_INFORMATION =
      'Error loading facility information.';

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_INVALID =
      'Longitude must be between -180 and 180.';

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_MUST_BE_NUMBER =
      'Longitude must be a number.';

  //i18n: Error message for not saving facility information successfully
  messages.ERROR_SAVING_FACILITY_INFORMATION =
      'Error saving facility information.';

  //i18n: Error message for a value that is not a number
  messages.ERROR_VALUE_MUST_BE_NUMBER =
      'Value must be a number.';

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE =
      '${NUM_FACILITIES} Facilities within ${RADIUS_MILES} miles';

  //i18n: A place that provides a particular service
  messages.FACILITY =
      'Facility';

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Haiti ministry of health (MSPP); no translation necessary.
  messages.PCODE =
      'PCode';

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Pan-American Health Organization; no translation necessary.
  messages.HEALTHC_ID =
      'HealthC ID';

  //i18n: Label for a filter that restricts results to the current map viewport
  messages.IN_MAP_VIEW =
      'in map view';

  //i18n: Message indicating loading hospital information
  messages.LOADING =
    'Loading...';

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS =
      'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');

  //i18n: Label for a new subject
  messages.NEW_SUBJECT =
      'New facility';

  //i18n: Notification for a facility with missing location information.
  messages.NO_LOCATION_ENTERED =
      'This facility does not yet have a location entered.';

  //i18n: Error message when there are no facilities to view on the map.
  messages.NO_MATCHING_FACILITIES =
      'No matching facilities. Try zooming out or choosing a different filter.';

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS =
     'Open/Total Beds';

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION =
      'p ${PHONE}';

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP =
      'First select a hospital from the list on the left. Then Print will ' +
      'print a list of hospitals in order of distance from your selection.';

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP =
      'Print a list of hospitals in order of distance from ${FACILITY_NAME}';

  //i18n: Message indicating hospital information has been saved
  messages.SAVED =
    'Your edit has been saved';

  //i18n: Message indicating saving hospital information
  messages.SAVING =
    'Saving...';

  //i18n: work done by someone that benefits another
  messages.SERVICES =
      'Services';

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW =
      'Show';

  //i18n: Message explaining how to add a latitude and longitude to a facility.
  messages.SIGN_IN_TO_EDIT_LOCATION =
      '${START_LINK}Sign in${END_LINK} to view the edit form and add a latitude and longitude.';

  //i18n: Label to subscribe from a subject
  messages.SUBSCRIBE_TO_UPDATES =
      'Subscribe to email updates';

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE =
      '${HOURS}:${MINUTES} ${ZONE}';

  //i18n: Label to unsubscribe to a subject
  messages.UNSUBSCRIBE =
      'Unsubscribe';

  //i18n: Message indicating the user is unsubscribed
  messages.UNSUBSCRIBED =
      'Unsubscribed.';

  //i18n: Label indicating a record was updated
  messages.UPDATED =
      'Updated';

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
