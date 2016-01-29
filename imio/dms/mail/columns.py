# -*- coding: utf-8 -*-
"""Custom columns."""
from z3c.table import column
from zope.component import getMultiAdapter
from imio.dashboard.columns import ActionsColumn, PrettyLinkColumn
from collective.eeafaceted.z3ctable.columns import DateColumn, MemberIdColumn, VocabularyColumn, DxWidgetRenderColumn
from collective.eeafaceted.z3ctable import _ as _cez
from imio.prettylink.interfaces import IPrettyLink


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


class SenderColumn(PrettyLinkColumn):

    sort_index = -1
    attrName = 'sender'
    showContentIcon = True

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        rel_val = getattr(obj, self.attrName, None)
        if not rel_val:
            return u'-'
        target = getattr(rel_val, 'to_object', None)
        if not target:
            return u'-'
        pl = IPrettyLink(target)
        pl.showContentIcon = self.showContentIcon
        return pl.getLink()

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
