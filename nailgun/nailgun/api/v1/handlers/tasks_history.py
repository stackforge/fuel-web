# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
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

from nailgun.api.v1.handlers import base
from nailgun.api.v1.handlers.base import content
from nailgun.api.v1.validators import tasks_history
from nailgun import objects


class TasksHistoryCollectionHandler(base.CollectionHandler):

    collection = objects.TasksHistoryCollection
    validator = tasks_history.TasksHistoryValidator

    @content
    def GET(self, task_deployment_id):
        """:returns: Collection of JSONized TasksHistory objects.

        :http: * 200 (OK)
               * 404 (cluster not found in db)
        """
        # TODO(vsharshov): add node and status filters
        self.get_object_or_404(objects.Task, task_deployment_id)
        return self.collection.to_json(
            self.collection.get_by_task_deployment_id(task_deployment_id)
        )
