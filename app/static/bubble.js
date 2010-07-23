// Copyright 2010 Google Inc. All Rights Reserved.

/**
 * @fileoverview Javascript convenience functions for bubble.py.
 * @author pfritzsche@google.com (Phil Fritzsche)
 */

/**
 * Subscribes or unsubscribes to a subject.
 * {HTMLAnchorElement} element the anchor element that was clicked
 * {string} subdomain the current subdomain
 * {string} subject_name the subject being [un/]subscribed to/from
 * {string} frequency the frequency to set the subscription to
 */
function subscribe_on_off(element, subdomain, subject_name, frequency) {
  var subscribing = element.innerHTML == locale.SUBSCRIBE_TO_UPDATES();

  var post_data = "action=";
  post_data += subscribing ? "subscribe" : "unsubscribe";
  post_data += "&subdomain=" + subdomain + "&subject_name=" +
      subdomain + ':' + subject_name;

  $j.ajax({
    type: "POST",
    url: "/subscribe",
    data: post_data,
    success: function(msg) {
      display_saved_message(element, subscribing, subdomain, frequency);
    },
    error: function(xhr, text_status, error) {
      log(text_status + ', ' + error);
      alert(locale.ERROR());
    }
  });
}

/**
 * Displays a message on screen, specifying if the subject has been succesfully
 * subscribed to or unsubscribed from.
 * {HTMLDivElement} element the loading div element
 * {boolean} subscribing true if subscribing, false if unsubscribing
 * {string} subdomain the current subdomain
 * {string} frequency the frequency to set the subscription to
 */
function display_saved_message(element, subscribing, subdomain, frequency) {
  var message = '';
  if (subscribing) {
    message = locale.EMAIL_SUBSCRIPTION_SAVED({
      FREQUENCY: frequency,
      START_LINK: '<a href="/settings?subdomain=' + subdomain +'">',
      END_LINK: '</a>'
    });
  } else {
    message = locale.UNSUBSCRIBED();
  }

  element.innerHTML = subscribing ? locale.UNSUBSCRIBE() :
      locale.SUBSCRIBE_TO_UPDATES();
  show_status(message, 5000, true);
}

