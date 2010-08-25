/*
# Copyright 2010 Google Inc.
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
 * @fileoverview JavaScript code to display and handle related actions for the
 *     first-time visit splash pop up.
 * @author pfritzsche@google.com (Phil Fritzsche)
 */

function show_splash(show) {
  $j('body').css('overflow', show ? 'hidden' : 'auto');
  var background_fader = $('background-fader');
  background_fader.style.display = show ? '' : 'none';

  var splash_popup = $('splash-popup');
  splash_popup.style.display = show ? '' : 'none';
  if (show) {
    center_element(splash_popup);
    $j(window).resize(function() {
      center_element(splash_popup);
    });
  } else {
    $j(window).resize(null);
  }
}

function center_element(elem) {
  var window_size = get_window_size();
  elem.style.left = (window_size[0] / 2) - (elem.clientWidth / 2) + 'px';
  elem.style.top = (window_size[1] / 2) - (elem.clientHeight / 2) + 'px';
}
