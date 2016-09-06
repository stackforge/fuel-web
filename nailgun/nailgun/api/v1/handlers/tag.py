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

"""
Handlers dealing with tags
"""
from nailgun.api.v1.handlers.base import BaseHandler
from nailgun.api.v1.handlers.base import CollectionHandler
from nailgun.api.v1.handlers.base import handle_errors
from nailgun.api.v1.handlers.base import SingleHandler

from nailgun.api.v1.validators.base import BasicValidator
from nailgun.api.v1.validators.tag import TagValidator

from nailgun import objects


class TagHandler(SingleHandler):
    """Tag single handler"""

    single = objects.Tag
    validator = TagValidator


class TagCollectionHandler(CollectionHandler):
    """Tag collection handler"""

    collection = objects.TagCollection
    validator = TagValidator


class NodeTagAssignmentHandler(BaseHandler):

    validator = BasicValidator

    @handle_errors
    def POST(self, node_id):
        node = self.get_object_or_404(
            objects.Node,
            node_id
        )

        data = self.checked_data(
            self.validator.validate
        )

        tags = self.get_objects_list_or_404(
            objects.TagCollection,
            data
        )

        objects.Node.assign_tags(node, tags)
        raise self.http(200, None)


class NodeTagUnassignmentHandler(BaseHandler):

    validator = BasicValidator

    @handle_errors
    def POST(self, node_id):
        node = self.get_object_or_404(
            objects.Node,
            node_id
        )

        data = self.checked_data(
            self.validator.validate
        )

        tags = self.get_objects_list_or_404(
            objects.TagCollection,
            data
        )

        objects.Node.unassign_tags(node, tags)
        raise self.http(200, None)
