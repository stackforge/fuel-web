# -*- coding: utf-8 -*-
#
#    Copyright 2013-2014 Mirantis, Inc.
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

from tests.base import BaseTestCase


class TestHandlers(BaseTestCase):

    def test_node_action(self):
        help_msg = ["fuel node [-h] [--env ENV]",
                    "[--list | --set | --delete | --network | --disk |"
                    " --deploy | --delete-from-db | --provision]", "-h",
                    "--help", " -s", "--default", " -d", "--download", " -u",
                    "--upload", "--dir", "--node", "--node-id", " -r",
                    "--role", "--net"]
        self.check_all_in_msg("help node", help_msg)

        self.check_for_rows_in_table("node --quiet")

        for action in ("set", "remove", "--network", "--disk"):
            self.check_if_required("node {0}".format(action))

        self.load_data_to_nailgun_server()
        self.check_number_of_rows_in_table(
            "node --node 9f:b7,9d:24,ab:aa --quiet",
            3
        )

    def test_selected_node_deploy_or_provision(self):
        self.load_data_to_nailgun_server()
        self.run_cli_commands((
            "environment-create NewEnv 1 --quiet",
            "--env-id=1 node set --node 1 --role=controller --quiet"
        ))
        commands = ("--provision", "--deploy")
        for action in commands:
            self.check_if_required(
                "--env-id=1 node {0}".format(action)
            )
        messages = (
            "Started provisioning nodes [1].\n",
            "Started deploying nodes [1].\n"
        )
        for cmd, msg in zip(commands, messages):
            self.check_for_stdout(
                "--env-id=1 node {0} --node=1 --quiet".format(cmd),
                msg
            )

    def test_check_wrong_server(self):
        os.environ["SERVER_ADDRESS"] = "0"
        result = self.run_cli_command("-h", check_errors=True)
        self.assertEqual(result.stderr, '')
        del os.environ["SERVER_ADDRESS"]

    def test_wrong_credentials(self):
        result = self.run_cli_command(
            "--os-username=a --os-password=a node --quiet",
            check_errors=True
        )
        self.assertEqual(result.stderr,
        '\n        Unauthorized: need authentication!\n'
        '        Please provide user and password via client --os-username '
        '--os-password\n        or modify "KEYSTONE_USER" and "KEYSTONE_PASS" '
        'in\n        /etc/fuel/client/config.yaml\n')

    def test_destroy_node(self):
        self.load_data_to_nailgun_server()
        self.run_cli_commands((
            "environment-create NewEnv 1 --quiet",
            "--env-id=1 node set --node 1 --role=controller --quiet"
        ))
        msg = ("Nodes with id [1] has been deleted from fuel db.\n"
               "You should still delete node from cobbler\n")
        self.check_for_stdout(
            "node --node 1 --delete-from-db --quiet",
            msg
        )

    def test_for_examples_in_action_help(self):
        actions = (
            "node", "stop", "deployment", "reset", "task", "network",
            "settings", "provisioning", "environment", "deploy-changes",
            "role", "release", "snapshot", "health"
        )
        for action in actions:
            self.check_all_in_msg("help {0}".format(action), ("Examples",))

    # skip this test
    def test_task_action_urls(self):
        self.skipTest("Currently support of --debug flag for "
                      "previous code base is broken so skip this test")

        self.check_all_in_msg(
            "task --task-id 1 --debug",
            [
                "GET http://127.0.0.1",
                "/api/v1/tasks/1/"
            ],
            check_errors=True
        )
        self.check_all_in_msg(
            "task --task-id 1 --delete --debug",
            [
                "DELETE http://127.0.0.1",
                "/api/v1/tasks/1/?force=0"
            ],
            check_errors=True
        )
        self.check_all_in_msg(
            "task --task-id 1 --delete --force --debug",
            [
                "DELETE http://127.0.0.1",
                "/api/v1/tasks/1/?force=1"
            ],
            check_errors=True
        )


class TestUserActions(BaseTestCase):

    # TODO(aroma): move it to tests of global options
    def test_change_password_params(self):
        self.skipTest('Should be moved to tests of global options')
        cmd = "user --change-password"
        msg = "Expect password [--newpass NEWPASS]"
        result = self.run_cli_command(cmd, check_errors=True)
        self.assertTrue(msg, result)


class TestCharset(BaseTestCase):

    # TODO(aroma): move it to tests for cliff version command
    def test_charset_problem(self):
        self.skipTest('Should be moved to test_env_command suite')
        self.skipTest("Should be moved ")
        self.load_data_to_nailgun_server()
        self.run_cli_commands((
            "env create --name=привет --release=1 --quiet",
            "--env-id=1 node set --node 1 --role=controller --quiet",
            "env --quiet"
        ))


class TestFiles(BaseTestCase):

    def test_file_creation(self):
        self.load_data_to_nailgun_server()
        self.run_cli_commands((
            "environment-create NewEnv 1 --quiet",
            "--env-id=1 node set --node 1 --role=controller --quiet",
            "--env-id=1 node set --node 2,3 --role=compute --quiet"
        ))
        for action in ("network", "settings"):
            for format_ in ("yaml", "json"):
                self.check_if_files_created(
                    "--env 1 {0} --download --{1}".format(action, format_),
                    ("{0}_1.{1}".format(action, format_),)
                )
        command_to_files_map = (
            (
                "--env 1 deployment --default",
                (
                    "deployment_1",
                    "deployment_1/primary-controller_1.yaml",
                    "deployment_1/compute_2.yaml",
                    "deployment_1/compute_3.yaml"
                )
            ),
            (
                "--env 1 provisioning --default",
                (
                    "provisioning_1",
                    "provisioning_1/engine.yaml",
                    "provisioning_1/node-1.yaml",
                    "provisioning_1/node-2.yaml",
                    "provisioning_1/node-3.yaml"
                )
            ),
            (
                "--env 1 deployment --default --json",
                (
                    "deployment_1/primary-controller_1.json",
                    "deployment_1/compute_2.json",
                    "deployment_1/compute_3.json"
                )
            ),
            (
                "--env 1 provisioning --default --json",
                (
                    "provisioning_1/engine.json",
                    "provisioning_1/node-1.json",
                    "provisioning_1/node-2.json",
                    "provisioning_1/node-3.json"
                )
            ),
            (
                "node --node 1 --disk --default",
                (
                    "node_1",
                    "node_1/disks.yaml"
                )
            ),
            (
                "node --node 1 --network --default",
                (
                    "node_1",
                    "node_1/interfaces.yaml"
                )
            ),
            (
                "node --node 1 --disk --default --json",
                (
                    "node_1/disks.json",
                )
            ),
            (
                "node --node 1 --network --default --json",
                (
                    "node_1/interfaces.json",
                )
            )
        )
        for command, files in command_to_files_map:
            self.check_if_files_created(command, files)

    def check_if_files_created(self, command, paths):
        command_in_dir = "{0} --dir={1} --quiet".format(command,
                                                        self.temp_directory)
        self.run_cli_command(command_in_dir)
        for path in paths:
            self.assertTrue(os.path.exists(
                os.path.join(self.temp_directory, path)
            ))


class TestDownloadUploadNodeAttributes(BaseTestCase):

    def test_upload_download_interfaces(self):
        self.load_data_to_nailgun_server()
        cmd = "node --node-id 1 --network --quiet"
        self.run_cli_commands((self.download_command(cmd),
                              self.upload_command(cmd)))

    def test_upload_download_disks(self):
        self.load_data_to_nailgun_server()
        cmd = "node --node-id 1 --disk --quiet"
        self.run_cli_commands((self.download_command(cmd),
                              self.upload_command(cmd)))


class TestDeployChanges(BaseTestCase):

    def test_deploy_changes_no_failure(self):
        self.load_data_to_nailgun_server()
        env_create = "environment-create test 1 --quiet"
        add_node = "--env-id=1 node set --node 1 --role=controller --quiet"
        deploy_changes = "deploy-changes --env 1 --quiet"
        self.run_cli_commands((env_create, add_node, deploy_changes))
