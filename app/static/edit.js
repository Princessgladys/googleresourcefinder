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
 * @fileoverview Functions for the edit page
 */

(function() {
  var button_click = '';

  function $(id) {
    return document.getElementById(id);
  }

  function ensure_array_indexOf() {
    // Array.prototype.indexOf is not implemented in all browsers
    if (!Array.prototype.indexOf) {
      Array.prototype.indexOf = function(elt /*, from*/) {
        var len = this.length;

        var from = Number(arguments[1]) || 0;
        from = (from < 0) ? Math.ceil(from) : Math.floor(from);
        if (from < 0) {
          from += len;          
        }

        for (; from < len; from++) {
          if (from in this && this[from] === elt) {
            return from;            
          }
        }
        return -1;
      };
    }
  }

  function set_error(name, valid, error) {
    $(name + '_errorbox').className =
        valid ? 'errorbox-good' : 'errorbox-bad';
    var errormsg = $(name + '_errormsg');
    errormsg.innerText = valid ? '' : error;      
    errormsg.className = valid ? 'hidden' : 'errormsg';    
  }

  function validate_name_affil() {
    var nickname = $('auth_nickname');
    if (!nickname) {
      return true;
    }
    var valid = validate_required_string(nickname);
    valid &= validate_required_string($('auth_affiliation'));
    return valid;
  }

  function validate_required_string(input, opt_error) {
    var value = input.value ? input.value.trim() : null;
    set_error(input.name, value, locale.ERROR_FIELD_IS_REQUIRED());
    return value ? true : false;
  }

  function is_valid_number(value) {
    return value.trim().match('^[0-9-\.]+$') ? true : false;
  }

  function validate_number(input) {
    var valid = true;
    if (input.value) {
      valid = is_valid_number(input.value);
    }
    set_error(input.name, valid, locale.ERROR_VALUE_MUST_BE_NUMBER());
    return valid;    
  }

  function validate_geopt(inputs) {
    var valid = true;
    var name = '';
    var error = [];
    for (var i = 0; i < inputs.length; i++) {
      var input = inputs[i];
      var name_coord = input.name.split('.');
      name = name_coord[0];
      var coord = name_coord[1];
      var input_valid = is_valid_number(input.value);
      if (input_valid) {
        var value = parseFloat(input.value.trim());
        if (coord == 'lat' && value < -90 || value > 90) {
          input_valid = false;
          error.push(locale.ERROR_LATITUDE_INVALID());
        } else if (coord == 'lon' && value < -180 || value > 180) {
          input_valid = false;
          error.push(locale.ERROR_LONGITUDE_INVALID());
        }
      } else {
        error.push(coord == 'lat' ? locale.ERROR_LATITUDE_MUST_BE_NUMBER()
                   : locale.ERROR_LONGITUDE_MUST_BE_NUMBER());
      }
      valid &= input_valid;
    }

    set_error(name, valid, error.join('\n'));
    return valid;
  }

  function validate() {
    if (button_click !== 'save') {
      return true;
    }

    var valid = validate_name_affil();

    var trs = document.getElementsByTagName('tr');
    for (var i = 0; i < trs.length; i++) {
      var tr = trs[i];
      var classes = tr.className.split(' ');
      if (classes.indexOf('int') != -1 || classes.indexOf('float') != -1) {
        valid &= validate_number(tr.getElementsByTagName('input')[0]);
      } else if (classes.indexOf('geopt') != -1) {
        var inputs = tr.getElementsByTagName('input');
        valid &= validate_geopt([inputs[0], inputs[1]]);
      }
    }      

    return valid ? true : false;
  }

  function save() {
    button_click = 'save';
  }

  function cancel() {
    button_click = 'cancel';
  }

  function init() {
    ensure_array_indexOf();
    $('edit').onsubmit = validate;
    $('save').onclick = save;
    $('cancel').onclick = cancel;
  }

  init();
})();
