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

import copy

from oslo_serialization import jsonutils

from nailgun.db.sqlalchemy.models import Node
from nailgun.db.sqlalchemy.models import NodeNICInterface
from nailgun.db.sqlalchemy.models import Notification
from nailgun.settings import settings
from nailgun.test.base import BaseIntegrationTest
from nailgun.utils import reverse


class TestHandlers(BaseIntegrationTest):
    def test_node_list_empty(self):
        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual([], resp.json_body)

    def test_notification_node_id(self):
        node = self.env.create_node(
            api=True,
            meta=self.env.default_metadata()
        )
        notif = self.db.query(Notification).first()
        self.assertEqual(node['id'], notif.node_id)
        resp = self.app.get(
            reverse('NotificationCollectionHandler'),
            headers=self.default_headers
        )
        notif_api = resp.json_body[0]
        self.assertEqual(node['id'], notif_api['node_id'])

    def test_node_get_with_cluster(self):
        self.env.create(
            cluster_kwargs={"api": True},
            nodes_kwargs=[
                {"cluster_id": None},
                {},
            ]
        )
        cluster = self.env.clusters[0]

        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            params={'cluster_id': cluster.id},
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(resp.json_body))
        self.assertEqual(
            self.env.nodes[1].id,
            resp.json_body[0]['id']
        )

    def test_node_get_with_cluster_None(self):
        self.env.create(
            cluster_kwargs={"api": True},
            nodes_kwargs=[
                {"cluster_id": None},
                {},
            ]
        )

        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            params={'cluster_id': ''},
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(resp.json_body))
        self.assertEqual(self.env.nodes[0].id, resp.json_body[0]['id'])

    def test_node_get_without_cluster_specification(self):
        self.env.create(
            cluster_kwargs={"api": True},
            nodes_kwargs=[
                {"cluster_id": None},
                {},
            ]
        )

        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual(2, len(resp.json_body))

    def test_node_get_with_cluster_and_assigned_ip_addrs(self):
        self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[
                {"pending_addition": True, "api": True},
                {"pending_addition": True, "api": True}
            ]
        )

        self.env.network_manager.assign_ips(
            self.env.clusters[-1],
            self.env.nodes,
            "management"
        )

        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            headers=self.default_headers
        )

        self.assertEqual(200, resp.status_code)
        self.assertEqual(2, len(resp.json_body))

    def test_node_creation(self):
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps({'mac': self.env.generate_random_mac(),
                             'meta': self.env.default_metadata(),
                             'status': 'discover'}),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual('discover', resp.json_body['status'])

    def test_node_update(self):
        node = self.env.create_node(api=False)
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'mac': node.mac, 'manufacturer': 'new'}]),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)
        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            headers=self.default_headers
        )
        node = self.db.query(Node).get(node.id)
        self.assertEqual('new', node.manufacturer)

    def test_node_update_empty_mac_or_id(self):
        node = self.env.create_node(api=False)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'manufacturer': 'man0'}]),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json_body["message"],
            "Neither MAC nor ID is specified"
        )

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'id': node.id,
                              'mac': None,
                              'manufacturer': 'man4'}]),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(
            "schema['properties']['mac']",
            resp.json_body["message"]
        )
        self.assertIn(
            "None is not of type 'string'",
            resp.json_body["message"]
        )

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'mac': node.mac,
                              'manufacturer': 'man5'}]),
            headers=self.default_headers
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'id': node.id,
                              'manufacturer': 'man6'}]),
            headers=self.default_headers
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'mac': node.mac,
                              'manufacturer': 'man7'}]),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'id': node.id,
                              'mac': node.mac,
                              'manufacturer': 'man8'}]),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)

    def node_update_with_invalid_id(self):
        node = self.env.create_node(api=False)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'id': 'new_id',
                              'mac': node.mac}]),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json_body["message"],
            "Invalid ID specified"
        )

    def test_node_update_agent_discover(self):
        self.env.create_node(
            api=False,
            status='provisioning',
            meta=self.env.default_metadata()
        )
        node_db = self.env.nodes[0]
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps(
                {'mac': node_db.mac,
                 'status': 'discover', 'manufacturer': 'new'}
            ),
            headers=self.default_headers
        )
        self.assertEqual(resp.status_code, 200)
        resp = self.app.get(
            reverse('NodeCollectionHandler'),
            headers=self.default_headers
        )
        node_db = self.db.query(Node).get(node_db.id)
        self.assertEqual('new', node_db.manufacturer)
        self.assertEqual('provisioning', node_db.status)

    def test_stopped_node_network_update_restricted_for_agent(self):
        node = self.env.create_node(
            api=False,
            status='stopped',
            meta=self.env.default_metadata()
        )
        node_db = self.env.nodes[0]
        interfaces = node.meta['interfaces']
        new_interfaces = copy.deepcopy(interfaces)
        new_interfaces[1]['mac'] = '2a:00:0d:0d:00:2a'
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps(
                {
                    'mac': node_db.mac,
                    'meta': {
                        'interfaces': new_interfaces
                    }
                }
            ),
            headers=self.default_headers
        )
        self.assertEqual(resp.status_code, 200)
        node_db = self.db.query(Node).get(node_db.id)
        interface_db = self.db.query(NodeNICInterface).filter_by(
            node_id=node_db.id,
            name=new_interfaces[1]['name']
        ).first()

        self.assertNotEqual(
            interface_db.mac,
            '2a:00:0d:0d:00:2a')

    def test_stopped_node_network_update_allowed_for_ui(self):
        node = self.env.create_node(
            api=False,
            status='stopped',
            meta=self.env.default_metadata()
        )
        node_db = self.env.nodes[0]
        interfaces = node.meta['interfaces']
        new_interfaces = copy.deepcopy(interfaces)
        new_interfaces[1]['mac'] = '2a:00:0d:0d:00:2a'
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([
                {
                    'mac': node_db.mac,
                    'meta': {
                        'interfaces': new_interfaces
                    }
                }
            ]),
            headers=self.default_headers
        )
        self.assertEqual(resp.status_code, 200)
        interface_db = self.db.query(NodeNICInterface).filter_by(
            node_id=node_db.id,
            name=new_interfaces[1]['name']
        ).first()

        self.assertEqual(
            interface_db.mac,
            '2a:00:0d:0d:00:2a')

    def test_node_timestamp_updated_only_by_agent(self):
        node = self.env.create_node(api=False)
        timestamp = node.timestamp
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([
                {'mac': node.mac, 'status': 'discover',
                 'manufacturer': 'old'}
            ]),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)
        node = self.db.query(Node).get(node.id)
        self.assertEqual(node.timestamp, timestamp)

        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps(
                {'mac': node.mac, 'status': 'discover',
                 'manufacturer': 'new'}
            ),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)
        node = self.db.query(Node).get(node.id)
        self.assertNotEqual(node.timestamp, timestamp)
        self.assertEqual('new', node.manufacturer)

    def test_agent_caching(self):
        node = self.env.create_node(api=False)
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({
                'mac': node.mac,
                'manufacturer': 'new',
                'agent_checksum': 'test'
            }),
            headers=self.default_headers)
        response = resp.json_body
        self.assertEqual(resp.status_code, 200)
        self.assertFalse('cached' in response and response['cached'])
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({
                'mac': node.mac,
                'manufacturer': 'new',
                'agent_checksum': 'test'
            }),
            headers=self.default_headers)
        response = resp.json_body
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('cached' in response and response['cached'])

    def test_agent_updates_node_by_interfaces(self):
        node = self.env.create_node(api=False)
        interface = node.meta['interfaces'][0]
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({
                'mac': '00:00:00:00:00:00',
                'meta': {
                    'interfaces': [interface]},
            }),
            headers=self.default_headers)

        self.assertEqual(resp.status_code, 200)

    def test_agent_node_create_and_update_with_non_unique_macs_in_meta(self):
        meta = self.env.default_metadata()
        uniq_mac1 = 'de:ad:be:ef:00:01'
        uniq_mac2 = 'de:ad:be:ef:00:02'
        uniq_mac3 = 'de:ad:be:ef:00:03'
        uniq_mac4 = 'de:ad:be:ef:00:04'
        # this test requires at least 2 interface structures in meta
        self.assertEqual(len(meta['interfaces']) >= 2, True)
        # we need only 2 interfaces for this test
        meta['interfaces'] = meta['interfaces'][:2]
        # the first interface will have a unique mac
        meta['interfaces'][0]['mac'] = uniq_mac1
        # the second will have a non-unique mac from settings
        meta['interfaces'][1]['mac'] = settings.NON_UNIQUE_MACS[0]
        # create a node with one unique and one non-unique mac
        node = self.env.create_node(api=False, meta=meta)

        # fail to create another node with the same unique mac in meta
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps({'mac': uniq_mac1,
                             'meta': meta,
                             'status': 'discover'}),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 409)

        # create another node with a new unique and the same non-unique mac
        meta['interfaces'][0]['mac'] = uniq_mac2
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps({'mac': uniq_mac2,
                             'meta': meta,
                             'status': 'discover'}),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 201)

        # update a node by incorrect mac and meta with a correct unique mac
        meta['interfaces'][0]['mac'] = uniq_mac1
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({'mac': uniq_mac3,
                             'meta': meta,
                             'manufacturer': 'man1'}),
            headers=self.default_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json_body['id'], node.id)

        # fail to update a node by incorrect mac and meta with a correct but
        # non-unique mac
        meta['interfaces'].pop(0)
        resp = self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({'mac': uniq_mac4,
                             'meta': meta,
                             'manufacturer': 'man2'}),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 400)

    def test_node_create_ip_not_in_admin_range(self):
        node = self.env.create_node(api=False)

        # Set IP outside of admin network range on eth1
        meta = copy.deepcopy(node.meta)
        meta['interfaces'][1]['ip'] = '10.21.0.3'

        self.app.put(
            reverse('NodeAgentHandler'),
            jsonutils.dumps({
                'mac': node.mac,
                'meta': meta,
            }),
            headers=self.default_headers)

        self.env.network_manager.update_interfaces_info(node)

        # node.mac == eth0 mac so eth0 should now be admin interface
        admin_iface = self.env.network_manager.get_admin_interface(node)

        self.assertEqual(admin_iface.name, 'eth0')

    def test_node_create_ext_mac(self):
        node1 = self.env.create_node(
            api=False
        )
        node2_json = {
            "mac": self.env.generate_random_mac(),
            "meta": self.env.default_metadata(),
            "status": "discover"
        }
        node2_json["meta"]["interfaces"][0]["mac"] = node1.mac
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps(node2_json),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 409)

    def test_node_create_without_mac(self):
        node = self.env.create_node(
            api=True,
            exclude=["mac"],
            expect_http=400,
            expected_error="No mac address specified"
        )
        self.assertEqual(node, None)

    def test_node_create_with_invalid_disk_model(self):
        meta = self.env.default_metadata()
        meta['disks'][0]['model'] = None

        node = self.env.create_node(
            api=True,
            expect_http=201,
            meta=meta
        )
        self.assertIsNotNone(node)

    def test_node_create_mac_validation(self):
        # entry format: (mac_address, http_response_code)
        maccaddresses = (
            # invalid macaddresses
            ('60a44c3528ff', 400),
            ('60:a4:4c:35:28', 400),
            ('60:a4:4c:35:28:fg', 400),
            ('76:DC:7C:CA:G4:75', 400),
            ('76-DC-7C-CA-G4-75', 400),

            # valid macaddresses
            ('60:a4:4c:35:28:ff', 201),
            ('48-2C-6A-1E-59-3D', 201),
        )

        for mac, http_code in maccaddresses:
            response = self.app.post(
                reverse('NodeCollectionHandler'),
                jsonutils.dumps({
                    'mac': mac,
                    'status': 'discover',
                }),
                headers=self.default_headers,
                expect_errors=(http_code != 201)
            )
            self.assertEqual(response.status_code, http_code)

    def test_node_update_ext_mac(self):
        meta = self.env.default_metadata()
        node1 = self.env.create_node(
            api=False,
            mac=meta["interfaces"][0]["mac"],
            meta={}
        )
        node1_json = {
            "mac": self.env.generate_random_mac(),
            "meta": meta
        }
        # We want to be sure that new mac is not equal to old one
        self.assertNotEqual(node1.mac, node1_json["mac"])

        # Here we are trying to update node
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([node1_json]),
            headers=self.default_headers,
            expect_errors=True
        )
        self.assertEqual(resp.status_code, 200)

        # Here we are checking if node mac is successfully updated
        self.assertEqual(node1_json["mac"], resp.json_body[0]["mac"])
        self.assertEqual(meta, resp.json_body[0]["meta"])

    def test_duplicated_node_create_fails(self):
        node = self.env.create_node(api=False)
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps({'mac': node.mac, 'status': 'discover'}),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(409, resp.status_code)

    def test_node_creation_fail(self):
        resp = self.app.post(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps({'mac': self.env.generate_random_mac(),
                             'meta': self.env.default_metadata(),
                             'status': 'error'}),
            headers=self.default_headers,
            expect_errors=True)
        self.assertEqual(resp.status_code, 403)

    def test_reset_cluster_name_when_unassign_node(self):
        node_name = 'new_node_name'
        self.env.create(
            nodes_kwargs=[
                {'pending_roles': ['controller'],
                 'pending_addition': True,
                 'name': node_name}])

        node = self.env.nodes[0]

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            jsonutils.dumps([{'id': node.id,
                              'cluster_id': None,
                              'pending_roles': []}]),
            headers=self.default_headers)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(resp.json_body))
        self.assertEqual(node.id, resp.json_body[0]['id'])
        self.assertEqual(node.name, node_name)
        self.assertEqual(node.cluster, None)
        self.assertEqual(node.pending_roles, [])

    def test_discovered_node_unified_name(self):
        node_mac = self.env.generate_random_mac()

        def node_name_test(mac):
            self.env.create_node(
                api=True,
                **{'mac': mac}
            )

            node = self.app.get(reverse('NodeCollectionHandler')).json_body[0]
            self.assertEqual(node['name'],
                             'Untitled ({0})'.format(node_mac[-5:]))

        node_name_test(node_mac.upper())

        node_id = self.app.get(
            reverse('NodeCollectionHandler')
        ).json_body[0]['id']

        self.app.delete(
            reverse('NodeHandler', {'obj_id': node_id})
        )

        node_name_test(node_mac.lower())
