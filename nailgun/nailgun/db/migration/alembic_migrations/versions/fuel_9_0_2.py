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

"""Fuel 9.0.2

Revision ID: 675105097a69
Revises: 11a9adc6d36a
Create Date: 2016-04-28 22:23:40.895589

"""

from alembic import op
from oslo_serialization import jsonutils
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2314e5d63c9'
down_revision = '675105097a69'

rule_to_pick_bootdisk = [
    {'type': 'exclude_disks_by_name',
     'regex': '^nvme',
     'description': 'NVMe drives should be skipped as accessing such drives '
                    'during the boot typically requires using UEFI which is '
                    'still not supported by fuel-agent (it always installs '
                    'BIOS variant of  grub). '
                    'grub bug (http://savannah.gnu.org/bugs/?41883)'},
    {'type': 'pick_root_disk_if_disk_name_match',
     'regex': '^md',
     'root_mount': '/',
     'description': 'If we have /root on fake raid, then /boot partition '
                    'should land on to it too. We can\'t proceed with '
                    'grub-install otherwise.'}
]


def upgrade():
    upgrade_release_with_rules_to_pick_bootable_disk()


def downgrade():
    downgrade_release_with_rules_to_pick_bootable_disk()


def upgrade_release_with_rules_to_pick_bootable_disk():
    connection = op.get_bind()
    select_query = sa.sql.text(
        "SELECT id, volumes_metadata FROM releases "
        "WHERE volumes_metadata IS NOT NULL")
    update_query = sa.sql.text(
        "UPDATE releases SET volumes_metadata = :volumes_metadata "
        "WHERE id = :id")

    for id, volumes_metadata in connection.execute(select_query):
        volumes_metadata = jsonutils.loads(volumes_metadata)

        volumes_metadata['rule_to_pick_boot_disk'] = rule_to_pick_bootdisk

        connection.execute(
            update_query,
            id=id,
            volumes_metadata=jsonutils.dumps(volumes_metadata),
        )

def downgrade_release_with_rules_to_pick_bootable_disk():
    connection = op.get_bind()
    select_query = sa.sql.text(
        "SELECT id, volumes_metadata FROM releases "
        "WHERE volumes_metadata IS NOT NULL")
    update_query = sa.sql.text(
        "UPDATE releases SET volumes_metadata = :volumes_metadata "
        "WHERE id = :id")

    for id, volumes_metadata in connection.execute(select_query):
        volumes_metadata = jsonutils.loads(volumes_metadata)
        if 'rule_to_pick_boot_disk' in volumes_metadata:
            del(volumes_metadata['rule_to_pick_boot_disk'])

            connection.execute(
                update_query,
                id=id,
                volumes_metadata=jsonutils.dumps(volumes_metadata),
            )