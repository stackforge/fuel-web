# -*- coding: utf-8 -*-

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

from nailgun import objects


class NailgunClusterAdapter(object):
    def __init__(self, cluster):
        self.cluster = cluster

    @property
    def id(self):
        return self.cluster.id

    @property
    def net_provider(self):
        return self.cluster.net_provider

    @property
    def release(self):
        return NailgunReleaseAdapter(self.cluster.release)

    @property
    def generated_attrs(self):
        return self.cluster.attributes.generated

    @generated_attrs.setter
    def generated_attrs(self, attrs):
        self.cluster.attributes.generated = attrs

    @property
    def editable_attrs(self):
        return self.cluster.attributes.editable

    @editable_attrs.setter
    def editable_attrs(self, attrs):
        self.cluster.attributes.editable = attrs

    def get_create_data(self):
        return objects.Cluster.get_create_data(self.cluster)

    def get_network_manager(self):
        net_manager = objects.Cluster.get_network_manager(
            instance=self.cluster)
        return net_manager

    @classmethod
    def get_nodes_by_role(cls, cluster, role):
        return objects.Cluster.get_nodes_by_role(cluster, role)

    @classmethod
    def get_by_uid(cls, cluster_id):
        return objects.Cluster.get_by_uid(cluster_id)


class NailgunReleaseAdapter(object):
    def __init__(self, release):
        self.release = release

    @property
    def is_deployable(self):
        return self.release.is_deployable

    def __cmp__(self, other):
        if isinstance(other, NailgunReleaseAdapter):
            other = other.release
        return self.release.__cmp__(other)


class NailgunNodeAdapter(object):

    def __init__(self, node):
        self.node = node

    @property
    def hostname(self):
        return self.node.hostname

    @hostname.setter
    def hostname(self, hostname):
        self.node.hostname = hostname
