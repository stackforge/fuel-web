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


from stevedore.extension import ExtensionManager

from nailgun.errors import errors
from nailgun.extensions import consts


def get_extensions_manager(**kwargs):
    """Loads Nailgun extension using stevedore

    :param kwargs: might be used for additional options for stevedore
                   ExtensionManager such as `on_load_failure_callback` boolean
    :returns: stevedore.extension.ExtensionManager object
    """
    return ExtensionManager(namespace=consts.EXTENSIONS_NAMESPACE, **kwargs)


def get_all_extensions():
    """Retrieves all available extensions for Nailgun

    :returns: generator of extensions objects
    """
    mgr = get_extensions_manager()
    return (ext.plugin for ext in mgr.extensions)


def get_extension(name):
    """Retrieves extension by name

    :param str name: name of the extension
    :returns: extension class
    """
    extension = next(
        (e for e in get_all_extensions() if e.name == name), None)

    if extension is None:
        raise errors.CannotFindExtension(
            "Cannot find extension with name '{0}'".format(name))

    return extension


def _get_extension_by_node_or_env(call_name, node):
    found_extension = None

    # Try to find extension in node
    if node:
        for extension in node.extensions:
            if call_name in get_extension(extension).provides:
                found_extension = extension

    # Try to find extension by environment
    if not found_extension and node.cluster:
        for extension in node.cluster.extensions:
            if call_name in get_extension(extension).provides:
                found_extension = extension

    if not found_extension:
        raise errors.CannotFindExtension(
            "Cannot find extension which provides "
            "'{0}' call".format(call_name))

    return get_extension(found_extension)


def node_extension_call(call_name, node, *args, **kwargs):
    extension = _get_extension_by_node_or_env(call_name, node)

    return getattr(extension, call_name)(node, *args, **kwargs)


def fire_callback_on_node_create(node):
    for extension in get_all_extensions():
        extension.on_node_create(node)


def fire_callback_on_node_update(node):
    for extension in get_all_extensions():
        extension.on_node_update(node)


def fire_callback_on_node_reset(node):
    for extension in get_all_extensions():
        extension.on_node_reset(node)


def fire_callback_on_node_delete(node):
    for extension in get_all_extensions():
        extension.on_node_delete(node)


def fire_callback_on_node_collection_delete(node_ids):
    for extension in get_all_extensions():
        extension.on_node_collection_delete(node_ids)


def fire_callback_on_cluster_delete(cluster):
    for extension in get_all_extensions():
        extension.on_cluster_delete(cluster)
