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

from nailgun.db.sqlalchemy.models import Cluster
from nailgun.db.sqlalchemy.models import node
from nailgun.errors import errors
from nailgun.network.checker import NetworkCheck
from nailgun.task import helpers
from nailgun.test.base import BaseIntegrationTest

from mock import patch
from mock import MagicMock


class FakeTask(object):
    def __init__(self, cluster):
        self.cluster = cluster


class TestNetworkCheck(BaseIntegrationTest):

    def setUp(self):
        super(TestNetworkCheck, self).setUp()
        self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[
                {"api": True,
                 "pending_addition": True},
            ]
        )
        self.task = FakeTask(self.env.clusters[0])

    def test_expose_error_messages(self):
        self.fail('Not implemented')

    def test_check_untagged_intersection(self):
        self.fail('Not implemented')

    def test_check_network_address_spaces_intersection(self):
        self.fail('Not implemented')

    def test_check_public_floating_ranges_intersection(self):
        self.fail('Not implemented')

    def test_check_vlan_ids_range_and_intersection(self):
        self.fail('Not implemented')

    def test_check_networks_amount(self):
        self.fail('Not implemented')

    def test_neutron_check_segmentation_ids(self):
        self.fail('Not implemented')

    def test_neutron_check_network_address_spaces_intersection(self):
        self.fail('Not implemented')

    def test_neutron_check_l3_addresses_not_match_subnet_and_broadcast(self):
        self.fail('Not implemented')

    def test_check_network_classes_exclude_loopback(self):
        checker = NetworkCheck(self.task, {})
        checker.networks = [{'cidr': '192.168.0.0/24'}]
        self.assertNotRaises(errors.InvalidData,
                             checker.check_network_classes_exclude_loopback)

    @patch.object(helpers, 'db')
    def test_check_network_classes_exclude_loopback_fail(self, mocked_method):
        checker = NetworkCheck(self.task, {})
        networks = ['224.0.0.0/3', '127.0.0.0/8']
        for network in networks:
            checker.networks = [{'id': 1, 'cidr': network, 'name': 'fake'}]
            self.assertRaises(errors.NetworkCheckError,
                              checker.check_network_classes_exclude_loopback)
        self.assertEquals(mocked_method.call_count, 4)

    def test_check_network_addresses_not_match_subnet_and_broadcast(self):
        self.fail('Not implemented')

    def test_check_bond_slaves_speeds(self):
        cluster = self.env.create(
            nodes_kwargs=[
                {'roles': ['controller'], 'pending_addition': True}
            ]
        )
        cluster_db = self.db.query(Cluster).get(cluster['id'])

        checker = NetworkCheck(FakeTask(cluster_db), {})
        checker.check_bond_slaves_speeds()

        self.assertEquals(checker.err_msgs, [])
        bond_if1 = node.NodeBondInterface()
        bond_if2 = node.NodeBondInterface()

        nic1 = node.NodeNICInterface()
        nic2 = node.NodeNICInterface()
        nic3 = node.NodeNICInterface()
        nic1.current_speed = 100
        nic2.current_speed = 10
        nic3.current_speed = None
        bond_if1.slaves = [nic1, nic2, nic3]
        bond_if2.slaves = [nic3]
        checker.cluster.nodes[0].bond_interfaces = [bond_if1, bond_if2]

        checker.check_bond_slaves_speeds()
        self.assertEquals(len(checker.err_msgs), 2)

    def test_check_configuration_neutron(self):
        checker = NetworkCheck(self.task, {})
        checker.net_provider = 'neutron'
        checker.neutron_check_network_address_spaces_intersection = MagicMock()
        checker.neutron_check_segmentation_ids = MagicMock()
        checker.neutron_check_l3_addresses_not_match_subnet_and_broadcast = MagicMock()

        checker.check_public_floating_ranges_intersection = MagicMock()
        checker.check_network_address_spaces_intersection = MagicMock()
        checker.check_networks_amount = MagicMock()
        checker.check_vlan_ids_range_and_intersection = MagicMock()

        checker.check_network_classes_exclude_loopback = MagicMock()
        checker.check_network_addresses_not_match_subnet_and_broadcast = MagicMock()

        checker.check_configuration()

        not_called = [
            'check_public_floating_ranges_intersection',
            'check_network_address_spaces_intersection',
            'check_networks_amount',
            'check_vlan_ids_range_and_intersection'
        ]
        for method in not_called:
            mocked = getattr(checker, method)
            self.assertFalse(mocked.called)

        called = [
            'neutron_check_network_address_spaces_intersection',
            'neutron_check_segmentation_ids',
            'neutron_check_l3_addresses_not_match_subnet_and_broadcast',
            'check_network_classes_exclude_loopback',
            'check_network_addresses_not_match_subnet_and_broadcast'
        ]
        for method in called:
            mocked = getattr(checker, method)
            mocked.assert_any_call()

    def test_check_configuration_nova_network(self):
        checker = NetworkCheck(self.task, {})
        checker.net_provider = 'nova-network'
        checker.neutron_check_network_address_spaces_intersection = MagicMock()
        checker.neutron_check_segmentation_ids = MagicMock()
        checker.neutron_check_l3_addresses_not_match_subnet_and_broadcast = MagicMock()

        checker.check_public_floating_ranges_intersection = MagicMock()
        checker.check_network_address_spaces_intersection = MagicMock()
        checker.check_networks_amount = MagicMock()
        checker.check_vlan_ids_range_and_intersection = MagicMock()

        checker.check_network_classes_exclude_loopback = MagicMock()
        checker.check_network_addresses_not_match_subnet_and_broadcast = MagicMock()

        checker.check_configuration()

        not_called = [
            'neutron_check_network_address_spaces_intersection',
            'neutron_check_segmentation_ids',
            'neutron_check_l3_addresses_not_match_subnet_and_broadcast'
        ]
        for method in not_called:
            mocked = getattr(checker, method)
            self.assertFalse(mocked.called)

        called = [
            'check_public_floating_ranges_intersection',
            'check_network_address_spaces_intersection',
            'check_networks_amount',
            'check_vlan_ids_range_and_intersection',
            'check_network_classes_exclude_loopback',
            'check_network_addresses_not_match_subnet_and_broadcast'
        ]
        for method in called:
            mocked = getattr(checker, method)
            mocked.assert_any_call()

    @patch.object(NetworkCheck, 'check_untagged_intersection')
    @patch.object(NetworkCheck, 'check_bond_slaves_speeds')
    def test_check_interface_mapping(self, mock_untagged, mock_bond):
        checker = NetworkCheck(self.task, {})
        checker.check_interface_mapping()
        mock_untagged.assert_called_with()
        mock_bond.assert_called_with()


