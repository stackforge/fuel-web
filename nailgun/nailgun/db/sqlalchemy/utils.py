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

import netaddr
import six
from sqlalchemy import types as sa_types


def make_dsn(engine, host, port, user, passwd, name):
    """Constructs DSN string that can be used to connect to database.

    If host starts with '/' it will be treated as a socket and port will be
    ingored.

    :param engine: DB engine
    :param host: DB host or socket
    :param port: DB port (empty if using socket)
    :param user: DB user name
    :param passwd: DB user password
    :param name: name of the database
    """
    if host.startswith('/'):
        # use socket
        dsn = "{engine}://{user}:{passwd}@/{name}?host={host}"
    else:
        # use regular connection
        dsn = "{engine}://{user}:{passwd}@{host}:{port}/{name}"

    return dsn.format(
        engine=engine,
        host=host,
        port=port,
        user=user,
        passwd=passwd,
        name=name,
    )


class EUIEncodedString(sa_types.TypeDecorator):
    """Type serialized as EUI-encoded string in db."""

    impl = sa_types.TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            raise ValueError('HW address cannot be None.')

        # Validate and save value if it is already a string.
        if isinstance(value, six.string_types) or isinstance(value, six.text_type):
            # TODO(romcheg): This validation should also support
            # other kinds of hardware addresses. This should be done
            # in one of the following patches.
            if not netaddr.valid_mac(value):
                raise ValueError('The value is not a valid mac address')

            return value
        elif isinstance(value, netaddr.EUI):
            value.dialect=netaddr.mac_unix
            return str(value)
        else:
            raise ValueError('The value shoud be either a string or '
                             'a netaddr.EUI object.')

    def process_result_value(self, value, dialect):
        try:
            value = netaddr.EUI(value, dialect=netaddr.mac_unix)
        except netaddr.AddrFormatError as e:
            raise ValueError('%s is not a valid HW address.')

        return value
