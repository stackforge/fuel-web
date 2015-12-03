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

from copy import copy
from copy import deepcopy
from mock import patch

from nailgun.db.sqlalchemy.models.mutable import MutableDict
from nailgun.db.sqlalchemy.models.mutable import MutableList
from nailgun.test.base import BaseUnitTest


@patch('nailgun.db.sqlalchemy.models.mutable.MutableDict.changed')
class TestMutableDict(BaseUnitTest):
    def setUp(self):
        self.standard = {'1': 1}
        self.m_dict = MutableDict()
        self.m_dict.update(self.standard)

    def test_pop_existing(self, m_changed):
        self.assertEqual(self.m_dict.pop('1'), self.standard.pop('1'))
        m_changed.assert_called_once_with()

    def test_pop_existing_with_default(self, m_changed):
        self.assertEqual(self.m_dict.pop('1', None),
                         self.standard.pop('1', None))
        m_changed.assert_called_once_with()

    def test_pop_not_existing(self, m_changed):
        self.assertRaises(KeyError, self.m_dict.pop, '2')
        self.assertFalse(m_changed.called)

    def test_pop_not_existing_with_default(self, m_changed):
        self.assertEqual(self.m_dict.pop('2', {}), self.standard.pop('2', {}))
        m_changed.assert_called_once_with()

    def test_popitem(self, m_changed):
        self.assertItemsEqual(self.m_dict.popitem(), self.standard.popitem())
        m_changed.assert_called_once_with()

        m_changed.reset_mock()
        self.assertRaises(KeyError, self.m_dict.popitem)
        self.assertFalse(m_changed.called)


class TestMutableListBase(BaseUnitTest):
    def setUp(self):
        self.m_list = MutableList()


@patch('sqlalchemy.ext.mutable.Mutable.coerce')
class TestMutableListCoerce(TestMutableListBase):
    def setUp(self):
        super(TestMutableListCoerce, self).setUp()

    def test_coerce_mutable_list(self, m_coerce):
        lst = MutableList()
        self.assertIsInstance(self.m_list.coerce('key', lst), MutableList)
        self.assertFalse(m_coerce.called)

    def test_coerce_list(self, m_coerce):
        lst = list()
        self.assertIsInstance(self.m_list.coerce('key', lst), MutableList)
        self.assertFalse(m_coerce.called)

    def test_coerce_not_acceptable_object(self, m_coerce):
        m_coerce.return_value = None
        obj = dict()
        self.m_list.coerce('key', obj)
        m_coerce.assert_called_once_with('key', obj)


@patch('nailgun.db.sqlalchemy.models.mutable.MutableList.changed')
class TestMutableList(TestMutableListBase):
    def setUp(self):
        super(TestMutableList, self).setUp()
        self.standard = ['element1', 'element2']
        self.m_list.extend(self.standard)

    def _do(self, method, *args, **kwargs):
        getattr(self.m_list, method)(*args, **kwargs)
        getattr(self.standard, method)(*args, **kwargs)

    def _assert_list_not_changed(self, m_changed):
        self.assertFalse(m_changed.called)
        self.assertItemsEqual(self.standard, self.m_list)

    def _assert_call_list_changed_once(self, m_changed):
        m_changed.assert_called_once_with()
        self.assertItemsEqual(self.standard, self.m_list)

    def test_append(self, m_changed):
        self._do('append', 'element')
        self._assert_call_list_changed_once(m_changed)

    def test_extend(self, m_changed):
        self._do('extend', ('element3', 'element4', 'element5'))
        self._assert_call_list_changed_once(m_changed)

    def test_extend_failure(self, m_changed):
        self.assertRaises(TypeError, self.m_list.extend, None)
        self._assert_list_not_changed(m_changed)

    def test_insert(self, m_changed):
        self._do('insert', 1, 'new_element')
        self._assert_call_list_changed_once(m_changed)

    def test_insert_failure(self, m_changed):
        self.assertRaises(TypeError, self.m_list.insert, None, 'element')
        self._assert_list_not_changed(m_changed)

    def test_pop_default(self, m_changed):
        self.assertEqual(self.standard.pop(), self.m_list.pop())
        self._assert_call_list_changed_once(m_changed)

    def test_pop_of_specified_element(self, m_changed):
        self.assertEqual(self.standard.pop(0), self.m_list.pop(0))
        self._assert_call_list_changed_once(m_changed)

    def test_pop_wrong_index_type(self, m_changed):
        self.assertRaises(TypeError, self.m_list.pop, 'str')
        self._assert_list_not_changed(m_changed)

    def test_pop_out_of_range(self, m_changed):
        self.assertRaises(IndexError, self.m_list.pop, len(self.m_list))
        self._assert_list_not_changed(m_changed)

    def test_remove(self, m_changed):
        self._do('remove', 'element1')
        self._assert_call_list_changed_once(m_changed)

    def test_remove_failure(self, m_changed):
        self.assertRaises(ValueError, self.m_list.remove, None)
        self._assert_list_not_changed(m_changed)

    def test_set_item(self, m_changed):
        self.m_list[0] = 'new_element'
        self.standard[0] = 'new_element'
        self._assert_call_list_changed_once(m_changed)

    def test_set_item_failure(self, m_changed):
        self.assertRaises(
            IndexError, self.m_list.__setitem__, len(self.m_list), 'element')
        self._assert_list_not_changed(m_changed)

    def test_del_item(self, m_changed):
        del self.m_list[0]
        del self.standard[0]
        self._assert_call_list_changed_once(m_changed)

    def test_del_item_failure(self, m_changed):
        self.assertRaises(
            IndexError, self.m_list.__delitem__, len(self.m_list))
        self._assert_list_not_changed(m_changed)

    def test_get_state(self, m_changed):
        self.assertIsInstance(self.m_list.__getstate__(), list)
        self._assert_list_not_changed(m_changed)

    def test_set_state(self, m_changed):
        self.m_list.__setstate__([])
        self.standard = []
        self._assert_call_list_changed_once(m_changed)

    def test_set_state_failure(self, m_changed):
        self.assertRaises(TypeError, self.m_list.__setstate__, None)
        self._assert_list_not_changed(m_changed)

    def test_set_slice(self, m_changed):
        self._do('__setslice__', 0, 2, ('element',))
        self._assert_call_list_changed_once(m_changed)

    def test_set_slice_failure(self, m_changed):
        self.assertRaises(
            TypeError, self.m_list.__setslice__, 0, 5, None)
        self._assert_list_not_changed(m_changed)

    def test_set_slice_integration(self, m_changed):
        self.m_list[0:2] = ['new_element']
        self.standard[0:2] = ['new_element']
        self._assert_call_list_changed_once(m_changed)

        m_changed.reset_mock()
        self.m_list[:] = ["again_new_element"]
        self.standard[:] = ["again_new_element"]
        self._assert_call_list_changed_once(m_changed)

    def test_del_slice(self, m_changed):
        self._do('__delslice__', 0, 2)
        self._assert_call_list_changed_once(m_changed)

    def test_del_slice_failure(self, m_changed):
        self.assertRaises(
            TypeError, self.m_list.__delslice__, 0, None)
        self._assert_list_not_changed(m_changed)

    def test_del_slice_integration(self, m_changed):
        del self.m_list[0:2]
        del self.standard[0:2]
        self._assert_call_list_changed_once(m_changed)

    def test_copy(self, m_changed):
        clone = copy(self.m_list)
        self.assertEqual(clone, self.m_list)
        m_changed.assert_called_once_with()

    def test_deep_copy(self, m_changed):
        lst = MutableList(('element1', 'element2'))
        self.m_list.insert(0, lst)

        m_changed.reset_mock()
        clone = deepcopy(self.m_list)
        # changed should calls two times
        # - root cloned list (clone)
        # - mutable list element in root list (cloned lst)
        self.assertEqual(m_changed.call_count, 2)

        lst[0] = 'new_element'
        self.assertEqual(clone[0][0], 'element1')
        self.assertEqual(self.m_list[0][0], 'new_element')


@patch('nailgun.db.sqlalchemy.models.mutable.MutableList.changed')
class TestEmptyMutableList(TestMutableListBase):
    def setUp(self):
        super(TestEmptyMutableList, self).setUp()

    def test_pop_default_from_empty_list(self, m_changed):
        self.assertRaises(IndexError, self.m_list.pop)
        self.assertFalse(m_changed.called)
        self.assertEqual([], self.m_list)
