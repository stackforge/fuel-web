#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import os

import yaml


class NailgunPlugin(object):
    __metaclass__ = abc.ABCMeta

    config = {}
    config_file = "config.yaml"

    def __init__(self):
        self.plugin_name = self.__module__.split(".")[0]
        from nailgun.plugins.storage import PluginStorage
        self.storage = PluginStorage(
            plugin_name=self.plugin_name
        )
        self._load_config()

    def _load_config(self):
        if os.access(self.config_file, os.R_OK):
            with open(self.config_file, "r") as conf:
                self.config.update(
                    yaml.load(conf.read())
                )
