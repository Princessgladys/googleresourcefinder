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

"""Geographical functions.  All measurements are in metres."""

from math import asin, cos, pi, sin, sqrt

EARTH_RADIUS = 6371009

def hav(theta):
    """Computes the haversine of an angle given in radians."""
    return sin(theta/2)**2

def central_angle((phi_s, lam_s), (phi_f, lam_f)):
    """Returns the central angle between two points on a sphere, whose
    locations are given as (latitude, longitude) pairs in radians."""
    d_phi = phi_s - phi_f
    d_lam = lam_s - lam_f
    return 2*asin(sqrt(hav(d_phi) + cos(phi_s)*cos(phi_f)*hav(d_lam)))

def distance(start, finish):
    """Approximates the distance in metres between two points on the Earth,
    which are given as {'lat':y, 'lon':x} objects in degrees."""
    start_rad = (start['lat']*pi/180, start['lon']*pi/180)
    finish_rad = (finish['lat']*pi/180, finish['lon']*pi/180)
    return central_angle(start_rad, finish_rad)*EARTH_RADIUS
