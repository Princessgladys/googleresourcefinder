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
 */
function subscribe_on_off(element, subdomain, subject_name) {
  var on_off = element.innerHTML == "Subscribe";

  var post_data = "action=";
  post_data += on_off ? "subscribe" : "unsubscribe";
  post_data += "&subdomain=" + subdomain + "&subject_name=" +
      subdomain + ':' + subject_name;

  $j.ajax({
    type: "POST",
    url: "/subscribe",
    data: post_data,
    success: function(msg) {
      element.innerHTML = on_off ? "Unsubscribe" : "Subscribe";
    },
    error: function(xhr, text_status, error) {
      alert(locale.ERROR());
    }
  });
}

