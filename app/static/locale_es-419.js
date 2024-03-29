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
  messages.ADD = "A\u00f1adir";

  //i18n: Label for every item in a list.
  messages.ALL = "Todos";

  //i18n: Label for a cancel link
  messages.CANCEL = "Cancelar";

  //i18n: Message explaining how to place a new subject on the map
  messages.CLICK_TO_ADD_SUBJECT = "Haga clic en una ubicaci\u00f3n en el mapa para colocar el marcador de una nueva instalaci\u00f3n.";

  //i18n: Date at a given time (example: Jan 21, 2010 at 14:32 UTC-4)
  messages.DATE_AT_TIME = "${DATE} a las ${TIME}";

  //i18n: Local date format (example: Jan 21, 2010)
  messages.DATE_FORMAT_MEDIUM = "${MONTH} ${DAY}, ${YEAR}";

  //i18n: Displaying markers on a map for facilities within RADIUS_MILES
  //i18n: miles of a location
  messages.DISPLAYING_FACILITIES_IN_RANGE = "Muestra las instituciones dentro de ${RADIUS_MILES} millas";

  //i18n: Displaying markers on a map for the NUM_FACILITIES closest to a 
  //i18n: location
  messages.DISPLAYING_CLOSEST_N_FACILITIES = "Muestra ${NUM_FACILITIES} las instituciones m\u00e1s cercanas";

  //i18n: A distance (example: 3.11 miles (5 km))
  messages.DISTANCE = "${MILES}millas (${KM} km)";

  //i18n: Meaning: administrative division
  messages.DISTRICT = "Distrito";

  //i18n: Notifies user how to add latitude and longitude values.
  messages.EDIT_LATITUDE_LONGITUDE = "Puede agregar una latitud y longitud en el editar formulario.";

  //i18n: Saved message; e-mail subscription has been saved
  messages.EMAIL_SUBSCRIPTION_SAVED = "Usted recibir\u00e1 actualizaciones ${FREQUENCY} de correo electr\u00f3nico para este servicio. Utilice la ${START_LINK}Configuraci\u00f3n${END_LINK} de p\u00e1gina para cambiar la configuraci\u00f3n de suscripci\u00f3n.";

  //i18n: Eror message, shown when an error occurs.
  messages.ERROR = "Ha ocurrido un error. Vuelve a intentarlo m\u00e1s tarde.";

  //i18n: Error message for required field.
  messages.ERROR_FIELD_IS_REQUIRED = "Este campo es requerido.";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_INVALID = "La latitud debe estar entre -90 y 90";

  //i18n: Error message for invalid latitude.
  messages.ERROR_LATITUDE_MUST_BE_NUMBER = "La latitud debe ser un n\u00famero";

  //i18n: Error message for not loading edit form successfully
  messages.ERROR_LOADING_EDIT_FORM = "Error al cargar editar formulario.";

  //i18n: Error message for not loading facility information successfully
  messages.ERROR_LOADING_FACILITY_INFORMATION = "Error al cargar instituci\u00f3n de informaci\u00f3n.";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_INVALID = "La longitud debe estar entre -180 y 180";

  //i18n: Error message for invalid longitude.
  messages.ERROR_LONGITUDE_MUST_BE_NUMBER = "La longitud debe ser un n\u00famero";

  //i18n: Error message for not saving facility information successfully
  messages.ERROR_SAVING_FACILITY_INFORMATION = "Error al guardar instituci\u00f3n de informaci\u00f3n.";

  //i18n: Error message for a value that is not a number
  messages.ERROR_VALUE_MUST_BE_NUMBER = "El valor debe ser un n\u00famero";

  //i18n: Number of facilities within range of a location.
  //i18n: (example: 5 Facilities within 10 miles)
  messages.FACILITIES_IN_RANGE = "${NUM_FACILITIES} Instituciones dentro de${RADIUS_MILES} millas";

  //i18n: A place that provides a particular service
  messages.FACILITY = "Instituci\u00f3n";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Haiti ministry of health (MSPP); no translation necessary.
  messages.PCODE = "PCode";

  //i18n: Proper name of an ID for a health facility defined by the 
  //i18n: Pan-American Health Organization; no translation necessary.
  messages.HEALTHC_ID = "ID HealthC";

  //i18n: Label for a filter that restricts results to the current map viewport
  messages.IN_MAP_VIEW = "en vista de mapa";

  //i18n: Message indicating loading hospital information
  messages.LOADING = "Cargando...";

  // Month indices run from 0 to 11 (Jan to Dec)
  //i18n: Abbreviated months of the year.
  messages.MONTH_ABBRS = "Ene feb mar abr may jun jul ago sept oct nov dic".split(' ');

  //i18n: Label for a new subject
  messages.NEW_SUBJECT = "Nueva instituci\u00f3n";

  //i18n: Notification for a facility with missing location information.
  messages.NO_LOCATION_ENTERED = "Esta instituci\u00f3n no dispone a\u00fan de un lugar entr\u00f3.";

  //i18n: Error message when there are no facilities to view on the map.
  messages.NO_MATCHING_FACILITIES = "No hay instituci\u00f3nes se pongan en venta. Trate de alejar el zoom o la elecci\u00f3n de un filtro diferente.";

  //i18n: Header showing the number of available beds out of the number of
  //i18n: total beds that are available in a hospital
  messages.OPEN_TOTAL_BEDS = "Camas libres/totales";

  //i18n: Very short abbreviation for a phone number, indended to disambiguate
  //i18n: from a fax number.  (example: p 555-555-5555)
  messages.PHONE_ABBREVIATION = "p ${PHONE}";

  //i18n: Tooltip explaining how to enable print mode
  messages.PRINT_DISABLED_TOOLTIP = "Primero selecciona un hospital de la lista de la izquierda. Luego Imprimir imprimir\u00e1 un listado de los hospitales en orden de distancia desde tu selecci\u00f3n.";

  //i18n: Tooltip explaining a 'Print' link
  messages.PRINT_ENABLED_TOOLTIP = "Imprime una lista de hospitales por orden de distancia desde ${FACILITY_NAME}";

  //i18n: Message indicating hospital information has been saved
  messages.SAVED = "Sus cambios se han guardado";

  //i18n: Message indicating saving hospital information
  messages.SAVING = "Guardando...";

  //i18n: work done by someone that benefits another
  messages.SERVICES = "Servicios";

  //i18n: Label for a control that filters a list of facilities
  messages.SHOW = "Mostrar";

  //i18n: Message explaining how to add a latitude and longitude to a facility.
  messages.SIGN_IN_TO_EDIT_LOCATION = "Accede para ver el editar formulario y agregar una latitud y longitud.";

  //i18n: Label to subscribe from a subject
  messages.SUBSCRIBE_TO_UPDATES = "Suscribirse a las Actualizaciones por Correo Electr\u00f3nico";

  //i18n: Time format (example 14:32 UTC-4)
  messages.TIME_FORMAT_MEDIUM_WITH_ZONE = "${HOURS}:${MINUTES} ${ZONE}";

  //i18n: Label to unsubscribe to a subject
  messages.UNSUBSCRIBE = "Darse de Baja de Comprobarse";

  //i18n: Message indicating the user is unsubscribed
  messages.UNSUBSCRIBED = "Dados de baja.";

  //i18n: Label indicating a record was updated
  messages.UPDATED = "Actualizado";

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
