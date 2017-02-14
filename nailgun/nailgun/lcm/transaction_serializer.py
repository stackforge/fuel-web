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

import datetime
from distutils.version import StrictVersion
import functools
import multiprocessing
import os
import pickle
from Queue import Queue
import threading
import yaml

import dispy
import six

from nailgun import consts
from nailgun import errors
from nailgun.lcm.task_serializer import Context
from nailgun.lcm.task_serializer import TasksSerializersFactory
from nailgun.logger import logger
from nailgun import objects
from nailgun.settings import settings
from nailgun.utils.resolvers import NameMatchingPolicy


# This class has similar functional with TasksSerializer from task deploy
# but there is no chance to re-use TasksSerializer until bug
# https://bugs.launchpad.net/fuel/+bug/1562292 is not fixed


def _serialize_task_for_node(factory, node_and_task):
    node_id, task = node_and_task
    logger.debug(
        "applying task '%s' for node: %s", task['id'], node_id
    )
    try:
        task_serializer = factory.create_serializer(task)
        serialized = task_serializer.serialize(node_id)
        return node_id, serialized
    except Exception:
        logger.exception(
            "failed to serialize task '%s' for node: %s", task['id'], node_id
        )
        raise


def _initialize_worker(serializers_factory, context):
    globals()['__factory'] = serializers_factory(context)


def _serialize_task_for_node_in_worker(node_and_task_and_err):
    node_and_task, err = node_and_task_and_err

    # NOTE(el): See comment for `wrap_task_iter` method.
    if err:
        raise err

    return _serialize_task_for_node(globals()['__factory'], node_and_task)


class SingleWorkerConcurrencyPolicy(object):
    def execute(self, context, serializers_factory, tasks):
        """Executes task serialization synchronously, task by task.

        :param context: the transaction context
        :param serializers_factory: the serializers factory
        :param tasks: the tasks to serialize
        :return sequence of serialized tasks
        """
        factory = serializers_factory(context)
        return six.moves.map(
            lambda x: _serialize_task_for_node(factory, x),
            tasks
        )


def wrap_task_iter(iterator):
    """Workaround is required to prevent deadlock.

    Due to a bug in core python library [1], if iterator passed
    to imap or imap_unordered raises an exception, it hangs in
    deadlock forever, the issue is fixed in python 2.7.10, but
    upstream repositories have much older version.

    [1] http://bugs.python.org/issue23051
    """
    try:
        for i in iterator:
            yield i, None
    except Exception as e:
        yield (None, None), e


class MultiProcessingConcurrencyPolicy(object):
    def __init__(self, workers_num):
        self.workers_num = workers_num

    def execute(self, context, serializers_factory, tasks):
        """Executes task serialization in parallel.

        :param context: the transaction context
        :param serializers_factory: the serializers factory
        :param tasks: the tasks to serialize
        :return sequence of serialized tasks
        """
        pool = multiprocessing.Pool(
            processes=self.workers_num,
            initializer=_initialize_worker,
            initargs=(serializers_factory, context)
        )

        try:
            result = pool.imap_unordered(
                _serialize_task_for_node_in_worker, wrap_task_iter(tasks)
            )
            for r in result:
                yield r
        except Exception:
            pool.terminate()
            raise
        else:
            pool.close()
        finally:
            pool.join()


def _dispy_setup_computation_node(context_file, settings_data_file):
    """Loads the context and settings into memory

    This function is called before computation on the dispy node.
    Function must return 0 on success. This is checked by dispy

    :return: 0
    """
    global __dispy_context, __dispy_settings_config

    import pickle
    import yaml

    with open(context_file) as f:
        __dispy_context = pickle.load(f)

    with open(settings_data_file) as f:
        __dispy_settings_config = yaml.safe_load(f)

    return 0


def _dispy_cleanup_computation_node():
    """Removes loaded context and settings

    This function is called after computation finished on the dispy node.
    """
    global __dispy_context, __dispy_settings_config
    del __dispy_context, __dispy_settings_config


def _dispy_serialize_task_for_node(formatter_context, node_and_task):
    """Remote serialization call for DistributedProcessingPolicy

    Code of the function is copied to the workers and executed there, thus
    we are including all required imports inside the function.

    :param formatter_context: formatter context
    :param node_and_task: tuple of node_id and task data
    :return: (node_id, serialized), error
    """

    from nailgun.lcm.task_serializer import TasksSerializersFactory
    from nailgun.settings import settings

    try:
        node_id, task = node_and_task

        # Restoring settings
        settings.config = __dispy_settings_config  # noqa: F821
        formatter_context['SETTINGS'] = settings

        # Loading context
        factory = TasksSerializersFactory(__dispy_context)  # noqa: F821
        serializer = factory.create_serializer(task)

        serialized = serializer.serialize(
            node_id, formatter_context=formatter_context)

        return (node_id, serialized), None

    except Exception as e:
        return (node_id, None), e


class DistributedProcessingPolicy(object):

    resubmit_statuses = (dispy.DispyJob.Cancelled, dispy.DispyJob.Abandoned,
                         dispy.DispyJob.Terminated)

    def __init__(self, transaction):
        self.upper_bound = settings.LCM_DS_JOBS_UPPER_BOUND
        self.lower_bound = settings.LCM_DS_JOBS_LOWER_BOUND
        # Use Condition variable to protect access to pending_jobs,
        # as '_job_callback' is executed in another thread
        self.jobs_cond = threading.Condition()
        self.pending_jobs = {}
        self.ready_jobs = Queue()
        self.transaction = transaction
        self.job_cluster = None
        self.context = None

    def _job_callback(self, job):
        logger.debug("Callback for job '%s' called. Job has status '%s'",
                     job.id, job.status)

        resubmit_job = job.status in self.resubmit_statuses

        if resubmit_job or job.status == dispy.DispyJob.Finished:

            # 'pending_jobs' is shared between two threads, so access it with
            # 'jobs_cond' (see below)
            self.jobs_cond.acquire()

            try:
                if job.id:  # Job may have finished before 'main' assigned id

                    if job.id in self.pending_jobs:
                        logger.debug("Callback for job '%s' called with %s. "
                                     "Pending jobs count: %s",
                                     job.id, job.result,
                                     len(self.pending_jobs))
                        if resubmit_job:
                            logger.debug("Job %s has status %s and going to "
                                         "be resubmitted", job.id, job.status)
                            submit_args = self.pending_jobs[job.id]
                            self.job_cluster.submit(*submit_args)
                        else:
                            logger.debug("Adding result of job '%s' to the "
                                         "ready_jobs queue. Job result: %s",
                                         job.id, job.result)
                            self.ready_jobs.put(job.result)
                            self.pending_jobs.pop(job.id)
                    else:
                        logger.warning("Callback for job '%s' called when job "
                                       "is already removed from pending. "
                                       "Pending jobs count: %s",
                                       job.id, len(self.pending_jobs))

                    if len(self.pending_jobs) <= self.lower_bound:
                        self.jobs_cond.notify()
                else:
                    # If job has no id and is not finished it will be
                    # resubmitted in the 'execute' function. Finished job
                    # will be placed directly to ready_jobs
                    if not resubmit_job:
                        logger.debug("Callback is called for job without id. "
                                     "Adding directly to the ready_jobs "
                                     "queue. Job result: %s", job.result)
                        self.ready_jobs.put(job.result)

            finally:
                self.jobs_cond.release()

    def _save_context(self, context):
        """Saves transaction context into file

        :param context: transaction context
        :return: file name of saved context
        """
        file_name = '{0}_context.p'.format(self.transaction.id)
        logger.debug("Saving context to the master node: %s", file_name)
        context_file = os.path.join(settings.LCM_DS_WORKING_DIR, file_name)
        with open(context_file, mode='w') as f:
            pickle.dump(context, f)
        return context_file

    def _save_settings(self, settings_data):
        """Saves settings data into file

        :param settings_data: settings data
        :return: file name of saved settings
        """
        file_name = '{0}_settings.yaml'.format(self.transaction.id)
        logger.debug("Saving settings to the master node: %s", file_name)
        settings_data_file = os.path.join(settings.LCM_DS_WORKING_DIR,
                                          file_name)
        with open(settings_data_file, mode='w') as f:
            yaml.safe_dump(settings_data, f)
        return settings_data_file

    def _create_job_cluster(self, context):
        """Configures and creates JobCluster

        Context and settings will be saved into files and passed to
        each dispy node.

        :param context: transaction context
        :return: dispy.JobCluster
        """
        now = datetime.datetime.utcnow()
        recover_name = settings.LCM_DS_RECOVER_FILE_TPL.format(
            self.transaction.id, now.strftime('%Y%m%d%H%M%S%f')
        )
        recover_file = os.path.join(settings.LCM_DS_WORKING_DIR, recover_name)

        context_file = self._save_context(context)
        settings_data_file = self._save_settings(settings.config)

        # Adding cluster nodes to the JobCluster
        if settings.LCM_DS_NODES:
            nodes = settings.LCM_DS_NODES
        else:
            nodes = ['localhost']
            for node in self.transaction.cluster.nodes:
                logger.debug("Adding node %s (%s) to the job cluster",
                             node.id, node.ip)
                nodes.append(node.ip)

        self.job_cluster = dispy.JobCluster(
            _dispy_serialize_task_for_node,
            callback=self._job_callback,
            loglevel=logger.level,
            pulse_interval=settings.LCM_DS_JOB_PULSE,
            ping_interval=settings.LCM_DS_NODE_PING,
            reentrant=True,
            nodes=nodes,
            port=settings.LCM_DS_JOB_CLUSTER_PORT,
            recover_file=recover_file,
            depends=[context_file, settings_data_file],
            setup=functools.partial(_dispy_setup_computation_node,
                                    context_file,
                                    settings_data_file),
            cleanup=_dispy_cleanup_computation_node
        )

    def _destroy_job_cluster(self):
        """Destroys job cluster"""
        self.job_cluster.wait()
        self.job_cluster.print_status()
        self.job_cluster.close()
        self.job_cluster = None
        logger.debug("Job cluster destroyed")

    def _get_ready_jobs(self):
        while not self.ready_jobs.empty():
            (node_id, serialized), exc = self.ready_jobs.get()
            logger.debug("Got ready job on node %s, serialized: %s, error: %s",
                         node_id, serialized, exc)
            self.ready_jobs.task_done()
            if exc is not None:
                raise exc
            yield node_id, serialized

    def execute(self, context, _, tasks):
        """Executes task serialization on distributed nodes

        :param context: the transaction context
        :param _: the serializers factory
        :param tasks: the tasks to serialize
        :return sequence of serialized tasks
        """
        logger.debug("Performing distributed tasks processing")
        self._create_job_cluster(context)

        task_context = Context(context)
        formatter_contexts_idx = {}

        try:
            for task in tasks:
                node_id, task_data = task
                task_id = task_data['id']
                job_id = '{0}-{1}'.format(node_id, task_id)

                # Checking formatter context is already calculated
                if node_id not in formatter_contexts_idx:
                    formatter_context = task_context.get_formatter_context(
                        node_id)
                    # Settings file is already sent to the workers
                    formatter_context.pop('SETTINGS', None)
                    formatter_contexts_idx['node_id'] = formatter_context
                else:
                    formatter_context = formatter_contexts_idx['node_id']

                logger.debug("Creating job for task: '%s' on node: %s",
                             task_id, node_id)
                submit_args = formatter_context, task
                job = self.job_cluster.submit(*submit_args)

                self.jobs_cond.acquire()
                try:
                    job.id = job_id
                    # There is a chance the job may have finished and
                    # job_callback called by this time, so put it in
                    # 'pending_jobs' only if job is pending
                    if job.status in (dispy.DispyJob.Created,
                                      dispy.DispyJob.Running):
                        self.pending_jobs[job_id] = submit_args
                        logger.debug(
                            "Job '%s' submitted. Pending jobs count: %s",
                            job.id, len(self.pending_jobs)
                        )

                        if len(self.pending_jobs) >= self.upper_bound:
                            while len(self.pending_jobs) > self.lower_bound:
                                self.jobs_cond.wait()

                        for ready_job in self._get_ready_jobs():
                            yield ready_job

                    elif job.status in self.resubmit_statuses:
                        # Resubmitted task has job_id and it is already
                        # in pending_jobs, so all following resubmits will be
                        # performed in the _job_callback. We are inside of
                        # synchronization block, thus it is safe to add job
                        # into pending_jobs.
                        self.pending_jobs[job_id] = submit_args
                        resubmit_job = self.job_cluster.submit(*submit_args)
                        resubmit_job.id = job_id
                        logger.debug(
                            "Job '%s' re-submitted. Pending jobs count: %s",
                            resubmit_job.id, len(self.pending_jobs)
                        )

                except Exception:
                    logger.exception("Task processing failed: %s",
                                     task_data['id'])
                    raise
                finally:
                    self.jobs_cond.release()

        finally:
            logger.debug("Distributed tasks processing finished")
            self._destroy_job_cluster()

        for ready_job in self._get_ready_jobs():
            yield ready_job


def is_distributed_processing_enabled(transaction):
    if settings.LCM_DS_ENABLED:
        return True
    attrs = objects.Cluster.get_editable_attributes(transaction.cluster)
    policy = attrs.get('common', {}).get('serialization_policy', {})
    return policy.get('value') == consts.SERIALIZATION_POLICY.distributed


def get_processing_policy(transaction):
    if is_distributed_processing_enabled(transaction):
        return DistributedProcessingPolicy(transaction)
    cpu_num = settings.LCM_SERIALIZERS_CONCURRENCY_FACTOR
    if not cpu_num:
        try:
            cpu_num = multiprocessing.cpu_count()
        except NotImplementedError:
            cpu_num = 1

    if cpu_num > 1:
        return MultiProcessingConcurrencyPolicy(cpu_num)
    return SingleWorkerConcurrencyPolicy()


class TransactionSerializer(object):
    """The deploy tasks serializer."""

    serializer_factory_class = TasksSerializersFactory

    min_supported_task_version = StrictVersion(consts.TASK_CROSS_DEPENDENCY)

    unversioned_task_types = (
        consts.ORCHESTRATOR_TASK_TYPES.stage,
        consts.ORCHESTRATOR_TASK_TYPES.skipped
    )

    def __init__(self, transaction, context, resolver):
        self.resolver = resolver
        self.context = context
        self.tasks_graph = {}
        self.tasks_dictionary = {}
        # the list of groups, that contains information about
        # ids of nodes in this group and how many nodes in this group can fail
        # and deployment will not be interrupted
        self.fault_tolerance_groups = []
        self.processing_policy = get_processing_policy(transaction)

    @classmethod
    def serialize(cls, transaction, context, tasks, resolver):
        """Resolves roles and dependencies for tasks.

        :param transaction: transaction
        :param context: the deployment context
        :param tasks: the deployment tasks
        :param resolver: the nodes tag resolver
        :return: the list of serialized task per node
        """
        serializer = cls(transaction, context, resolver)
        serializer.process_tasks(tasks)
        serializer.resolve_dependencies()
        tasks_graph = serializer.tasks_graph
        for node_id in tasks_graph:
            tasks_graph[node_id] = list(
                six.itervalues(tasks_graph[node_id])
            )

        return (
            serializer.tasks_dictionary,
            tasks_graph,
            {'fault_tolerance_groups': serializer.fault_tolerance_groups}
        )

    @classmethod
    def ensure_task_based_deploy_allowed(cls, task):
        """Raises error if task does not support cross-dependencies.

        :param task: the task instance
        :raises: errors.TaskBaseDeploymentNotAllowed
        """
        if task.get('type') in cls.unversioned_task_types:
            return

        version = StrictVersion(task.get('version', '0.0.0'))
        if version < cls.min_supported_task_version:
            message = (
                "Task '{0}' does not support cross-dependencies.\n"
                "You can enable option 'propagate_task_deploy'"
                "for cluster to use task adaptation mechanism."
                .format(task['id'])
            )
            logger.warning(message)
            if settings.LCM_CHECK_TASK_VERSION:
                raise errors.TaskBaseDeploymentNotAllowed(message)

    def process_tasks(self, tasks):
        """Process all deployment tasks

        :param tasks: the deployment tasks
        :return the mapping tasks per node
        """
        serialized = self.processing_policy.execute(
            self.context,
            self.serializer_factory_class,
            self.expand_tasks(tasks)
        )

        for node_and_task in serialized:
            node_id, task = node_and_task
            node_tasks = self.tasks_graph.setdefault(node_id, {})
            # de-duplication the tasks on node
            # since task can be added after expanding of group need to
            # overwrite task if existed task is skipped and new is not skipped.
            if self.need_update_task(node_tasks, task):
                node_tasks[task['id']] = task

        # make sure that null node is present
        self.tasks_graph.setdefault(None, {})

    def expand_tasks(self, tasks):
        groups = []
        tasks_mapping = {}

        for task in tasks:
            if task.get('type') == consts.ORCHESTRATOR_TASK_TYPES.group:
                groups.append(task)
            else:
                self.ensure_task_based_deploy_allowed(task)
                tasks_mapping[task['id']] = task
                for node_id in self.resolve_nodes(task):
                    yield node_id, task

        for task in groups:
            node_ids = self.resolver.resolve(
                task.get('tags', task.get('roles', task.get('groups')))
            )
            if not node_ids:
                continue

            for sub_task_id in task.get('tasks', ()):
                try:
                    sub_task = tasks_mapping[sub_task_id]
                except KeyError:
                    msg = 'Task {0} cannot be resolved'.format(sub_task_id)
                    logger.error(msg)
                    raise errors.InvalidData(msg)
                # if group is not excluded, all task should be run as well
                # otherwise check each task individually
                for node_id in node_ids:
                    yield node_id, sub_task

            self.fault_tolerance_groups.append({
                'name': task['id'],
                'node_ids': list(node_ids),
                'fault_tolerance': self.calculate_fault_tolerance(
                    task.get('fault_tolerance'), len(node_ids)
                )
            })

    def resolve_nodes(self, task):
        if task.get('type') == consts.ORCHESTRATOR_TASK_TYPES.stage:
            # all synchronisation tasks will run on sync node
            return [None]
        # TODO(bgaifullin) remove deprecated groups
        return self.resolver.resolve(
            task.get('tags', task.get('roles', task.get('groups')))
        )

    def resolve_dependencies(self):
        """Resolves tasks dependencies."""

        for node_id, tasks in six.iteritems(self.tasks_graph):
            for task_id, task in six.iteritems(tasks):
                requires = set(self.expand_dependencies(
                    node_id, task.pop('requires', None)
                ))
                requires.update(self.expand_cross_dependencies(
                    task_id, node_id, task.pop('cross_depends', None)
                ))
                required_for = set(self.expand_dependencies(
                    node_id, task.pop('required_for', None)
                ))
                required_for.update(self.expand_cross_dependencies(
                    task_id, node_id, task.pop('cross_depended_by', None)
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

    def expand_cross_dependencies(self, task_id, node_id, dependencies):
        """Expands task dependencies on same node.

        :param task_id: the ID of task
        :param node_id: the ID of target node
        :param dependencies: the list of cross-node dependencies
        """
        if not dependencies:
            return

        for dep in six.moves.filter(None, dependencies):
            roles = dep.get('tags', dep.get('role', consts.TASK_ROLES.all))

            if roles == consts.TASK_ROLES.self:
                node_ids = [node_id]
                excludes = []
            elif roles is None:
                node_ids = [None]
                excludes = []
            else:
                node_ids = self.resolver.resolve(
                    roles, dep.get('policy', consts.NODE_RESOLVE_POLICY.all)
                )
                excludes = [(task_id, node_id)]

            relations = self.resolve_relation(dep['name'], node_ids, excludes)
            for rel in relations:
                yield rel

    def resolve_relation(self, name, node_ids, excludes=None):
        """Resolves the task relation.

        :param name: the name of task
        :param node_ids: the ID of nodes where need to search
        :param excludes: the nodes to exclude
        """
        match_policy = NameMatchingPolicy.create(name)
        for node_id in node_ids:
            for task_name in self.tasks_graph.get(node_id, ()):
                if excludes and (task_name, node_id) in excludes:
                    continue
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

    @classmethod
    def calculate_fault_tolerance(cls, percentage_or_value, total):
        """Calculates actual fault tolerance value.

        :param percentage_or_value: the fault tolerance as percent of nodes
            that can fail or actual number of nodes,
            the negative number means the number of nodes
            which have to deploy successfully.
        :param total: the total number of nodes in group
        :return: the actual number of nodes that can fail
        """
        if percentage_or_value is None:
            # unattainable number
            return total + 1

        if isinstance(percentage_or_value, six.string_types):
            percentage_or_value = percentage_or_value.strip()

        try:
            if (isinstance(percentage_or_value, six.string_types) and
                    percentage_or_value[-1] == '%'):
                value = (int(percentage_or_value[:-1]) * total) // 100
            else:
                value = int(percentage_or_value)

            if value < 0:
                # convert negative value to number of nodes which may fail
                value = max(0, total + value)
            return value
        except ValueError as e:
            logger.error(
                "Failed to handle fault_tolerance: '%s': %s. it is ignored",
                percentage_or_value, e
            )
            # unattainable number
            return total + 1
