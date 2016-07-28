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
import web

from nailgun.api.v1.handlers.base import CollectionHandler
from nailgun.api.v1.handlers.base import content
from nailgun.api.v1.handlers.base import SingleHandler
from nailgun.api.v1.validators.deployment_graph import DeploymentGraphValidator
from nailgun import objects
from nailgun.objects.serializers.deployment_graph import \
    DeploymentGraphSerializer
from nailgun import utils


class RelatedDeploymentGraphHandler(SingleHandler):
    """Handler for deployment graph related to model."""

    validator = DeploymentGraphValidator
    serializer = DeploymentGraphSerializer
    single = objects.DeploymentGraph
    related = None  # related should be substituted during handler inheritance

    @content
    def GET(self, obj_id, graph_type=None):
        """Get deployment graph.

        :param obj_id: related model ID
        :type obj_id: int|basestring
        :param graph_type: deployment graph type, default is 'default'
        :type graph_type: basestring

        :returns: Deployment graph
        :rtype: dict

        :http: * 200 OK
               * 400 (no graph of such type)
               * 404 (release object not found)
        """
        obj = self.get_object_or_404(self.related, int(obj_id))
        deployment_graph = self.single.get_for_model(obj, graph_type)
        if deployment_graph:
            return self.single.to_json(deployment_graph)
        else:
            raise self.http(404, "Graph with type: {0} is not defined".format(
                graph_type))

    @content
    def POST(self, obj_id, graph_type=None):
        """Create deployment graph.

        :param obj_id: related model ID
        :type obj_id: int|basestring
        :param graph_type: deployment graph type, default is 'default'
        :type graph_type: basestring

        :returns:  Deployment graph data
        :rtype: dict

        :http: * 200 (OK)
               * 400 (invalid data specified)
               * 409 (object already exists)

        """
        obj = self.get_object_or_404(self.related, int(obj_id))
        data = self.checked_data()
        deployment_graph = self.single.get_for_model(obj, graph_type)
        if deployment_graph:
            raise self.http(409, 'Deployment graph with type "{0}" already '
                                 'exist.'.format(graph_type))
        else:
            deployment_graph = self.single.create_for_model(
                data, obj, graph_type=graph_type)
            return self.single.to_json(deployment_graph)

    @content
    def PUT(self, obj_id, graph_type=None):
        """Update deployment graph.

        :param obj_id: related model ID
        :type obj_id: int|basestring
        :param graph_type: deployment graph type, default is 'default'
        :type graph_type: basestring

        :returns:  Deployment graph data
        :rtype: dict

        :http: * 200 (OK)
               * 400 (invalid data specified)
               * 404 (object not found in db)

        """
        obj = self.get_object_or_404(self.related, int(obj_id))
        data = self.checked_data()
        deployment_graph = self.single.get_for_model(obj, graph_type)
        if deployment_graph:
            self.single.update(deployment_graph, data)
            return self.single.to_json(deployment_graph)
        else:
            raise self.http(404, "Graph with type: {0} is not defined".format(
                graph_type))

    @content
    def PATCH(self, obj_id, graph_type=None):
        """Update deployment graph.

        :param obj_id: related model ID
        :type obj_id: int|basestring
        :param graph_type: deployment graph type, default is 'default'
        :type graph_type: basestring

        :returns:  Deployment graph data
        :rtype: dict

        :http: * 200 (OK)
               * 400 (invalid data specified)
               * 404 (object not found in db)
        """
        return self.PUT(obj_id, graph_type)

    def DELETE(self, obj_id, graph_type=None):
        """Delete deployment graph.

        :param obj_id: related model ID
        :type obj_id: int|basestring
        :param graph_type: deployment graph type, default is 'default'
        :type graph_type: basestring

        :http: * 204 (OK)
               * 404 (object not found in db)
        """

        obj = self.get_object_or_404(self.related, int(obj_id))
        deployment_graph = self.single.get_for_model(obj, graph_type)
        if deployment_graph:
            self.single.delete(deployment_graph)
        else:
            raise self.http(404, "Graph with type: {0} is not defined".format(
                graph_type))


class RelatedDeploymentGraphCollectionHandler(CollectionHandler):
    """Handler for deployment graphs related to the models collection."""

    validator = DeploymentGraphValidator
    collection = objects.DeploymentGraphCollection
    related = None  # related should be substituted during handler inheritance

    @content
    def GET(self, obj_id):
        """Get deployment graphs list for given object.

        :returns: JSONized object.

        :http: * 200 (OK)
               * 400 (invalid object data specified)
               * 404 (object not found in db)
        """
        related_model = self.get_object_or_404(self.related, int(obj_id))
        graphs = self.collection.get_for_model(related_model)
        return self.collection.to_json(graphs)


class DeploymentGraphHandler(SingleHandler):
    """Handler for fetching and deletion of the deployment graph."""

    validator = DeploymentGraphValidator
    single = objects.DeploymentGraph

    @content
    def DELETE(self, obj_id):
        """Delete deployment graph.

        :http: * 204 (OK)
               * 404 (object not found in db)
        """
        d_e = self.get_object_or_404(self.single, obj_id)
        self.single.delete(d_e)
        raise self.http(204)

    @content
    def PATCH(self, obj_id):
        return self.PUT(obj_id)


class DeploymentGraphCollectionHandler(CollectionHandler):
    """Handler for deployment graphs collection."""
    collection = objects.DeploymentGraphCollection

    @content
    def GET(self):
        """Get deployment graphs list with filtering.

        :returns: JSONized object.

        :http: * 200 (OK)
               * 400 (invalid object data specified)
               * 404 (object not found in db)
        :http GET params:
               * clusters_ids = comma separated list of clusters IDs
               * plugins_ids = comma separated list of plugins IDs
               * releases_ids = comma separated list of releases IDs
               * graph_types = comma separated list of deployment graph types
               * fetch_related = 0/1 bool value that enables fetching graphs
                 related to clusters release and plugins (default=0/False)
        """

        def _get_list_web_arg(attr):
            input_defaults = {attr: None}
            web_input = getattr(web.input(**input_defaults), attr)
            if web_input:
                return web_input.split(',')

        # process args
        clusters_ids = _get_list_web_arg('clusters_ids')
        plugins_ids = _get_list_web_arg('plugins_ids')
        releases_ids = _get_list_web_arg('releases_ids')
        graph_types = _get_list_web_arg('graph_types')
        fetch_related = utils.parse_bool(
            web.input(fetch_related='0').fetch_related
        )

        entities = []  # here all objects for which related graphs is fetched

        # almost nothing to filter
        no_filters = not (clusters_ids or plugins_ids or releases_ids)

        if no_filters:
            if not graph_types:  # no conditions at all
                return self.collection.to_json(self.collection.all())
            else:
                return self.collection.to_json(
                    self.collection.filter_by_graph_types(graph_types)
                )

        if clusters_ids:
            entities.extend(
                objects.ClusterCollection.filter_by_id_list(
                    None, clusters_ids
                ).all()
            )
        if plugins_ids:
            entities.extend(
                objects.PluginCollection.filter_by_id_list(
                    None, plugins_ids
                ).all()
            )
        if releases_ids:
            entities.extend(
                objects.ReleaseCollection.filter_by_id_list(
                    None, releases_ids
                ).all()
            )

        return self.collection.to_json(
            self.collection.get_related_graphs(
                entities, graph_types, fetch_related
            )
        )
