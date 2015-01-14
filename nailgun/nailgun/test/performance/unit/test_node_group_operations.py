# -*- coding: utf-8 -*-
#    Copyright 2015 Mirantis, Inc.
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

import functools

from nailgun.test.base import EnvironmentManager
from nailgun.test.performance.base import BaseUnitLoadTestCase
from nailgun.test.performance.base import evaluate_unit_performance


class NodeGroupOperationsLoadTest(BaseUnitLoadTestCase):

    @classmethod
    def setUpClass(cls):
        super(NodeGroupOperationsLoadTest, cls).setUpClass()

        cls.env = EnvironmentManager(app=cls.app, session=cls.db)
        cls.env.upload_fixtures(cls.fixtures)
        cls.cluster = cls.env.create_cluster(
            api=False,
            net_provider='neutron',
            net_segment_type='gre'
        )
        cls.group = cls.env.create_node_group()

        cls.env.create_nodes(cls.NODES_NUM, cluster_id=cls.cluster['id'])

    @evaluate_unit_performance
    def test_node_group_collection_retrieve(self):
        func = functools.partial(
            self.get_handler,
            'NodeGroupCollectionHandler',
        )

        self.check_time_exec(func)

    @evaluate_unit_performance
    def test_node_group_collection_create(self):
        func = functools.partial(
            self.post_handler,
            'NodeGroupCollectionHandler',
            {
                'cluster_id': self.cluster.id,
                'name': 'test_group',
            }
        )

        self.check_time_exec(func)
