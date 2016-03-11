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

import collections
from distutils.version import StrictVersion

import six

from nailgun import consts
from nailgun.errors import errors
from nailgun.lcm.task_serializer import TasksSerializersFactory
from nailgun.logger import logger
from nailgun.utils.role_resolver import NameMatchingPolicy
from nailgun.utils.role_resolver import NullResolver


class TransactionSerializer(object):
    """The deploy tasks serializer."""

    min_supported_task_version = StrictVersion(consts.TASK_CROSS_DEPENDENCY)

    def __init__(self, context, role_resolver):
        self.role_resolver = role_resolver
        self.task_serializer_factory = TasksSerializersFactory(context)
        self.tasks_graph = collections.defaultdict(dict)

    @classmethod
    def serialize(cls, context, tasks, role_resolver):
        """Resolves roles and dependencies for tasks.

        :param context: the deployment context
        :param tasks: the deployment tasks
        :param role_resolver: the nodes role resolver
        :return: the list of serialized task per node
        """
        serializer = cls(context, role_resolver)
        serializer.process_tasks(tasks)
        serializer.resolve_dependencies()
        tasks_graph = serializer.tasks_graph
        for node_id in tasks_graph:
            tasks_graph[node_id] = list(
                six.itervalues(tasks_graph[node_id])
            )
        return tasks_graph

    @classmethod
    def ensure_task_based_deploy_allowed(cls, task):
        """Raises error if task does not support cross-dependencies.

        :param task: the task instance
        :raises: errors.TaskBaseDeploymentNotAllowed
        """
        return
        if task.get('type') == consts.ORCHESTRATOR_TASK_TYPES.stage:
            return

        task_version = StrictVersion(task.get('version', '1.0.0'))
        if task_version < cls.min_supported_task_version:
            logger.warning(
                "Task '%s' does not supported task based deploy.",
                task['id']
            )
            raise errors.TaskBaseDeploymentNotAllowed

    def process_tasks(self, tasks):
        """Process all deployment tasks

        :param tasks: the deployment tasks
        :return the mapping tasks per node
        """

        tasks_mapping = dict()
        groups = list()

        for task in tasks:
            self.ensure_task_based_deploy_allowed(task)

            if task.get('type') == consts.ORCHESTRATOR_TASK_TYPES.group:
                groups.append(task)
            else:
                tasks_mapping[task['id']] = task
                # self.process_task()
                # skip = not self.task_filter(task['id'])
                self.process_task(task, self.role_resolver)

        for task in groups:
            node_ids = self.role_resolver.resolve(task.get('role', ()))
            for sub_task_id in task.get('tasks', ()):
                try:
                    sub_task = tasks_mapping[sub_task_id]
                except KeyError:
                    raise errors.InvalidData(
                        'Task %s cannot be resolved', sub_task_id
                    )

                # if group is not excluded, all task should be run as well
                # otherwise check each task individually
                self.process_task(sub_task, NullResolver(node_ids))

        # make sure that null node is present
        self.tasks_graph.setdefault(None, dict())

    def process_task(self, task, role_resolver):
        """Processes one task one nodes of cluster.

        :param task: the task instance
        :param role_resolver: the role resolver
        """

        task_serializer = self.task_serializer_factory.create_serializer(task)
        for node_id in self.resolve_nodes(task, role_resolver):
            task = task_serializer.serialize(node_id)
            node_tasks = self.tasks_graph[node_id]
            # de-duplication the tasks on node
            # since task can be added after expand group need to
            # overwrite if existed task is skipped and new is not skipped.
            if self.need_update_task(node_tasks, task):
                node_tasks[task['id']] = task

    @staticmethod
    def resolve_nodes(task, role_resolver):
        if task.get('type') == consts.ORCHESTRATOR_TASK_TYPES.stage:
            return [None]
        # TODO(bgaifullin) remove deprecated groups
        return role_resolver.resolve(task.get('roles', task.get('groups')))

    def resolve_dependencies(self):
        """Resolves tasks dependencies."""

        for node_id, tasks in six.iteritems(self.tasks_graph):
            for task in six.itervalues(tasks):
                requires = set(self.expand_dependencies(
                    node_id, task.pop('requires', None)
                ))
                requires.update(self.expand_cross_dependencies(
                    node_id, task.pop('cross_depends', None)
                ))
                required_for = set(self.expand_dependencies(
                    node_id, task.pop('required_for', None)
                ))
                required_for.update(self.expand_cross_dependencies(
                    node_id, task.pop('cross_depended_by', None)
                ))
                # render
                if requires:
                    task['requires'] = [
                        dict(six.moves.zip(('name', 'node_id'), r))
                        for r in requires
                    ]
                if required_for:
                    task['required_for'] = [
                        dict(six.moves.zip(('name', 'node_id'), r))
                        for r in required_for
                    ]

    def expand_dependencies(self, node_id, dependencies):
        """Expands task dependencies on same node.

        :param node_id: the ID of target node
        :param dependencies: the list of dependencies on same node
        """
        if not dependencies:
            return

        # need to search dependencies on node and in sync points
        node_ids = [node_id, None]
        for name in dependencies:
            for rel in self.resolve_relation(name, node_ids):
                yield rel

    def expand_cross_dependencies(self, node_id, dependencies):
        """Expands task dependencies on same node.

        :param node_id: the ID of target node
        :param dependencies: the list of cross-node dependencies
        """
        if not dependencies:
            return

        for dep in dependencies:
            roles = dep.get('role', consts.TASK_ROLES.all)

            if roles == consts.TASK_ROLES.self:
                node_ids = [node_id]
            else:
                node_ids = self.role_resolver.resolve(
                    roles, dep.get('policy', consts.NODE_RESOLVE_POLICY.all)
                )
            relations = self.resolve_relation(dep['name'], node_ids)
            for rel in relations:
                yield rel

    def resolve_relation(self, name, node_ids):
        """Resolves the task relation.

        :param name: the name of task
        :param node_ids: the ID of nodes where need to search
        """
        match_policy = NameMatchingPolicy.create(name)
        for node_id in node_ids:
            for task_name in self.tasks_graph[node_id]:
                if match_policy.match(task_name):
                    yield task_name, node_id

    @classmethod
    def need_update_task(cls, tasks, task):
        """Checks that task shall overwrite existed one or should be added.

        :param tasks: the current node tasks
        :param task: the astute task object
        :return True if task is not present or must be overwritten
                otherwise False
        """
        existed_task = tasks.get(task['id'])
        if existed_task is None:
            return True

        if existed_task['type'] == task['type']:
            return False

        return task['type'] != consts.ORCHESTRATOR_TASK_TYPES.skipped
