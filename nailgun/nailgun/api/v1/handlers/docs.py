# -*- coding: utf-8 -*-

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


from nailgun.api import swagger
from nailgun.api.v1.handlers.base import BaseHandler, content

import web


"""
Swagger docs handler.
"""


class DocsHandler(BaseHandler):
    def OPTIONS(self):
        self.cors_headers()

    @content
    def GET(self):
        self.cors_headers()

        s = swagger.Swagger()

        return s.get_spec()

    def cors_headers(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        web.header('Access-Control-Allow-Headers', 'X-Auth-Token')
