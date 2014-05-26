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

import inspect


REVERSE_CACHE = {}


def _fill_cache(path, obj):
    from nailgun.api.v2.controllers.base import BaseController

    klass = obj
    if obj.__class__ != type:
        klass = obj.__class__

    for k, v in klass.__dict__.items():
        if isinstance(v, BaseController):
            klass_name = v.__class__.__name__
            new_path = '{0}/{1}'.format(path, k)

            if klass_name not in REVERSE_CACHE:
                REVERSE_CACHE[klass_name] = {
                    'class': v,
                    'path': new_path,
                }
                REVERSE_CACHE[klass_name.replace('Controller', 'Handler')] = \
                    REVERSE_CACHE[klass_name]

                _fill_cache(new_path, v)


def reverse(class_name, kwargs=None):
    from nailgun.api.v2.controllers.root import RootController

    kwargs = kwargs or {}

    if not REVERSE_CACHE:
        _fill_cache('', RootController)

    controller = REVERSE_CACHE[class_name]
    klass = controller['class']
    path = controller['path']

    # TODO(pkaminski): The problem with Pecan's reverse is that a single
    # controller can serve both single and collection. This is a problem:
    # by doing reverse with just controller's class name we don't know
    # whether user wants to get all collection or a single object.
    # Solution is to either add 'type=single/collection' to the reverse
    # method or write Controllers the same way as was for old web.py
    # Handlers, i.e. CollectionHandler, SingleHandler as separate classes
    # Here for simplicity I just take the reverse of get_all method of klass.
    argspec = inspect.getargspec(klass.get_all)
    params = ['%%(%s)s' % param for param in argspec.args[1:]]

    url = '/'.join([path] + params)

    return url % kwargs
