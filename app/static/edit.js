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

function make_visible(id) {
  document.getElementById(id).style.visibility = "visible";
}

(function() {
  var button_click = '';

  /**
   * Shorthand for document.getElementById.
   * @param {string} id - ID of an element in the dom
   * @return {Element|null} - the first element in the dom with that id, or null
   */
  function $(id) {
    return document.getElementById(id);
  }

  /**
   * Sets the error state of an attribute with the given name by toggling the
   * css class an error border with id <name>_errorbox and an error message with
   * id <name>_errormsg.
   * @param {string} name - the name of the attribute
   * @param {boolean} valid - true to display the error state, false to clear it
   * @param {string} error - the error message to display if valid is false
   */
  function set_error(name, valid, error) {
    $(name + '_errorbox').className =
        valid ? 'errorbox-good' : 'errorbox-bad';
    var errormsg = $(name + '_errormsg');
    errormsg.innerHTML = valid ? '' : to_html(error);
    errormsg.className = valid ? 'hidden' : 'errormsg';    
  }

  /**
   * Validates the name and affiliation fields, present the first time a user
   * makes an edit. If the fields are not present, returns true.
   */
  function validate_name_affil() {
    var nickname = $('account_nickname');
    if (!nickname) {
      return true;
    }
    var valid = validate_required_string(nickname);
    // careful to avoid short-circuiting here
    return validate_required_string($('account_affiliation')) && valid;
  }

  /**
   * Validates a string that is required, meaning that empty or whitespace
   * is considered an error.
   * @param input {Element} input - the input element to validate
   * @param opt_error {string|null} opt_error - optional error message. If
   * missing, a generic "Field is required" message is used.
   */
  function validate_required_string(input, opt_error) {
    var value = input.value ? jQuery.trim(input.value) : null;
    set_error(input.name, value, locale.ERROR_FIELD_IS_REQUIRED());
    return value ? true : false;
  }

  /**
   * Returns true if the given string is a valid number. Currently supports only
   * one number format; '-1234.5' is valid, but '1,234.5' and '3,50' are not.
   * @param {string} value - a string representing a number
   * @return {boolean} - true if the value is valid
   */
  function is_valid_number(value) {
    return jQuery.trim(value).match('^[0-9-\.]+$') ? true : false;
  }

  /**
   * Validates a numeric input field.
   * @param {Element} input - input field to validate
   * @return {boolean} - true if the value of the input is valid. If false, has
   * a side effect of displaying a "Value must be a number" error message
   */
  function validate_number(input) {
    var valid = true;
    if (input.value) {
      valid = is_valid_number(input.value);
    }
    set_error(input.name, valid, locale.ERROR_VALUE_MUST_BE_NUMBER());
    return valid;    
  }

 /**
  * Validates fields representing (latitude, longitude) coordinates.
  * @param {Array.<Element>} inputs - an array of 2 elements, one with name
  * <name>.lat and the other with name <name>.lon
  * @return {boolean} - true if the pair is a valid pair of coordinates, meaning
  * both values are numbers in the valid ranges, otherwise false
  */
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
        var value = parseFloat(jQuery.trim(input.value));
        if (coord == 'lat' && value < -90 || value > 90) {
          input_valid = false;
          error.push(locale.ERROR_LATITUDE_INVALID());
        } else if (coord == 'lon' && value < -180 || value > 180) {
          input_valid = false;
          error.push(to_html(locale.ERROR_LONGITUDE_INVALID()));
        }
      } else {
        error.push(to_html(
                     coord == 'lat' ? locale.ERROR_LATITUDE_MUST_BE_NUMBER()
                       : locale.ERROR_LONGITUDE_MUST_BE_NUMBER()));
      }
      valid = valid && input_valid;
    }

    set_error(name, valid, HTML(error.join('<br>')));
    return valid;
  }

  /**
   * If the save button is clicked, validate relevant inputs on the page,
   * and display error messages if fields are invalid.
   * input elements are discovered by checking for marker class names on
   * parent 'tr' elements.
   * @return {boolean} - true if the "save" button was not pressed or all 
   * inputs are valid, otherwise false
   */
  function validate() {
    if (button_click !== 'save') {
      return true;
    }

    var valid_arr = [validate_name_affil()];

    var trs = document.getElementsByTagName('tr');
    for (var i = 0; i < trs.length; i++) {
      var tr = trs[i];
      var classes = tr.className.split(' ');
      if (jQuery.inArray('int', classes) != -1
          || jQuery.inArray('float', classes) != -1) {
        valid_arr.push(validate_number(tr.getElementsByTagName('input')[0]));
      } else if (jQuery.inArray('geopt', classes) != -1) {
        var inputs = tr.getElementsByTagName('input');
        valid_arr.push(validate_geopt([inputs[0], inputs[1]]));
      }
    }      

    return jQuery.inArray(false, valid_arr) == -1;
  }

  /**
   * Initializes comment visibility and installs onclick handlers to make
   * comments visible if their values are updated.
   */
  function init_comment_visibility() {
    var trs = document.getElementsByTagName('tr');
    for (var i = 0; i < trs.length; i++) {
      var tr = trs[i];
      var classes = tr.className.split(' ');
      if (classes.length > 1) {
        var divs = tr.getElementsByTagName('div');
        var attribute_name = "";
        for (var div_index = 0; div_index < inputs.length; div_index++) {
          var div = divs[div_index];
          if (div.className == "comment") {
            tr.onclick = new Function(
              'make_visible("' + div.id + '");');
            var inputs = input.getElementsByTagName('input');
            if (inputs.length > 0) {
              var input = divs[0];
              if (input.value == '') {
                input.style.visibility = "hidden";
              } else {
                input.style.visibility = "visible";                
              }
            }
          }
        }
      }
    }
  }

  /**
   * Handler for a click of the save button.
   */
  function save() {
    button_click = 'save';
  }

  /**
   * Handler for a click of the cancel button.
   */
  function cancel() {
    button_click = 'cancel';
  }

  /**
   * Initializes event handlers for the page.
   */
  function init() {
    $('edit').onsubmit = validate;
    $('save').onclick = save;
    $('cancel').onclick = cancel;
    init_comment_visibility();
  }

  init();
})();
