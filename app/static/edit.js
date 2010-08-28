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
 * Validates the name field, present the first time a user
 * makes an edit. If the field is not present, returns true.
 * @return {boolean} - true if the field is valid or not present
 */
function validate_name() {
  var nickname = $('account_nickname');
  if (!nickname) {
    return true;
  }
  return validate_required_string(nickname);
}

/**
 * Validates the affiliation field, present the first time a user
 * makes an edit. If the field is not present, returns true.
 * @return {boolean} - true if the field is valid or not present
 */
function validate_affil() {
  var affiliation = $('account_affiliation');
  if (!affiliation) {
    return true;
  }
  return validate_required_string(affiliation);
}

/**
 * Validates a string that is required, meaning that empty or whitespace
 * is considered an error.
 * @param input {Element} input - the input element to validate
 * @param opt_error {string|null} opt_error - optional error message. If
 * missing, a generic "Field is required" message is used.
 * @return {boolean} - true if the input is valid
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
  var blank_count = 0;
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
        error.push(HTML('<br>'));
      } else if (coord == 'lon' && value < -180 || value > 180) {
        input_valid = false;
        error.push(to_html(locale.ERROR_LONGITUDE_INVALID()));
        error.push(HTML('<br>'));
      }
    } else {
      error.push(to_html(
                   coord == 'lat' ? locale.ERROR_LATITUDE_MUST_BE_NUMBER()
                     : locale.ERROR_LONGITUDE_MUST_BE_NUMBER()));
      error.push(HTML('<br>'));
      if (!jQuery.trim(input.value)) {
        blank_count++;
      }
    }
    valid = valid && input_valid;
  } 

  if (blank_count == inputs.length) {
    // If all inputs are blank, this is valid
    valid = true;
  }

  set_error(name, valid, error);
  return valid;
}

/**
 * If the save button is clicked, validate relevant inputs on the page,
 * and display error messages if fields are invalid.
 * Input elements are discovered by checking for marker class names on
 * parent 'tr' elements.
 * @return {boolean} - true if the "save" button was not pressed or all 
 * inputs are valid, otherwise false
 */
function validate() {
  var failed = false;
  function confirm(valid, element) {
    if (!valid && !failed) {
      failed = element; 
    }
  }

  confirm(validate_name(), $('account_nickname'));
  confirm(validate_affil(), $('account_affiliation'));

  var trs = document.getElementsByTagName('tr');
  for (var i = 0; i < trs.length; i++) {
    var tr = trs[i];
    var classes = tr.className.split(' ');
    if (jQuery.inArray('int', classes) != -1
        || jQuery.inArray('float', classes) != -1) {

      var input = tr.getElementsByTagName('input')[0];
      confirm(validate_number(input), input);
    } else if (jQuery.inArray('geopt', classes) != -1) {
      var inputs = tr.getElementsByTagName('input');
      confirm(validate_geopt([inputs[0], inputs[1]]), inputs[0]);
    }
  }      
  if (failed) {
    failed.focus();
  }
  return !failed;
}

/**
 * Makes the element with the given id visible.
 * @param {string} id - the id of the element to make visible
 */  
function make_visible(id) {
  $(id).style.display = '';
}

/**
 * Returns a closure that when called will make the given element visible.
 * @param {Element} elem - the element to make visible
 * @return {function} the closure
 */
function make_visible_closure(elem) {
  return function() {
    make_visible(elem.id);
  };
}

/**
 * Initializes comments as hidden and installs onclick handlers to make
 * comments visible if their values are updated.
 */
function init_edit_comments(opt_parent) {
  var parent = opt_parent || document;
  var trs = parent.getElementsByTagName('tr');
  for (var i = 0; i < trs.length; i++) {
    var tr = trs[i];
    var classes = tr.className.split(' ');
    if (classes.length > 1) {
      var divs = tr.getElementsByTagName('div');
      var attribute_name = "";
      for (var div_index = 0; div_index < divs.length; div_index++) {
        var div = divs[div_index];
        if (div.className == "comment") {
          var closure = make_visible_closure(div);
          var elements = get_edit_elements(tr);
          for (var el_index = 0; el_index < elements.length; el_index++) {
            var element = elements[el_index];
            // Set onclick as well as onfocus for checkboxes, which don't
            // always register a focus event when clicked (eg when clicking on
            // the checkbox label)
            element.onfocus = closure;
            element.onclick = closure;
          }
        }
      }
    }
  }
}

/**
 * Returns the 'editable' elements (inputs, selects, textareas) with
 * the given ancestor.
 * @param {Element} ancestor - the ancestor
 * @return {Array} - editable elements
 */
function get_edit_elements(ancestor) {
  var elements = [];
  var element_index = 0;
  var inputs = ancestor.getElementsByTagName('input');
  for (var i = 0; i < inputs.length; i++) {
    elements[element_index++] = inputs[i];
  }
  var selects = ancestor.getElementsByTagName('select');
  for (var j = 0; j < selects.length; j++) {
    elements[element_index++] = selects[j];
  }
  var textareas = ancestor.getElementsByTagName('textarea');
  for (var k = 0; k < textareas.length; k++) {
    elements[element_index++] = textareas[k];
  }
  return elements;
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
 * Initializes event handlers for the page when not embedded on the main page.
 */
function init_edit(embed, edit_url, opt_parent) {
  if (embed) {
    $('save').onclick = function() {
      inplace_edit_save(edit_url);
    };
    $('cancel').onclick = inplace_edit_cancel;
    $('edit').onsubmit = function() {
      return false;
    };
    $('edit').onkeypress = function(e) {
      var event = e || window.event;
      if (event.keyCode == 13 &&
          e.target.nodeName.toLowerCase() != 'textarea') {
        $('save').onclick();          
      }
    };
  } else {
    $('save').onclick = save;
    $('cancel').onclick = cancel;
    $('edit').onsubmit = function() {
      if (button_click !== 'save') {
        return true;
      }
      return validate();
    };
  }
  init_edit_comments(opt_parent);
}
