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
      frequency) {
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
      show_status(get_subscription_message(subscribed, subdomain, frequency),
                  5000, true);
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
function get_subscription_message(subscribed, subdomain, frequency) {
  var message = '';
  if (!subscribed) {
    message = locale.EMAIL_SUBSCRIPTION_SAVED({
      FREQUENCY: frequency,
      START_LINK: '<a href="/settings?subdomain=' + subdomain +'">',
      END_LINK: '</a>'
    });
  } else {
    message = locale.UNSUBSCRIBED();
  }
  return message;
}

