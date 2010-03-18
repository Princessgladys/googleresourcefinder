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

uniqId=12110;  
rmapper.get_bubble_html = function(facility, attributes, last_report_date, user) {
  HTML = '<div id="bubble">' +
  '<h1>${facility_title}</h1>' +
  '<div class="bubble-l2"> Facility ID: ${facility_id} | Updated ${last_updated} | {$edit_code}</div>' +
  '  <div class="bubble-main-info">' +
  '    <hr>' +
  '    <table>' +
  '    <thead>' +
  '      <tr>' +
  '        <th class="bubble-info-ava"> availability </th>' +
  '        <th> capacity </th>' +
  '        <th> services </th>' +
  '      </tr>' +
  '    </thead>' +
  '    <tbody>' +
  '      <tr>' +
  '        <th class="bubble-info-number bubble-info-ava"> ${availability} </th>' +
  '        <th class="bubble-info-number"> ${capacity} </th>' +
  '        <th class="bubble-info-serv"> Ultrasound, Orthopedic, Obstetrics, another</th>' +
  '      </tr>' +
  '    </tbody>' +
  '    </table>' +
  '    <hr>' +
  '  </div>' +
  '  <div id="tabs-${__ID__}">' +
  '    <ul>' +
  '      <li ><a href="#tabs-${__ID__}-1">Facility Details</a></li> ' +
  '      <li ><a href="#tabs-${__ID__}-2">Change History</a></li>' +
  '    </ul>' +
  '    <div id="tabs-${__ID__}-1" >' +
  '    <table>' +
  '    <tbody id="bubble_attributes_body">' +
  '      <tr class="item">' +
  '        <th class="bubble_attr_title"> </th>' +
  '        <th class="bubble_attr_value"> </th>' +
  '      </tr>' +
  '    </tbody>' +
  '    </table>' +
  '    </div>' +
  '    <div id="tabs-${__ID__}-2" >' +
  'TAB 2.' +
  '    </div>' +
  '  </div>' +
  '</div>';

  uniqId++;
  var vars = {__ID__: uniqId,
              facility_title: 'Ans A Foleu',
              availability: 38,
              capacity: 45,
  }
  var rendered_html = render_template(HTML, vars)
  var tempDiv = document.createElement('div');
  tempDiv.innerHTML = rendered_html;
  jQuery('#bubble-temp-placeholder').append(tempDiv);

  attrs = [
  {bubble_attr_title: "Organization Type",
   bubble_attr_value: "Red Cross Hospital"},
  {bubble_attr_title: "Transportation",
   bubble_attr_value: "Patient pickup available and reachable by road"}];

  jQuery('#bubble_attributes_body').items('replace', attrs).chain();

  final_html = tempDiv.innerHTML;
  jQuery('#bubble-temp-placeholder').empty();
  
  return ['#tabs-'+uniqId, final_html ];
}
