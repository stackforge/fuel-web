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

import json
from netaddr import IPAddress
from netaddr import IPNetwork

from nailgun.api.models import NetworkGroup
from nailgun.test.base import BaseIntegrationTest
from nailgun.test.base import reverse


class TestNovaHandlers(BaseIntegrationTest):

    def setUp(self):
        super(TestNovaHandlers, self).setUp()
        self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[
                {"pending_addition": True},
            ]
        )
        self.cluster = self.env.clusters[0]
        resp = self.get_networks(self.cluster.id)
        self.nets = json.loads(resp.body)

    def get_networks(self, cluster_id, expect_errors=False):
        return self.app.get(
            reverse('NovaNetworkConfigurationHandler',
                    kwargs={'cluster_id': cluster_id}),
            headers=self.default_headers,
            expect_errors=expect_errors)

    def update_networks(self, cluster_id, networks, expect_errors=False):
        return self.app.put(
            reverse('NovaNetworkConfigurationHandler',
                    kwargs={'cluster_id': cluster_id}),
            json.dumps(networks),
            headers=self.default_headers,
            expect_errors=expect_errors)

    def find_net_by_name(self, name):
        for net in self.nets['networks']:
            if net['name'] == name:
                return net

    def test_network_checking(self):
        resp = self.update_networks(self.cluster.id, self.nets)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'ready')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')

        ngs_created = self.db.query(NetworkGroup).filter(
            NetworkGroup.name.in_([n['name'] for n in self.nets['networks']])
        ).all()
        self.assertEquals(len(ngs_created), len(self.nets['networks']))

    def test_network_checking_fails_if_admin_intersection(self):
        admin_ng = self.env.network_manager.get_admin_network_group()
        self.find_net_by_name('fixed')["cidr"] = admin_ng.cidr

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between networks: "
            "admin (PXE), fixed."
        )

    def test_network_checking_fails_if_admin_intersection_ip_range(self):
        admin_ng = self.env.network_manager.get_admin_network_group()
        cidr = IPNetwork(admin_ng.cidr)
        self.find_net_by_name('public')['ip_ranges'] = [
            [str(IPAddress(cidr.first)), str(IPAddress(cidr.last))]
        ]

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between networks: "
            "admin (PXE), public."
        )

    def test_network_checking_fails_if_amount_flatdhcp(self):
        net = self.find_net_by_name('management')
        net["amount"] = 2
        net["cidr"] = "10.10.0.0/23"

        resp = self.update_networks(self.cluster.id, {'networks': [net]},
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Network amount for 'management' is more than 1 "
            "while using FlatDHCP manager."
        )

    def test_fails_if_netmask_for_public_network_not_set_or_not_valid(self):
        net_without_netmask = self.find_net_by_name('public')
        net_with_invalid_netmask = self.find_net_by_name('public')

        net_without_netmask['netmask'] = None
        net_with_invalid_netmask['netmask'] = '255.255.255.2'

        for net in [net_without_netmask, net_with_invalid_netmask]:
            resp = self.update_networks(self.cluster.id, {'networks': [net]},
                                        expect_errors=True)
            self.assertEquals(resp.status, 202)
            task = json.loads(resp.body)
            self.assertEquals(task['status'], 'error')
            self.assertEquals(task['progress'], 100)
            self.assertEquals(task['name'], 'check_networks')
            self.assertEquals(
                task['message'], 'Invalid netmask for public network')

    def test_network_checking_fails_if_networks_cidr_intersection(self):
        self.find_net_by_name('management')["cidr"] = \
            self.find_net_by_name('storage')["cidr"]

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between "
            "networks: management, storage."
        )

    def test_network_checking_fails_if_networks_cidr_range_intersection(self):
        self.find_net_by_name('public')["ip_ranges"] = \
            [['192.18.17.65', '192.18.17.143']]
        self.find_net_by_name('management')["cidr"] = '192.18.17.0/25'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between "
            "networks: public, management."
        )

    def test_network_checking_no_public_floating_ranges_intersection(self):
        self.find_net_by_name('public')["ip_ranges"] = \
            [['192.18.17.5', '192.18.17.43'],
             ['192.18.17.59', '192.18.17.90']]
        self.find_net_by_name('floating')["ip_ranges"] = \
            [['192.18.17.125', '192.18.17.143'],
             ['192.18.17.159', '192.18.17.190']]

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'ready')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')

    def test_network_checking_fails_if_public_ranges_intersection(self):
        self.find_net_by_name('public')["ip_ranges"] = \
            [['192.18.17.65', '192.18.17.143'],
             ['192.18.17.129', '192.18.17.190']]

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between ranges of public network."
        )

    def test_network_checking_fails_if_floating_ranges_intersection(self):
        self.find_net_by_name('floating')["ip_ranges"] = \
            [['192.18.17.65', '192.18.17.143'],
             ['192.18.17.129', '192.18.17.190']]

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Address space intersection between ranges of floating network."
        )


class TestNeutronHandlersGre(BaseIntegrationTest):

    def setUp(self):
        super(TestNeutronHandlersGre, self).setUp()
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(meta, [{
            "mac": "00:00:00:00:00:66",
            "max_speed": 1000,
            "name": "eth0",
            "current_speed": 1000
        }, {
            "mac": "00:00:00:00:00:77",
            "max_speed": 1000,
            "name": "eth1",
            "current_speed": None}])
        self.env.create(
            cluster_kwargs={
                'net_provider': 'neutron',
                'net_segment_type': 'gre'
            },
            nodes_kwargs=[
                {
                    'api': True,
                    'roles': ['controller'],
                    'pending_addition': True,
                    'meta': meta,
                    'mac': "00:00:00:00:00:66"
                }
            ]
        )
        self.cluster = self.env.clusters[0]
        self.nets = self.env.generate_ui_neutron_networks(self.cluster.id)

    def update_networks(self, cluster_id, networks, expect_errors=False):
        return self.app.put(
            reverse('NeutronNetworkConfigurationHandler',
                    kwargs={'cluster_id': cluster_id}),
            json.dumps(networks),
            headers=self.default_headers,
            expect_errors=expect_errors)

    def test_network_checking(self):
        resp = self.update_networks(self.cluster.id, self.nets)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'ready')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        ngs_created = self.db.query(NetworkGroup).filter(
            NetworkGroup.name.in_([n['name'] for n in self.nets['networks']])
        ).all()
        self.assertEquals(len(ngs_created), len(self.nets['networks']))

    def test_network_checking_fails_if_network_is_at_admin_iface(self):
        node_db = self.env.nodes[0]
        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={
                'node_id': node_db.id
            }),
            headers=self.default_headers
        )
        ifaces = json.loads(resp.body)
        ifaces[1]["assigned_networks"], ifaces[0]["assigned_networks"] = \
            ifaces[0]["assigned_networks"], ifaces[1]["assigned_networks"]
        self.app.put(
            reverse('NodeCollectionNICsHandler', kwargs={
                'node_id': node_db.id
            }),
            json.dumps([{"interfaces": ifaces, "id": node_db.id}]),
            headers=self.default_headers
        )

        resp = self.app.put(
            reverse(
                'ClusterChangesHandler',
                kwargs={'cluster_id': self.cluster.id}),
            headers=self.default_headers
        )

        self.assertEquals(resp.status, 200)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'deploy')
        self.assertEquals(
            task['message'].find(
                "Some networks are "
                "assigned to the same physical interface as "
                "admin (PXE) network. You should move them to "
                "another physical interfaces:"),
            0
        )

    def test_network_checking_fails_if_admin_intersection(self):
        admin_ng = self.env.network_manager.get_admin_network_group()
        self.nets['networks'][-1]["cidr"] = admin_ng.cidr

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Intersection with admin "
            "network(s) '{0}' found".format(
                admin_ng.cidr
            )
        )

    def test_network_checking_fails_if_admin_intersection_ip_range(self):
        admin_ng = self.env.network_manager.get_admin_network_group()
        base = IPNetwork(admin_ng.cidr)
        base.prefixlen += 1
        start_range = str(base[0])
        end_range = str(base[-1])
        self.nets['networks'][1]['ip_ranges'] = [
            [start_range, end_range]
        ]

        resp = self.update_networks(
            self.cluster.id, self.nets, expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "IP range {0} - {1} in {2} network intersects with admin "
            "range of {3}".format(
                start_range, end_range,
                self.nets['networks'][1]['name'],
                admin_ng.cidr
            )
        )

    def test_network_checking_fails_if_untagged_intersection(self):
        for n in self.nets['networks']:
            n['vlan_start'] = None

        self.update_networks(self.cluster.id, self.nets)

        resp = self.app.put(
            reverse(
                'ClusterChangesHandler',
                kwargs={'cluster_id': self.cluster.id}),
            headers=self.default_headers
        )

        self.assertEquals(resp.status, 200)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'deploy')
        self.assertEquals(
            task['message'].find(
                "Some untagged networks are "
                "assigned to the same physical interface. "
                "You should assign them to "
                "different physical interfaces:"),
            0
        )

    def test_network_checking_fails_if_public_gateway_not_in_cidr(self):
        for n in self.nets['networks']:
            if n['name'] == 'public':
                n['gateway'] = '172.16.10.1'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Public gateway 172.16.10.1 is not in "
            "Public address space 172.16.1.0/24."
        )

    def test_network_checking_fails_if_public_float_range_not_in_cidr(self):
        for n in self.nets['networks']:
            if n['name'] == 'public':
                n['cidr'] = '172.16.10.0/24'
                n['gateway'] = '172.16.10.1'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Floating address range 172.16.1.131:172.16.1.254 is not in "
            "Public address space 172.16.10.0/24."
        )

    def test_network_checking_fails_if_network_ranges_intersect(self):
        for n in self.nets['networks']:
            if n['name'] == 'management':
                n['cidr'] = '192.168.1.0/24'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Intersection between network address spaces found:\n"
            "management, storage"
        )

    def test_network_checking_fails_if_internal_gateway_not_in_cidr(self):
        int = self.nets['neutron_parameters']['predefined_networks']['net04']
        int['L3']['gateway'] = '172.16.10.1'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Internal gateway 172.16.10.1 is not in "
            "Internal address space 192.168.111.0/24."
        )

    def test_network_checking_fails_if_internal_w_floating_intersection(self):
        int = self.nets['neutron_parameters']['predefined_networks']['net04']
        int['L3']['cidr'] = '172.16.1.128/26'
        int['L3']['gateway'] = '172.16.1.129'

        resp = self.update_networks(self.cluster.id, self.nets,
                                    expect_errors=True)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'],
            "Intersection between Internal CIDR and Floating range."
        )


class TestNeutronHandlersVlan(BaseIntegrationTest):

    def setUp(self):
        super(TestNeutronHandlersVlan, self).setUp()
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(meta, [{
            "mac": "00:00:00:00:00:66",
            "max_speed": 1000,
            "name": "eth0",
            "current_speed": 1000
        }, {
            "mac": "00:00:00:00:00:77",
            "max_speed": 1000,
            "name": "eth1",
            "current_speed": None
        }, {
            "mac": "00:00:00:00:00:88",
            "max_speed": 1000,
            "name": "eth2",
            "current_speed": None}])
        self.env.create(
            cluster_kwargs={
                'net_provider': 'neutron',
                'net_segment_type': 'vlan'
            },
            nodes_kwargs=[
                {
                    'api': True,
                    'roles': ['controller'],
                    'pending_addition': True,
                    'meta': meta,
                    'mac': "00:00:00:00:00:66"
                }
            ]
        )
        self.cluster = self.env.clusters[0]
        self.nets = self.env.generate_ui_neutron_networks(self.cluster.id)

    def update_networks(self, cluster_id, networks, expect_errors=False):
        return self.app.put(
            reverse('NeutronNetworkConfigurationHandler',
                    kwargs={'cluster_id': cluster_id}),
            json.dumps(networks),
            headers=self.default_headers,
            expect_errors=expect_errors)

    def test_network_checking(self):
        resp = self.update_networks(self.cluster.id, self.nets)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'ready')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        ngs_created = self.db.query(NetworkGroup).filter(
            NetworkGroup.name.in_([n['name'] for n in self.nets['networks']])
        ).all()
        self.assertEquals(len(ngs_created), len(self.nets['networks']))

    def test_network_checking_failed_if_private_paired_w_other_network(self):
        node_db = self.env.nodes[0]
        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={
                'node_id': node_db.id
            }),
            headers=self.default_headers
        )
        ifaces = json.loads(resp.body)
        priv_net = filter(
            lambda nic: (nic["name"] in ["private"]),
            ifaces[1]["assigned_networks"]
        )
        ifaces[1]["assigned_networks"].remove(priv_net[0])
        ifaces[2]["assigned_networks"].append(priv_net[0])
        self.app.put(
            reverse('NodeCollectionNICsHandler', kwargs={
                'node_id': node_db.id
            }),
            json.dumps([{"interfaces": ifaces, "id": node_db.id}]),
            headers=self.default_headers
        )

        resp = self.app.put(
            reverse(
                'ClusterChangesHandler',
                kwargs={'cluster_id': self.cluster.id}),
            headers=self.default_headers
        )

        self.assertEquals(resp.status, 200)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'deploy')
        self.assertEquals(
            task['message'].find(
                "Some networks are "
                "assigned to the same physical interface as "
                "private network. You should move them to "
                "another physical interfaces:"),
            0
        )

    def test_network_checking_failed_if_networks_tags_in_neutron_range(self):
        for n in self.nets['networks']:
            n['vlan_start'] += 1000

        resp = self.update_networks(self.cluster.id, self.nets)
        self.assertEquals(resp.status, 202)
        task = json.loads(resp.body)
        self.assertEquals(task['status'], 'error')
        self.assertEquals(task['progress'], 100)
        self.assertEquals(task['name'], 'check_networks')
        self.assertEquals(
            task['message'].find(
                "Networks VLAN tags are in "
                "ID range defined for Neutron L2. "
                "You should assign VLAN tags that are "
                "not in Neutron L2 VLAN ID range:"),
            0
        )
