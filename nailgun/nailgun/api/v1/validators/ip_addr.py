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


from oslo_serialization import jsonutils
import six

from nailgun.api.v1.validators.base import BasicValidator
from nailgun.api.v1.validators.json_schema import ip_addr
from nailgun.errors import errors
from nailgun import objects


class IPAddrValidator(BasicValidator):
    single_schema = ip_addr.IP_ADDR_UPDATE_SCHEMA
    collection_schema = ip_addr.IP_ADDRS_UPDATE_SCHEMA
    updatable_fields = (
        "ip_addr",
        "is_user_defined",
    )

    @classmethod
    def validate_update(cls, data, existing_obj):
        if isinstance(data, six.string_types):
            data = cls.validate_json(data)

        existing_data = dict(existing_obj)

        bad_fields = []
        for field, value in six.iteritems(data):
            old_value = existing_data.get(field)
            # field that not allowed to be changed is changed
            if value != old_value and field not in cls.updatable_fields:
                bad_fields.append(field)

        if bad_fields:
            bad_fields_verbose = ", ".join(repr(bf) for bf in bad_fields)
            raise errors.InvalidData(
                "\n".join([
                    "The following fields: {0} are not allowed to be "
                    "updated for record:".format(bad_fields_verbose),
                    jsonutils.dumps(data),
                ])
            )
        return data

    @classmethod
    def validate_collection_update(cls, data, cluster_id=None):
        error_messages = []
        data_to_update = cls.validate_json(data)
        for record in data_to_update:
            instance = objects.IPAddr.get_by_uid(record.get('id'))
            if instance:
                try:
                    cls.validate_update(record, instance)
                except errors.InvalidData as e:
                    error_messages.append(e.message)
            else:
                error_messages.append(
                    "IPAddr with (ID={0}) "
                    "is not found".format(record.get('id'))
                )

        if error_messages:
            raise errors.InvalidData("\n".join(error_messages))

        return data_to_update
