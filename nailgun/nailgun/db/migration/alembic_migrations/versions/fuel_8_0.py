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

"""empty message

Revision ID: 43b2cb64dae6
Revises: 1e50a4903910
Create Date: 2015-09-03 12:28:11.132934

"""
from alembic import op
import sqlalchemy as sa

from nailgun.db.sqlalchemy.models import fields

# revision identifiers, used by Alembic.
revision = '43b2cb64dae6'
down_revision = '1e50a4903910'


def upgrade():
    op.add_column(
        'nodes',
        sa.Column(
            'serialized_interface_config', fields.JSON(), nullable=True,
            server_default=None)
    )


def downgrade():
    op.drop_column('nodes', 'serialized_interface_config')
