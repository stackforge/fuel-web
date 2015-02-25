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

"""fuel_5_1

Revision ID: 52924111f7d8
Revises: 1a1504d469f8
Create Date: 2014-06-09 13:25:25.773543
"""

# revision identifiers, used by Alembic.
revision = '52924111f7d8'
down_revision = '1a1504d469f8'

from alembic import op
from oslo.serialization import jsonutils
import sqlalchemy as sa
from sqlalchemy.sql import text

from nailgun import consts
from nailgun.db.sqlalchemy.models.fields import JSON
from nailgun.utils.migration import drop_enum
from nailgun.utils.migration import upgrade_clusters_replaced_info
from nailgun.utils.migration import upgrade_enum
from nailgun.utils.migration import upgrade_release_attributes_50_to_51
from nailgun.utils.migration import upgrade_release_roles_50_to_51


cluster_changes_old = (
    'networks',
    'attributes',
    'disks'
)
cluster_changes_new = consts.CLUSTER_CHANGES


task_names_old = (
    'super',
    'deploy',
    'deployment',
    'provision',
    'stop_deployment',
    'reset_environment',
    'node_deletion',
    'cluster_deletion',
    'check_before_deployment',
    'check_networks',
    'verify_networks',
    'check_dhcp',
    'verify_network_connectivity',
    'redhat_setup',
    'redhat_check_credentials',
    'redhat_check_licenses',
    'redhat_download_release',
    'redhat_update_cobbler_profile',
    'dump',
    'capacity_log'
)
task_names_new = consts.TASK_NAMES


cluster_statuses_old = (
    'new',
    'deployment',
    'stopped',
    'operational',
    'error',
    'remove'
)
cluster_statuses_new = consts.CLUSTER_STATUSES


notification_topics_old = (
    'discover',
    'done',
    'error',
    'warning',
)
notification_topics_new = consts.NOTIFICATION_TOPICS


neutron_l23_providers_old = (
    'ovs'
)
neutron_l23_providers_new = consts.NEUTRON_L23_PROVIDERS


def upgrade():
    upgrade_schema()
    upgrade_data()


def upgrade_schema():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'releases',
        sa.Column(
            'can_update_from_versions',
            JSON(),
            nullable=False,
            server_default='[]'
        )
    )
    op.add_column(
        'releases',
        sa.Column(
            'wizard_metadata',
            JSON(),
            nullable=True
        )
    )
    op.add_column(
        'clusters',
        sa.Column(
            'pending_release_id',
            sa.Integer(),
            nullable=True
        )
    )
    op.create_foreign_key(
        'fk_pending_release_id',
        'clusters',
        'releases',
        ['pending_release_id'],
        ['id'],
    )
    upgrade_enum(
        "clusters",                 # table
        "status",                   # column
        "cluster_status",           # ENUM name
        cluster_statuses_old,       # old options
        cluster_statuses_new        # new options
    )
    upgrade_enum(
        "tasks",                    # table
        "name",                     # column
        "task_name",                # ENUM name
        task_names_old,             # old options
        task_names_new              # new options
    )
    upgrade_enum(
        "notifications",            # table
        "topic",                    # column
        "notif_topic",              # ENUM name
        notification_topics_old,    # old options
        notification_topics_new,    # new options
    )
    upgrade_enum(
        "cluster_changes",          # table
        "name",                     # column
        "possible_changes",         # ENUM name
        cluster_changes_old,        # old options
        cluster_changes_new         # new options
    )

    upgrade_enum(
        "neutron_config",           # table
        "net_l23_provider",         # column
        "net_l23_provider",         # ENUM name
        neutron_l23_providers_old,  # old options
        neutron_l23_providers_new   # new options
    )

    op.drop_table('red_hat_accounts')
    drop_enum('license_type')
    op.add_column('nodes', sa.Column(
        'replaced_deployment_info', JSON(), nullable=True))
    op.add_column('nodes', sa.Column(
        'replaced_provisioning_info', JSON(), nullable=True))
    ### end Alembic commands ###


def upgrade_data():
    connection = op.get_bind()

    # upgrade release data from 5.0 to 5.1
    upgrade_releases(connection)
    upgrade_clusters_replaced_info(connection)


def upgrade_releases(connection):
    select = text(
        """SELECT id, attributes_metadata, roles_metadata
        from releases""")
    update = text(
        """UPDATE releases
        SET attributes_metadata = :attrs, roles_metadata = :roles,
        wizard_metadata = :wiz_meta
        WHERE id = :id""")
    r = connection.execute(select)

    # reading fixture files in loop is in general a bad idea and as long as
    # wizard_metadata is the same for all existing releases getting it can
    # be moved outside of the loop

    for release in r:
        attrs_meta = upgrade_release_attributes_50_to_51(
            jsonutils.loads(release[1]))
        roles_meta = upgrade_release_roles_50_to_51(
            jsonutils.loads(release[2]))
        connection.execute(
            update,
            id=release[0],
            attrs=jsonutils.dumps(attrs_meta),
            roles=jsonutils.dumps(roles_meta),
            wiz_meta=jsonutils.dumps(_wizard_meta)
        )


def downgrade():
    downgrade_data()
    downgrade_schema()


def downgrade_schema():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('nodes', 'replaced_provisioning_info')
    op.drop_column('nodes', 'replaced_deployment_info')
    upgrade_enum(
        "neutron_config",           # table
        "net_l23_provider",         # column
        "net_l23_provider",         # ENUM name
        neutron_l23_providers_new,  # old options
        neutron_l23_providers_old   # new options
    )

    upgrade_enum(
        "cluster_changes",          # table
        "name",                     # column
        "possible_changes",         # ENUM name
        cluster_changes_new,        # new options
        cluster_changes_old,        # old options
    )
    upgrade_enum(
        "notifications",            # table
        "topic",                    # column
        "notif_topic",              # ENUM name
        notification_topics_new,    # new options
        notification_topics_old,    # old options
    )
    upgrade_enum(
        "tasks",                    # table
        "name",                     # column
        "task_name",                # ENUM name
        task_names_new,             # old options
        task_names_old              # new options
    )
    upgrade_enum(
        "clusters",                 # table
        "status",                   # column
        "cluster_status",           # ENUM name
        cluster_statuses_new,       # old options
        cluster_statuses_old        # new options
    )

    op.drop_constraint(
        'fk_pending_release_id',
        'clusters',
        type_='foreignkey'
    )
    op.drop_column('clusters', 'pending_release_id')
    op.drop_column('releases', 'can_update_from_versions')
    op.create_table('red_hat_accounts',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('username',
                              sa.String(length=100),
                              nullable=False),
                    sa.Column('password',
                              sa.String(length=100),
                              nullable=False),
                    sa.Column('license_type', sa.Enum('rhsm', 'rhn',
                                                      name='license_type'),
                              nullable=False),
                    sa.Column('satellite',
                              sa.String(length=250),
                              nullable=False),
                    sa.Column('activation_key',
                              sa.String(length=300),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    ### end Alembic commands ###


def downgrade_data():
    # PLEASE NOTE. It was decided not to downgrade release data (5.1 to 5.0)
    # because it's not possible in most situations.
    pass


_wizard_meta = {
    "Mode": {
        "mode": {
            "type": "radio",
            "bind": "cluster:mode",
            "values": [
                {
                    "data": "ha_compact",
                    "label": "cluster.mode.ha_compact"
                },
                {
                    "data": "multinode",
                    "label": "cluster.mode.multinode"
                }
            ]
        }
    },
    "Compute": {
        "hypervisor": {
            "type": "radio",
            "value": "qemu",
            "weight": 5,
            "bind": "settings:common.libvirt_type.value",
            "values": [
                {
                    "data": "kvm",
                    "label": "dialog.create_cluster_wizard.compute.kvm",
                    "description": "dialog.create_cluster_wizard."
                    "compute.kvm_description"
                },
                {
                    "data": "qemu",
                    "label": "dialog.create_cluster_wizard.compute.qemu",
                    "description": "dialog.create_cluster_wizard."
                    "compute.qemu_description"
                },
                {
                    "data": "vcenter",
                    "label": "dialog.create_cluster_wizard.compute.vcenter",
                    "description": "dialog.create_cluster_wizard."
                    "compute.vcenter_description"
                }
            ]
        },
        "host_ip": {
            "type": "text",
            "label": "dialog.create_cluster_wizard.compute.vcenter_ip",
            "description": "dialog.create_cluster_wizard.compute."
            "vcenter_ip_description",
            "weight": 10,
            "bind": "settings:vcenter.host_ip.value",
            "restrictions": [
                {
                    "condition": "Compute.hypervisor != 'vcenter'",
                    "action": "hide",
                    "message": None
                }
            ],
            "regex": {
                "source": "^(([\\d]|[1-9][\\d]|1[\\d]{2}|2[0-4][\\d]"
                "|25[0-5])\\.){3}([\\d]|[1-9][\\d]|1[\\d]{2}"
                "|2[0-4][\\d]|25[0-5])$",
                "error": "dialog.create_cluster_wizard.compute."
                "vcenter_ip_warning"
            }
        },
        "vc_user": {
            "type": "text",
            "label": "dialog.create_cluster_wizard.compute.vcenter_username",
            "description": "dialog.create_cluster_wizard.compute."
            "vcenter_username_description",
            "weight": 20,
            "bind": "settings:vcenter.vc_user.value",
            "restrictions": [
                {
                    "condition": "Compute.hypervisor != 'vcenter'",
                    "action": "hide",
                    "message": None
                }
            ],
            "regex": {
                "source": "\\S",
                "error": "dialog.create_cluster_wizard.compute."
                "vcenter_user_warning"
            }
        },
        "vc_password": {
            "type": "password",
            "label": "dialog.create_cluster_wizard.compute.vcenter_password",
            "description": "dialog.create_cluster_wizard.compute."
            "vcenter_password_description",
            "weight": 30,
            "bind": "settings:vcenter.vc_password.value",
            "restrictions": [
                {
                    "condition": "Compute.hypervisor != 'vcenter'",
                    "action": "hide",
                    "message": None
                }
            ],
            "regex": {
                "source": "\\S",
                "error": "dialog.create_cluster_wizard.compute."
                "vcenter_password_warning"
            }
        },
        "cluster": {
            "type": "text",
            "label": "dialog.create_cluster_wizard.compute.vcenter_cluster",
            "description": "dialog.create_cluster_wizard.compute."
            "vcenter_cluster_description",
            "weight": 40,
            "bind": "settings:vcenter.cluster.value",
            "restrictions": [
                {
                    "condition": "Compute.hypervisor != 'vcenter'",
                    "action": "hide",
                    "message": None
                }
            ],
            "regex": {
                "source": "^([^,\\ ]+([\\ ]*[^,\\ ])*)(,[^,\\ ]+([\\ ]"
                "*[^,\\ ])*)*$",
                "error": "dialog.create_cluster_wizard.compute."
                "vcenter_cluster_warning"
            }
        }
    },
    "Network": {
        "manager": {
            "type": "radio",
            "values": [
                {
                    "data": "nova-network",
                    "label": "dialog.create_cluster_wizard.network."
                    "nova_network",
                    "bind": [
                        {
                            "cluster:net_provider": "nova_network"
                        }
                    ]
                },
                {
                    "data": "neutron-gre",
                    "label": "dialog.create_cluster_wizard.network.neutr_gre",
                    "restrictions": [
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.network.hypervisor_alert"
                        }
                    ],
                    "bind": [
                        {
                            "cluster:net_provider": "neutron"
                        },
                        {
                            "cluster:net_segment_type": "gre"
                        }
                    ]
                },
                {
                    "data": "neutron-vlan",
                    "label": "dialog.create_cluster_wizard.network.neutr_vlan",
                    "restrictions": [
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.network.hypervisor_alert"
                        }
                    ],
                    "bind": [
                        {
                            "cluster:net_provider": "neutron"
                        },
                        {
                            "cluster:net_segment_type": "vlan"
                        }
                    ]
                },
                {
                    "data": "neutron-nsx",
                    "label": "dialog.create_cluster_wizard.network.neutr_nsx",
                    "restrictions": [
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.network.hypervisor_alert"
                        },
                        {
                            "condition": "not ('experimental' in "
                            "version:feature_groups)",
                            "action": "disable",
                            "message": "Neutron with NSX can be "
                            "used with Experimental mode only. "
                            "Please, look at the documentation to enable it"
                        },
                        {
                            "condition": "('experimental' in "
                            "version:feature_groups) and "
                            "(NameAndRelease.release_operating_system "
                            "== 'Ubuntu')",
                            "action": "none",
                            "message": "NSX with Ubuntu was not tested "
                            "properly and can be inoperable"
                        }
                    ],
                    "bind": [
                        {
                            "cluster:net_provider": "neutron"
                        },
                        {
                            "cluster:net_l23_provider": "nsx"
                        },
                        {
                            "cluster:net_segment_type": "gre"
                        },
                        {
                            "settings:nsx_plugin.metadata.enabled": True
                        }
                    ]
                }
            ]
        }
    },
    "Storage": {
        "cinder": {
            "type": "radio",
            "values": [
                {
                    "data": "default",
                    "label": "dialog.create_cluster_wizard.storage.default",
                    "bind": [
                        {
                            "settings:storage.volumes_lvm.value": True
                        }
                    ]
                },
                {
                    "data": "ceph",
                    "label": "dialog.create_cluster_wizard.storage.ceph",
                    "restrictions": [
                        {
                            "not ('ceph-osd' in NameAndRelease."
                            "release_roles)": "dialog."
                            "create_cluster_wizard.storage.alert"
                        },
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.storage."
                            "cinder_vcenter_alert"
                        },
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.storage.vmdk_alert"
                        }
                    ],
                    "bind": [
                        {
                            "settings:storage.volumes_ceph.value": True
                        },
                        {
                            "settings:storage.volumes_lvm.value": False
                        }
                    ]
                }
            ]
        },
        "glance": {
            "type": "radio",
            "values": [
                {
                    "data": "default",
                    "label": "dialog.create_cluster_wizard.storage.default"
                },
                {
                    "data": "ceph",
                    "label": "dialog.create_cluster_wizard.storage.ceph",
                    "restrictions": [
                        {
                            "not ('ceph-osd' in NameAndRelease."
                            "release_roles)": "dialog."
                            "create_cluster_wizard.storage.alert"
                        },
                        {
                            "Compute.hypervisor == 'vcenter'": "dialog."
                            "create_cluster_wizard.storage."
                            "glance_vcenter_alert"
                        }
                    ],
                    "bind": [
                        {
                            "settings:storage.images_ceph.value": True
                        }
                    ]
                }
            ]
        }
    },
    "AdditionalServices": {
        "sahara": {
            "type": "checkbox",
            "label": "dialog.create_cluster_wizard.additional.install_sahara",
            "description": "dialog.create_cluster_wizard.additional."
            "install_sahara_description",
            "bind": "settings:additional_components.sahara.value",
            "weight": 10
        },
        "murano": {
            "type": "checkbox",
            "label": "dialog.create_cluster_wizard.additional.install_murano",
            "description": "dialog.create_cluster_wizard.additional."
            "install_murano_description",
            "bind": "settings:additional_components.murano.value",
            "weight": 20,
            "restrictions": [
                {
                    "Network.manager == 'nova-network'": "dialog."
                    "create_cluster_wizard.additional.network_mode_alert"
                }
            ]
        },
        "ceilometer": {
            "type": "checkbox",
            "label": "dialog.create_cluster_wizard.additional."
            "install_ceilometer",
            "description": "dialog.create_cluster_wizard.additional."
            "install_ceilometer_description",
            "bind": "settings:additional_components.ceilometer.value",
            "weight": 30
        }
    },
    "Ready": {}
}
