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

rmapper.bubble = {};

rmapper.bubble.format_attr = function(attr, value) {
  switch (attr.type) {
    case 'contact':
      value = (value || '').replace(/^[\s\|]+|[\s\|]+$/g, '');
      value = value ? value.replace(/\|/g, ', ') : '\u2013';
      break;
    case 'date':
      value = (value || '').replace(/T.*/, '') || '\u2013';
      break;
    case 'str':
      value = value || '\u2013';
      break;
    case 'text':
      value = '<div class="text">' + value || '' + '</div>';
      break;
    case 'choice':
      value = translate_value(value) || '\u2013';
      break;
    case 'multi':
      value = translate_values(value || ['\u2013']).join(', ');
      break;
    case 'int':
    case 'float':
      if (value === null || value === undefined) {
        value = '\u2013';
      }
      if (value === 0) {
        value = '<span class="stockout">0</span>';
      }
    break;
  }

  return value
}
    
uniqId=12110;  
rmapper.bubble.get_html = function(facility, attribute_is,
                                   last_report_date) {

  uniqId++;
  var vars = {__ID__: uniqId,
              facility: facility,
              attribute_is: attribute_is,
              last_updated: last_report_date,
              availability: facility.last_report && 
                 facility.last_report.values[patient_count_attribute_i] || null,
              capacity: facility.last_report &&
                  facility.last_report.values[patient_capacity_attribute_i] || null,
              attrs: [ {title: "Organization Type",
                        value: "Red Cross Hospital"},
                       {title: "Transportation",
                        value:
                        "Patient pickup available and reachable by road"}]
  }
  var rendered_html = tmpl("bubble_tmpl", vars);

  return {tabs_id: '#tabs-'+uniqId, html: rendered_html };
}
