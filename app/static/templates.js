/*
# Copyright 2009-2010 by Ka-Ping Yee
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
 * @fileoverview An HTML-safe template substitution mechanism that maintains
 *     a type distinction between strings and "HTML objects" to help prevent
 *     cross-site scripting.  An HTML object is an object with a single
 *     'HTML' property containing HTML that is known to be safe, such as
 *     {HTML: '<em>fancy</em> words'}.  Always use to_html() to yield HTML
 *     that is safe to emit or set as innerHTML.
 * @author kpy@google.com (Ka-Ping Yee)
 */

/**
 * Constructs an HTML object with the given markup.
 * @param {string} markup - A string of HTML markup known to be safe.
 * @return {Object} - An HTML object containing the given markup.
 */
function HTML(markup) {
  return {'HTML': markup};
}

/**
 * Converts the given strings or HTML objects to an HTML string.  Any HTML that
 *     is emitted into the page (e.g. set as innerHTML) should be obtained from 
 *     a call to this function.  Strings are HTML-escaped; HTML objects have
 *     their content passed through as safe HTML; arrays are joined.
 * @param {string|number|Object|Array.<string|number|Object|Array>} content -
 *     A string, number, HTML object, or an array of such values.
 * @return {string} - A string of HTML.
 */
function to_html(content) {
  if (content.constructor === Array) {
    var markup = [];
    for (var i = 0; i < content.length; i++) {
      markup.push(to_html(content[i]));
    }
    return markup.join('');
  }
  var type = typeof content;
  var result = (type === 'object' && 'HTML' in content) ? content.HTML :
      type === 'number' ? content + '' :
      type === 'string' ? content.replace('&', '&amp;').replace('"', '&quot;').
                                  replace('<', '&lt;').replace('>', '&gt;') :
      '[TYPE ERROR]';
  return result;
}

/**
 * Renders a string, a string template as a string, or an HTML template as an
 *     HTML object.  See renderText and renderHtml for details.
 * @param {string|Object} template - A string, string template or HTML template.
 *     Null or empty strings will be rendered as en-dashes (U+2013).
 * @param {Object} opt_params - An object whose property values are substituted
 *     for placeholders in the template. If missing, the template is rendered
 *     as a string.
 * @return {string|Object} - The rendered string or HTML object.
 */
function render(template, opt_params) {
  if (!opt_params) {
    return (template || typeof(template) === 'number') ? template : '\u2013';
  }

  var result = (typeof template === 'object' && 'HTML' in template) ?
    render_html(template, opt_params) : render_text(template, opt_params);
  return result;
}

/**
 * Renders an HTML template obtained from a hidden element in the document.
 * @param {string} template_id - The ID of the element containing the template.
 * @param {Object} params - An object whose property values are substituted
 *     for placeholders in the template.
 * @return {Object} - The rendered HTML object.
 */
function render_template(template_id, params) {
  return render(HTML(document.getElementById(template_id).innerHTML), params);
}

/**
 * Substitutes parameters into the placeholders in a given string template,
 *     producing a plain string (NOT safe to emit directly in HTML).
 * @param {string} template - A template string containing placeholders of
 *     the form '${NAME}', where 'NAME' is a key in the 'params' object.
 *     The special placeholder '${$}' becomes '$'.
 * @param {string} params - An object whose property values are substituted
 *     for placeholders in the template string.  The values can be strings
 *     or numbers. Missing or null values will be rendered as en-dashes
 *     (U+2013).  Values of incorrect types will be rendered as '[TYPE ERROR]'.
 * @return {string} - The rendered text string (unrestricted plain text,
 *     NOT safe to emit directly in HTML).
 */
function render_text(template, params) {
  function get_param(match, name) {
    var param = params[name];
    var type = typeof param;
    return (name === '$') ? '$' :
        (type === 'undefined' || param === null) ? '\u2013' :
        (type === 'string' || type === 'number') ? param  + '' :
        '[TYPE ERROR]';
  }
  return template.replace(/\$\{(\w+)\}/g, get_param);
}

/**
 * Substitutes parameters into the placeholders in a given HTML template,
 *     producing an HTML object.
 * @param {Object} template - A template HTML object, whose 'HTML' property
 *     is a string containing placeholders of the form '${NAME}', where
 *     'NAME' is a key in the 'params' object.  The special placeholder
 *     '${$}' becomes '$'.
 * @param {string} params An object whose property values are substituted
 *     for placeholders in the template string.  The values can be strings,
 *     numbers, or HTML objects.  String values will be HTML-escaped;
 *     HTML objects will have their contents passed through as safe HTML.
 *     Missing or null values will be rendered as en-dashes (U+2013).
 *     Parameters of incorrect types will be rendered as '[TYPE ERROR]'.
 * @return {Object} An HTML object containing the rendered result (i.e.
 *     an object with a single 'HTML' property containing a string).
 */
function render_html(template, params) {
  function get_param(match, name) {
    var param = params[name];
    return (name === '$') ? '$' :
        (typeof param === 'undefined' || param === null) ? '\u2013' :
        to_html(param);
  }
  return {HTML: template.HTML.replace(/\$\{(\w+)\}/g, get_param)};
}
