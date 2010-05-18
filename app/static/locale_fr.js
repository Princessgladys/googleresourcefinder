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
  messages.ALL = "Tous";

  //i18n: Indicates a user should call for availability of beds
  //i18n: and services at a hospital.
  messages.CALL_FOR_AVAILABILITY = "Merci d'appeler pour conna\u00eetre les disponibilit\u00e9s.";

  //i18n: Date at a give time (example: Jan 21, 2010 at 14:32 UTC-4)
  messages.DATE_AT_TIME = "${DATE} \u00e0 ${TIME}";

  //i18n: Local date format (example: Jan 21, 2010)
  messages.DATE_FORMAT_MEDIUM = "${DAY} ${MONTH} ${YEAR}";

  //i18n: Displaying markers on a map for facilities within RADIUS_MILES
  //i18n: miles of a location
  messages.DISPLAYING_FACILITIES_IN_RANGE = "Tous les \u00e9tablissements dans un rayon de ${RADIUS_MILES}\u00a0miles";

  //i18n: Displaying markers on a map for the NUM_FACILITIES closest to a 
  //i18n: location
  messages.DISPLAYING_CLOSEST_N_FACILITIES = "Les ${NUM_FACILITIES}\u00a0\u00e9tablissements les plus proches";

  //i18n: A distance (example: 3.11 miles (5 km))
  messages.DISTANCE = "${MILES}\u00a0miles (${KM}\u00a0km)";

  //i18n: Meaning: administrative division
  messages.DISTRICT = "District";

  //i18n: Link to edit the data for a facility record.
  messages.EDIT_LINK_HTML = HTML("${LINK_START}Modifier cet enregistrement${LINK_END}");

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE = "${NUM_FACILITIES}\u00a0\u00e9tablissements dans un rayon de ${RADIUS_MILES}\u00a0miles";

  //i18n: A place that provides a particular service
  messages.FACILITY = "\u00c9tablissement";

  //i18n: Latitude and longitude location on earth.
  messages.GEOLOCATION_HTML = HTML("Latitude\u00a0: ${LATITUDE}<br>Longitude\u00a0: ${LONGITUDE}");

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS = "janv. f\u00e9vr. mars avr. mai juin juil. ao\u00fbt sept. oct. nov. d\u00e9c.".split(' ');

  //i18n: Form option for disagreement.
  messages.NO = "Non";

  //i18n: Indicates there is no availability information for this hospital.
  messages.NO_AVAILABILITY = "Aucune information concernant les disponibilit\u00e9s";

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS = "Lits libres/au total";

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION = "t ${PHONE}";

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP = "S\u00e9lectionnez d'abord un h\u00f4pital dans la liste de gauche, puis cliquez sur \"Imprimer\" pour imprimer une liste d'h\u00f4pitaux tri\u00e9s en fonction de la distance qui les s\u00e9pare de votre s\u00e9lection.";

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP = "Imprimer une liste d'h\u00f4pitaux tri\u00e9s selon la distance qui les s\u00e9pare de ${FACILITY_NAME}";

  //i18n: Link to request access for editing a facility record.
  messages.REQUEST_EDIT_ACCESS_HTML = HTML("${LINK_START}Demander l'acc\u00e8s pour modification${LINK_END}");

  //i18n: work done by someone that benefits another
  messages.SERVICES = "Services";

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW = "Afficher\u00a0:";

  //i18n: Indicates a user needs to sign in to edit data on a facility.
  messages.SIGN_IN_TO_EDIT = "Connectez-vous pour apporter des modifications.";

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE = "${HOURS}:${MINUTES} ${ZONE}";

  //i18n: Label indicating a record was updated
  messages.UPDATED = "Mise \u00e0 jour\u00a0:";

  //i18n: Form option for agreement.
  messages.YES = "Oui";

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
