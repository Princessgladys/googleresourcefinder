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
  messages.ADD = "Ajouter";

  //i18n: Label for every item in a list.
  messages.ALL = "Tous";

  //i18n: Label for a cancel link
  messages.CANCEL = "Annuler";

  //i18n: Message explaining how to place a new subject on the map
  messages.CLICK_TO_ADD_SUBJECT = "Cliquez sur un emplacement sur la carte pour placer le marqueur d'une nouvelle installation.";

  //i18n: Date at a given time (example: Jan 21, 2010 at 14:32 UTC-4)
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

  //i18n: Notifies user how to add latitude and longitude values.
  messages.EDIT_LATITUDE_LONGITUDE = "Vous pouvez ajouter une latitude et la longitude dans le formulaire de modification.";

  //i18n: Saved message; e-mail subscription has been saved
  messages.EMAIL_SUBSCRIPTION_SAVED = "Vous recevrez par courriel des mises \u00e0 jour ${FREQUENCY} pour cette installation. Utilisez la page des ${START_LINK}Param\u00e8tres${END_LINK} pour modifier les param\u00e8tres d'abonnement.";

  //i18n: Eror message, shown when an error occurs.
  messages.ERROR = "Une erreur s'est produite. Veuillez r\u00e9essayer ult\u00e9rieurement.";

  //i18n: Error message for required field.
  messages.ERROR_FIELD_IS_REQUIRED = "Ce champ est obligatoire.";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_INVALID = "Latitude doit \u00eatre comprise entre -90 et 90";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_MUST_BE_NUMBER = "Latitude doit \u00eatre un nombre";

  //i18n: Error message for not loading edit form successfully
  messages.ERROR_LOADING_EDIT_FORM = "Erreur lors du chargement de modifier le formulaire.";

  //i18n: Error message for not loading facility information successfully
  messages.ERROR_LOADING_FACILITY_INFORMATION = "Erreur lors du chargement des informations de installation.";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_INVALID = "Longitude doit \u00eatre comprise entre -180 et 180";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_MUST_BE_NUMBER = "Longitude doit \u00eatre un nombre";

  //i18n: Error message for not saving facility information successfully
  messages.ERROR_SAVING_FACILITY_INFORMATION = "Erreur lors du enregistrement des informations de installation.";

  //i18n: Error message for a value that is not a number
  messages.ERROR_VALUE_MUST_BE_NUMBER = "La valeur doit \u00eatre un nombre";

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE = "${NUM_FACILITIES}\u00a0\u00e9tablissements dans un rayon de ${RADIUS_MILES}\u00a0miles";

  //i18n: A place that provides a particular service
  messages.FACILITY = "\u00c9tablissement";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Haiti ministry of health (MSPP); no translation necessary.
  messages.PCODE = "PCode";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Pan-American Health Organization; no translation necessary.
  messages.HEALTHC_ID = "ID HealthC";

  //i18n: Label for a filter that restricts results to the current map viewport
  messages.IN_MAP_VIEW = "en vue sur la carte";

  //i18n: Message indicating loading hospital information
  messages.LOADING = "Chargement...";

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS = "janv. f\u00e9vr. mars avr. mai juin juil. ao\u00fbt sept. oct. nov. d\u00e9c.".split(' ');

  //i18n: Label for a new subject
  messages.NEW_SUBJECT = "Une nouvelle installation";

  //i18n: Notification for a facility with missing location information.
  messages.NO_LOCATION_ENTERED = "Cette \u00e9tablissement ne dispose pas encore d'un emplacement est entr\u00e9";

  //i18n: Error message when there are no facilities to view on the map.
  messages.NO_MATCHING_FACILITIES = "Aucune installation correspondant. Essayez un zoom arri\u00e8re ou en choisissant un filtre diff\u00e9rent.";

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS = "Lits libres/total";

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION = "t ${PHONE}";

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP = "S\u00e9lectionnez d'abord un h\u00f4pital dans la liste de gauche, puis cliquez sur \"Imprimer\" pour imprimer une liste d'h\u00f4pitaux tri\u00e9s en fonction de la distance qui les s\u00e9pare de votre s\u00e9lection.";

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP = "Imprimer une liste d'h\u00f4pitaux tri\u00e9s selon la distance qui les s\u00e9pare de ${FACILITY_NAME}";

  //i18n: Message indicating hospital information has been saved
  messages.SAVED = "Vos modifications ont \u00e9t\u00e9 enregistr\u00e9es";

  //i18n: Message indicating saving hospital information
  messages.SAVING = "Enregistrement...";

  //i18n: work done by someone that benefits another
  messages.SERVICES = "Services";

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW = "Montrer";

  //i18n: Message explaining how to add a latitude and longitude to a facility.
  messages.SIGN_IN_TO_EDIT_LOCATION = "${START_LINK}Connectez-vous${END_LINK} pour afficher le formulaire de modification et d'ajouter une latitude et la longitude";

  //i18n: Label to subscribe from a subject
  messages.SUBSCRIBE_TO_UPDATES = "Abonnez-vous aux mises \u00e0 jour par courriel";

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE = "${HOURS}:${MINUTES} ${ZONE}";

  //i18n: Label to unsubscribe to a subject
  messages.UNSUBSCRIBE = "Vous D\u00e9sabonner de V\u00e9rifier";

  //i18n: Message indicating the user is unsubscribed
  messages.UNSUBSCRIBED = "D\u00e9sabonn\u00e9.";

  //i18n: Label indicating a record was updated
  messages.UPDATED = "Mise \u00e0 jour\u00a0:";

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
