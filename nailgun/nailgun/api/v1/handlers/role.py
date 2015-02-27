# -*- coding: utf-8 -*-

# Copyright 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from nailgun.api.v1.handlers import base
from nailgun import objects


class RoleHandler(base.SingleHandler):

    single = objects.Role

    def GET(self, obj_id):
        role = self.single.get_by_uid(obj_id)
        return self.single.to_json(role)

    def PUT(self, obj_id):
        role = self.single.get_by_uid(obj_id)
        role = self.single.update(role, self.checked_data())
        return self.single.to_json(role)

    def DELETE(self, obj_id):
        role = self.single.get_by_uid(obj_id)
        self.single.delete(role)


class RoleCollectionHandler(base.CollectionHandler):

    collection = objects.RoleCollection

    def GET(self):
        return self.collection.to_json(self.collection.all())

    def POST(self):

        role = self.single.create(self.checked_data())
        return self.single.to_json(role)
