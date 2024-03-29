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

"""Storage for secrets and cryptographic operations."""

from google.appengine.ext import db
import hashlib
import hmac
import pickle
import random
import time

class Secret(db.Model):
    """An application-wide secret, identified by its key_name."""
    value = db.ByteStringProperty(required=True)


def sha1_hmac(key, bytes):
    """Computes a hexadecimal HMAC using the SHA1 digest algorithm."""
    return hmac.new(key, bytes, digestmod=hashlib.sha1).hexdigest()

def sha256_hmac(key, bytes):
    """Computes a hexadecimal HMAC using the SHA256 digest algorithm."""
    return hmac.new(key, bytes, digestmod=hashlib.sha256).hexdigest()

def generate_random_key():
    """Generates a random 32-byte key."""
    # The key is in hexadecimal because PubSubHubbub runs into Unicode
    # decoding problems with keys that contain non-7-bit characters.
    return ''.join('%02x' % random.randrange(256) for i in range(32))

def get_key(name):
    """Gets a secret key with the given name, or creates a new random key."""
    secret = Secret.get_by_key_name(name)
    if not secret:
        secret = Secret(key_name=name, value=generate_random_key())
        secret.put()
    return secret.value

def get_secret(name, default=''):
    """Gets the secret with the given name, or returns the default value."""
    secret = Secret.get_by_key_name(name)
    if secret:
        return secret.value
    return default

def sign(key_name, data, lifetime=None):
    """Produces a signature for the given data.  If 'lifetime' is specified,
    the signature expires in 'lifetime' seconds."""
    expiry = lifetime and int(time.time() + lifetime) or 0
    bytes = pickle.dumps((data, expiry))
    return sha256_hmac(get_key(key_name), bytes) + '.' + str(expiry)

def verify(key_name, data, signature):
    """Checks that a signature matches the given data and hasn't expired."""
    try:
        mac, expiry = signature.split('.', 1)
        expiry = int(expiry)
    except ValueError:
        return False
    if expiry == 0 or time.time() < expiry:
        bytes = pickle.dumps((data, expiry))
        return sha256_hmac(get_key(key_name), bytes) == mac
