# -*- coding: utf-8 -*-
"""Custom columns."""
from z3c.table import column
from zope.component import getMultiAdapter
from imio.dashboard.columns import ActionsColumn, RelationPrettyLinkColumn
from collective.eeafaceted.z3ctable.columns import DateColumn, MemberIdColumn, VocabularyColumn, DxWidgetRenderColumn
from collective.eeafaceted.z3ctable import _ as _cez


class TreatingGroupsColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedGroupColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedUserColumn(MemberIdColumn):

    attrName = u'assigned_user'


class DueDateColumn(DateColumn):

    attrName = u'due_date'


class IMActionsColumn(ActionsColumn):

    params = {'showHistory': True, 'showActions': False}


class MailTypeColumn(VocabularyColumn):

    vocabulary = u'imio.dms.mail.IMMailTypesVocabulary'


class Sender2Column(DxWidgetRenderColumn):
# 3 à 4 fois plus lent que SenderColumn

    field_name = 'sender'
    prefix = 'escape'


class SenderColumn(RelationPrettyLinkColumn):

    attrName = 'sender'
    params = {'showContentIcon': True, 'target': '_blank'}


# Columns for collective.task.browser.table.TasksTable


class ObjectBrowserViewCallColumn(column.Column):
    """A column that display the result of a given browser view name call."""
    # column not sortable
    sort_index = -1
    params = {}
    view_name = None

    def renderCell(self, item):
        if not self.view_name:
            raise KeyError('A "view_name" must be defined for column "{0}" !'.format(self.attrName))
        return getMultiAdapter((item, self.request), name=self.view_name)(**self.params)


class TaskActionsColumn(ObjectBrowserViewCallColumn):

    header = _cez("header_actions")
    weight = 70
    view_name = 'actions_panel'
    params = {'showHistory': True, 'showActions': False}
