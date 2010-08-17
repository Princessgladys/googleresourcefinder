// Copyright 2010 Google Inc. All Rights Reserved.

/**
 * @fileoverview Javascript convenience functions for bubble.py.
 * @author pfritzsche@google.com (Phil Fritzsche)
 */

/**
 * Subscribes or unsubscribes to a subject.
 * @param {HTMLAnchorElement} element the anchor element that was clicked
 * @param {boolean} subscribed true if subscribed, false if insubscribed
 * @param {string} subdomain the current subdomain
 * @param {string} subject_name the subject being [un/]subscribed to/from
 * @param {string} frequency the frequency to set the subscription to
 */
function subscribe_on_off(element, subscribed, subdomain, subject_name,
      frequency, settings_url) {
  var post_data = {
    action: subscribed ? "unsubscribe" : "subscribe",
    subdomain: subdomain,
    subject_name: subdomain + ":" + subject_name,
    frequency: frequency
  }

  $j.ajax({
    type: "POST",
    url: "/subscribe",
    data: post_data,
    success: function(msg) {
      element.innerHTML = !subscribed ? locale.UNSUBSCRIBE() :
          locale.SUBSCRIBE_TO_UPDATES();
      element.onclick = function onclick(event) {
        subscribe_on_off(element, !subscribed, subdomain, subject_name,
            frequency);
      };
      show_status(get_subscription_message(
          subscribed, subdomain, frequency, settings_url), 5000, true);
    },
    error: function(xhr, text_status, error) {
      log(text_status + ', ' + error);
      alert(locale.ERROR());
    }
  });
}

/**
 * Generates a message, specifying if the subject has been succesfully
 * subscribed to or unsubscribed from.
 * @param {boolean} subscribed true if subscribed, false if unsubscribed
 * @param {string} subdomain the current subdomain
 * @param {string} frequency the frequency to set the subscription to
 * @return {string} the message to display
 */
function get_subscription_message(subscribed, subdomain, frequency,
    settings_url) {
  var message = '';
  if (!subscribed) {
    message = locale.EMAIL_SUBSCRIPTION_SAVED({
      FREQUENCY: frequency,
      START_LINK: '<a href="' + settings_url +'">',
      END_LINK: '</a>'
    });
  } else {
    message = locale.UNSUBSCRIBED();
  }
  return message;
}

/**
 * Sends an AJAX request to /purge to purge the specified facility from the
 * database.
 * @param {string} subdomain the current subdomain
 * @param {string} subject_name the key name of the subject to be purged
 */
function purge_subject(subdomain, subject_name) {
  var confirmation_text = 'This will PERMANENTLY REMOVE this facility from ' +
      'the database. Are you sure you want to continue?';
  if (confirm(confirmation_text)) {
    var post_data = {
      subdomain: subdomain,
      subject_name: subject_name
    };

    $j.ajax({
      type: "POST",
      url: "/purge",
      data: post_data,
      success: function(response) {
        window.location.reload();
      },
      error: function(xhr, text_status, error) {
        log(text_status + ', ' + error);
        alert(locale.ERROR());
      }
    });
  }
}

