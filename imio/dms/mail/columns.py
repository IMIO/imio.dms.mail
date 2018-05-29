# -*- coding: utf-8 -*-
"""Custom columns."""
import os

from z3c.table import column
from zope.component import getMultiAdapter
from zope.i18n import translate

from AccessControl import getSecurityManager
from plone import api
from plone.app.uuid.utils import uuidToCatalogBrain
from Products.CMFPlone.utils import safe_unicode

from collective.dms.basecontent.browser.column import ExternalEditColumn as eec_base
from collective.eeafaceted.z3ctable.columns import DateColumn, MemberIdColumn, VocabularyColumn, DxWidgetRenderColumn
from collective.eeafaceted.z3ctable.columns import I18nColumn
from collective.eeafaceted.z3ctable import _ as _cez
from collective.task.interfaces import ITaskMethods
from imio.dashboard.columns import ActionsColumn, RelationPrettyLinkColumn, PrettyLinkColumn


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


class Sender2Column(DxWidgetRenderColumn):  # pragma: no cover
# 3 à 4 fois plus lent que Sender3Column

    field_name = 'sender'
    prefix = 'escape'


class Sender3Column(RelationPrettyLinkColumn):  # pragma: no cover
# 3 à 4 fois plus lent que SenderColumn
    attrName = 'sender'
    params = {'showContentIcon': True, 'target': '_blank'}

    def target_display(self, obj):
        self.params['contentValue'] = obj.get_full_title()
        return PrettyLinkColumn.getPrettyLink(self, obj)


class ContactsColumn(PrettyLinkColumn):

    attrName = ''
    i_cache = {}
    sort_index = -1  # not sortable
    ul_class = 'contacts_col'

    def _icons(self, c_brain):
        """See docstring in interfaces.py."""
        if c_brain.portal_type not in self.i_cache:
            icon_link = ''
            purl = api.portal.get_tool('portal_url')()
            typeInfo = api.portal.get_tool('portal_types')[c_brain.portal_type]
            if typeInfo.icon_expr:
                # we assume that stored icon_expr is like string:${portal_url}/myContentIcon.png
                # or like string:${portal_url}/++resource++imio.dashboard/dashboardpodtemplate.png
                contentIcon = '/'.join(typeInfo.icon_expr.split('/')[1:])
                title = translate(typeInfo.title, domain=typeInfo.i18n_domain, context=self.request)
                icon_link = u"<img title='%s' src='%s/%s' />" % (safe_unicode(title), purl, contentIcon)
            self.i_cache[c_brain.portal_type] = icon_link
        return self.i_cache[c_brain.portal_type]

    def renderCell(self, item):
        """ """
        value = self.getValue(item)
        if not value:
            return '-'
        ret = []
        if not isinstance(value, list):
            value = [value]
        for val in value:
            if val.startswith('l:'):
                continue
            c_brain = uuidToCatalogBrain(val)
            if not c_brain:
                ret.append('-')
            else:
                ret.append(u"<a href='%s' target='_blank' class='pretty_link link-tooltip'>"
                           u"<span class='pretty_link_icons'>%s</span>"
                           u"<span class='pretty_link_content'>%s</span></a>"
                           % (c_brain.getURL(), self._icons(c_brain), safe_unicode(c_brain.get_full_title))
                           )
        l_ret = len(ret)
        if l_ret == 1:
            return ret[0]
        elif l_ret > 1:
            return '<ul class="%s"><li>%s</li></ul>' % (self.ul_class, '</li>\n<li>'.join(ret))
        else:
            return '-'


class SenderColumn(ContactsColumn):

    attrName = 'sender_index'


class TaskParentColumn(PrettyLinkColumn):

    params = {'showContentIcon': True, 'target': '_blank'}
    sort_index = -1  # not sortable

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        parent = ITaskMethods(obj).get_highest_task_parent(task=True)
        return PrettyLinkColumn.getPrettyLink(self, parent)


class RecipientsColumn(ContactsColumn):

    attrName = 'recipients_index'


class OutgoingDateColumn(DateColumn):

    attrName = u'in_out_date'
    # long_format = True


class ReviewStateColumn(I18nColumn):

    i18n_domain = 'plone'
    weight = 30

    def renderCell(self, item):
        value = self.getValue(item)
        if not value:
            return u'-'
        wtool = api.portal.get_tool('portal_workflow')
        state_title = wtool.getTitleForStateOnType(value, item.portal_type)
        return translate(state_title,
                         domain=self.i18n_domain,
                         context=self.request)


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
    attrName = 'actions'
    params = {'showHistory': True, 'showActions': False}


# Columns for collective.task.browser.table.TasksTable

class ExternalEditColumn(eec_base):

    lockedLinkName = 'view'
    lockedIconName = 'lock_icon.png'
    lockedLinkContent = ""

    def actionAvailable(self, obj):
        sm = getSecurityManager()
        if not sm.checkPermission('Modify portal content', obj):
            return False, False

        if obj.file is None:
            return False, False

        ext = os.path.splitext(obj.file.filename)[-1].lower()
        if ext in (u'.pdf', u'.jpg', '.jpeg'):
            return False, False

        view = getMultiAdapter((obj, self.request), name='externalEditorEnabled')
        # check locking separately
        available = (view.isEnabledOnThisContentType() and
                     view.isActivatedInMemberProperty() and
                     view.isActivatedInSiteProperty() and
                     view.isWebdavEnabled() and
                     not view.isObjectTemporary() and
                     not view.isStructuralFolder() and
                     view.isExternalEditLink_())
        return available, view.isObjectLocked()

    def renderCell(self, item):
        obj = item.getObject()
        available, locked = self.actionAvailable(obj)
        # don't display icon if not available and object not locked
        if not available and not locked:
            return u''
        if locked:
            link_url = '%s/view' % item.getURL()
            icon_name = 'lock_icon.png'
            lock_info = getMultiAdapter((obj, self.request), name="plone_lock_info")
            lock_details = lock_info.lock_info()
            link_title = translate('description_webdav_locked_by_author_on_time', domain='plone', context=self.request,
                                   mapping={'author': safe_unicode(lock_details['fullname']),
                                            'time': lock_details['time_difference']})
        else:
            link_url = '%s/@@external_edit' % item.getURL()
            icon_name = 'extedit_icon.png'
            link_title = translate(self.linkContent, context=self.request)

        link_content = u"""<img title="%s" src="%s" />""" % (
            link_title, '%s/%s' % (self.table.portal_url, icon_name))

        return '<a href="%s"%s%s%s>%s</a>' % (link_url, self.getLinkTarget(item), self.getLinkCSS(item),
                                              self.getLinkTitle(item), link_content)


class NoExternalEditColumn(eec_base):

    def renderCell(self, item):
        return u''


# Columns for contacts dashboard

class ContactTitleColumn(PrettyLinkColumn):

    attrName = 'get_full_title'
    params = {'target': '_blank', 'additionalCSSClasses': ['link-tooltip']}

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        self.params['contentValue'] = getattr(obj, self.attrName)()
        return PrettyLinkColumn.getPrettyLink(self, obj)
