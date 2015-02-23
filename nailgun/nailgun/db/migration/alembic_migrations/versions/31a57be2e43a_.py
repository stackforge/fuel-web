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

Revision ID: 31a57be2e43a
Revises: 37608259013
Create Date: 2015-02-23 13:14:37.142459

"""

# revision identifiers, used by Alembic.
revision = '31a57be2e43a'
down_revision = '37608259013'

from alembic import op
import sqlalchemy as sa

from nailgun.db.sqlalchemy.models import fields


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'network_groups',
        sa.Column('additional_roles', fields.JSON(), server_default='[]'))

    # TODO(dshulyak) add ['mesh'] role for management network of old releases
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('network_groups', 'additional_roles')
    ### end Alembic commands ###
