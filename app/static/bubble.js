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
 * @fileoverview Functions for rendering the InfoWindow for a facility.
 */

rf.bubble = {};

/**
 * Renders an attribute value, in a manner appropriate for the attribute type.
 */
rf.bubble.format_attr = function(attr, value) {
  if (value === null || value === undefined || value === '') {
    return render(value);
  }
  switch (attr.type) {
    case 'contact':
      value = (value || '').replace(/^[\s\|]+|[\s\|]+$/g, '');
      return render((value || '').replace(/\|/g, ', '));
    case 'date':
      return value.replace(/T.*/, '');
    case 'text':
      return render(HTML('<div class="text">${TEXT}</div>', {TEXT: value}));
    case 'bool':
      return value ? locale.YES() : locale.NO();
    case 'choice':
      return translate_value(value);
    case 'multi':
      return translate_values(value).join(', ');
    case 'geopt':
      return '(' + value.lat + ', ' + value.lon + ')';
    case 'str':
    case 'int':
    case 'float':
    default:
      return value + '';
  }
};

/**
 * Renders the HTML content of the InfoWindow for a given facility.
 */
rf.bubble.get_html = function(facility, attribute_is, last_updated) {
  var EDIT_URL = '/edit?facility_name=${FACILITY_NAME}';
  var AVAILABILITY_CELLS = HTML(
    '<td class="availability">' +
    '  <div class="number">${AVAILABILITY}</div></td>' +
    '<td class="capacity">' +
    '  <div class="number">${CAPACITY}</div></td>');
  var AVAILABILITY_UNKNOWN = HTML(
    '<td class="no-information" colspan="2">${MESSAGE}</td>');
  var ATTRIBUTE_ROW = HTML(
    '<tr class="item"><td class="label">${LABEL}</td>' +
    '<td class="value" colspan="2">${VALUE}</td></tr>');
  var HISTORY_ROW = HTML(
    '<tr><td>${LABEL}: ${VALUE}</td><td>${AUTHOR}, ' + 
    '${AFFILIATION}</td><td>${COMMENT}</td><td>${DATE}</td></tr>');

  var edit_url = render(EDIT_URL, {FACILITY_NAME: facility.name});
  var edit_link = locale.EDIT_LINK_HTML({
      LINK_START: render(HTML('<a href="${URL}">'), {URL: edit_url}),
      LINK_END: HTML('</a>')
    });

  var values = facility && facility.values;
  var availability_info;
  if (values && typeof(values[attributes_by_name.total_beds]) === 'number') {
    availability_info = render(AVAILABILITY_CELLS, {
      AVAILABILITY: values[attributes_by_name.available_beds],
      CAPACITY: values[attributes_by_name.total_beds]
    });
  } else if (values && values[attributes_by_name.phone]) {
    availability_info = render(AVAILABILITY_UNKNOWN, {
      MESSAGE: locale.CALL_FOR_AVAILABILITY()
    });
  } else {
    availability_info = render(AVAILABILITY_UNKNOWN, {
      MESSAGE: locale.NO_AVAILABILITY()
    });
  }

  var location = facility.values[attributes_by_name.location];
  var geolocation_info = locale.GEOLOCATION_HTML({
    LATITUDE: location.lat,
    LONGITUDE: location.lon
  });

  var healthc_id = values && values[attributes_by_name.healthc_id] || '\u2013';
  var address_info = render(values && values[attributes_by_name.address]);

  var attributes_to_hide = {};
  attributes_to_hide[attributes_by_name.title] = true;
  attributes_to_hide[attributes_by_name.location] = true;
  attributes_to_hide[attributes_by_name.available_beds] = true;
  attributes_to_hide[attributes_by_name.total_beds] = true;
  attributes_to_hide[attributes_by_name.healthc_id] = true;
  attributes_to_hide[attributes_by_name.address] = true;

  var attributes_info = [];
  for (var i = 0; i < attribute_is.length; i++) {
    var a = attribute_is[i];
    if (attributes_to_hide[a]) {
      continue;
    }
    var attribute = attributes[a];
    var value = null;
    if (facility) {
      value = facility.values[a];
    }
    if (value !== null && value !== '') {
      attributes_info.push(render(ATTRIBUTE_ROW, {
        LABEL: messages.attribute_name[attribute.name],
        VALUE: rf.bubble.format_attr(attribute, value)
      }));
    }
  }

  var history_info = [];
  if (facility) {
    for (var j = 0; j < attribute_is.length; j++) {
      var a = attribute_is[j];
      if (facility.timestamps && facility.timestamps[a]) {
        var attribute = attributes[a];
        history_info.push(render(HISTORY_ROW, {
          DATE: facility.timestamps[a],
          LABEL: messages.attribute_name[attribute.name],
          VALUE: rf.bubble.format_attr(attribute, facility.values[a]),
          AUTHOR: facility.sources[a],
          AFFILIATION: facility.affiliations[a],
          COMMENT: facility.comments[a]
        }));
      } 
    } 
  }

  return render_template('bubble_template', {
    FACILITY_TITLE: facility.values[attributes_by_name.title],
    FACILITY_NAME: facility.name,
    HEALTHC_ID: healthc_id,
    LAST_UPDATED: last_updated,
    EDIT_LINK: edit_link,
    AVAILABILITY_INFO: availability_info,
    FACILITY_SERVICES: rf.get_services(facility),
    ADDRESS_INFO: address_info,
    GEOLOCATION_INFO: geolocation_info,
    ATTRIBUTES_INFO: attributes_info,
    HISTORY_INFO: history_info
  });
}
