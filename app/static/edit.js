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

  function validate_name_affil() {
    if (button_click !== 'save') {
      return true;
    }
    var nickname = $('auth_nickname');
    var affiliation = $('auth_affiliation');
    if (!nickname) {
      return true;
    }
    
    var nickname_value = nickname.value ? nickname.value.trim() : null;
    var affiliation_value = affiliation.value ? affiliation.value.trim() : null;

    $('nickname_errorbox').className =
        nickname_value ? 'errorbox-good' : 'errorbox-bad';
    $('nickname_errormsg').className =
        nickname_value ? 'hidden' : 'errormsg';
    $('affiliation_errorbox').className =
        affiliation_value ? 'errorbox-good' : 'errorbox-bad';
    $('affiliation_errormsg').className =
        affiliation_value ? 'hidden' : 'errormsg';
    
    return nickname_value && affiliation_value ? true : false;
  }

  function init() {
    $('edit').onsubmit = validate_name_affil;
    $('save').onclick = save;
    $('cancel').onclick = cancel;
  }

  init();
})();
