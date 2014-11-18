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

import os

from novaclient import client as nova_client

from nailgun.network import manager
from nailgun import objects
from nailgun.settings import settings


class OpenStackInfoCollector(object):

    def __init__(self, cluster, cluster_nodes):
        proxy_port = 8888
        self.online_controller = filter(
            lambda node: "controller" in node.roles and node.online is True,
            cluster_nodes
        )[0]

        proxy_host = self.online_controller.ip
        os.environ["http_proxy"] = "http://{0}:{1}".format(proxy_host,
                                                           proxy_port)

        access_data = objects.Cluster.get_creds(cluster)

        os_user = access_data["user"]["value"]
        os_password = access_data["password"]["value"]
        os_tenant = access_data["tenant"]["value"]

        self.compute_service_type = "compute"

        auth_host = self.get_host_for_auth(cluster)
        auth_url = "http://{0}:5000/v2.0/".format(auth_host)

        self.initialize_clients(os_user, os_password, os_tenant, auth_url)

    def initialize_clients(self, *auth_creds):
        self.nova_client = nova_client.Client(
            settings.NOVACLIENT_VERSION,
            *auth_creds,
            service_type=self.compute_service_type
        )

    def get_host_for_auth(self, nodes):
        return manager.NetworkManager._get_ip_by_network_name(
            self.online_controller, "management"
        ).ip_addr

    def get_info(self):
        openstack_info = {
            "instances_count": len(self.nova_client.servers.list())
        }

        self.clean_env()

        return openstack_info

    def clean_env(self):
        if os.environ.get("http_proxy"):
            del(os.environ["http_proxy"])
