# coding: utf-8

# Copyright 2016 Mirantis, Inc.
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


import alembic
from copy import deepcopy
import datetime
from oslo_serialization import jsonutils


import sqlalchemy as sa

from nailgun.db import db
from nailgun.db import dropdb
from nailgun.db.migration import ALEMBIC_CONFIG
from nailgun.test import base


_prepare_revision = '3763c404ca48'
_test_revision = 'f2314e5d63c9'

ATTRIBUTES_METADATA = {
    'editable': {
        'common': {}
    }
}
SECURITY_GROUPS = {
    'value': 'iptables_hybrid',
    'values': [
        {
            'data': 'openvswitch',
            'label': 'Open vSwitch Firewall Driver',
            'description': 'Choose this type of firewall driver if you'
                           ' use OVS Brige for networking needs.'
        },
        {
            'data': 'iptables_hybrid',
            'label': 'Iptables-based Firewall Driver',
            'description': 'Choose this type of firewall driver if you'
                           ' use Linux Bridge for networking needs.'
        }
    ],
    'group': 'security',
    'weight': 20,
    'type': 'radio',
}

ROLES_META = {
    'controller': {
        'tags': [
            'controller',
            'rabbitmq',
            'database',
            'keystone',
            'neutron'
        ]
    }
}

PLUGIN_ROLE_META = {
    'test_plugin_role': {
        'tags': ['test_plugin_tag']
    }
}

PLUGIN_TAGS_META = {
    'test_plugin_tag':
        {'has_primary': False}
}

TAGS_META = {
    'controller': {
        'has_primary': True,
    },
    'rabbitmq': {
        'has_primary': True
    },
    'database': {
        'has_primary': True
    },
    'keystone': {
        'has_primary': True
    },
    'neutron': {
        'has_primary': True
    }
}


def setup_module():
    dropdb()
    alembic.command.upgrade(ALEMBIC_CONFIG, _prepare_revision)
    prepare()
    alembic.command.downgrade(ALEMBIC_CONFIG, _test_revision)


def prepare():
    meta = base.reflect_db_metadata()
    attrs_with_sec_group = deepcopy(ATTRIBUTES_METADATA)
    attrs_with_sec_group.setdefault('editable', {}).setdefault(
        'common', {}).setdefault('security_groups', SECURITY_GROUPS)
    plugin = {
        'name': 'Test_P',
        'version': '3.0.0',
        'title': 'Test Plugin',
        'package_version': '5.0.0',
        'roles_metadata': jsonutils.dumps(PLUGIN_ROLE_META),
        'tags_metadata': jsonutils.dumps(PLUGIN_TAGS_META)
    }
    result = db.execute(meta.tables['plugins'].insert(), [plugin])
    for release_name, env_version, cluster_name, attrs in zip(
            ('release_1', 'release_2', 'release_3'),
            ('mitaka-9.0', 'liberty-8.0', 'mitaka-9.0'),
            ('cluster_1', 'cluster_2', 'cluster_3'),
            (ATTRIBUTES_METADATA, ATTRIBUTES_METADATA, attrs_with_sec_group)
    ):
        release = {
            'name': release_name,
            'version': env_version,
            'operating_system': 'ubuntu',
            'state': 'available',
            'deployment_tasks': '[]',
            'roles_metadata': jsonutils.dumps(ROLES_META),
            'tags_matadata': jsonutils.dumps(TAGS_META),
            'is_deployable': True,
            'networks_metadata': '{}',
            'attributes_metadata': jsonutils.dumps(attrs)
        }
        result = db.execute(meta.tables['releases'].insert(), [release])
        release_id = result.inserted_primary_key[0]

        result = db.execute(
            meta.tables['clusters'].insert(),
            [{
                'name': cluster_name,
                'release_id': release_id,
                'mode': 'ha_compact',
                'status': 'new',
                'net_provider': 'neutron',
                'grouping': 'roles',
                'fuel_version': '9.0',
                'deployment_tasks': '[]',
                'roles_metadata': jsonutils.dumps(ROLES_META),
                'tags_metadata': '{}',
            }])

        cluster_id = result.inserted_primary_key[0]
        editable = attrs.get('editable', {})
        db.execute(
            meta.tables['attributes'].insert(),
            [{
                'cluster_id': cluster_id,
                'editable': jsonutils.dumps(editable)
            }]
        )

    db.execute(
        meta.tables['nodes'].insert(),
        [{
            'uuid': 'fcd49872-3917-4a18-98f9-3f5acfe3fdec',
            'cluster_id': cluster_id,
            'group_id': None,
            'status': 'ready',
            'roles': ['role_x', 'role_y'],
            'primary_tags': ['role_y', 'test'],
            'meta': '{}',
            'mac': 'bb:aa:aa:aa:aa:aa',
            'timestamp': datetime.datetime.utcnow(),
        }]
    )
    db.commit()


class TestAttributesDowngrade(base.BaseAlembicMigrationTest):

    def test_cluster_attributes_downgrade(self):
        clusters_attributes = self.meta.tables['attributes']
        results = db.execute(
            sa.select([clusters_attributes.c.editable]))
        for editable in results:
            editable = jsonutils.loads(editable[0])
            common = editable.setdefault('common', {})
            self.assertEqual(common.get('security_groups'), None)

    def test_release_attributes_downgrade(self):
        releases = self.meta.tables['releases']
        results = db.execute(
            sa.select([releases.c.attributes_metadata]))
        for attrs in results:
            attrs = jsonutils.loads(attrs[0])
            common = attrs.setdefault('editable', {}).setdefault('common', {})
            self.assertEqual(common.get('security_groups'), None)


class TestPluginTags(base.BaseAlembicMigrationTest):
    def test_primary_tags_downgrade(self):
        nodes = self.meta.tables['nodes']
        query = sa.select([nodes.c.primary_roles]).where(
            nodes.c.uuid == 'fcd49872-3917-4a18-98f9-3f5acfe3fdec')
        primary_roles = db.execute(query).fetchone()[0]
        self.assertItemsEqual(primary_roles, ['role_y'])

    def test_downgrade_tags_metadata(self):
        releases = self.meta.tables['releases']
        self.assertNotIn('tags_metadata', releases.c._all_columns)

        clusters = self.meta.tables['clusters']
        self.assertNotIn('tags_metadata', clusters.c._all_columns)
        self.assertNotIn('roles_metadata', clusters.c._all_columns)

        plugins = self.meta.tables['plugins']
        self.assertNotIn('tags_metadata', plugins.c._all_columns)

    def test_downgrade_field_tags_from_roles(self):
        releases = self.meta.tables['releases']
        query = sa.select([releases.c.roles_metadata])
        for role_meta in db.execute(query).fetchall():
            self.assertNotIn('tags', role_meta)

        plugins = self.meta.tables['plugins']
        query = sa.select([plugins.c.roles_metadata])
        for role_meta in db.execute(query):
            self.assertNotIn('tags', role_meta)
