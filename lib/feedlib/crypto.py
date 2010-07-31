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

"""Cryptographic operations.

The arguments to these functions refer to secret keys by name.  The actual keys
are stored in configuration settings and created as needed (see config.py)."""

import hashlib
import hmac
import pickle
import time

import config


def sha1_hmac(key_name, bytes):
    """Computes a hexadecimal HMAC using the SHA1 digest algorithm."""
    key = config.get_or_generate(key_name)
    return hmac.new(key, bytes, digestmod=hashlib.sha1).hexdigest()

def sha256_hmac(key_name, bytes):
    """Computes a hexadecimal HMAC using the SHA256 digest algorithm."""
    key = config.get_or_generate(key_name)
    return hmac.new(key, bytes, digestmod=hashlib.sha256).hexdigest()

def sign(key_name, data, lifetime=None):
    """Produces a signature for the given data.  If 'lifetime' is specified,
    the signature expires in 'lifetime' seconds."""
    expiry = lifetime and int(time.time() + lifetime) or 0
    bytes = pickle.dumps((data, expiry))
    return sha256_hmac(key_name, bytes) + '.' + str(expiry)

def verify(key_name, data, signature):
    """Checks that a signature matches the given data and hasn't expired."""
    try:
        mac, expiry = signature.split('.', 1)
        expiry = int(expiry)
    except ValueError:
        return False
    if expiry == 0 or time.time() < expiry:
        bytes = pickle.dumps((data, expiry))
        return sha256_hmac(key_name, bytes) == mac
