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

import mock

from nailgun import consts
from nailgun import objects
from nailgun.rpc import receiver
from nailgun.transactions import manager

from nailgun.test import base


class TestTransactionManager(base.BaseIntegrationTest):

    def setUp(self):
        super(TestTransactionManager, self).setUp()
        self.cluster = self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[
                {"status": consts.NODE_STATUSES.discover},
                {"status": consts.NODE_STATUSES.discover, "online": False},
            ],
            release_kwargs={
                'version': 'mitaka-9.0',
                'operating_system': consts.RELEASE_OS.ubuntu
            })
        objects.DeploymentGraph.create_for_model(
            {
                'tasks': [
                    {
                        'id': 'test_task',
                        'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
                        'roles': ['/.*/']
                    },
                    {
                        'id': 'test_task_2',
                        'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
                        'roles': ['/.*/']
                    },
                ],
                'name': 'test_graph',
            },
            instance=self.cluster,
            graph_type='test_graph')
        self.manager = manager.TransactionsManager(self.cluster.id)
        self.receiver = receiver.NailgunReceiver

    def _sucess(self, transaction_uuid):
        self.receiver.transaction_resp(
            task_uuid=transaction_uuid,
            nodes=[
                {'uid': n.uid, 'status': consts.NODE_STATUSES.ready}
                for n in self.cluster.nodes
            ],
            progress=100,
            status=consts.TASK_STATUSES.ready)

    def _fail(self, transaction_uuid):
        self.receiver.transaction_resp(
            task_uuid=transaction_uuid,
            nodes=[
                {'uid': n.uid, 'status': consts.NODE_STATUSES.error}
                for n in self.cluster.nodes
            ],
            progress=100,
            status=consts.TASK_STATUSES.error)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_graph(self, rpc_mock):
        task = self.manager.execute(graphs=[{"type": "test_graph"}])

        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        self._sucess(task.subtasks[0].uuid)
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_few_graphs(self, rpc_mock):
        objects.DeploymentGraph.create_for_model(
            {
                'tasks': [
                    {
                        'id': 'super-mega-other-task',
                        'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
                        'roles': ['/.*/']
                    },
                ],
                'name': 'test_graph_2',
            },
            instance=self.cluster,
            graph_type='test_graph_2')

        task = self.manager.execute(graphs=[
            {"type": "test_graph"},
            {"type": "test_graph_2"},
        ])

        self.assertItemsEqual(
            ["test_graph", "test_graph_2"],
            [sub.graph_type for sub in task.subtasks])

        # Only a message for the first graph should be sent, because
        # the second graph should be sent by RPC receiver once first
        # one is completed.
        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        # Consider we've got success from Astute.
        self._sucess(task.subtasks[0].uuid)

        # It's time to send the second graph to execution.
        rpc_mock.cast.assert_called_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[1].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'super-mega-other-task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        # Consider we've got success from Astute.
        self._sucess(task.subtasks[1].uuid)

        # Ensure the top leve transaction is ready.
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_few_graphs_first_fail(self, rpc_mock):
        objects.DeploymentGraph.create_for_model(
            {
                'tasks': [
                    {
                        'id': 'super-mega-other-task',
                        'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
                        'roles': ['/.*/']
                    },
                ],
                'name': 'test_graph_2',
            },
            instance=self.cluster,
            graph_type='test_graph_2')

        task = self.manager.execute(graphs=[
            {"type": "test_graph"},
            {"type": "test_graph_2"},
        ])

        self.assertItemsEqual(
            ["test_graph", "test_graph_2"],
            [sub.graph_type for sub in task.subtasks])

        # Only a message for the first graph should be sent, because
        # the second graph should be sent by RPC receiver once first
        # one is completed.
        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        self._fail(task.subtasks[0].uuid)

        self.assertEqual(rpc_mock.cast.call_count, 1)
        self.assertEqual(task.status, consts.TASK_STATUSES.error)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_w_task(self, rpc_mock):
        task = self.manager.execute(graphs=[
            {
                "type": "test_graph",
                "tasks": ["test_task"],
            }])

        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'skipped',
                                'fail_on_error': False,
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        self._sucess(task.subtasks[0].uuid)
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_w_non_existing_task(self, rpc_mock):
        task = self.manager.execute(graphs=[
            {
                "type": "test_graph",
                "tasks": ["non_exist"],
            }])

        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'skipped',
                                'fail_on_error': False,
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'skipped',
                                'fail_on_error': False,
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        self._sucess(task.subtasks[0].uuid)
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_dry_run(self, rpc_mock):
        task = self.manager.execute(
            graphs=[{"type": "test_graph"}], dry_run=True)

        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        self.cluster.nodes[0].uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': True,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }])

        self._sucess(task.subtasks[0].uuid)
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)

    @mock.patch('nailgun.transactions.manager.rpc')
    def test_execute_on_one_node(self, rpc_mock):
        node = self.env.create_node(
            cluster_id=self.cluster.id, pending_roles=["compute"])

        task = self.manager.execute(graphs=[
            {
                "type": "test_graph",
                "nodes": [node.id],
            }])

        rpc_mock.cast.assert_called_once_with(
            'naily',
            [{
                'args': {
                    'tasks_metadata': {'fault_tolerance_groups': []},
                    'task_uuid': task.subtasks[0].uuid,
                    'tasks_graph': {
                        None: [],
                        node.uid: [
                            {
                                'id': 'test_task',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            },
                            {
                                'id': 'test_task_2',
                                'type': 'puppet',
                                'fail_on_error': True,
                                'parameters': {'cwd': '/'}
                            }
                        ]
                    },
                    'tasks_directory': {},
                    'dry_run': False,
                },
                'respond_to': 'transaction_resp',
                'method': 'task_deploy',
                'api_version': '1'
            }]
        )

        self._sucess(task.subtasks[0].uuid)
        self.assertEqual(task.status, consts.TASK_STATUSES.ready)
