## Publish-subscribe protocol ##

Resource Finder implements the [PubSubHubbub protocol](http://code.google.com/p/pubsubhubbub), both as a publisher and a subscriber.  This means that every edit is published on an outgoing Atom feed, and Resource Finder can also subscribe to other Atom feeds and process their entries as edits.  These are just ordinary Atom feeds with some small changes; the PubSubHubbub part enables subscribers to receive the new entries immediately without having to constantly

<br>
<h2>Receiving edits from Resource Finder</h2>

Every time a record is edited in Resource Finder, a new entry is published on the outgoing Atom feed at:<br>
<br>
<blockquote><code>https://</code><var>subdomain</var><code>.resource-finder.appspot.com/feeds/delta</code></blockquote>

Replace <var>subdomain</var> with the appropriate subdomain; for example, use <code>haiti.resource-finder.appspot.com</code> for the Haiti instance of Resource Finder.<br>
<br>
To receive immediate notification on every edit, subscribe to this feed using the PubSubHubbub protocol.<br>
<br>
<br>
<h2>Sending edits to Resource Finder</h2>

Resource Finder can subscribe to other Atom feeds and ingest their edits.  In order for you to send edits to Resource Finder, you publish an Atom feed, and the administrator of the Resource Finder instance has to configure Resource Finder to subscribe to your URL.  You can use any <code>https</code> URL to host your feed.<br>
<br>
<br>
<h2>Atom entry format</h2>

See below for an example of the XML format used in these feeds.  The same format is used for both outgoing and incoming edits.<br>
<br>
<pre><code>&lt;?xml version="1.0" encoding="utf-8"?&gt;<br>
&lt;feed xmlns="http://www.w3.org/2005/Atom"<br>
    xmlns:report="http://schemas.google.com/report/2010"<br>
    xmlns:gs="http://schemas.google.com/spreadsheets/2006"&gt;<br>
  &lt;entry&gt;<br>
    &lt;author&gt;<br>
&lt;!-- The author is specified as a mailto: or tel: URL.  For tel: URLs, use --&gt;<br>
&lt;!-- a globally unique number, including "+" and country code.             --&gt;<br>
      &lt;uri&gt;tel:+50912345678&lt;/uri&gt;<br>
    &lt;/author&gt;<br>
<br>
&lt;!-- Unique ID of the facility to be updated.  Haiti users should mostly   --&gt;<br>
&lt;!-- only deal with the numeric part, so the producer of this XML entry    --&gt;<br>
&lt;!-- will generally prepend "paho.org/HealthC_ID/" for transmission.       --&gt;<br>
    &lt;report:subject&gt;paho.org/HealthC_ID/1234567&lt;/report:subject&gt;<br>
<br>
&lt;!-- Always a complete RFC 3339 timestamp in UTC.                          --&gt;<br>
    &lt;report:observed&gt;2010-06-29T15:27:39Z&lt;/report:observed&gt;<br>
<br>
&lt;!-- Every entry has exactly one &lt;report:content&gt; element, which contains  --&gt;<br>
&lt;!-- exactly one &lt;report:row&gt; element, which contains the data fields.     --&gt;<br>
    &lt;report:content type="{http://schemas.google.com/report/2010}row"&gt;<br>
      &lt;report:row&gt;<br>
<br>
&lt;!-- All field values are specified with the &lt;gs:field&gt; tag.  Each field   --&gt;<br>
&lt;!-- can appear at most once, and all are optional.  Any field can be      --&gt;<br>
&lt;!-- present and empty, which indicates that this update should erase the  --&gt;<br>
&lt;!-- existing contents the field.  Field values are freeform strings       --&gt;<br>
&lt;!-- unless otherwise indicated in comments below.                         --&gt;<br>
<br>
        &lt;gs:field name="title"&gt;Title&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="alt_title"&gt;Alternate Title&lt;/gs:field&gt;<br>
<br>
&lt;!-- The value of "available_beds", if present, must be an integer.        --&gt;<br>
        &lt;gs:field name="available_beds"&gt;55&lt;/gs:field&gt;<br>
<br>
&lt;!-- The value of "total_beds", if present, must be an integer.            --&gt;<br>
        &lt;gs:field name="total_beds"&gt;66&lt;/gs:field&gt;<br>
<br>
&lt;!-- "services" contains zero or more values separated by commas.          --&gt;<br>
&lt;!-- Permitted values are:                                                 --&gt;<br>
&lt;!--     GENERAL_SURGERY                                                   --&gt;<br>
&lt;!--     ORTHOPEDICS                                                       --&gt;<br>
&lt;!--     NEUROSURGERY                                                      --&gt;<br>
&lt;!--     VASCULAR_SURGERY                                                  --&gt;<br>
&lt;!--     INTERNAL_MEDICINE                                                 --&gt;<br>
&lt;!--     CARDIOLOGY                                                        --&gt;<br>
&lt;!--     INFECTIOUS_DISEASE                                                --&gt;<br>
&lt;!--     PEDIATRICS                                                        --&gt;<br>
&lt;!--     POSTOPERATIVE_CARE                                                --&gt;<br>
&lt;!--     REHABILITATION                                                    --&gt;<br>
&lt;!--     OBSTETRICS_GYNECOLOGY                                             --&gt;<br>
&lt;!--     MENTAL_HEALTH                                                     --&gt;<br>
&lt;!--     DIALYSIS                                                          --&gt;<br>
&lt;!--     LAB                                                               --&gt;<br>
&lt;!--     X_RAY                                                             --&gt;<br>
&lt;!--     CT_SCAN                                                           --&gt;<br>
&lt;!--     BLOOD_BANK                                                        --&gt;<br>
&lt;!--     MORTUARY_SERVICES                                                 --&gt;<br>
        &lt;gs:field name="services"&gt;ORTHOPEDICS,CARDIOLOGY,X_RAY&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="contact_name"&gt;Name&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="phone"&gt;+12 345-678-90&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="email"&gt;user@example.com&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="department"&gt;Ouest&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="district"&gt;Léogâne&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="commune"&gt;Petit-Goâve&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="address"&gt;123 Example Street&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="location"&gt;18.3037,-72.8636&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="accuracy"&gt;Description of location accuracy.&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="organization"&gt;Example Organization&lt;/gs:field&gt;<br>
<br>
&lt;!-- "organization_type" contains one of these permitted values:           --&gt;<br>
&lt;!--     PUBLIC                                                            --&gt;<br>
&lt;!--     FOR_PROFIT                                                        --&gt;<br>
&lt;!--     UNIVERSITY                                                        --&gt;<br>
&lt;!--     COMMUNITY                                                         --&gt;<br>
&lt;!--     NGO                                                               --&gt;<br>
&lt;!--     FAITH_BASED                                                       --&gt;<br>
&lt;!--     MILITARY                                                          --&gt;<br>
&lt;!--     MIXED                                                             --&gt;<br>
        &lt;gs:field name="organization_type"&gt;PUBLIC&lt;/gs:field&gt;<br>
<br>
&lt;!-- "category" contains one of these permitted values:                    --&gt;<br>
&lt;!--     HOSPITAL                                                          --&gt;<br>
&lt;!--     CLINIC                                                            --&gt;<br>
&lt;!--     MOBILE_CLINIC                                                     --&gt;<br>
&lt;!--     DISPENSARY                                                        --&gt;<br>
        &lt;gs:field name="category"&gt;HOSPITAL&lt;/gs:field&gt;<br>
<br>
&lt;!-- "construction" contains one of these permitted values:                --&gt;<br>
&lt;!--     REINFORCED_CONCRETE                                               --&gt;<br>
&lt;!--     UNREINFORCED_MASONRY                                              --&gt;<br>
&lt;!--     WOOD_FRAME                                                        --&gt;<br>
&lt;!--     ADOBE                                                             --&gt;<br>
        &lt;gs:field name="construction"&gt;REINFORCED_CONCRETE&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="damage"&gt;Text describing building damage.&lt;/gs:field&gt;<br>
<br>
&lt;!-- "operational_status" contains one of these permitted values:          --&gt;<br>
&lt;!--     OPERATIONAL                                                       --&gt;<br>
&lt;!--     NO_SURGICAL_CAPACITY                                              --&gt;<br>
&lt;!--     FIELD_HOSPITAL                                                    --&gt;<br>
&lt;!--     FIELD_WITH_HOSPITAL                                               --&gt;<br>
&lt;!--     CLOSED_OR_CLOSING                                                 --&gt;<br>
&lt;!-- This field indicates the level of functionality.  "OPERATIONAL" means --&gt;<br>
&lt;!-- fully operational; "NO_SURGICAL_CAPACITY" means unable to perform     --&gt;<br>
&lt;!-- surgeries; "FIELD_HOSPITAL" means as functional as a field hospital;  --&gt;<br>
&lt;!-- "FIELD_WITH_HOSPITAL" means as functional as a field hospital that is --&gt;<br>
&lt;!-- co-located with a hospital; CLOSED_OR_CLOSING" means closed or in the --&gt;<br>
&lt;!-- process of closing.                                                   --&gt;<br>
        &lt;gs:field name="operational_status"&gt;OPERATIONAL&lt;/gs:field&gt;<br>
<br>
        &lt;gs:field name="comments"&gt;Arbitrary comment text goes here.&lt;/gs:field&gt;<br>
<br>
&lt;!-- "reachable_by_road" contains one of these permitted values:           --&gt;<br>
&lt;!--     TRUE                                                              --&gt;<br>
&lt;!--     FALSE                                                             --&gt;<br>
        &lt;gs:field name="reachable_by_road"&gt;TRUE&lt;/gs:field&gt;<br>
<br>
&lt;!-- "can_pick_up_patients" contains one of these permitted values:        --&gt;<br>
&lt;!--     TRUE                                                              --&gt;<br>
&lt;!--     FALSE                                                             --&gt;<br>
        &lt;gs:field name="can_pick_up_patients"&gt;FALSE&lt;/gs:field&gt;<br>
<br>
      &lt;/report:row&gt;<br>
    &lt;/report:content&gt;<br>
  &lt;/entry&gt;<br>
&lt;/feed&gt;<br>
</code></pre>