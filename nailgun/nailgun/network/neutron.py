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

import itertools
import netaddr
import six

from nailgun import consts
from nailgun.db import db
from nailgun.db.sqlalchemy import models
from nailgun.errors import errors
from nailgun.logger import logger
from nailgun.network.manager import AllocateVIPs70Mixin
from nailgun.network.manager import AllocateVIPs80Mixin
from nailgun.network.manager import AssignIPs61Mixin
from nailgun.network.manager import AssignIPs70Mixin
from nailgun.network.manager import AssignIPsLegacyMixin
from nailgun.network.manager import NetworkManager
from nailgun import objects
from nailgun.orchestrator.neutron_serializers import \
    NeutronNetworkTemplateSerializer70


class NeutronManager(NetworkManager):

    @classmethod
    def create_neutron_config(
            cls, cluster, segmentation_type=None,
            net_l23_provider=consts.NEUTRON_L23_PROVIDERS.ovs):

        neutron_config = models.NeutronConfig(
            cluster_id=cluster.id,
            net_l23_provider=net_l23_provider)

        if segmentation_type is not None:
            neutron_config.segmentation_type = segmentation_type

        meta = cluster.release.networks_metadata["neutron"]["config"]
        for key, value in meta.iteritems():
            if hasattr(neutron_config, key):
                setattr(neutron_config, key, value)

        db().add(neutron_config)
        db().flush()
        return neutron_config

    @classmethod
    def generate_vlan_ids_list(cls, data, cluster, ng):
        if ng.get("name") == consts.NETWORKS.private and \
                cluster.network_config.segmentation_type == \
                consts.NEUTRON_SEGMENT_TYPES.vlan:
            if data.get("networking_parameters", {}).get("vlan_range"):
                vlan_range = data["networking_parameters"]["vlan_range"]
            else:
                vlan_range = cluster.network_config.vlan_range
            return range(vlan_range[0], vlan_range[1] + 1)
        return [int(ng.get("vlan_start"))] if ng.get("vlan_start") else []

    @classmethod
    def get_ovs_bond_properties(cls, bond):
        props = []
        if 'lacp' in bond.mode:
            props.append('lacp=active')
            props.append('bond_mode=balance-tcp')
        else:
            props.append('bond_mode=%s' % bond.mode)
        return props


class NeutronManagerLegacy(AssignIPsLegacyMixin, NeutronManager):
    pass


class NeutronManager61(AssignIPs61Mixin, NeutronManager):
    pass


class NeutronManager70(
    AllocateVIPs70Mixin, AssignIPs70Mixin, NeutronManager
):

    @classmethod
    def build_role_to_network_group_mapping(cls, cluster, node_group_name):
        """Build network role to network map according to template data

        If template is not loaded, empty map is returned.

        :param cluster: Cluster instance
        :type cluster: Cluster model
        :param node_group_name: Node group name
        :type  node_group_name: string
        :return: Network role to network map
        :rtype: dict
        """
        template = cluster.network_config.configuration_template
        if template is None:
            return {}

        node_group = template['adv_net_template'][node_group_name]
        endpoint_to_net_group = {}
        for net_group, value in six.iteritems(
                node_group['network_assignments']):
            endpoint_to_net_group[value['ep']] = net_group

        result = {}
        for scheme in six.itervalues(node_group['network_scheme']):
            for role, endpoint in six.iteritems(scheme['roles']):
                if endpoint in endpoint_to_net_group:
                    result[role] = endpoint_to_net_group[endpoint]

        return result

    @classmethod
    def get_network_group_for_role(cls, network_role, net_group_mapping):
        """Returns network group to which network role is associated

        If networking template is set first lookup happens in the
        template. Otherwise the default network group from
        the network role is returned.

        :param network_role: Network role dict
        :type network_role: dict
        :param net_group_mapping: Network role to network group mapping
        :type  net_group_mapping: dict
        :return: Network group name
        :rtype: str
        """
        return net_group_mapping.get(
            network_role['id'], network_role['default_mapping'])

    @classmethod
    def get_node_networks_with_ips(cls, node):
        """Returns IP, CIDR, meta, gateway for each network on given node."""
        if not node.group_id:
            return {}

        ngs = db().query(models.NetworkGroup, models.IPAddr.ip_addr).\
            filter(models.NetworkGroup.group_id == node.group_id). \
            filter(models.IPAddr.network == models.NetworkGroup.id). \
            filter(models.IPAddr.node == node.id)
        if not ngs:
            return {}

        networks = {}
        for ng, ip in ngs:
            networks[ng.name] = {
                'ip': cls.get_ip_w_cidr_prefix_len(ip, ng),
                'cidr': ng.cidr,
                'meta': ng.meta,
                'gateway': ng.gateway
            }
        admin_ng = cls.get_admin_network_group(node.id)
        if admin_ng:
            networks[admin_ng.name] = {
                'ip': cls.get_ip_w_cidr_prefix_len(
                    cls.get_admin_ip_for_node(node.id), admin_ng),
                'cidr': admin_ng.cidr,
                'meta': admin_ng.meta,
                'gateway': admin_ng.gateway
            }
        return networks

    @classmethod
    def get_node_endpoints(cls, node):
        """Get a set of endpoints for node for the case when template is loaded

        Endpoints are taken from 'endpoints' field
        of templates for every node role.
        """
        endpoints = set()
        template = node.network_template

        for role in node.all_roles:
            role_templates = template['templates_for_node_role'][role]
            for role_template in role_templates:
                endpoints.update(
                    template['templates'][role_template]['endpoints'])

        return endpoints

    @classmethod
    def get_node_network_mapping(cls, node):
        """Get (network, endpoint) mappings for node with loaded template

        Returns a list of pairs (network, endpoint) for particular node
        for the case when template is loaded. Networks are aggregated for all
        node roles assigned to node. Endpoints are taken from 'endpoints' field
        of templates for every node role and they are mapped to networks from
        'network_assignments' field.
        """
        output = []
        endpoints = cls.get_node_endpoints(node)

        mappings = node.network_template['network_assignments']
        for netgroup, endpoint in six.iteritems(mappings):
            if endpoint['ep'] in endpoints:
                output.append((netgroup, endpoint['ep']))

        return output

    @classmethod
    def get_network_name_to_endpoint_mappings(cls, cluster):
        """Returns endpoint-to-network mappings for node groups in cluster

            {
                "node_group1": {
                    "endpoint1": "network_name1",
                    "endpoint2": "network_name2",
                    ...
                },
                ...
            }

        """
        output = {}
        template = cluster.network_config.configuration_template[
            'adv_net_template']

        for ng in cluster.node_groups:
            output[ng.id] = {}
            mappings = template[ng.name]['network_assignments']
            for network, endpoint in six.iteritems(mappings):
                output[ng.id][endpoint['ep']] = network

        return output

    @classmethod
    def assign_ips_in_node_group(cls, net_id, net_name, node_ids, ip_ranges):
        """Assigns IP addresses for nodes in given network."""
        ips_by_node_id = db().query(
            models.IPAddr.ip_addr,
            models.IPAddr.node
        ).filter_by(
            network=net_id
        )

        nodes_dont_need_ip = set()
        ips_in_use = set()
        for ip_str, node_id in ips_by_node_id:
            ip_addr = netaddr.IPAddress(ip_str)
            for ip_range in ip_ranges:
                if ip_addr in ip_range:
                    nodes_dont_need_ip.add(node_id)
                    ips_in_use.add(ip_str)

        nodes_need_ip = node_ids - nodes_dont_need_ip

        free_ips = cls.get_free_ips_from_ranges(
            net_name, ip_ranges, ips_in_use, len(nodes_need_ip))

        for ip, node_id in zip(free_ips, nodes_need_ip):
            logger.info(
                "Assigning IP for node '{0}' in network '{1}'".format(
                    node_id,
                    net_name
                )
            )
            ip_db = models.IPAddr(node=node_id,
                                  ip_addr=ip,
                                  network=net_id)
            db().add(ip_db)
        db().flush()

    @classmethod
    def assign_ips_for_nodes_w_template(cls, cluster, nodes):
        """Assign IPs for the case when network template is applied.

        IPs for every node are allocated only for networks which are mapped
        to the particular node according to the template.
        """
        network_by_group = db().query(
            models.NetworkGroup.id,
            models.NetworkGroup.name,
            models.NetworkGroup.meta,
        ).join(
            models.NetworkGroup.nodegroup
        ).filter(
            models.NodeGroup.cluster_id == cluster.id,
            models.NetworkGroup.name != consts.NETWORKS.fuelweb_admin
        )

        ip_ranges_by_network = db().query(
            models.IPAddrRange.first,
            models.IPAddrRange.last,
        ).join(
            models.NetworkGroup.ip_ranges,
            models.NetworkGroup.nodegroup
        ).filter(
            models.NodeGroup.cluster_id == cluster.id
        )

        for group_id, nodes_in_group in itertools.groupby(
                nodes, lambda n: n.group_id):

            net_names_by_node = {}
            for node in nodes_in_group:
                net_names_by_node[node.id] = \
                    set(x[0] for x in cls.get_node_network_mapping(node))

            networks = network_by_group.filter(
                models.NetworkGroup.group_id == group_id)
            for net_id, net_name, net_meta in networks:
                if not net_meta.get('notation'):
                    continue
                node_ids = set(node_id
                               for node_id, net_names
                               in six.iteritems(net_names_by_node)
                               if net_name in net_names)
                ip_ranges_ng = ip_ranges_by_network.filter(
                    models.IPAddrRange.network_group_id == net_id
                )
                ip_ranges = [netaddr.IPRange(r.first, r.last)
                             for r in ip_ranges_ng]

                cls.assign_ips_in_node_group(
                    net_id, net_name, node_ids, ip_ranges
                )

        cls.assign_admin_ips(nodes)

    @classmethod
    def _split_iface_name(cls, iface):
        try:
            iface, vlan = iface.split('.')
        except ValueError:
            vlan = None

        return (iface, vlan)

    @classmethod
    def get_interfaces_from_template(cls, node):
        """Parse transformations for all node role templates.

        Returns a list of bare interfaces and bonds.
        """
        transformations = \
            NeutronNetworkTemplateSerializer70.generate_transformations(node)

        interfaces = {}
        for tx in transformations:
            if tx['action'] == 'add-port':
                key = tx.get('bridge', tx['name'])
                interfaces[key] = {
                    'name': tx['name'],
                    'type': consts.NETWORK_INTERFACE_TYPES.ether
                }

            if tx['action'] == 'add-bond':
                key = tx.get('bridge', tx['name'])
                interfaces[key] = {
                    'name': tx['name'],
                    'slaves': [{'name': cls._split_iface_name(i)[0]}
                               for i in tx['interfaces']],
                    'type': consts.NETWORK_INTERFACE_TYPES.bond,
                    'bond_properties': tx.get('bond_properties', {})
                }

        return interfaces

    @classmethod
    def assign_networks_by_template(cls, node):
        """Configures a node's network-to-nic mapping based on its template.

        This also creates bonds in the database and ensures network
        groups are assigned to the correct interface or bond.
        """
        interfaces = cls.get_interfaces_from_template(node)

        endpoint_mapping = cls.get_node_network_mapping(node)
        em = dict((reversed(ep) for ep in endpoint_mapping))

        node_ifaces = {}
        for bridge, values in interfaces.items():
            network = em.get(bridge)
            # There is no network associated with this bridge (e.g. br-aux)
            if not network:
                continue

            iface, vlan = cls._split_iface_name(values['name'])

            node_ifaces.setdefault(iface, values)
            node_ifaces[iface].setdefault('assigned_networks', [])

            # Default admin network has no node group
            if network == consts.NETWORKS.fuelweb_admin:
                net_db = cls.get_admin_network_group(node.id)
            else:
                net_db = objects.NetworkGroup.get_from_node_group_by_name(
                    node.group_id, network)

            if not net_db:
                logger.warning(
                    ("Failed to assign network {0} on node {1}"
                     " because it does not exist.").format(network, node.id))
            else:
                # Ensure network_group configuration is consistent
                # with the template
                if vlan != net_db.vlan_start:
                    net_db.vlan_start = vlan
                    db().add(net_db)
                    db().flush()

                ng = {'id': net_db.id}
                node_ifaces[iface]['assigned_networks'].append(ng)

            if values['type'] == consts.NETWORK_INTERFACE_TYPES.ether:
                nic = objects.Node.get_nic_by_name(node, iface)
                node_ifaces[iface]['id'] = nic.id

        node_data = {
            'id': node.id,
            'interfaces': node_ifaces.values()
        }
        cls._update_attrs(node_data)


class NeutronManager80(AllocateVIPs80Mixin, NeutronManager70):

    @classmethod
    def assign_vip(cls, nodegroup, network_name,
                   vip_name=consts.NETWORK_VIP_TYPES.haproxy):
        """Idempotent assignment of VirtualIP addresses to nodegroup.
        Returns VIP for given nodegroup and network.

        It's required for HA deployment to have IP address
        not assigned to any of nodes. Currently we need one
        VIP per network in cluster. If cluster already has
        IP address from this network, it remains unchanged.
        If one of the nodes is the node from other cluster,
        this func will fail.

        :param nodegroup: Nodegroup instance
        :type nodegroup: NodeGroup model
        :param network_name: Network name
        :type  network_name: str
        :param vip_name: Type of VIP
        :type  vip_name: str
        :returns: assigned VIP (string)
        :raises: Exception
        """
        network = db().query(models.NetworkGroup).\
            filter_by(name=network_name, group_id=nodegroup.id).first()
        ips_in_use = None

        # FIXME:
        #   Built-in fuelweb_admin network doesn't belong to any node
        #   group, since it's shared between all clusters. So we need
        #   to handle this very special case if we want to be able
        #   to allocate VIP in default admin network.
        if not network and network_name == consts.NETWORKS.fuelweb_admin:
            network = cls.get_admin_network_group()

        if not network:
            raise errors.CanNotFindNetworkForNodeGroup(
                u"Network '{0}' for nodegroup='{1}' not found.".format(
                    network_name, nodegroup.name))

        cluster_vip = db().query(models.IPAddr).filter_by(
            network=network.id,
            node=None,
            vip_info={'name': vip_name}
        ).first()
        # check if cluster_vip is in required cidr: network.cidr
        if cluster_vip and cls.check_ip_belongs_to_net(cluster_vip.ip_addr,
                                                       network):
            return cluster_vip.ip_addr

        if network_name == consts.NETWORKS.fuelweb_admin:
            # Nodes not currently assigned to a cluster will still
            # have an IP from the appropriate admin network assigned.
            # So we much account for ALL admin IPs, not just the ones
            # allocated in the current cluster.
            node_ips = db().query(models.Node.ip).all()
            ips_in_use = set(ip[0] for ip in node_ips)

        # IP address has not been assigned, let's do it
        vip = cls.get_free_ips(network, ips_in_use=ips_in_use)[0]
        ne_db = models.IPAddr(network=network.id, ip_addr=vip,
                              vip_info={'name': vip_name})

        # delete stalled VIP address after new one was found.
        if cluster_vip:
            db().delete(cluster_vip)

        db().add(ne_db)
        db().flush()

        return vip
