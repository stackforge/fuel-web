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

import alembic
import sqlalchemy as sa

from nailgun import consts
from nailgun.db import db
from nailgun.db import dropdb
from nailgun.db.migration import ALEMBIC_CONFIG
from nailgun.test import base


_prepare_revision = '1e50a4903910'
_test_revision = '43b2cb64dae6'


def setup_module(module):
    dropdb()
    alembic.command.upgrade(ALEMBIC_CONFIG, _prepare_revision)
    prepare()
    alembic.command.upgrade(ALEMBIC_CONFIG, _test_revision)


def prepare():
    meta = base.reflect_db_metadata()
    db.execute(
        meta.tables['tasks'].insert(),
        [
            {
                'cluster_id': None,
                'uuid': 'fake_task_uuid_0',
                'name': consts.TASK_NAMES.node_deletion,
                'message': None,
                'status': consts.TASK_STATUSES.running,
                'progress': 0,
                'cache': None,
                'result': None,
                'parent_id': None,
                'weight': 1
            }
        ])

    db.commit()


class TestTakInOrchestrator(base.BaseAlembicMigrationTest):

    def test_new_in_orchestrator(self):
        result = db.execute(
            sa.select([self.meta.tables['tasks']
                       .c.is_in_orchestrator]))
        values = set(row[0] for row in result.fetchall())
        self.assertEqual(set((False,)), values)
