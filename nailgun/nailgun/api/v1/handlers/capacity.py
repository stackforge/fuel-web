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

import pecan

import codecs
import cStringIO
import csv
from hashlib import md5
import tempfile

from nailgun.db.sqlalchemy.models import CapacityLog
from nailgun import objects

from nailgun.api.v2.controllers.base import BaseController
from nailgun.task.manager import GenerateCapacityLogTaskManager


"""
Capacity audit handlers
"""


class UnicodeWriter(object):
    """Unicode CSV writer.

    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    Source: http://docs.python.org/2/library/csv.html#examples
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        # We have only string and int types in capacity log now.
        # Don't need to convert int values to string for writhing it to file.
        self.writer.writerow(
            [s.encode("utf-8") if type(s) != int else s for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class CapacityLogCsvController(BaseController):

    @pecan.expose(content_type='application/octet-stream')
    def get_all(self):
        capacity_log = objects.CapacityLog.get_latest()
        if not capacity_log:
            raise self.http(404)

        report = capacity_log.report
        f = tempfile.TemporaryFile(mode='r+b')
        csv_file = UnicodeWriter(f, delimiter=',',
                                 quotechar='|', quoting=csv.QUOTE_MINIMAL)

        csv_file.writerow(['Fuel version', report['fuel_data']['release']])
        csv_file.writerow(['Fuel UUID', report['fuel_data']['uuid']])

        csv_file.writerow(['Environment Name', 'Node Count'])
        for stat in report['environment_stats']:
            csv_file.writerow([stat['cluster'], stat['nodes']])

        csv_file.writerow(['Total number allocated of nodes',
                           report['allocation_stats']['allocated']])
        csv_file.writerow(['Total number of unallocated nodes',
                           report['allocation_stats']['unallocated']])

        csv_file.writerow([])
        csv_file.writerow(['Node role(s)',
                           'Number of nodes with this configuration'])
        for roles, count in report['roles_stat'].iteritems():
            csv_file.writerow([roles, count])

        f.seek(0)
        checksum = md5(f.read()).hexdigest()
        csv_file.writerow([])
        csv_file.writerow(['Checksum', checksum])

        filename = 'fuel-capacity-audit.csv'

        response = pecan.response
        response.content_disposition = 'attachment; filename="{0}"'.format(
            filename
        )
        response.content_length = f.tell()
        f.seek(0)
        return f.read()


class CapacityLogController(BaseController):
    """Task single handler
    """
    csv = CapacityLogCsvController()

    fields = (
        "id",
        "report"
    )

    model = CapacityLog

    @pecan.expose(template='json:', content_type='application/json')
    def get_all(self):
        capacity_log = objects.CapacityLog.get_latest()
        if not capacity_log:
            raise self.http(404)
        return self.render(capacity_log)

    @pecan.expose(template='json:', content_type='application/json')
    def put(self, dummy=None):
        """Starts capacity data generation.

        :returns: JSONized Task object.
        :http: * 200 (setup task successfully executed)
               * 202 (setup task created and started)
               * 400 (data validation failed)
               * 404 (cluster not found in db)
        """
        # TODO(pkaminski): this seems to be synchronous, no task needed here
        manager = GenerateCapacityLogTaskManager()
        task = manager.execute()

        self.raise_task(task)
