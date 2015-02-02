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
from nailgun.openstack.common import jsonutils

from nailgun.api.v1.validators.release import ReleaseValidator
from nailgun.errors import errors
from nailgun.test.base import BaseTestCase


class TestReleaseValidator(BaseTestCase):

    def setUp(self):
        super(TestReleaseValidator, self).setUp()

        self.release = {
            'name': 'Test Release',
            'version': '2014.2-6.0',
            'operating_system': 'CentOS'
        }
        self.validator = ReleaseValidator

    def get_release(self, release):
        return jsonutils.dumps(release)

    def test_name_is_mandatory(self):
        self.release.pop('name')

        self.assertRaisesRegexp(
            errors.InvalidData,
            'No release name specified',
            self.validator.validate,
            self.get_release(self.release))

    def test_version_is_mandatory(self):
        self.release.pop('version')

        self.assertRaisesRegexp(
            errors.InvalidData,
            'No release version specified',
            self.validator.validate,
            self.get_release(self.release))

    def test_operating_system_is_mandatory(self):
        self.release.pop('operating_system')

        self.assertRaisesRegexp(
            errors.InvalidData,
            'No release operating system specified',
            self.validator.validate,
            self.get_release(self.release))

    def test_default_are_good(self):
        self.validator.validate(self.get_release(self.release))
