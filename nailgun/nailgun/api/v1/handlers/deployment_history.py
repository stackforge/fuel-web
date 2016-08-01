# -*- coding: utf-8 -*-

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

import csv
from StringIO import StringIO
import web

from oslo_serialization import jsonutils

from nailgun.api.v1.handlers import base
from nailgun.api.v1.handlers.decorators import handle_errors
from nailgun.api.v1.handlers.decorators import to_json
from nailgun.api.v1.handlers.decorators import validate
from nailgun.api.v1.validators.deployment_history import \
    DeploymentHistoryValidator
from nailgun import errors
from nailgun import objects


class DeploymentHistoryCollectionHandler(base.CollectionHandler):

    collection = objects.DeploymentHistoryCollection
    validator = DeploymentHistoryValidator

    def _to_csv(self, data):
        keys = list(data[0].keys())

        res = StringIO()
        csv_writer = csv.writer(res)
        csv_writer.writerow(keys)
        for obj in data:
            values = []
            for k in keys:
                v = obj.get(k)
                if isinstance(v, (list, dict)):
                    v = jsonutils.dumps(v)
                values.append(v)
            csv_writer.writerow(values)

        return res.getvalue()

    @handle_errors
    @validate
    def GET(self, transaction_id):
        """:returns: Collection of JSONized DeploymentHistory records.

        :http: * 200 (OK)
               * 400 (Bad tasks in given transaction)
               * 404 (transaction not found in db, task not found in snapshot)
        """
        # get transaction data
        transaction = self.get_object_or_404(
            objects.Transaction, transaction_id)

        # process input parameters
        nodes_ids = self.get_param_as_set('nodes_ids')
        statuses = self.get_param_as_set('statuses')
        tasks_names = self.get_param_as_set('tasks_names')
        try:
            self.validator.validate_query(nodes_ids=nodes_ids,
                                          statuses=statuses,
                                          tasks_names=tasks_names)
        except errors.ValidationException as exc:
            raise self.http(400, exc.message)

        # fetch and serialize history
        data = self.collection.get_history(transaction=transaction,
                                           nodes_ids=nodes_ids,
                                           statuses=statuses,
                                           tasks_names=tasks_names)

        # FIXME: Accept is a very complicated header, need
        # to handle it appropriately
        if 'text/csv' in web.ctx.env.get('HTTP_ACCEPT', ''):
            web.header('Content-Type', 'text/csv', unique=True)
            web.header('Content-Disposition',
                       'attachment; filename="output.csv"')
            ret = self._to_csv(data)
            web.header('Content-Length', len(ret))
            return ret
        else:
            web.header('Content-Type', 'application/json', unique=True)
            return jsonutils.dumps(data)
