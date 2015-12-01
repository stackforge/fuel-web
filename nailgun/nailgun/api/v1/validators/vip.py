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

from nailgun.api.v1.validators.base import BasicValidator
from nailgun.api.v1.validators.json_schema import vip as vip_schema


class VIPValidator(BasicValidator):
    collection_schema = vip_schema.VIPS_SCHEMA

    @classmethod
    def validate(cls, data):
        parsed = super(VIPValidator, cls).validate(data)
        cls.validate_schema(
            parsed,
            vip_schema.VIP_INFO_SCHEMA
        )
        return parsed

    @classmethod
    def validate_update(cls, data, instance):
        parsed = super(VIPValidator, cls).validate(data)
        cls.validate_schema(
            parsed,
            vip_schema.VIP_INFO_SCHEMA   # update schema is similar
        )
        return parsed

    @classmethod
    def validate_create(cls, data):
        return cls.validate(data)
