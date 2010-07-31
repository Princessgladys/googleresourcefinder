# Copyright 2010 Google Inc.
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

"""An in-memory replacement for config.Config, to support unit testing."""

class FakeConfig:
    """An in-memory fake for the config.Config entity."""
    data = {}

    def __init__(self, key_name, value):
        self.key_name = key_name
        self.value = value

    def put(self):
        self.data[self.key_name] = self.value

    @classmethod
    def get_by_key_name(cls, key_name):
        if key_name in cls.data:
            return FakeConfig(key_name, cls.data[key_name])

    @classmethod
    def get_or_insert(cls, key_name, value):
        if key_name not in cls.data:
            cls.data[key_name] = value
        return FakeConfig(key_name, cls.data[key_name])


def use_fake_config(**kwargs):
    """Replace the real Config with a fake that contains the given settings."""
    import config
    config.Config = FakeConfig
    FakeConfig.data.update(kwargs)
