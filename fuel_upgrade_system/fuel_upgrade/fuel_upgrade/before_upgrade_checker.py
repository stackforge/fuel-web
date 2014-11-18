# -*- coding: utf-8 -*-

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

import abc

import requests
import six

from fuel_upgrade import errors
from fuel_upgrade import utils

from fuel_upgrade.clients import NailgunClient
from fuel_upgrade.clients import OSTFClient
from fuel_upgrade.logger import upgrade_logger


logger = upgrade_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseBeforeUpgradeChecker(object):
    """Base class for before ugprade checkers
    """

    @abc.abstractmethod
    def check(self):
        """Run check
        """


class CheckNoRunningTasks(BaseBeforeUpgradeChecker):
    """Checks that there is no running tasks

    :param config: config object where property endpoints
                   returns dict with nailgun host and port
    """

    def __init__(self, context):
        nailgun = context.config.endpoints['nginx_nailgun']
        self.nailgun_client = NailgunClient(**nailgun)

    def check(self):
        """Sends request to nailgun
        to make sure that there are no
        running tasks
        """
        logger.info('Check nailgun tasks')

        try:
            tasks = self.nailgun_client.get_tasks()
        except requests.ConnectionError:
            raise errors.NailgunIsNotRunningError(
                'Cannot connect to rest api service')

        logger.debug('Nailgun tasks %s', tasks)

        running_tasks = filter(
            lambda t: t['status'] == 'running', tasks)

        if running_tasks:
            tasks_msg = ['id={0} cluster={1} name={2}'.format(
                t.get('id'),
                t.get('cluster'),
                t.get('name')) for t in running_tasks]

            error_msg = 'Cannot run upgrade, tasks are running: {0}'.format(
                ' '.join(tasks_msg))

            raise errors.CannotRunUpgrade(error_msg)


class CheckNoRunningOstf(BaseBeforeUpgradeChecker):
    """Checks that there's no running OSTF tasks.

    :param context: a context object with config and required space info
    """

    def __init__(self, context):
        self.ostf = OSTFClient(**context.config.endpoints['ostf'])

    def check(self):
        logger.info('Check OSTF tasks')

        try:
            tasks = self.ostf.get_tasks()
        except requests.ConnectionError:
            raise errors.OstfIsNotRunningError(
                'Cannot connect to OSTF service.')

        logger.debug('OSTF tasks: %s', tasks)

        running_tasks = filter(
            lambda t: t['status'] == 'running', tasks)

        if running_tasks:
            raise errors.CannotRunUpgrade(
                'Cannot run upgrade since there are OSTF running tasks.')


class CheckFreeSpace(BaseBeforeUpgradeChecker):
    """Checks that there is enough free space on devices

    :param list upgraders: list of upgarde engines
    """

    def __init__(self, context):
        self.required_spaces = context.required_free_spaces

    def check(self):
        """Check free space
        """
        logger.info('Check if devices have enough free space')
        logger.debug(
            'Required spaces from upgrade '
            'engines %s', self.required_spaces)

        mount_points = self.space_required_for_mount_points()
        logger.debug(
            'Mount points and sum of required spaces '
            '%s', mount_points)

        error_mount_point = self.list_of_error_mount_points(mount_points)
        logger.debug(
            "Mount points which don't have "
            "enough free space %s", error_mount_point)

        self.check_result(error_mount_point)

    def space_required_for_mount_points(self):
        """Iterates over required spaces generates
        list of mount points with sum of required space

        :returns: dict where key is mount point
                  and value is required free space
        """
        sum_of_spaces = {}
        for required_space in self.required_spaces:
            if not required_space:
                continue

            for path, size in sorted(required_space.items()):
                mount_path = utils.find_mount_point(path)
                sum_of_spaces.setdefault(mount_path, 0)
                sum_of_spaces[mount_path] += size

        return sum_of_spaces

    def list_of_error_mount_points(self, mount_points):
        """Returns list of devices which don't have
        enough free space

        :param list mount_points: elements are dicts
                  where key is path to mount point
                  and value is required space for
                  this mount point
        :returns: list where elements are dicts
                  {'path': 'path to mount point',
                   'size': 'required free space'
                   'available': 'available free space'}
        """
        free_space_error_devices = []
        for path, required_size in sorted(mount_points.items()):
            free_space = utils.calculate_free_space(path)

            if free_space < required_size:
                free_space_error_devices.append({
                    'path': path,
                    'size': required_size,
                    'available': free_space})

        return free_space_error_devices

    def check_result(self, error_devices):
        """Checks if there are some devices which
        don't have enough free space for upgrades

        :raises: NotEnoughFreeSpaceOnDeviceError
        """
        if not error_devices:
            return

        devices_msg = [
            'device {0} ('
            'required {1}MB, '
            'available {2}MB, '
            'not enough {3}MB'
            ')'.format(
                d['path'],
                d['size'],
                d['available'],
                d['size'] - d['available']) for d in error_devices]

        err_msg = 'Not enough free space on device: {0}'.format(
            ', '.join(devices_msg))

        raise errors.NotEnoughFreeSpaceOnDeviceError(err_msg)


class CheckUpgradeVersions(BaseBeforeUpgradeChecker):
    """Checks that it is possible to upgarde from
    current version to new one.

    :param config: config object
    """

    def __init__(self, context):
        config = context.config
        #: version of fuel which user wants to upgrade from
        self.from_version = config.from_version
        #: version of fuel which user wants to upgrade to
        self.to_version = config.new_version

    def check(self):
        """Compares two versions previous and new

        :raises: WrongVersionError
        """
        logger.info('Check upgrade versions')

        result = utils.compare_version(self.from_version, self.to_version)
        err_msg = None
        if result == 0:
            err_msg = 'Cannot upgrade to the same version of fuel ' \
                      '{0} -> {1}'.format(
                          self.from_version, self.to_version)
        elif result == -1:
            err_msg = 'Cannot upgrade from higher version of fuel ' \
                      'to lower {0} -> {1}'.format(
                          self.from_version, self.to_version)

        if err_msg:
            raise errors.WrongVersionError(err_msg)


class CheckRequiredVersion(BaseBeforeUpgradeChecker):
    """Checks that user's going to upgrade Fuel from the required version.

    :param context: a context object with config and required space info
    """

    def __init__(self, context):
        #: version of fuel which user wants to upgrade from
        self.from_version = context.config.from_version
        #: a list of versions from which user can upgrade
        self.can_upgrade_from = context.config.can_upgrade_from

    def check(self):
        logger.info('Check required Fuel version')

        if self.from_version not in self.can_upgrade_from:
            raise errors.WrongVersionError(
                'Cannot upgrade from Fuel {0}. You can upgrade only from '
                'one of next versions: {1}'.format(
                    self.from_version, ', '.join(self.can_upgrade_from)))
