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

import copy

import mock

from nailgun.api.v1.validators import ip_addr
from nailgun.errors import errors
from nailgun.test import base


class TestIpAddrValidator(base.BaseUnitTest):

    def setUp(self):
        super(TestIpAddrValidator, self).setUp()

        self.create_data = {
            'ip_addr': "192.168.0.15",
            'network': -1,
            'vip_name': 'test',
            'is_user_defined': True
        }
        self.cluster = mock.Mock()
        self.cluster.configure_mock(id=-1)

        self.ng = mock.Mock()
        self.ip_addr = mock.Mock()

        self.ng_object_patcher = mock.patch(
            'nailgun.api.v1.validators.ip_addr.objects.NetworkGroup'
            '.get_by_uid',
            new=mock.Mock(return_value=self.ng)
        )
        self.ip_addr_col_patcher = mock.patch(
            'nailgun.api.v1.validators.ip_addr.objects.IPAddrCollection'
            '.get_all_by_addr',
            new=mock.Mock(
                return_value=mock.Mock(
                    first=mock.Mock(return_value=self.ip_addr)
                )
            )
        )

        self.ng_object_patcher.start()
        self.ip_addr_col_patcher.start()

    def tearDown(self):
        self.ng_object_patcher.stop()
        self.ip_addr_col_patcher.stop()

        super(TestIpAddrValidator, self).tearDown()

    def test_schema_validation_fail(self):
        for field in self.create_data:
            data = copy.deepcopy(self.create_data)
            del data[field]

            self.assertRaises(
                errors.InvalidData,
                ip_addr.IPAddrValidator.validate_create,
                data,
                self.cluster
            )

    def test_network_not_belong_to_cluster_fail(self):
        self.ng.nodegroup.cluster_id = 0

        self.assertRaises(
            errors.CannotCreate,
            ip_addr.IPAddrValidator.validate_create,
            self.create_data,
            self.cluster
        )

    def test_ip_addr_intersection(self):
        self.ng.nodegroup.cluster_id = -1

        self.assertRaises(
            errors.CannotCreate,
            ip_addr.IPAddrValidator.validate_create,
            self.create_data,
            self.cluster
        )

    def test_validation_passed(self):
        self.ng.nodegroup.cluster_id = -1

        with mock.patch(
            'nailgun.api.v1.validators.ip_addr.objects.IPAddrCollection'
            '.get_all_by_addr',
            new=mock.Mock(
                return_value=mock.Mock(
                    first=mock.Mock(return_value=None)
                )
            )
        ):
            data = ip_addr.IPAddrValidator.validate_create(self.create_data,
                                                           self.cluster)
            self.assertEqual(self.create_data, data)
