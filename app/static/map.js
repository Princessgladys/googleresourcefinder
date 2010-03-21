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
// ==== Constants

var STATUS_GOOD = 1;
var STATUS_BAD = 2;
var STATUS_UNKNOWN = 3;
var MAX_STATUS = 3;

var STATUS_ICON_COLORS = [null, '080', 'a00', '444'];
var STATUS_TEXT_COLORS = [null, '040', 'a00', '444'];
var STATUS_ZINDEXES = [null, 3, 2, 1];
var STATUS_LABELS = [
  null,
  'One or more ${all_supplies}',
  'No ${any_supply}',
  'Data missing for ${any_supply}'
];

var MONTH_ABBRS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');

var INFO_TEMPLATE =
    '<div class="facility-info">' +
    '  <h1>${facility_title}</h1>' +
    '  <div class="caption">' +
    '    ${user_action_html}' +
    '  </div>' +
    '  <div class="attributes">${attributes}</div>' +
    '</div>';

var ATTRIBUTE_TEMPLATE =
    '<div class="attribute">' +
    '  <span class="title">${attribute_title}</span>: ' +
    '  <span class="value">${attribute_value}</span>' +
    '</div>';

// ==== Data loaded from the data store

var attributes = [null];
var attributes_by_name = {};  // {attribute_name: attribute_i}
var facility_types = [null];
var facilities = [null];
var divisions = [null];
var messages = {};  // {namespace: {name: {language: message}}

// ==== Columns shown in the facility table

rmapper.get_services_from_values = function(values) {

  services = translate_values(
      [].concat(values[attributes_by_name.specialty_care] || [])
      .concat(values[attributes_by_name.medical_equipment] || []))
  .join(', ');
  return services;
}

rmapper.get_services = function(facility) {

  var services = '';
  if (facility.last_report) {
    var values = facility.last_report.values;
    services = rmapper.get_services_from_values(values);
  }
  return services;
}

  
var summary_columns = [
  null, {
    get_title: function() {
      var beds_div = $$('div', {'class': 'beds'}, 'Open/Total Beds');
      return $$('div', {}, [beds_div, 'Services']);
    },
    get_value: function(values) {
      var services = rmapper.get_services_from_values(values);
      var capacity = values[attributes_by_name.patient_capacity];
      var patients = values[attributes_by_name.patient_count];
      var open_beds = '\u2013';
      if (capacity === null) {
        capacity = '\u2013';
      } else if (patients !== null) {
        open_beds = capacity - patients;
      }
      var beds = open_beds + ' / ' + capacity;
      var beds_div = $$('div', {'class': 'beds'}, beds);
      // WebKit rendering bug: vertical alignment is off if services is ''.
      return $$('div', {}, [beds_div, services || '\u00a0']);
    }
  }
];

// ==== Filtering controls

var supply_sets = [
  null, {
    description_all: 'doctors',
    description_any: 'doctors',
    abbreviation: 'Doctors',
    supplies: [5]
  }, {
    description_all: 'patients',
    description_any: 'patients',
    abbreviation: 'Patients',
    supplies: [6]
  }, {
    description_all: 'beds',
    description_any: 'beds',
    abbreviation: 'Beds',
    supplies: [7]
  }, {
    description_all: 'capacity',
    description_any: 'capacity',
    abbreviation: 'Capacity',
    supplies: [8]
  }
];

var DEFAULT_SUPPLY_SET_I = 1;

// ==== Selection state

var selected_supply_set_i = -1;
var selected_supply_set = null;
var selected_filter_attribute_i = 0;
var selected_filter_value = null;
var selected_status_i = -1;
var selected_division_i = -1;
var selected_division = null;
var selected_facility_i = -1;
var selected_facility = null;

var facility_status_is = [];  // status of each facility for selected supplies
var bounds_match_selected_division = false;  // to skip redundant redraws

// ==== Live API objects

var map = null;
var info = null;
var markers = [];  // marker for each facility

// ==== Debugging

// Print a message to the Safari or Firebug console.
function log() {
  if (typeof console !== 'undefined' && console.log) {
    console.log.apply(console, arguments);
  }
}

// ==== DOM utilities
var $j = jQuery;

// Get an element by its id.
function $(id) {
  return document.getElementById(id);
}

// Special-case attribute handling.  For each ('k', 'v') pair, attribute k is
// set by assigning to element.v rather than element.setAttribute('k', ...).
var SPECIAL_ATTRIBUTES = {
  'class': 'className',
  colspan: 'colSpan',
  onchange: 'onchange',
  onclick: 'onclick',
  onmouseout: 'onmouseout',
  onmouseover: 'onmouseover'
};

// Create an element with the given tag name and attributes.
function $$(tag_name, attrs, content) {
  var element = document.createElement(tag_name);
  for (var key in attrs) {
    if (typeof attrs[key] !== 'function') {
      element.setAttribute(key, attrs[key]);
    }
    if (key in SPECIAL_ATTRIBUTES) {
      element[SPECIAL_ATTRIBUTES[key]] = attrs[key];
    }
  }
  if (content !== undefined) {
    set_children(element, content);
  }
  return element;
}

// Replace all the children of an element with the given array of children.
function set_children(element, children) {
  if (!is_array(children)) {
    children = [children];
  }
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
  for (var i = 0; i < children.length; i++) {
    var child = children[i];
    if (!child.tagName) {
      child = document.createTextNode('' + child);
    }
    element.appendChild(child);
  }
}

// Get the size of the document area of the browser window.
function get_window_size() {
  var width = window.innerWidth;
  var height = window.innerHeight;
  if (typeof(width) === 'undefined') {
    width = document.body.offsetWidth; // for IE
    height = document.body.offsetHeight; // for IE
  }
  return [width, height];
}

// Get the top coordinate of a given element relative to the whole document.
function get_element_top(element) {
  var top = 0;
  for (var node = element; node; node = node.offsetParent) {
    top += node.offsetTop;
  }
  return top;
}

// ==== Array utilities

function filter(array, predicate) {
  var results = [];
  for (var i = 0; i < array.length; i++) {
    if (predicate(array[i])) {
      results.push(array[i]);
    }
  }
  return results;
}

function any(array, predicate) {
  return filter(array, predicate).length > 0;
}

function contains(array, element) {
  return any(array, function(e) { return e === element; });
}

function last(array, count) {
  return array[array.length - (count || 1)];
}

function is_array(thing) {
  return (typeof thing === 'object') && (thing.constructor === Array);
}

// ==== String utilities

function translate_value(value) {
  var message = messages.attribute_value[value];
  return message && message.en || value;
}

function translate_values(values) {
  var results = [];
  for (var i = 0; i < values.length; i++) {
    results.push(translate_value(values[i]));
  }
  return results;
}

function html_escape(text) {
  return ('' + text).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function maybe_selected(selected) {
  return selected ? ' selected' : '';
}

function render_template(template, params) {
  var result = template;
  for (var name in params) {
    var placeholder = new RegExp('\\$\\{' + name + '\\}', 'g');
    var substitution;
    if (name === '$') {
      substitution = '$';
    } else if (params[name] === undefined || params[name] === null) {
      substitution = '\u2013';
    } else if (typeof params[name] === 'object') {
      substitution = params[name].html;
    } else {
      substitution = html_escape(params[name]);
    }
    result = result.replace(placeholder, substitution);
  }
  return result;
}

function make_icon(title, status, detail) {
  var text = detail ? title : '';
  var text_size = detail ? 10 : 0;
  var text_fill = STATUS_TEXT_COLORS[status];
  var icon = 'greek_cross_4w10';
  var icon_size = '12';
  var icon_fill = STATUS_ICON_COLORS[status];
  var icon_outline = 'fff';
  var params = [
      text, text_size, text_fill,
      icon, icon_size, icon_fill, icon_outline
  ].join('|');
  return 'http://chart.apis.google.com/chart?chst=d_simple_text_icon_above&' +
      'chld=' + encodeURIComponent(params);
}

// ==== Maps API

// Construct and set up the Map and InfoWindow objecs.
function initialize_map() {
  if (map) return;

  map = new google.maps.Map($('map'), {
    zoom: 1,
    center: new google.maps.LatLng(0, 0),
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    mapTypeControl: true,
    scaleControl: true,
    navigationControl: true,
    navigationControlOptions: {style: google.maps.NavigationControlStyle.SMALL}
  });
  google.maps.event.addListener(map, 'tilesloaded', set_map_opacity);

  info = new google.maps.InfoWindow();
}

// Reduce the opacity of the map layer to make markers stand out.
function set_map_opacity() {
  var panes = $('map').firstChild.firstChild;
  for (var pane = panes.firstChild; pane; pane = pane.nextSibling) {
    if (!pane.id.match(/^pane/)) {
      pane.style.opacity = 0.7;
      break;
    }
  }
}

// Construct and set up the map markers for the facilities.
function initialize_markers() {
  for (var f = 1; f < facilities.length; f++) {
    var facility = facilities[f];
    var location = facility.location;
    markers[f] = new google.maps.Marker({
      position: new google.maps.LatLng(location.lat, location.lon),
      map: map,
      icon: make_icon(facility.title, STATUS_UNKNOWN, false),
      title: facility.title
    });
    google.maps.event.addListener(markers[f], 'click', facility_selector(f));
  }
}

// ==== Display construction routines

// Set up the supply selector (currently unused).
function initialize_supply_selector() {
  var tbody = $('supply-tbody');
  var tr = $$('tr');
  var cells = [];
  for (var s = 1; s < supply_sets.length; s++) {
    cells.push($$('td', {
      id: 'supply-set-' + s,
      'class': 'supply-set',
      onclick: supply_set_selector(s),
      onmouseover: hover_activator('supply-set-' + s),
      onmouseout: hover_deactivator('supply-set-' + s)
    }, supply_sets[s].abbreviation));
  }
  set_children(tbody, tr);
  set_children(tr, cells);
}

// Create option elements for all the allowed values for an attribute.
function add_filter_options(options, attribute_i) {
  var values = attributes[attribute_i].values;
  for (var v = 0 ; v < values.length; v++) {
    options.push($$('option', {value: attribute_i + ' ' + values[v]},
                    translate_value(values[v])));
  }
}

// Set up the filter widgets.
function initialize_filters() {
  var tbody = $('filter-tbody');
  var tr = $$('tr');
  var selector = $$('select', {
    id: 'specialty-selector',
    name: 'specialty',
    onchange: function() {
      select_filter.apply(null, $('specialty-selector').value.split(' '));
    }
  });
  var options = [];
  options.push($$('option', {value: '0 '}, 'All'));
  add_filter_options(options, attributes_by_name.specialty_care);
  add_filter_options(options, attributes_by_name.medical_equipment);
  set_children(selector, options);
  set_children(tr, [$$('td', {}, ['Show: ', selector])]);
  set_children(tbody, tr);
}

// Add the header to the division list.
function initialize_division_header() {
  var thead = $('division-thead');
  var tr = $$('tr');
  var cells = [$$('th', {}, 'Arrondissements')];
  for (var s = 1; s <= MAX_STATUS; s++) {
    cells.push($$('th', {'class': 'facility-count'},
        $$('img', {src: make_icon('', s, false)})));
  }
  cells.push($$('th', {'class': 'facility-count'}, 'All'));
  set_children(thead, tr);
  set_children(tr, cells);
}

// Add the header to the facility list.
function initialize_facility_header() {
  var thead = $('facility-thead');
  var tr = $$('tr');
  var cells = [$$('th', {}, 'Facility')];
  for (var c = 1; c < summary_columns.length; c++) {
    cells.push($$('th', {'class': 'value column_' + c},
                  summary_columns[c].get_title()));
  }
  set_children(thead, tr);
  set_children(tr, cells);
}

// ==== Display update routines

// Set the map bounds to fit all facilities in the given division.
function update_map_bounds(division_i) {
  if (bounds_match_selected_division && division_i === selected_division_i) {
    // The map hasn't been moved since it was last fit to this division.
    return;
  }

  var facility_is = divisions[division_i].facility_is;
  var bounds = new google.maps.LatLngBounds();
  for (var i = 0; i < facility_is.length; i++) {
    var location = facilities[facility_is[i]].location;
    if (location) {
      bounds.extend(new google.maps.LatLng(location.lat, location.lon));
    }
  }
  map.fitBounds(bounds);
  bounds_match_selected_division = true;
}

// Update the facility map icons based on their status and the zoom level.
function update_facility_icons() {
  var detail = map.getZoom() > 10;
  for (var f = 1; f < facilities.length; f++) {
    if (markers[f]) {
      var facility = facilities[f];
      var s = facility_status_is[f];
      markers[f].setIcon(make_icon(facility.title, s, detail));
      markers[f].setZIndex(STATUS_ZINDEXES[s]);
    }
  }
}

// Fill in the facility legend.
function update_facility_legend() {
  var rows = [];
  var stock = 'one dose';
  for (var s = 1; s <= MAX_STATUS; s++) {
    rows.push($$('tr', {'class': 'legend-row'}, [
      $$('th', {'class': 'legend-icon'},
        $$('img', {src: make_icon('', s, false)})),
      $$('td', {'class': 'legend-label status-' + s},
        render_template(STATUS_LABELS[s], {
          all_supplies: selected_supply_set.description_all,
          any_supply: selected_supply_set.description_any
        }))
    ]));
  }
  set_children($('legend-tbody'), rows);
}

// Repopulate the facility list based on the selected division and status.
function update_facility_list() {
  var rows = [];
  for (var i = 0; i < selected_division.facility_is.length; i++) {
    var f = selected_division.facility_is[i];
    var facility = facilities[f];
    var facility_type = facility_types[facility.type];
    if (selected_status_i === 0 ||
        facility_status_is[f] === selected_status_i) {
      var row = $$('tr', {
        id: 'facility-' + f,
        'class': 'facility' + maybe_selected(f === selected_facility_i),
        onclick: facility_selector(f),
        onmouseover: hover_activator('facility-' + f),
        onmouseout: hover_deactivator('facility-' + f)
      });
      var cells = [$$('td', {'class': 'facility-title'}, facility.title)];
      if (facility.last_report) {
        for (var c = 1; c < summary_columns.length; c++) {
          var value = summary_columns[c].get_value(facility.last_report.values);
          cells.push($$('td', {'class': 'value column_' + c}, value));
        }
      } else {
        for (var c = 1; c < summary_columns.length; c++) {
          cells.push($$('td'));
        }
      }
      set_children(row, cells);
      rows.push(row);
    }
  }
  set_children($('facility-tbody'), rows);
  if (!print) {
    update_facility_list_size();
  }
}

// Update the height of the facility list to exactly fit the window.
function update_facility_list_size() {
  var windowHeight = get_window_size()[1];
  var freshnessHeight = $('freshness').clientHeight;
  var listTop = get_element_top($('facility-list'));
  var listHeight = windowHeight - freshnessHeight - listTop;
  $('facility-list').style.height = listHeight + 'px';
  align_header_with_table($('facility-thead'), $('facility-tbody'));
}

// Update the width of header cells to match the table cells below.
function align_header_with_table(thead, tbody) {
  if (tbody.firstChild) {
    thead.parentNode.style.width = tbody.parentNode.clientWidth + 'px';
    var head_cell = thead.firstChild.firstChild;
    var body_cell = tbody.firstChild.firstChild;
    while (body_cell) {
      // Subtract 8 pixels to account for td padding: 2px 4px.
      head_cell.style.width = (body_cell.clientWidth - 8) + 'px';
      head_cell = head_cell.nextSibling;
      body_cell = body_cell.nextSibling;
    }
  }
}

// Determine the status of each facility according to the user's filters.
function update_facility_status_is() {
  for (var f = 1; f < facilities.length; f++) {
    var report = facilities[f].last_report;
    if (selected_filter_attribute_i <= 0) {
      facility_status_is[f] = STATUS_GOOD;
    } else if (!report) {
      facility_status_is[f] = STATUS_UNKNOWN;
    } else {
      facility_status_is[f] = STATUS_BAD;
      var a = selected_filter_attribute_i;
      if (attributes[a].type === 'multi') {
        if (contains(report.values[a] || [], selected_filter_value)) {
          facility_status_is[f] = STATUS_GOOD;
        }
      } else if (report.values[a] === selected_filter_value) {
        facility_status_is[f] = STATUS_GOOD;
      }
    }
  }
}

// Update the contents of the division list based on facility statuses. 
function update_division_list() {
  var rows = [];
  for (var d = 0; d < divisions.length; d++) {
    var division = divisions[d];
    var row = $$('tr', {
      id: 'division-' + d,
      'class': 'division'
    });
    var cells = [$$('td', {
      'class': 'division-title',
      onclick: division_and_status_selector(d, 0),
      onmouseover: hover_activator('division-' + d),
      onmouseout: hover_deactivator('division-' + d)
    }, division.title)];
    for (var s = 1; s <= MAX_STATUS; s++) {
      var facility_is = filter(division.facility_is,
        function (f) { return facility_status_is[f] === s; });
      cells.push($$('td', {
        'id': 'division-' + d + '-status-' + s,
        'class': 'facility-count status-' + s + maybe_selected(
            d === selected_division_i && s === selected_status_i),
        onclick: division_and_status_selector(d, s),
        onmouseover: hover_activator('division-' + d + '-status-' + s),
        onmouseout: hover_deactivator('division-' + d + '-status-' + s)
      }, facility_is.length));
    }
    cells.push($$('td', {
      'id': 'division-' + d + '-status-0',
      'class': 'facility-count status-0' + maybe_selected(
          d === selected_division_i && 0 === selected_status_i),
      onclick: division_and_status_selector(d, 0),
      onmouseover: hover_activator('division-' + d + '-status-0'),
      onmouseout: hover_deactivator('division-' + d + '-status-0')
    }, division.facility_is.length));
    set_children(row, cells);
    rows.push(row);
  }

  set_children($('division-tbody'), rows);
}

// Update the data freshness indicator.
function update_freshness(timestamp) {
  if (!timestamp) {
    $('freshness').innerHTML = 'No reports received';
    return;
  }

  var t = new Date();
  t.setTime(timestamp * 1000);

  var timeout = 1000;
  var seconds = (new Date()).getTime() / 1000 - timestamp;
  var minutes = seconds/60;
  var hours = seconds/3600;
  var age;
  if (hours >= 1.05) {
    age = (Math.ceil(hours * 10) / 10) + ' hours ago';
    timeout = 60000;
  } else if (minutes >= 1.5) {
    age = Math.ceil(minutes) + ' minutes ago';
    timeout = 10000;
  } else if (seconds >= 1.5) {
    age = Math.ceil(seconds) + ' seconds ago';
  } else if (seconds > 0) {
    age = '1 second ago';
  } else {
    age = Math.round(seconds) + ' seconds in the future';
  }

  $('freshness').innerHTML = 'Last updated ' + age +
      ' (' + format_timestamp(t) + ')';
  window.setTimeout(function () { update_freshness(timestamp); }, timeout);
}

// Format a JavaScript Date object as a human-readable string.
function format_timestamp(t) {
  var months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');
  var date = months[t.getMonth()] + ' ' + t.getDate() + ', ' + t.getFullYear();
  var hours = (t.getHours() < 10 ? '0' : '') + t.getHours();
  var minutes = (t.getMinutes() < 10 ? '0' : '') + t.getMinutes();
  var time = hours + ':' + minutes;
  var offset = - (t.getTimezoneOffset() / 60);
  var zone = 'UTC' + (offset > 0 ? '+' : '\u2212') + Math.abs(offset);
  return date + ' at ' + time + ' ' + zone;
}

// ==== UI event handlers

function initialize_handlers() {
  var window_size = [null, null];

  window.onresize = function () {
    var new_size = get_window_size();
    if (new_size[0] !== window_size[0] || new_size[1] !== window_size[1]) {
      handle_window_resize();
      window_size = new_size;
    }
  };

  google.maps.event.addListener(map, 'zoom_changed', handle_zoom_changed);
  google.maps.event.addListener(map, 'bounds_changed', handle_bounds_changed);
}

function handle_window_resize() {
  if (!print) {
    align_header_with_table($('division-thead'), $('division-tbody'));
    update_facility_list_size();
  }
}

function handle_zoom_changed() {
  update_facility_icons(); // amount of detail in icons depends on zoom level
}

function handle_bounds_changed() {
  bounds_match_selected_division = false;
}

function hover_activator(id) {
  return function () {
    var element = $(id);
    element.className = element.className + ' hover';
  };
}

function hover_deactivator(id) {
  return function () {
    var element = $(id);
    element.className = element.className.replace(/ hover/g, '');
  };
}

function supply_set_selector(supply_set_i) {
  return function () {
    select_supply_set(supply_set_i);
  };
}

function division_and_status_selector(division_i, status_i) {
  return function () {
    select_division_and_status(division_i, status_i);
  };
}

function facility_selector(facility_i) {
  return function () {
    select_facility(facility_i);
  };
}

// ==== Selection behaviour

function select_filter(attribute_i, value) {
  selected_filter_attribute_i = attribute_i;
  selected_filter_value = value;

  // Apply the filter to the facility list.
  update_facility_status_is();

  // Update the facility icons to reflect their status.
  update_facility_icons();

  // Update the facility counts in the division list.
  update_division_list();

  if (selected_division !== null) {
    // Filter the list of facilities by the selected supply set.
    update_facility_list();
  }
}

function select_supply_set(supply_set_i) {
  if (supply_set_i === selected_supply_set_i) {
    return;
  }

  // Update the selection.
  selected_supply_set_i = supply_set_i;
  selected_supply_set = supply_sets[supply_set_i];

  // Update the selection highlight.
  for (var s = 1; s < supply_sets.length; s++) {
    $('supply-set-' + s).className = 'supply-set' +
        maybe_selected(s === supply_set_i);
  }

  // Update the facility icon legend.
  update_facility_legend();

  // Update the status of each facility.
  update_facility_status_is();

  // Update the facility icons to reflect their status.
  update_facility_icons();

  // Update the facility counts in the division list.
  update_division_list();

  if (selected_division !== null) {
    // Filter the list of facilities by the selected supply set.
    update_facility_list();
  }
}

function select_division_and_status(division_i, status_i) {
  update_map_bounds(division_i);

  if (division_i === selected_division_i && status_i === selected_status_i) {
    return;
  }

  // Update the selection.
  selected_division_i = division_i;
  selected_division = divisions[division_i];
  selected_status_i = status_i;
  
  // Update the selection highlight.
  for (var d = 0; d < divisions.length; d++) {
    for (var s = 0; s <= MAX_STATUS; s++) {
      $('division-' + d + '-status-' + s).className =
          'facility-count status-' + s +
          maybe_selected(d === division_i && s === status_i);
    }
  }

  // Filter the list of facilities by the selected division and status.
  update_facility_list();
}

function select_facility(facility_i, ignore_current) {
  if (!ignore_current && facility_i === selected_facility_i) {
    return;
  }
  
  // Update the selection.
  selected_facility_i = facility_i;
  selected_facility = (facility_i <= 0) ? null : facilities[facility_i];

  // Update the selection highlight.
  for (var f = 1; f < facilities.length; f++) {
    var item = $('facility-' + f);
    if (item) {
      item.className = 'facility' + maybe_selected(f === facility_i);
    }
  }

  if (facility_i <= 0) {
    // No selection.
    info.close();
    return;
  }

  // Pop up the InfoWindow on the selected clinic.
  var last_report_date = 'No reports received';
  var last_report = selected_facility.last_report;
  if (last_report) {
    var ymd = last_report.date.split('-');
    last_report_date = 'Updated ' +
        MONTH_ABBRS[ymd[1] - 1] + ' ' + (ymd[2] - 0) + ', ' + ymd[0];
  }
  info.close();

  division_title = divisions[selected_facility.division_i].title;
  attribute_is = facility_types[selected_facility.type].attribute_is;

  bubble_info = rmapper.bubble.get_html(selected_facility, attribute_is,
                                        last_report_date);
  info.setContent(bubble_info.html)
  info.open(map, markers[selected_facility_i]);

  // this call sets up the tabs and need to be called after the dom was created
  jQuery(bubble_info.tabs_id).tabs();

}

// ==== Load data

function load_data(data) {
  attributes = data.attributes;
  facility_types = data.facility_types;
  facilities = data.facilities;
  divisions = data.divisions;
  messages = data.messages;

  attributes_by_name = {}
  for (var a = 1; a < attributes.length; a++) {
    attributes_by_name[attributes[a].name] = a;
    switch (attributes[a].name){
      case 'specialty_care': specialty_attribute_i = a; break;
      case 'medical_equipment': equipment_attribute_i = a; break;
      case 'patient_capacity': patient_capacity_attribute_i = a; break;
      case 'patient_count': patient_count_attribute_i = a; break;
    }
  }

  var facility_is = [];
  for (var i = 1; i < facilities.length; i++) {
    facility_is.push(i);
  }
  divisions[0] = {
    title: 'All arrondissements',
    facility_is: facility_is
  };

  initialize_supply_selector();
  initialize_filters();
  initialize_division_header();
  initialize_facility_header();

  initialize_map();
  initialize_markers();
  initialize_handlers();
  update_freshness(data.timestamp);

  select_supply_set(DEFAULT_SUPPLY_SET_I);
  select_division_and_status(0, STATUS_GOOD);
  handle_window_resize();

  log('Data loaded.');

  if (print) {
    set_children($('print-timestamp'),
        'Printed on ' + format_timestamp(new Date()));
    set_children($('site-url'),
        window.location.protocol + '//' + window.location.host);
  }

  start_monitoring();
}

// ==== In-place update

function start_monitoring() {
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = handle_monitor_notification;
  xhr.open('GET', '/monitor');
  xhr.send();
}

function handle_monitor_notification() {
  if (this.readyState == 4 && this.status == 200) {
    if (this.responseText != null && this.responseText.length) {
      eval(this.responseText);
    }
    start_monitoring();
  }
}

function set_facility_attribute(facility_name, attribute_name, value) {
  log(facility_name, attribute_name, value);
  var facility_i = 0;
  for (var f = 1; f < facilities.length; f++) {
    if (facilities[f].name == facility_name) {
      facility_i = f;
    }
  }
  var attribute_i = attributes_by_name[attribute_name];
  if (facility_i) {
    var facility = facilities[facility_i];
    if (!facility.last_report) {
      var nulls = [];
      for (var a = 0; a < attributes.length; a++) {
        nulls.push(null);
      }
      facility.last_report = {values: nulls};
    }
    facility.last_report.values[attribute_i] = value;
  }
  update_facility_row(facility_i);
}

var GLOW_COLORS = ['#ff4', '#ff4', '#ff5', '#ff6', '#ff8', '#ffa',
                   '#ffb', '#ffc', '#ffd', '#ffe', '#fffff8'];
var glow_element = null;
var glow_step = -1;

function glow(element) {
  if (glow_element) {
    glow_element.style.backgroundColor = '';
  }
  glow_element = element;
  glow_step = 0;
  glow_next();
}

function glow_next() {
  if (glow_element && glow_step < GLOW_COLORS.length) {
    glow_element.style.backgroundColor = GLOW_COLORS[glow_step];
    glow_step++;
    window.setTimeout(glow_next, 200);
  } else {
    if (glow_element) {
      glow_element.style.backgroundColor = '';
    }
    glow_element = null;
    glow_step = -1;
  }
}

function update_facility_row(facility_i) {
  var row = $('facility-' + facility_i);
  var cell = row.firstChild;
  var facility = facilities[facility_i];
  for (var c = 1; c < summary_columns.length; c++) {
    cell = cell.nextSibling;
    var value = summary_columns[c].get_value(facility.last_report.values);
    set_children(cell, value);
    cell.className = 'value column_' + c;
  }
  glow(row);
}

// ==== In-place editing

function edit_handler(edit_url) {
  // Use AJAX to load the form in the InfoWindow, then reopen the
  // InfoWindow so that it resizes correctly.
  log('Editing in place:', edit_url);
  $j.ajax({
    url: edit_url,
    success: function(data) {
      info.close();
      info.setContent('<div class="facility-info">' + data + '</div>');
      info.open(map, markers[selected_facility_i]);
    }
  });
  return false;
}

function request_role_handler(request_url) {
  // Use AJAX to load the form in the InfoWindow, then reopen the
  // InfoWindow so that it resizes correctly.
  log('reqest role:', request_url);
  $j.ajax({
    url: request_url,
    type: 'POST',
    success: function(data) {
       // TODO(eyalf): replace with a nice blocking popup
       alert(data)
    }
  });
  return false;
}

log('map.js finished loading.');
