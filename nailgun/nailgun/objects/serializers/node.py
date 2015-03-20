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

from nailgun import consts

from nailgun.objects.serializers.base import BasicSerializer
from nailgun.utils import extract_env_version


class NodeSerializer(BasicSerializer):

    fields = (
        'id',
        'name',
        'meta',
        'progress',
        'kernel_params',
        'roles',
        'pending_roles',
        'status',
        'mac',
        'fqdn',
        'ip',
        'manufacturer',
        'platform_name',
        'pending_addition',
        'pending_deletion',
        'os_platform',
        'error_type',
        'online',
        'cluster',
        'network_data',
        'group_id'
    )


class NodeInterfacesSerializer(BasicSerializer):

    nic_fields = (
        'id',
        'mac',
        'name',
        'type',
        'interface_properties',
        'state',
        'current_speed',
        'max_speed',
        'assigned_networks',
        'driver',
        'bus_info',
    )
    bond_fields = (
        'mac',
        'name',
        'type',
        'interface_properties',
        'mode',
        'bond_properties',
        'state',
        'assigned_networks'
    )

    nic_fields_60 = (
        'id',
        'mac',
        'name',
        'type',
        'state',
        'current_speed',
        'max_speed',
        'assigned_networks',
        'driver',
        'bus_info',
    )
    bond_fields_60 = (
        'mac',
        'name',
        'type',
        'mode',
        'bond_properties',
        'state',
        'assigned_networks'
    )

    @classmethod
    def serialize_nic_interface(cls, instance, fields=None, upto60=False):
        if not fields:
            fields = cls.nic_fields_60 if upto60 else cls.nic_fields
        return BasicSerializer.serialize(
            instance,
            fields=fields if fields else cls.nic_fields
        )

    @classmethod
    def serialize_bond_interface(cls, instance, fields=None, upto60=False):
        if not fields:
            fields = cls.bond_fields_60 if upto60 else cls.bond_fields
        data_dict = BasicSerializer.serialize(
            instance,
            fields=fields if fields else cls.bond_fields
        )
        data_dict['slaves'] = [{'name': slave.name}
                               for slave in instance.slaves]
        return data_dict

    @classmethod
    def serialize(cls, instance, fields=None):
        iface_types = consts.NETWORK_INTERFACE_TYPES
        upto60 = False
        if not fields and instance.node.cluster:
            ver = extract_env_version(instance.node.cluster.release.version)
            upto60 = ver.startswith('5') or ver.startswith('6.0')
        if instance.type == iface_types.ether:
            return cls.serialize_nic_interface(instance, upto60=upto60)
        elif instance.type == iface_types.bond:
            return cls.serialize_bond_interface(instance, upto60=upto60)
