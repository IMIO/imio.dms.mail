# -*- coding: utf-8 -*-
"""Custom columns."""
from z3c.table import column
from zope.component import getMultiAdapter
from collective.eeafaceted.z3ctable.columns import DateColumn, MemberIdColumn, VocabularyColumn
from collective.eeafaceted.z3ctable import _ as _cez


class TreatingGroupsColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedGroupColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedUserColumn(MemberIdColumn):

    attrName = u'assigned_user'


class DueDateColumn(DateColumn):

    attrName = u'due_date'

# Columns for collective.task.browser.table.TasksTable


class BrowserViewCallColumn(column.Column):
    """A column that display the result of a given browser view name call."""
    # column not sortable
    sort_index = -1
    params = {}
    view_name = None

    def renderCell(self, item):
        if not self.view_name:
            raise KeyError('A "view_name" must be defined for column "{0}" !'.format(self.attrName))
        return getMultiAdapter((item, self.request), name=self.view_name)(**self.params)


class TaskActionsColumn(BrowserViewCallColumn):

    header = _cez("header_actions")
    weight = 70
    view_name = 'actions_panel'
    params = {'showHistory': True, 'showActions': False}
