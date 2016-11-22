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

"""Fuel 9.2

Revision ID: 3763c404ca48
Revises: f2314e5d63c9
Create Date: 2016-10-11 16:33:57.247855

"""

from alembic import op
from oslo_serialization import jsonutils
import six

import sqlalchemy as sa

from nailgun.db.sqlalchemy.models import fields
from nailgun.utils import migration


# revision identifiers, used by Alembic.
revision = '3763c404ca48'
down_revision = 'f2314e5d63c9'


def upgrade():
    upgrade_vmware_attributes_metadata()
    upgrade_attributes_metadata()
    upgrade_cluster_roles()
    upgrade_tags_meta()
    upgrade_primary_unit()


def downgrade():
    downgrade_primary_unit()
    downgrade_tags_meta()
    downgrade_cluster_roles()
    downgrade_attributes_metadata()
    downgrade_vmware_attributes_metadata()


VCENTER_INSECURE = {
    'name': "vcenter_insecure",
    'type': "checkbox",
    'label': "Bypass vCenter certificate verification"
}

VCENTER_SECURITY_DISABLED = {
    'name': "vcenter_security_disabled",
    'type': "checkbox",
    'label': "Bypass vCenter certificate verification"
}

VCENTER_CA_FILE = {
    'name': "vcenter_ca_file",
    'type': 'file',
    'label': "CA file",
    'description': ('File containing the trusted CA bundle that emitted '
                    'vCenter server certificate. Even if CA bundle is not '
                    'uploaded, certificate verification is turned on.'),
    'restrictions': [{
        'message': ('Bypass vCenter certificate verification should be '
                    'disabled.'),
        'condition': 'current_vcenter:vcenter_security_disabled == true'
    }]
}

CA_FILE = {
    'name': "ca_file",
    'type': 'file',
    'label': "CA file",
    'description': ('File containing the trusted CA bundle that emitted '
                    'vCenter server certificate. Even if CA bundle is not '
                    'uploaded, certificate verification is turned on.'),
    'restrictions': [{
        'message': ('Bypass vCenter certificate verification should be '
                    'disabled.'),
        'condition': 'glance:vcenter_security_disabled == true'
    }]
}

SECURITY_GROUP = {
    'value': 'iptables_hybrid',
    'values': [
        {
            'data': 'openvswitch',
            'label': 'Open vSwitch Firewall Driver',
            'description': 'Choose this type of firewall driver if you'
                           ' use OVS Bridges for networking needs.'
        },
        {
            'data': 'iptables_hybrid',
            'label': 'Iptables-based Firewall Driver',
            'description': 'Choose this type of firewall driver if you'
                           ' use Linux Bridges for networking needs.'
        }
    ],
    'group': 'security',
    'weight': 20,
    'type': 'radio',
}

# version of Fuel when security group switch was added
FUEL_SECURITY_GROUP_VERSION = '9.0'


def update_vmware_attributes_metadata(upgrade):
    connection = op.get_bind()
    select_query = sa.sql.text(
        "SELECT id, vmware_attributes_metadata FROM releases "
        "WHERE vmware_attributes_metadata IS NOT NULL")
    update_query = sa.sql.text(
        "UPDATE releases SET vmware_attributes_metadata = "
        ":vmware_attributes_metadata WHERE id = :id")

    for id, attrs in connection.execute(select_query):
        attrs = jsonutils.loads(attrs)
        editable = attrs.setdefault('editable', {})
        metadata = editable.setdefault('metadata', [])
        value = editable.setdefault('value', {})

        for m in metadata:
            if not isinstance(m, dict):
                continue
            if m.get('name') == 'availability_zones':
                fields = m.setdefault('fields', [])
                names = [f['name'] for f in fields]
                av_z = value.setdefault('availability_zones', {})
                update_availability_zones(fields, av_z, names, upgrade)
            elif m.get('name') == 'glance':
                fields = m.setdefault('fields', [])
                names = [f['name'] for f in fields]
                glance = value.setdefault('glance', {})
                update_glance(fields, glance, names, upgrade)

        connection.execute(
            update_query,
            id=id,
            vmware_attributes_metadata=jsonutils.dumps(attrs))


def update_availability_zones(fields, values, names, upgrade):
    if upgrade:
        if 'vcenter_security_disabled' not in names:
            fields.insert(5, VCENTER_SECURITY_DISABLED)
            for value in values:
                value['vcenter_security_disabled'] = True
        if 'vcenter_insecure' in names:
            fields.remove(VCENTER_INSECURE)
            for value in values:
                del value['vcenter_insecure']
        for field in fields:
            if field['name'] == 'vcenter_ca_file':
                field['restrictions'] = VCENTER_CA_FILE['restrictions']
    else:
        if 'vcenter_insecure' not in names:
            fields.insert(5, VCENTER_INSECURE)
            for value in values:
                value['vcenter_insecure'] = True
        if 'vcenter_security_disabled' in names:
            fields.remove(VCENTER_SECURITY_DISABLED)
            for value in values:
                del value['vcenter_security_disabled']
        for field in fields:
            if field['name'] == 'vcenter_ca_file':
                del field['restrictions']


def update_glance(fields, values, names, upgrade):
    if upgrade:
        if 'vcenter_security_disabled' not in names:
            fields.insert(6, VCENTER_SECURITY_DISABLED)
            values['vcenter_security_disabled'] = True
        if 'vcenter_insecure' in names:
            fields.remove(VCENTER_INSECURE)
            del values['vcenter_insecure']
        for field in fields:
            if field['name'] == 'ca_file':
                field['restrictions'] = CA_FILE['restrictions']
    else:
        if 'vcenter_insecure' not in names:
            fields.insert(6, VCENTER_INSECURE)
            values['vcenter_insecure'] = True
        if 'vcenter_security_disabled' in names:
            fields.remove(VCENTER_SECURITY_DISABLED)
            del values['vcenter_security_disabled']
        for field in fields:
            if field['name'] == 'ca_file':
                del field['restrictions']


def upgrade_vmware_attributes_metadata():
    update_vmware_attributes_metadata(upgrade=True)


def downgrade_vmware_attributes_metadata():
    update_vmware_attributes_metadata(upgrade=False)


def upgrade_attributes_metadata():
    connection = op.get_bind()
    upgrade_release_attributes_metadata(connection)
    upgrade_cluster_attributes(connection)


def upgrade_release_attributes_metadata(connection):
    select_query = sa.sql.text(
        'SELECT id, attributes_metadata, version FROM releases '
        'WHERE attributes_metadata IS NOT NULL')

    update_query = sa.sql.text(
        'UPDATE releases SET attributes_metadata = :attributes_metadata '
        'WHERE id = :release_id')

    for release_id, attrs, release_version in connection.execute(select_query):
        if not migration.is_security_group_available(
                release_version, FUEL_SECURITY_GROUP_VERSION):
            continue
        attrs = jsonutils.loads(attrs)
        common = attrs.setdefault('editable', {}).setdefault('common', {})
        common.setdefault('security_group', SECURITY_GROUP)
        connection.execute(
            update_query,
            release_id=release_id,
            attributes_metadata=jsonutils.dumps(attrs))


def upgrade_cluster_attributes(connection):
    select_query = sa.sql.text(
        'SELECT cluster_id, editable, version FROM attributes INNER JOIN '
        'clusters ON clusters.id = attributes.cluster_id INNER JOIN releases '
        'ON releases.id = clusters.release_id WHERE editable IS NOT NULL')

    update_query = sa.sql.text(
        'UPDATE attributes SET editable = :editable WHERE cluster_id = '
        ':cluster_id')

    for cluster_id, editable, release_version in connection.execute(
            select_query
    ):
        if not migration.is_security_group_available(
                release_version, FUEL_SECURITY_GROUP_VERSION):
            continue
        editable = jsonutils.loads(editable)
        editable.setdefault('common', {}).setdefault('security_group',
                                                     SECURITY_GROUP)
        connection.execute(
            update_query,
            cluster_id=cluster_id,
            editable=jsonutils.dumps(editable))


def downgrade_attributes_metadata():
    connection = op.get_bind()
    downgrade_cluster_attributes(connection)
    downgrade_release_attributes_metadata(connection)


def downgrade_release_attributes_metadata(connection):
    select_query = sa.sql.text(
        'SELECT id, attributes_metadata FROM releases '
        'WHERE attributes_metadata IS NOT NULL')

    update_query = sa.sql.text(
        'UPDATE releases SET attributes_metadata = :attributes_metadata '
        'WHERE id = :release_id')

    for release_id, attrs in connection.execute(select_query):
        attrs = jsonutils.loads(attrs)
        attrs.setdefault('editable', {}).setdefault('common', {}).pop(
            'security_group', None)
        connection.execute(
            update_query,
            release_id=release_id,
            attributes_metadata=jsonutils.dumps(attrs))


def downgrade_cluster_attributes(connection):
    select_query = sa.sql.text(
        'SELECT cluster_id, editable FROM attributes '
        'WHERE editable IS NOT NULL')

    update_query = sa.sql.text(
        'UPDATE attributes SET editable = :editable '
        'WHERE cluster_id = :cluster_id')

    for cluster_id, editable in connection.execute(select_query):
        editable = jsonutils.loads(editable)
        editable.setdefault('common', {}).pop('security_group', None)
        connection.execute(
            update_query,
            cluster_id=cluster_id,
            editable=jsonutils.dumps(editable))


def upgrade_cluster_roles():
    op.add_column(
        'clusters',
        sa.Column('roles_metadata',
                  fields.JSON(),
                  default={},
                  server_default='{}'),
    )
    op.add_column(
        'clusters',
        sa.Column('volumes_metadata',
                  fields.JSON(),
                  default={},
                  server_default='{}'),
    )


def downgrade_cluster_roles():
    op.drop_column('clusters', 'volumes_metadata')
    op.drop_column('clusters', 'roles_metadata')


def upgrade_tags_meta():
    connection = op.get_bind()
    op.add_column(
        'releases',
        sa.Column('tags_metadata',
                  fields.JSON(),
                  server_default='{}',
                  nullable=False),
    )
    op.add_column(
        'clusters',
        sa.Column('tags_metadata',
                  fields.JSON(),
                  server_default='{}',
                  nullable=False),
    )
    op.add_column(
        'plugins',
        sa.Column('tags_metadata',
                  fields.JSON(),
                  server_default='{}',
                  nullable=False),
    )

    q_get_role_meta = "SELECT id, roles_metadata FROM {}"
    q_update_role_tags_meta = '''
        UPDATE {}
        SET roles_metadata = :roles_meta, tags_metadata = :tags_meta
        WHERE id = :obj_id
    '''

    for table in ['releases', 'plugins']:
        for obj_id, roles_meta in connection.execute(
                sa.text(q_get_role_meta.format(table))):
            tags_meta = {}
            roles_meta = jsonutils.loads(roles_meta or '{}')
            for role_name, meta in six.iteritems(roles_meta):
                meta['tags'] = [role_name]
                tags_meta[role_name] = {'has_primary': meta.get('has_primary',
                                                                False)}
            connection.execute(sa.text(q_update_role_tags_meta.format(table)),
                               roles_meta=jsonutils.dumps(roles_meta),
                               tags_meta=jsonutils.dumps(tags_meta),
                               obj_id=obj_id)


def downgrade_tags_meta():
    op.drop_column('plugins', 'tags_metadata')
    op.drop_column('clusters', 'tags_metadata')
    op.drop_column('releases', 'tags_metadata')


def upgrade_primary_unit():
    op.alter_column('nodes', 'primary_roles', new_column_name='primary_tags')


def downgrade_primary_unit():
    connection = op.get_bind()
    q_get_roles = sa.text('''
        SELECT id, roles, pending_roles, primary_tags
        FROM nodes
    ''')
    q_update_primary_tags = sa.text('''
        UPDATE nodes
        SET primary_tags = :primary_tags
        WHERE id = :node_id
    ''')
    for node_id, roles, p_roles, pr_tags in connection.execute(q_get_roles):
        primary_tags = list(set(roles + p_roles) & set(pr_tags))
        connection.execute(
            q_update_primary_tags,
            node_id=node_id,
            primary_tags=primary_tags
        )
    op.alter_column('nodes', 'primary_tags', new_column_name='primary_roles')
