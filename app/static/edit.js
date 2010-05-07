/*
# Copyright 2010 by Steve Hakusa
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
 * @fileoverview Functions for the edit page
 */

(function() {
  var button_click = '';

  function $(id) {
    return document.getElementById(id);
  }

  function save() {
    button_click = 'save';
  }

  function cancel() {
    button_click = 'cancel';
  }

  function check_tos() {
    if (button_click !== 'save') {
      return true;
    }
    var accepted_tos = $('accepted_tos');
    if (accepted_tos.value) {
      return true;
    }
    $('tos_errorbox').className = 'errorbox-bad';
    $('tos_errormsg').className = 'errormsg';
    return false;
  }

  function init() {
    $('edit').onsubmit = check_tos;
    $('save').onclick = save;
    $('cancel').onclick = cancel;
  }

  init();
})();
