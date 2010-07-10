// Copyright 2010 Google Inc. All Rights Reserved.

/**
 * @fileoverview Handles the server-client functionality for the settings page. 
 * @author pfritzsche@google.com (Phil Fritzsche)
 */

/**
 * Sends AJAX command to change current account's default frequency.
 * @param {string} subdomain current subdomain
 * @param {HTMLSelectelemtn} frequency the select menu with the frequency
 *   options
 */
function change_default_frequency(subdomain, frequency) {
  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=change_default_frequency&" +
      "frequency=" + frequency.value,
    success: function(msg) {
      window.location.reload();
    }
  });
}

/**
 * Sends AJAX command to unsubscribe from all checked off subjects.
 * @param {string} subdomain current subdomain
 */
function unsubscribe_checked(subdomain) {
  var subjects = new Array();
  var boxes = document.getElementsByName('subject-checkboxes');
  for (i = 0; i < boxes.length; i++) {
    if (boxes[i].checked) {
      var subject = document.getElementById(boxes[i].value);
      subjects.push(subject.id);
    }
  }

  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=unsubscribe_multiple&" +
      "subjects=" + JSON.stringify(subjects),
    success: function(msg) {
      window.location.reload();
    }
  });
}

/**
 * Sets all checked off subjects to the account's default frequency.
 * @param {string} subdomain current subdomain
 * @param {string} default_frequency user's default frequency for updates
 */
function set_checked_to_default(subdomain, default_frequency) {
  var subjects = new Array();
  var boxes = document.getElementsByName('subject-checkboxes');
  for (i = 0; i < boxes.length; i++) {
    if (boxes[i].checked) {
      var subject = document.getElementById(boxes[i].value);
      var cells = subject.getElementsByTagName("input");
      for (j = 1; j < cells.length; j++) {
        if (cells[j].getAttribute('class'))
          var old_frequency = cells[j].getAttribute('class');
        if (cells[j].value == default_frequency)
          cells[j].checked = true;
      }
      subjects.push(new change_info(subject.id, old_frequency,
                                    default_frequency));
    }
  }

  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=change_subscriptions&" +
      "subject_changes=" + JSON.stringify(subjects)
  });
}

/**
 * Changes current user's preferred e-mail format setting.
 * @param {string} subdomain current subdomain
 * @param {string} email_format desired e-mail format
 */
function change_email_format(subdomain, email_format) {
  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=change_email_format&" +
      "email_format=" + email_format
  });
}

/**
 * Changes user's locale.
 * @param {string} subdomain current subdomain
 * @param {string} locale desired locale
 */
function change_locale(subdomain, locale) {
  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=change_locale&" +
      "locale=" + locale.value
  });
}

/**
 * Changes frequency of a subject.
 * @param {string} subdomain current subdomain
 * @param {string} subject_name key name of the subject to be changed
 * @param {string} old_frequency user's old frequency for this subscription
 * @param {string} new_frequencydesired frequency for the subscription
 */
function change_frequency(subdomain, subject_name, old_frequency,
                          new_frequency) {
  jQuery.ajax({
    type: "POST",
    url: "/subscribe",
    data: "subdomain=" + subdomain + "&action=change_subscription" +
      "&subject_name=" + subject_name + "&old_frequency=" + old_frequency +
      "&new_frequency=" + new_frequency
  });
}

/**
 * JS Object for holding change information pertaining to a particular
 * subscription.
 * @param {string} subject_name the subject this change is about
 * @param {string} old_frequency uesr's old frequency for this subscription
 * @param {string} new_frequency desired frequency for the subscription
 */
function change_info(subject_name, old_frequency, new_frequency) {
  this.subject_name = subject_name;
  this.old_frequency = old_frequency;
  this.new_frequency = new_frequency;
}

/**
 * Iterates through the check list of subjects to make sure they are all checked
 * or unchecked.
 */
function check_uncheck_all() {
  var all_box = document.getElementsByName('subjects-check-all')[0];
  var boxes = document.getElementsByName('subject-checkboxes');
  for (i = 0; i < boxes.length; i++) {
    boxes[i].checked = (all_box.checked == true);
  }
}

/**
 * Iterates through the check list of subjects. If they are all checked, it
 * checks the 'check all' box. If they are not all checked, it makes sure the
 * check all box is unchecked.
 */
function check_checkboxes() {
  var all_box = document.getElementsByName('subjects-check-all')[0];
  var boxes = document.getElementsByName('subject-checkboxes');
  var all_true = true;
  for (i = 0; i < boxes.length; i++) {
    if (boxes[i].checked == false) {
      all_box.checked = false;
      all_true = false;
    }
  }

  if (all_true) {
    all_box.checked = true;
  }
}

