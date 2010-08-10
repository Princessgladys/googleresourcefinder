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

# See http://maps.google.com/maps/ms?ie=UTF8&t=h&hl=en&oe=UTF8&msa=0&msid=113976783681342652369.00048d55478bd638daa53
PAKISTAN_FLOOD_POLYGON = [(71.441345, 34.696461),
                          (71.908264, 34.903954),
                          (72.15271, 35.012001),
                          (72.704773, 35.038994),
                          (73.070068, 34.243595),
                          (73.262329, 33.78828),
                          (73.385925, 33.447487),
                          (72.806396, 31.807562),
                          (72.605896, 31.208103),
                          (72.522812, 30.968485),
                          (72.496719, 30.926968),
                          (72.441101, 30.824423),
                          (71.963196, 29.859701),
                          (71.8396, 29.293585),
                          (71.210632, 28.856703),
                          (70.990906, 28.562813),
                          (70.62561, 28.335814),
                          (70.048828, 27.797779),
                          (69.450073, 27.483908),
                          (69.252319, 27.088472),
                          (68.738708, 26.674459),
                          (68.862305, 26.041977),
                          (68.826599, 25.512699),
                          (68.834839, 25.371328),
                          (68.832092, 25.19997),
                          (68.664551, 24.926294),
                          (67.752686, 23.574057),
                          (66.401367, 24.901384),
                          (66.434326, 25.015928),
                          (66.873779, 25.212397),
                          (67.06604, 25.316717),
                          (67.392883, 25.435835),
                          (67.810364, 25.787527),
                          (67.428589, 26.470573),
                          (67.464294, 27.520451),
                          (67.549438, 28.144661),
                          (68.288269, 28.410728),
                          (68.491516, 28.502487),
                          (69.016113, 28.668901),
                          (69.862061, 29.05617),
                          (69.897766, 29.501768),
                          (70.090027, 31.043522),
                          (70.180664, 31.784218),
                          (70.219116, 32.143059),
                          (70.334473, 32.500496),
                          (70.489998, 33.023922),
                          (70.993652, 33.623768),
                          (71.441345, 34.696461)]

# See http://en.wikipedia.org/wiki/Administrative_units_of_Pakistan
PAKISTAN_ADMIN_AREAS = ['Balochistan', 'Khyber Pakhtunkhwa',
                        'North West Frontier', 'Punjab', 'Sindh',
                        'Islamabad Capital Territory',
                        'Federally Administered Tribal Areas',
                        'Azad Jammu and Kashmir', 'Gilgit-Baltistan']

# See http://en.wikipedia.org/wiki/Districts_of_Pakistan
PAKISTAN_DISTRICTS = [ 'Islamabad', 'Attock', 'Bahawalnagar', 'Bahawalpur',
                       'Bhakkar', 'Chakwal', 'Chiniot', 'Dera Ghazi Khan',
                       'Faisalabad', 'Gujranwala', 'Gujrat', 'Hafizabad',
                       'Jhang', 'Jhelum', 'Kasur', 'Khanewal', 'Khushab',
                       'Lahore', 'Layyah', 'Lodhran', 'Mandi Bahauddin',
                       'Mianwali', 'Multan', 'Muzaffargarh', 'Narowal',
                       'Nankana Sahib', 'Okara', 'Pakpattan',
                       'Rahim Yar Khan', 'Rajanpur', 'Rawalpindi',
                       'Sahiwal', 'Sargodha', 'Sheikhupura', 'Sialkot',
                       'Toba Tek Singh', 'Vehari', 'Badin', 'Dadu',
                       'Ghotki', 'Hyderabad', 'Jacobabad', 'Jamshoro',
                       'Karachi', 'Kashmore', 'Khairpur', 'Larkana',
                       'Matiari', 'Mirpurkhas', 'Naushahro Firoz',
                       'Nawabshah', 'Qamber and Shahdad Kot', 'Sanghar',
                       'Shikarpur', 'Sukkur', 'Tando Allahyar',
                       'Tando Muhammad Khan', 'Tharparkar', 'Thatta',
                       'Umerkot', 'Abbottabad', 'Bannu', 'Batagram',
                       'Buner', 'Charsadda', 'Chitral', 'Dera Ismail Khan',
                       'Hangu', 'Haripur', 'Karak', 'Kohat', 'Kohistan',
                       'Lakki Marwat', 'Lower Dir', 'Malakand', 'Mansehra',
                       'Mardan', 'Nowshera', 'Peshawar', 'Shangla', 'Swabi',
                       'Swat', 'Tank', 'Upper Dir', 'Ghanche', 'Skardu',
                       'Astore', 'Diamer', 'Ghizer', 'Gilgit',
                       'Hunza-Nagar District', 'Awaran', 'Barkhan', 'Bolan',
                       'Chagai[7]', 'Dera Bugti', 'Gwadar', 'Harnai',
                       'Jafarabad', 'Jhal Magsi', 'Kalat', 'Kech (Turbat)',
                       'Kharan', 'Khuzdar', 'Kohlu', 'Lasbela', 'Loralai',
                       'Mastung', 'Musakhel', 'Naseerabad', 'Nushki',
                       'Panjgur', 'Pishin', 'Qilla Abdullah',
                       'Qilla Saifullah', 'Quetta', 'Sherani', 'Sibi',
                       'Washuk', 'Zhob', 'Ziarat', 'Bajaur', 'Khyber',
                       'Kurram', 'Mohmand', 'North Waziristan', 'Orakzai',
                       'South Waziristan', 'Bhimber', 'Kotli', 'Mirpur',
                       'Bagh', 'Poonch', 'Sudhnati', 'Muzaffarabad', 'Neelum' ]

# Districts that have facilities both inside and outside FLOOD_POLYGON
PAKISTAN_FLOOD_BORDER_DISTRICTS = ['Toba Tek Singh', 'Abbottabad', 'Jamshoro',
                                   'Jhelum', 'Sargodha', 'Rawalpindi',
                                   'Bahawalpur', 'Jhang', 'Vehari', 'Khanewal']
