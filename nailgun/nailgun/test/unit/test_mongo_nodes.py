#    Copyright 2014 Mirantis, Inc.
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

from nailgun.consts import TASK_NAMES
from nailgun.db.sqlalchemy.models import Task
from nailgun.errors import errors
from nailgun import objects
from nailgun.task.task import CheckBeforeDeploymentTask
from nailgun.test import base


class TestMongoNodes(base.BaseTestCase):

    def update_meta(self, ceilometer, mongo):
        attr_meta = self.env.get_default_attributes_metadata()
        attr_meta['editable']['additional_components'].update({
            "ceilometer": {"value": ceilometer},
            "mongo": {"value": mongo}
        })
        return attr_meta

    def test_get_zero_mongo_nodes(self):
        self.env.create(
            nodes_kwargs=[{}]
        )
        cluster = self.env.clusters[0]
        nodes = objects.Cluster.get_mongo_nodes(cluster)
        self.assertEqual(len(nodes), 0)

    def test_get_mongo_nodes(self):
        self.env.create(
            nodes_kwargs=[
                {'pending_roles': ['mongo'],
                 'status': 'discover',
                 'pending_addition': True},
                {'pending_roles': ['mongo'],
                 'status': 'ready',
                 'pending_addition': True}
            ]
        )
        cluster = self.env.clusters[1]
        nodes = objects.Cluster.get_mongo_nodes(cluster)
        self.assertEqual(len(nodes), 2)

    def test_mongo_node_with_ext_mongo(self):
        self.env.create(
            release_kwargs={
                'attributes_metadata': self.update_meta(True, True)},
            nodes_kwargs=[
                {'pending_roles': ['mongo'],
                 'status': 'discover',
                 'pending_addition': True}
            ]
        )
        cluster = self.env.clusters[0]
        task = Task(name=TASK_NAMES.deploy, cluster=cluster)
        self.assertRaises(errors.ExtMongoCheckerError,
                          CheckBeforeDeploymentTask._check_mongo_nodes,
                          task)

    def test_ext_mongo_without_mongo_node(self):
        self.env.create(
            release_kwargs={
                'attributes_metadata': self.update_meta(True, True)},
            nodes_kwargs=[]
        )
        cluster = self.env.clusters[1]
        task = Task(name=TASK_NAMES.deploy, cluster=cluster)
        self.assertIsNone(CheckBeforeDeploymentTask._check_mongo_nodes(task))

    def test_without_any_mongo(self):
        self.env.create(
            release_kwargs={
                'attributes_metadata': self.update_meta(True, False)},
            nodes_kwargs=[]
        )
        cluster = self.env.clusters[2]
        task = Task(name=TASK_NAMES.deploy, cluster=cluster)
        self.assertIsNone(CheckBeforeDeploymentTask._check_mongo_nodes(task))

    def test_mongo_node_without_ext_mongo(self):
        self.env.create(
            release_kwargs={
                'attributes_metadata': self.update_meta(True, False)},
            nodes_kwargs=[
                {'pending_roles': ['mongo'],
                 'status': 'discover',
                 'pending_addition': True}
            ]
        )
        cluster = self.env.clusters[3]
        task = Task(name=TASK_NAMES.deploy, cluster=cluster)
        self.assertIsNone(CheckBeforeDeploymentTask._check_mongo_nodes(task))
