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


NETWORK_TEMPLATE = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "adv_net_template": {
            "id": "adv_net_template",
            "type": "object",
            "properties": {
                "default": {
                    "id": "default",
                    "type": "object",
                    "properties": {
                        "nic_mapping": {
                            "id": "nic_mapping",
                            "type": "object",
                            "properties": {
                                "default": {
                                    "id": "default",
                                    "type": "object"
                                }
                            },
                            "required": [
                                "default"
                            ]
                        },
                        "templates_for_node_role": {
                            "id": "templates_for_node_role",
                            "type": "object"
                        },
                        "network_assignments": {
                            "id": "network_assignments",
                            "type": "object"
                        },
                        "network_scheme": {
                            "id": "network_scheme",
                            "type": "object",
                            "properties": {
                                "storage": {
                                    "id": "storage",
                                    "type": "object",
                                },
                                "private": {
                                    "id": "private",
                                    "type": "object",
                                    "properties": {
                                        "transformations": {
                                            "id": "transformations",
                                            "type": "array",
                                        },
                                        "endpoints": {
                                            "id": "endpoints",
                                            "type": "array",
                                        },
                                        "roles": {
                                            "id": "roles",
                                            "type": "object"
                                        }
                                    }
                                },
                                "public": {
                                    "id": "public",
                                    "type": "object",
                                    "properties": {
                                        "transformations": {
                                            "id": "transformations",
                                            "type": "array"
                                        },
                                        "endpoints": {
                                            "id": "endpoints",
                                            "type": "array"
                                        },
                                        "roles": {
                                            "id": "roles",
                                            "type": "object"
                                        }
                                    }
                                },
                                "common": {
                                    "id": "common",
                                    "type": "object",
                                    "properties": {
                                        "transformations": {
                                            "id": "transformations",
                                            "type": "array"
                                        },
                                        "endpoints": {
                                            "id": "endpoints",
                                            "type": "array"
                                        },
                                        "roles": {
                                            "id": "roles",
                                            "type": "object"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": [
                        "nic_mapping",
                        "templates_for_node_role",
                        "network_assignments",
                        "network_scheme"
                    ]
                }
            },
            "required": [
                "default"
            ]
        }
    },
    "required": [
        "adv_net_template"
    ]
}
