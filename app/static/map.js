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
 * @fileoverview Main entry point. Manages parsing data from the page on load,
 *     displays it in the data view and map view, and sets up event handlers
 *     to handle the interaction between views.
 *     For now, also acts as the entry point for print view; take care to note
 *     use of the externally-defined 'print' variable.
 * @author kpy@google.com (Ka-Ping Yee)
 */

// ==== Constants

var STATUS_GOOD = 1;
var STATUS_BAD = 2;
var STATUS_UNKNOWN = 3;
var MAX_STATUS = 3;

var STATUS_ICON_COLORS = [null, '080', 'a00', '444'];
var STATUS_TEXT_COLORS = [null, '040', 'a00', '444'];
var STATUS_ZINDEXES = [null, 3, 2, 1];
var STATUS_LABEL_TEMPLATES = [
  null,
  'One or more ${ALL_SUPPLIES}',
  'No ${ANY_SUPPLY}',
  'Data missing for ${ANY_SUPPLY}'
];

// Temporary tweak for Health 2.0 demo (icons are always green).
STATUS_ICON_COLORS = [null, '080', '080', '080'];
STATUS_TEXT_COLORS = [null, '040', '040', '040'];

// In print view, limit the number of markers being printed on the map at once
// both for display and performance concerns.
// TODO: It would be better to instead figure out how to render markers in a
// smart way so that they do not overlap.
var MAX_MARKERS_TO_PRINT = 50;

var METERS_PER_MILE = 1609.344;
var METERS_PER_KM = 1000;

// Temporary for v1, this should be user-settable in the future
// TODO: Also need to update message in map.html that says "10 miles"
var PRINT_RADIUS_MILES = 10;
var PRINT_RADIUS_METERS = PRINT_RADIUS_MILES * METERS_PER_MILE;

// TODO: Re-enable when monitoring is re-enabled
var enable_freshness = false;

// ==== Data loaded from the data store

var attributes = [null];
var attributes_by_name = {};  // {attribute_name: attribute_i}
var subject_types = [null];
var subjects = [null];
var divisions = [null];
var messages = {};  // {namespace: {name: message}

// ==== Global status message fields

var status_message = false;
var status_temporary = false;
var status_timeout;

// ==== Columns shown in the subject table

rf.get_services_from_values = function(values) {
  services = translate_values(
      [].concat(values[attributes_by_name.services] || []))
  .join(', ');
  return services;
}

rf.get_services = function(subject) {
  var services = '';
  if (subject) {
    var values = subject.values;
    services = rf.get_services_from_values(values);
  }
  return services;
}

  
var summary_columns = [
  null, {
    get_title: function() {
      var beds_div = $$('div', {'class': 'beds'}, locale.OPEN_TOTAL_BEDS());
      return $$('div', {}, [beds_div, locale.SERVICES()]);
    },
    get_value: function(values) {
      var services = rf.get_services_from_values(values);
      var total_beds = render(values[attributes_by_name.total_beds]);
      var open_beds = render(values[attributes_by_name.available_beds]);
      var beds = open_beds + ' / ' + total_beds;
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
var selected_subject_i = -1;
var selected_subject = null;

var subject_status_is = [];  // status of each subject for selected supplies
var bounds_match_selected_division = false;  // to skip redundant redraws

// ==== Live API objects

var map = null;
var info = null;
var markers = [];  // marker for each subject
var marker_clusterer = null;  // clusters markers for efficient rendering
var converted_markers_for_print = 0; // part of a hack for print support

// ==== Debugging

// Print a message to the Safari or Firebug console.
function log() {
  // The strange way this function is written seems to be the only one
  // working on IE
  if (typeof console === 'undefined') {
    return;
  }
  if (console && console.log) {
    if (console.log.apply) {
      console.log.apply(console, arguments);      
    } else {
      console.log(arguments[0]);
    }
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
  return message && message || value;
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

function maybe_disabled(disabled) {
  return disabled ? ' disabled' : '';
}

function make_icon(title, status, detail, opt_icon, opt_icon_size,
    opt_icon_fill) {
  var text = detail ? title : '';
  var text_size = detail ? 10 : 0;
  var text_fill = STATUS_TEXT_COLORS[status];
  var icon = opt_icon || 'greek_cross_6w14';
  var icon_size = opt_icon_size || '16';
  var icon_fill = opt_icon_fill || STATUS_ICON_COLORS[status];
  var icon_outline = 'fff';
  var params = [
      text, text_size, text_fill,
      icon, icon_size, icon_fill, icon_outline
  ].join('|');
  var url = 'http://chart.apis.google.com/chart?chst=d_simple_text_icon_above&';
  // In print view, render icons as .gif's so they print correctly on older
  // browsers. In regular view, the default .pngs render better
  return url + (print ? 'chof=gif&' : '')
      + 'chld=' + encodeURIComponent(params);
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
  if (print) {
    google.maps.event.addListener(map, 'tilesloaded', convert_markers_for_print);
    google.maps.event.addListener(map, 'tilesloaded', hide_controls_for_print);
  }

  info = new google.maps.InfoWindow();

  var cluster_style = {
    url: make_icon(null, 1, null, 'greek_cross_12w30', '32'),
    height: 32,
    width: 32,
    opt_textColor: '#fff',
    Z: '#fff' // See http://code.google.com/p/google-maps-utility-library-v3/issues/detail?id=6    
  };
  // Turn off clustering in print view.
  var max_zoom = print ? -1 : 14;
  marker_clusterer = new MarkerClusterer(map, [], {
    maxZoom: max_zoom,  // closest zoom at which clusters are shown
    gridSize: 40, // size of square pixels in which to cluster
    // override default styles to render all cluster sizes with our custom icon
    styles: [cluster_style, cluster_style, cluster_style, cluster_style]
  });
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

// The v3 maps API does not have good print support.
// See http://code.google.com/p/gmaps-api-issues/issues/detail?id=1343
// The method modifies the DOM of the map to hide unwanted map controls
// and the mouse target layer that obstructs the markers during printing.
function hide_controls_for_print() {
  var mapDiv = $('map').firstChild;
  for (var control = mapDiv.firstChild; control;
       control = control.nextSibling) {
    if (control.style.zIndex == 10 && control.style.top) {
      control.className = 'gmnoprint';
    }
  }
  var panes = $('map').firstChild.firstChild;
  var duplicate_markers = 0;
  for (var pane = mapDiv.firstChild.firstChild; pane; pane = pane.nextSibling) {
    if (pane.style.zIndex == 105) {
      // Don't print anything in layer 105, the overlay mouse target layer.
      pane.className = 'gmnoprint';
      break;
    }
  }
}

// The v3 maps API does not have good print support.
// See http://code.google.com/p/gmaps-api-issues/issues/detail?id=1343
// The method converts background-image markers to actual <img> elements
// so that markers print reasonably well across browsers. Things are still 
// not perfect because of varying support for printing transparency.
function convert_markers_for_print() {
  var panes = $('map').firstChild.firstChild;
  var duplicate_markers = 0;
  for (var pane = panes.firstChild; pane; pane = pane.nextSibling) {
    if (pane.style.zIndex == 103) {
      for (var overlay = pane.firstChild; overlay;
           overlay = overlay.nextSibling) {
        // Convert background images to foreground images
        var src = overlay.style ? overlay.style.backgroundImage.toString() : '';
        if (src.indexOf('url') != -1) {
          // Remove the surrounding 'url()'
          src = src.substring(4, src.length - 1);
          overlay.style.backgroundImage = '';
          var img = document.createElement('img');
          overlay.appendChild(img);
          img.src = src;
          converted_markers_for_print++;
        } else if (overlay.style && overlay.style.zIndex) {
          // Pane 103 contains some divs with no zIndex or backgroundImage,
          // some divs with both zIndex and backgroundImage
          // and some divs with zIndex and no backgroundImage (the last set
          // are typically for markers that perfectly overlap another marker).
          // We have to count these, to know when we're done applying the hack.
          duplicate_markers++;
        }
      }
    }
  }
  if (converted_markers_for_print + duplicate_markers < markers.length) {
    // The DIVs for markers are added lazily and in batches. We don't know when
    // that happens, so we have to poll until we've converted all we can.
    window.setTimeout(convert_markers_for_print, 250);
  }
}

// Construct and set up the map markers for the subjects.
function initialize_markers() {
  for (var su = 1; su < subjects.length; su++) {
    var subject = subjects[su];
    var location = subject.values[attributes_by_name.location];
    if (!location) {
      markers[su] = null;
      continue;
    }
    var title = subject.values[attributes_by_name.title];
    markers[su] = new google.maps.Marker({
      position: new google.maps.LatLng(location.lat, location.lon),
      icon: make_icon(title, STATUS_UNKNOWN, false),
      title: title
    });
    if (!print) {
      google.maps.event.addListener(markers[su], 'click', subject_selector(su));
    }
    if (!print || su <= MAX_MARKERS_TO_PRINT) {
      subject.visible = true;
    }
  }

  var to_add = print ? markers.slice(1, MAX_MARKERS_TO_PRINT + 1)
      : markers.slice(1);
  marker_clusterer.addMarkers(to_add);
  log("init markers done");
}

// ==== Display construction routines

function initialize_language_selector() {
  var select = $('lang-select');
  if (!select) {
    return;
  }
  select.onchange = function() {
    window.location = select.options[select.selectedIndex].value;
  };
}

// Set up the supply selector (currently unused).
function initialize_supply_selector() {
  var tbody = $('supply-tbody');
  if (!tbody) {
    return;
  }
  var tr = $$('tr');
  var cells = [];
  for (var ss = 1; ss < supply_sets.length; ss++) {
    cells.push($$('td', {
      id: 'supply-set-' + ss,
      'class': 'supply-set',
      onclick: supply_set_selector(ss),
      onmouseover: hover_activator('supply-set-' + ss),
      onmouseout: hover_deactivator('supply-set-' + ss)
    }, supply_sets[ss].abbreviation));
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
  if (!tbody) {
    return;
  }
  var tr = $$('tr');
  var selector = $$('select', {
    id: 'specialty-selector',
    name: 'specialty',
    onchange: function() {
      var value = $('specialty-selector').value.split(' ');
      var trackedValue = value[1] ? value[1] : 'ANY';
      _gaq.push(['_trackEvent', 'subject_list', 'filter',
                 'Services contains ' + trackedValue]);
      select_filter.apply(null, value);
    }
  });
  var options = [];
  options.push($$('option', {value: '0 '}, locale.ALL()));
  add_filter_options(options, attributes_by_name.services);
  set_children(selector, options);
  set_children(tr, [$$('td', {}, [locale.SHOW() + ':', selector])]);
  set_children(tbody, tr);
}

// Add the header to the division list.
function initialize_division_header() {
  var thead = $('division-thead');
  if (!thead) {
    return;
  }
  var tr = $$('tr');
  var cells = [$$('th', {}, locale.DISTRICT())];
  for (var st = 1; st <= MAX_STATUS; st++) {
    cells.push($$('th', {'class': 'subject-count'},
        $$('img', {src: make_icon('', st, false)})));
  }
  cells.push($$('th', {'class': 'subject-count'}, 'All'));
  set_children(thead, tr);
  set_children(tr, cells);
}

// Add the header to the subject list.
function initialize_subject_header() {
  var thead = $('subject-thead');
  if (!thead) {
    return;
  }
  var tr = $$('tr');
  var cells = [$$('th', {}, locale.FACILITY())];
  for (var c = 1; c < summary_columns.length; c++) {
    cells.push($$('th', {'class': 'value column_' + c},
                  summary_columns[c].get_title()));
  }
  set_children(thead, tr);
  set_children(tr, cells);
}

// Initialize headers for print view.
function initialize_print_headers() {
  var now = new Date();

  set_children($('site-url'),
    window.location.protocol + '//' + window.location.host); 
  $('freshness').style.display = 'none';

  var date = format_date(now);
  var time = format_time(now);
  set_children($('header-print-date'), format_date(now));
  set_children($('header-print-time'), format_time(now));
  set_children($('print-date'), format_date(now));
  set_children($('print-time'), format_time(now));

  var tbody = $('print-summary-tbody');
  if (!tbody) {
    return;
  }
  var total_subjects = total_subject_count;
  var local_subjects = subjects.length - 1;  // ignore the selected one
  var available_subjects = 0;
  for (var i = 1; i < subjects.length; i++) {
    var values = subjects[i].values;
    if (values && values[attributes_by_name.available_beds] > 0) {
      available_subjects++;
    }
  }

  if (subjects.length >= MAX_MARKERS_TO_PRINT) {
    set_children($('header-print-subtitle'),
        locale.DISPLAYING_CLOSEST_N_FACILITIES(
            {NUM_FACILITIES: MAX_MARKERS_TO_PRINT}));
  } else {
    set_children($('header-print-subtitle'),
        locale.DISPLAYING_FACILITIES_IN_RANGE(
            {RADIUS_MILES: PRINT_RADIUS_MILES}));    
  }

  set_children($('print-subtitle'), locale.FACILITIES_IN_RANGE(
      {NUM_FACILITIES: local_subjects,
       RADIUS_MILES: PRINT_RADIUS_MILES}));
  set_children(tbody, $$('tr', {}, [
      $$('td', {}, [total_subjects]),
      $$('td', {}, [local_subjects]),
      $$('td', {}, [available_subjects])]));
}

// ==== Display update routines

// Set the map bounds to fit all subjects in the given division.
function update_map_bounds(division_i) {
  if (bounds_match_selected_division && division_i === selected_division_i) {
    // The map hasn't been moved since it was last fit to this division.
    return;
  }

  var subject_is = divisions[division_i].subject_is;
  var bounds = new google.maps.LatLngBounds();
  for (var i = 0; i < subject_is.length; i++) {
    var subject = subjects[subject_is[i]];
    var location = subject.values[attributes_by_name.location];
    if (location && subject.visible) {
      bounds.extend(new google.maps.LatLng(location.lat, location.lon));
    }
  }
  map.fitBounds(bounds);
  bounds_match_selected_division = true;
}

// Update the subject map icons based on their status and the zoom level.
function update_subject_icons() {
  var detail = map.getZoom() > 10;
  var markers_to_keep = [];
  for (var su = 1; su < subjects.length; su++) {
    if (markers[su]) {
      var subject = subjects[su];
      var st = subject_status_is[su];
      var title = subject.values[attributes_by_name.title];
      var icon_url = make_icon(title, st, detail);
      if (is_subject_closed(subject)) {
        icon_url = make_icon(title, st, detail, null, null, 'a00');
      }
      subject.visible = false;
      if (st == STATUS_GOOD) {
        markers[su].setIcon(icon_url);
        markers[su].setZIndex(STATUS_ZINDEXES[st]);
        markers_to_keep.push(markers[su]);
        if (!print || su <= MAX_MARKERS_TO_PRINT) {
          subject.visible = true;
        }
      }
    }
  }
  marker_clusterer.clearMarkers();
  var to_add = print ? markers_to_keep.slice(0, MAX_MARKERS_TO_PRINT)
      : markers_to_keep;
  marker_clusterer.addMarkers(to_add);
}

// Fill in the subject legend.
function update_subject_legend() {
  if (!$('legend-tbody')) {
    return;
  }
  var rows = [];
  var stock = 'one dose';
  for (var st = 1; st <= MAX_STATUS; st++) {
    rows.push($$('tr', {'class': 'legend-row'}, [
      $$('th', {'class': 'legend-icon'},
        $$('img', {src: make_icon('', st, false)})),
      $$('td', {'class': 'legend-label status-' + st},
        render(STATUS_LABEL_TEMPLATES[st], {
          ALL_SUPPLIES: selected_supply_set.description_all,
          ANY_SUPPLY: selected_supply_set.description_any
        }))
    ]));
  }
  set_children($('legend-tbody'), rows);
}

// Repopulate the subject list based on the selected division and status.
function update_subject_list() {
  if (!$('subject-tbody')) {
    return;
  }
  var rows = [];
  for (var i = 0; i < selected_division.subject_is.length; i++) {
    var su = selected_division.subject_is[i];
    var subject = subjects[su];
    var subject_type = subject_types[subject.type];
    if (!markers[su]) {
      // TODO(kpy): For now, subjects without locations are hidden
      // from the list.  Once we have a way to show the detail window for
      // subjects without locations, we can include them in the list.
      continue;
    }
    if (selected_status_i === 0 ||
        subject_status_is[su] === selected_status_i) {
      var row = $$('tr', {
        id: 'subject-' + su,
        'class': 'subject' +
            maybe_disabled(is_subject_closed(subject)) +
            maybe_selected(su === selected_subject_i),
        onclick: subject_selector(su),
        onmouseover: hover_activator('subject-' + su),
        onmouseout: hover_deactivator('subject-' + su)
      });
      var title = subject.values[attributes_by_name.title];
      var cells = [$$('td', {'class': 'subject-title'}, title)];
      if (subject) {
        for (var c = 1; c < summary_columns.length; c++) {
          var value = summary_columns[c].get_value(subject.values);
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
  set_children($('subject-tbody'), rows);
  update_subject_list_size();
}

// Populate the subject list for print view.
function update_print_subject_list() {
  if (!$('subject-print-tbody')) {
    return;
  }
  var rows = [];
  for (var i = 0; i < selected_division.subject_is.length; i++) {
    var su = selected_division.subject_is[i];
    var subject = subjects[su];
    var subject_type = subject_types[subject.type];
    if (selected_status_i === 0 ||
        subject_status_is[su] === selected_status_i) {
      var row = $$('tr', {
        id: 'subject-' + su,
        'class': 'subject-' + (i % 2 == 0 ? 'even' : 'odd')
      });
      var cells = [];
      var total_beds;
      var open_beds;
      var address;
      var general_info;
      var healthc_id;
      var pcode;
      if (subject) {
        var values = subject.values;
        total_beds = values[attributes_by_name.total_beds];
        open_beds = values[attributes_by_name.available_beds];
        address = values[attributes_by_name.address];
        general_info = values[attributes_by_name.contact_name];
        healthc_id = values[attributes_by_name.healthc_id];
        pcode = values[attributes_by_name.pcode];
        var phone = values[attributes_by_name.phone];
        if (phone) {
          general_info = (general_info ? general_info + ' ' : '')
              + locale.PHONE_ABBREVIATION({PHONE: phone});
        }
      }
      var dist_meters = subject.distance_meters;
      var dist;
      if (typeof(dist_meters) === 'number') {
        dist = locale.DISTANCE({
            MILES: format_number(dist_meters / METERS_PER_MILE, 1), 
            KM: format_number(dist_meters / METERS_PER_KM, 2)});
      }
      var title = subject.values[attributes_by_name.title];
      var subject_title = title + ' - '
        + locale.HEALTHC_ID() + ': ' + render(healthc_id)
        + ' - ' + locale.PCODE() + ': ' + render(pcode);
      cells.push($$('td', {'class': 'subject-beds-open'}, render(open_beds)));
      cells.push($$('td', {'class': 'subject-beds-total'},render(total_beds)));
      cells.push($$('td', {'class': 'subject-title'}, render(subject_title)));
      cells.push($$('td', {'class': 'subject-distance'}, render(dist)));
      cells.push($$('td', {'class': 'subject-address'}, render(address)));
      cells.push($$('td', {'class': 'subject-general-info'},
          render(general_info)));
      set_children(row, cells);
      rows.push(row);
    }
  }
  set_children($('subject-print-tbody'), rows);
}

// Update the height of the subject list to exactly fit the window.
function update_subject_list_size() {
  var windowHeight = get_window_size()[1];
  var freshnessHeight = $('freshness').clientHeight;
  var listTop = get_element_top($('subject-list'));
  var listHeight = windowHeight - freshnessHeight - listTop;
  $('subject-list').style.height = listHeight + 'px';
  align_header_with_table($('subject-thead'), $('subject-tbody'));
}

// Update the width of header cells to match the table cells below.
function align_header_with_table(thead, tbody) {
  if (tbody.firstChild) {
    thead.parentNode.style.width = tbody.parentNode.clientWidth + 'px';
    var head_cell = thead.firstChild.firstChild;
    var body_cell = tbody.firstChild.firstChild;
    while (body_cell) {
      // Subtract 8 pixels to account for td padding: 2px 4px.
      // TODO: fix for IE
      if (body_cell.clientWidth) {
        head_cell.style.width = (body_cell.clientWidth - 8) + 'px';
      }
      head_cell = head_cell.nextSibling;
      body_cell = body_cell.nextSibling;
    }
  }
}

// Determine the status of each subject according to the user's filters.
function update_subject_status_is() {
  for (var su = 1; su < subjects.length; su++) {
    var subject = subjects[su];
    if (selected_filter_attribute_i <= 0) {
      subject_status_is[su] = STATUS_GOOD;
    } else if (!subject) {
      subject_status_is[su] = STATUS_UNKNOWN;
    } else {
      subject_status_is[su] = STATUS_BAD;
      var a = selected_filter_attribute_i;
      if (attributes[a].type === 'multi') {
        if (contains(subject.values[a] || [], selected_filter_value)) {
          subject_status_is[su] = STATUS_GOOD;
        }
      } else if (report.values[a] === selected_filter_value) {
        subject_status_is[su] = STATUS_GOOD;
      }
    }
  }
}

// Update the contents of the division list based on subject statuses. 
function update_division_list() {
  if (!$('division-tbody')) {
    return;
  }
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
    for (var st = 1; st <= MAX_STATUS; st++) {
      var subject_is = filter(division.subject_is,
        function (subject_i) { return subject_status_is[subject_i] === st; });
      cells.push($$('td', {
        'id': 'division-' + d + '-status-' + st,
        'class': 'subject-count status-' + st + maybe_selected(
            d === selected_division_i && st === selected_status_i),
        onclick: division_and_status_selector(d, st),
        onmouseover: hover_activator('division-' + d + '-status-' + st),
        onmouseout: hover_deactivator('division-' + d + '-status-' + st)
      }, subject_is.length));
    }
    cells.push($$('td', {
      'id': 'division-' + d + '-status-0',
      'class': 'subject-count status-0' + maybe_selected(
          d === selected_division_i && 0 === selected_status_i),
      onclick: division_and_status_selector(d, 0),
      onmouseover: hover_activator('division-' + d + '-status-0'),
      onmouseout: hover_deactivator('division-' + d + '-status-0')
    }, division.subject_is.length));
    set_children(row, cells);
    rows.push(row);
  }

  set_children($('division-tbody'), rows);
}

// Update the data freshness indicator.
function update_freshness(timestamp) {
  if (!enable_freshness) {
    $('freshness-text').style.display = 'none';
  }

  if (!timestamp) {
    $('freshness-text').innerHTML = 'No reports received';
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

  $('freshness-text').innerHTML = 'Last updated ' + age +
      ' (' + format_timestamp(t) + ')';
  window.setTimeout(function () { update_freshness(timestamp); }, timeout);
}

// Disable the print link in the user header.  This is done when no subjects
// are selected
function disable_print_link() {
  var print_link = $('print-link');
  if (!print_link) {
    return;
  }
  print_link.href = 'javascript:void(0)';
  print_link.title = locale.PRINT_DISABLED_TOOLTIP();
  print_link.target = '';  // prevent Selenium from opening a window in testing
  print_link.onclick = function() {
    // TODO: Use a nice model dialog instead of alert
    alert(locale.PRINT_DISABLED_TOOLTIP());
    return false;
  };
}

// Enable the print link in the user header. This is done when a subject has
// been selected.
function enable_print_link() {
  var print_link = $('print-link');
  if (!print_link) {
    return;
  }
  var subject = selected_subject;
  var location = subject.values[attributes_by_name.location];
  var title = subject.values[attributes_by_name.title];
  print_link.href = print_url + render(
      '&lat=${LAT}&lon=${LON}&rad=${RAD}',
      {LAT: location.lat, LON: location.lon, RAD: PRINT_RADIUS_METERS}
  );
  print_link.title = locale.PRINT_ENABLED_TOOLTIP({FACILITY_NAME: title});
  print_link.target = '_blank';
  print_link.onclick = null;
}

// Format a JavaScript Date object as a human-readable string.
function format_timestamp(t) {
  return locale.DATE_AT_TIME({ DATE: format_date(t), TIME: format_time(t) });
}

// Format a JavaScript Date object as a human-readable date string.
function format_date(t) {
  // Note: t.getMonth() returns a number from 0-11
  return locale.DATE_FORMAT_MEDIUM({MONTH: locale.MONTH_ABBRS[t.getMonth()](),
      DAY: t.getDate(), YEAR: t.getFullYear()});
}

// Format a JavaScript Date object as a human-readable time string.
function format_time(t) {
  var hours = (t.getHours() < 10 ? '0' : '') + t.getHours();
  var minutes = (t.getMinutes() < 10 ? '0' : '') + t.getMinutes();
  var offset = - (t.getTimezoneOffset() / 60);
  var zone = 'UTC' + (offset > 0 ? '+' : '\u2212') + Math.abs(offset);
  return locale.TIME_FORMAT_MEDIUM_WITH_ZONE(
      {HOURS: hours, MINUTES: minutes, ZONE: zone});
}

// Format a number to decimal_places places.
function format_number(num, decimal_places) {
  var integer_part = Math.floor(num);
  var mantissa = Math.round((num % 1) * Math.pow(10, decimal_places));
  return integer_part + '.' + mantissa;
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
    update_subject_list_size();
  }
}

function handle_zoom_changed() {
  update_subject_icons(); // amount of detail in icons depends on zoom level
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

function subject_selector(subject_i) {
  return function () {
    select_subject(subject_i);
  };
}

// ==== Selection behaviour

function select_filter(attribute_i, value) {
  selected_filter_attribute_i = attribute_i;
  selected_filter_value = value;

  // Apply the filter to the subject list.
  update_subject_status_is();

  // Update the subject icons to reflect their status.
  update_subject_icons();

  // Update the subject counts in the division list.
  update_division_list();

  if (selected_division !== null) {
    // Filter the list of subjects by the selected supply set.
    update_subject_list();
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
  if($('supply-tbody')) {
    for (var ss = 1; ss < supply_sets.length; ss++) {
      $('supply-set-' + ss).className = 'supply-set' +
          maybe_selected(ss === supply_set_i);
    }
  }

  // Update the subject icon legend.
  update_subject_legend();

  // Update the status of each subject.
  update_subject_status_is();

  // Update the subject icons to reflect their status.
  update_subject_icons();

  // Update the subject counts in the division list.
  update_division_list();

  if (selected_division !== null) {
    // Filter the list of subjects by the selected supply set.
    update_subject_list();
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
  if ($('division-thead')) {
    for (var d = 0; d < divisions.length; d++) {
      for (var st = 0; st <= MAX_STATUS; st++) {
        $('division-' + d + '-status-' + st).className =
            'subject-count status-' + st +
            maybe_selected(d === division_i && st === status_i);
      }
    }    
  }

  // Filter the list of subjects by the selected division and status.
  update_subject_list();
}

function select_subject(subject_i) {
  // Update the selection.
  selected_subject_i = subject_i;
  selected_subject = (subject_i <= 0) ? null : subjects[subject_i];

  // Update the selection highlight.
  for (var su = 1; su < subjects.length; su++) {
    var item = $('subject-' + su);
    if (item) {
      item.className = 'subject' +
          maybe_disabled(is_subject_closed(subjects[su])) +
          maybe_selected(su === selected_subject_i);
    }
  }

  if (subject_i <= 0) {
    // No selection.
    info.close();
    return;
  }

  // Pop up the InfoWindow on the selected clinic, if it has a location.
  info.close();

  if (markers[selected_subject_i]) {
    show_loading(true);
    var url = bubble_url + (bubble_url.indexOf('?') >= 0 ? '&' : '?') +
        'subject_name=' + selected_subject.name;
    _gaq.push(['_trackEvent', 'bubble', 'open', selected_subject.name]);
    jQuery.ajax({
      url: url,
      type: 'GET',
      timeout: 10000,
      error: function(request, text_status, error_thrown){
        log(text_status + ', ' + error_thrown);
        alert(locale.ERROR_LOADING_FACILITY_INFORMATION());
        show_loading(false);
      },
      success: function(result){
        info.setContent(result);
        info.open(map, markers[selected_subject_i]);
        // Sets up the tabs and should be called after the DOM is created.
        jQuery('#bubble-tabs').tabs({
          select: function(event, ui) {
            _gaq.push(['_trackEvent', 'bubble', 'click ' + ui.panel.id,
                       selected_subject.name]);
          }
        });

        var bubbleAvailability = $('bubble-availability');
        var bubbleCapacity = $('bubble-capacity');

        if (bubbleAvailability) {
          selected_subject.values[attributes_by_name.available_beds] =
              bubbleAvailability.innerHTML;          
        }
        if (bubbleCapacity) {
          selected_subject.values[attributes_by_name.total_beds] =
              bubbleCapacity.innerHTML; 
        }
        update_subject_row(subject_i);

        show_loading(false);
      }
    });

    // Enable the Print link (which requires a center location).
    enable_print_link();
  }
}

function update_status() {
  var status = $('loading');

  if (status_temporary) {
    status.innerHTML = status_temporary;
    status.style.display = '';
  } else if (status_message) {
    status.innerHTML = status_message;
    status.style.display = '';
  } else {
    status.style.display = 'none';
  }
}

function show_status(message) {
  status_message = message;
  update_status();
}

function clear_status() {
  status_message = false;
  update_status();
}

function show_loading(show) {
  if (show) {
    show_status(locale.LOADING());    
  } else {
    clear_status();
  }
}

function show_temporary_status(message, duration) {
  status_temporary = message;
  update_status();

  clearTimeout(status_timeout);
  status_timeout = setTimeout(function () { 
    status_temporary = false;
    update_status();
  }, duration);
}

// ==== Load data

function load_data(data, selected_subject_name) {
  attributes = data.attributes;
  subject_types = data.subject_types;
  subjects = data.subjects;
  messages = data.messages;
  total_subject_count = data.total_subject_count;

  attributes_by_name = {};
  for (var a = 1; a < attributes.length; a++) {
    attributes_by_name[attributes[a].name] = a;
    switch (attributes[a].name){
      case 'specialty_care': specialty_attribute_i = a; break;
      case 'medical_equipment': equipment_attribute_i = a; break;
      case 'patient_capacity': patient_capacity_attribute_i = a; break;
      case 'patient_count': patient_count_attribute_i = a; break;
    }
  }

  var subject_is = [];
  for (var i = 1; i < subjects.length; i++) {
    subject_is.push(i);
    if (selected_subject_name == subjects[i].name) {
      selected_subject_i = i;
    }
  }
  divisions = [{
    title: 'All divisions',
    subject_is: subject_is
  }];

  if (!print) {
    // The print link is not shown in print view, no need to disable it
    disable_print_link();
    // The supply selector, filters, division header and subject
    // header all do not appear in print view; don't bother initializing them.
    initialize_supply_selector();
    initialize_filters();
    initialize_division_header();
    initialize_subject_header();    
  }

  initialize_language_selector();
  initialize_map();
  initialize_markers();
  initialize_handlers();
  update_freshness(data.timestamp);

  select_supply_set(DEFAULT_SUPPLY_SET_I);
  select_division_and_status(0, STATUS_GOOD);
  if (selected_subject_i != -1) {
    window.setTimeout(subject_selector(selected_subject_i), 500);
  }

  if (print) {
    initialize_print_headers();
    update_print_subject_list();
  } else {
    handle_window_resize();
  }

  show_loading(false);
  log('Data loaded.');

  // TODO: Test further and re-enable
  //start_monitoring();
}

// ==== In-place update

function start_monitoring() {
  // TODO: fix for IE
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = handle_monitor_notification;
  xhr.open('GET', '/monitor');
  xhr.send('');
}

function handle_monitor_notification() {
  if (this.readyState == 4 && this.status == 200) {
    if (this.responseText != null && this.responseText.length) {
      eval(this.responseText);
    }
    start_monitoring();
  }
}

function set_subject_attribute(subject_name, attribute_name, value) {
  log(subject_name, attribute_name, value);
  var subject_i = 0;
  for (var su = 1; su < subjects.length; su++) {
    if (subjects[su].name == subject_name) {
      subject_i = su;
    }
  }
  var attribute_i = attributes_by_name[attribute_name];
  if (subject_i) {
    var subject = subjects[subject_i];
    if (!subject) {
      var nulls = [];
      for (var a = 0; a < attributes.length; a++) {
        nulls.push(null);
      }
      subject.values = nulls;
    }
    subject.values[attribute_i] = value;
  }
  update_subject_row(subject_i);
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

function update_subject_row(subject_i, opt_glow) {
  var row = $('subject-' + subject_i);
  var cell = row.firstChild;
  var subject = subjects[subject_i];
  for (var c = 1; c < summary_columns.length; c++) {
    cell = cell.nextSibling;
    var value = summary_columns[c].get_value(subject.values);
    set_children(cell, value);
    cell.className = 'value column_' + c;
  }
  if (opt_glow) {
    glow(row);
  }
}

// ==== In-place editing

function inplace_edit_handler(edit_url) {
  // Use AJAX to load the form in the InfoWindow, then reopen the
  // InfoWindow so that it resizes correctly.
  log('Editing in place:', edit_url);

  show_loading(true);
  $j.ajax({
    url: edit_url,
    type: 'GET',
    error: function(request, textStatus, errorThrown) {
      log(textStatus + ', ' + errorThrown);
      alert(locale.ERROR_LOADING_EDIT_FORM());
      show_loading(false);
    },
    success: function(data) {
      var edit_data = $('edit-data');
      edit_data.innerHTML = data;
      edit_data.style.display = '';

      var windowHeight = get_window_size()[1];
      var editTop = get_element_top(edit_data);
      edit_data.style.height = (windowHeight - editTop) + 'px';

      $('data').style.display = 'none';
      init_edit(true, edit_url, edit_data);
      show_loading(false);
    }
  });

  return false;
}

function inplace_edit_save(edit_url) {
  save();
  if (validate()) {
    log('Saving in place');

    show_status(locale.SAVING());
    $j.ajax({
      url: edit_url,
      type: 'POST',
      data: $j('#edit').serialize(),
      error: function(request, textStatus, errorThrown) {
	log(textStatus + ', ' + errorThrown);
	alert(locale.ERROR_SAVING_FACILITY_INFORMATION());
	show_loading(false);
      },
      success: function(data) {
	$('data').style.display = '';
	$('edit-data').style.display = 'none';
	select_subject(selected_subject_i);
	show_temporary_status(locale.SAVED(), 5000);
      }
    });
  }

  return false;
}

function inplace_edit_cancel() {
      cancel();
      $('data').style.display = '';
      $('edit-data').style.display = 'none';
}

function request_action_handler(request_url) {
  // Use AJAX to load the form in the InfoWindow, then reopen the
  // InfoWindow so that it resizes correctly.
  log('reqest action:', request_url);
  $j.ajax({
    url: request_url,
    type: 'POST',
    success: function(data) {
       // TODO(eyalf): replace with a nice blocking popup
       alert(data);
    }
  });
  return false;
}

// Returns true IFF the operational status of the subject is set to
// CLOSED_OR_CLOSING
function is_subject_closed(subject) {
  if (subject) {
    var op_status = subject.values[attributes_by_name.operational_status];
    if (op_status == 'CLOSED_OR_CLOSING') {
      return true;
    }
  }

  return false;
};

log('map.js finished loading.');
