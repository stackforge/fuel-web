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

from nailgun.db import db
from nailgun.db.sqlalchemy import models

from nailgun.objects import NailgunCollection
from nailgun.objects import NailgunObject
from nailgun.objects.serializers.tasks_history \
    import TasksHistorySerializer


class TasksHistory(NailgunObject):

    model = models.TasksHistory
    serializer = TasksHistorySerializer

    def update(cls, task_deployment_id, node_id, task_name, status, summary):
        q_task_history = cls.filter_by(
            None,
            task_deployment_id=task_deployment_id,
            task_name=task_name,
            node_id=node_id,
        )
        task_history = q_task_history.first()
        task_history.status = status
        task_history.summary = summary


class TasksHistoryCollection(NailgunCollection):

    single = TasksHistory

    @classmethod
    def create(cls, deployment_task_id, tasks_graph):
        for node_id in tasks_graph:
            for task in tasks_graph[node_id]:
                if not task.get('task_name'):
                    continue
                task_history = TasksHistory(
                    deployment_task_id=deployment_task_id,
                    node_id=node_id,
                    task_id=task['task_name'])
                db().add(task_history)
        db().flush()

    @classmethod
    def get_by_task_deployment_id(cls, task_deployment_id):
        if task_deployment_id == '':
            return cls.filter_by(None, task_deployment_id=None)
        return cls.filter_by(None, task_deployment_id=task_deployment_id)
