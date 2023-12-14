# -*- coding: utf-8 -*-
"""Custom columns."""
from AccessControl import getSecurityManager
from collective.dms.basecontent.browser.column import ExternalEditColumn as eec_base
from collective.dms.basecontent.browser.column import IconColumn
from collective.dms.basecontent.browser.column import LinkColumn as lc_base
from collective.documentgenerator.browser.table import ActionsColumn as DGActionsColumn
from collective.documentviewer.settings import Settings
from collective.eeafaceted.z3ctable import _ as _cez
from collective.eeafaceted.z3ctable.columns import ActionsColumn
from collective.eeafaceted.z3ctable.columns import BaseColumn
from collective.eeafaceted.z3ctable.columns import ColorColumn
from collective.eeafaceted.z3ctable.columns import DateColumn
from collective.eeafaceted.z3ctable.columns import DxWidgetRenderColumn
from collective.eeafaceted.z3ctable.columns import I18nColumn
from collective.eeafaceted.z3ctable.columns import MemberIdColumn
from collective.eeafaceted.z3ctable.columns import PrettyLinkColumn
from collective.eeafaceted.z3ctable.columns import RelationPrettyLinkColumn
from collective.eeafaceted.z3ctable.columns import VocabularyColumn
from collective.task.interfaces import ITaskMethods
from imio.dms.mail import _
from imio.helpers.content import uuidToCatalogBrain
from html import escape
from plone import api
from Products.CMFPlone import PloneMessageFactory as PMF
from Products.CMFPlone.utils import safe_unicode
from z3c.table import column
from z3c.table.column import LinkColumn
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.i18n import translate

import Missing
import os


class IMTitleColumn(PrettyLinkColumn):
    """IM dashboard. xss ok"""

    params = {'showContentIcon': True, 'display_tag_title': False}


class OMColorColumn(ColorColumn):
    """OM dashboard. xss ok"""

    attrName = 'printable'
    i18n_domain = 'imio.dms.mail'
    sort_index = -1  # not sortable
    header = u'&nbsp;&nbsp;'
    header_js = '<script type="text/javascript">$(document).ready(function() {' \
                '$(".tooltip-title").tooltipster({position: "right", theme: "tooltipster-shadow"});});</script>'

    def is_printable(self, item):
        return item.markers is not Missing.Value and 'lastDmsFileIsOdt' in item.markers

    def renderCell(self, item):
        """Display a message."""
        msg = u'batch_printable_{}'.format(self.is_printable(item))
        translated_msg = translate(msg, domain=self.i18n_domain, context=self.request)
        return u'<div class="tooltip-title" title="{0}">&nbsp;</div>'.format(translated_msg)

    def getCSSClasses(self, item):
        """Generate a CSS class to apply on the TD depending on the value."""
        return {'tr': "min-height",  # needed so a 100% heigth td div works
                'td': "{0}_{1}_{2}".format(self.cssClassPrefix,
                                           str(self.attrName),
                                           self.is_printable(item))}


class OMTitleColumn(PrettyLinkColumn):
    """OM dashboard. xss ok"""

    params = {'showContentIcon': True, 'display_tag_title': False}


class TreatingGroupsColumn(VocabularyColumn):
    """IM, OM dashboard. xss ok"""

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedGroupColumn(VocabularyColumn):
    """Task dashboard. xss ok"""

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedUserColumn(MemberIdColumn):
    """IM dashboard. xss ok"""

    attrName = u'assigned_user'


class DueDateColumn(DateColumn):
    """Dashboards. xss ok"""

    attrName = u'due_date'


class IMActionsColumn(ActionsColumn):
    """IM dashboard. xss ok"""

    params = {'showHistory': True, 'showActions': True}


class MailTypeColumn(VocabularyColumn):
    """IM dashboard. xss ok"""

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
    """Dashboard. xss ok"""

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
                icon_link = u"<img title='%s' src='%s/%s' />" % (safe_unicode(escape(title)), purl, contentIcon)
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
            c_brain = uuidToCatalogBrain(val, unrestricted=True)
            if not c_brain:
                ret.append('-')
            else:
                ret.append(u"<a href='%s' target='_blank' class='pretty_link link-tooltip'>"
                           u"<span class='pretty_link_icons'>%s</span>"
                           u"<span class='pretty_link_content'>%s</span></a>"
                           % (c_brain.getURL(), self._icons(c_brain), safe_unicode(escape(c_brain.get_full_title)))
                           )
        l_ret = len(ret)
        if l_ret == 1:
            return ret[0]
        elif l_ret > 1:
            return '<ul class="%s"><li>%s</li></ul>' % (self.ul_class, '</li>\n<li>'.join(ret))
        else:
            return '-'


class SenderColumn(ContactsColumn):
    """IM dashboard. xss ok"""

    attrName = 'sender_index'
    header = _cez('header_sender')
    # TODO maybe replace this column with OMSenderVocabulary ?


class TaskParentColumn(PrettyLinkColumn):
    """Task dashboard. xss ok"""

    params = {'showContentIcon': True, 'target': '_blank'}
    sort_index = -1  # not sortable
    header = _cez('header_task_parent')

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        parent = ITaskMethods(obj).get_highest_task_parent(task=True)
        return PrettyLinkColumn.getPrettyLink(self, parent)


class RecipientsColumn(ContactsColumn):
    """OM dashboard. xss ok"""

    attrName = 'recipients_index'
    header = _cez('header_recipients')


class OutgoingDateColumn(DateColumn):
    """OM dashboard. xss ok"""

    attrName = u'in_out_date'
    # long_format = True


class SendModesColumn(VocabularyColumn):
    """OM dashboard. xss ok"""

    attrName = 'Subject'
    vocabulary = u'imio.dms.mail.OMActiveSendModesVocabulary'


class ReviewStateColumn(I18nColumn):
    """Dashboards. xss ok"""

    i18n_domain = 'plone'
    weight = 30

    def renderCell(self, item):
        value = self.getValue(item)
        if not value:
            return u'-'
        wtool = api.portal.get_tool('portal_workflow')
        state_title = wtool.getTitleForStateOnType(value, item.portal_type)
        return translate(safe_unicode(state_title),
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
    """Tasks table viewlet. xss ok"""

    header = _cez("header_actions")
    weight = 70
    view_name = 'actions_panel'
    attrName = 'actions'
    params = {'showHistory': True, 'showActions': True}


# Columns for collective.dms.basecontent.browser.listing.VersionsTable

class ExternalEditColumn(eec_base):
    """Versions table. xss ok"""

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
                                   mapping={'author': escape(safe_unicode(lock_details['fullname'])),
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
    """IM Versions table. xss ok"""

    cssClasses = {'th': 'empty_col', 'td': 'empty_cell'}

    def renderCell(self, item):
        return u''


class DVConvertColumn(IconColumn):
    """Versions table. xss ok"""

    header = u""
    weight = 20
    linkName = "@@convert-to-documentviewer"
    # linkTarget = '_blank'
    linkContent = _('Update preview')
    iconName = "++resource++imio.dms.mail/dv_convert.svg"
    cssClasses = {'td': 'td_cell_convert'}

    def actionAvailable(self, item):
        various = getMultiAdapter((self.context, self.request), name='various-utils')
        if various.is_in_user_groups(groups=['encodeurs', 'expedition'], admin=True):
            return True
        else:
            obj = item.getObject()
            if api.user.has_permission('Modify portal content', obj=obj):
                settings = Settings(obj)
                return not settings.successfully_converted
            return False

    def renderCell(self, item):
        if not self.actionAvailable(item):
            return u""
        return super(DVConvertColumn, self).renderCell(item)


class HistoryColumn(lc_base):
    """ Not used because history view don't show old file version """

    linkName = '@@historyview'
    header = u''
    weight = 60

    def getLinkContent(self, item):
        title = translate('history.gif_icon_title', context=self.request, domain='imio.actionspanel')
        return u"""<img title="%s" src="%s" />""" % (
            title, '%s/++resource++imio.actionspanel/history.gif' % self.table.portal_url)


# Columns for contacts dashboard

class ContactTitleColumn(PrettyLinkColumn):
    """contact dashboards. xss ok"""

    attrName = 'get_full_title'
    params = {'target': '_blank', 'additionalCSSClasses': ['link-tooltip'], 'display_tag_title': False}

    def contentValue(self, item):
        """ """
        return item.get_full_title()


class ContactListTitleColumn(PrettyLinkColumn):
    """contact dashboards. xss ok"""

    params = {'target': '_blank', 'additionalCSSClasses': ['link-tooltip', 'contact-list'], 'display_tag_title': False}


class PathColumn(LinkColumn, BaseColumn):
    """Column that displays path. xss ok"""

    header = 'header_relative_path'
    attrName = 'title'
    linkTarget = '_blank'
    subPath = 'contact-lists-folder'
    sort_index = 'path'
    escape = False

    def init_paths(self, item):
        self.root_obj = self.get_root_obj(item)
        self.root_path = '/'.join(self.root_obj.getPhysicalPath())
        self.root_path_level = len(self.root_path.split('/'))
        self.paths = {'.': '-'}

    def get_root_obj(self, item):
        base_obj = self.context.__parent__
        if self.subPath:
            return base_obj[self.subPath]
        return base_obj

    def get_root_path(self, item):
        if self.subPath:
            return os.path.join(self.get_context_path(item), self.subPath)
        return self.get_context_path(item)

    def getLinkURL(self, item):
        """Setup link url."""
        return os.path.dirname(item.getURL())

    def rel_path_title(self, rel_path):
        parts = rel_path.split('/')
        context = self.root_obj
        for i, part in enumerate(parts):
            current_path = '/'.join(parts[:i + 1])
            parent_path = '/'.join(parts[:i])
            if part == '..':
                current_title = u'..'
                context = context.__parent__
            else:
                context = context[part]
                current_title = context.title
            self.paths[current_path] = (parent_path and u'%s/%s' % (self.paths[parent_path],
                                        current_title) or current_title)

    def getLinkContent(self, item):
        if not hasattr(self, 'paths'):
            self.init_paths(item)
        dir_path = os.path.dirname(item.getPath())
        rel_path = os.path.relpath(dir_path, self.root_path)
        if rel_path not in self.paths:
            self.rel_path_title(rel_path)
        return escape(self.paths[rel_path])

# ck-templates-listing columns


class TitleColumn(LinkColumn):
    """CKTemplates table. Personnel table. xss ok"""

    header = PMF("Title")
    weight = 10
    cssClasses = {'td': 'title-column'}

    def getLinkCSS(self, item):
        return ' class="state-%s"' % (api.content.get_state(obj=item))

    def getLinkContent(self, item):
        return item.title


class CKPathColumn(LinkColumn):
    """CKTemplates table. xss ok"""

    header = _("Relative path")
    weight = 20
    cssClasses = {'td': 'path-column'}
    linkTarget = '_blank'

    def getLinkURL(self, item):
        """Setup link url."""
        return item.__parent__.absolute_url()

    def getLinkContent(self, item):
        annot = IAnnotations(item)
        return annot.get('dmsmail.cke_tpl_tit', '-') or '-'


class ActionsColumn(DGActionsColumn):
    """CKTemplates table. xss ok"""

#    header = _("Actions")
    weight = 70
    params = {'useIcons': True, 'showHistory': False, 'showActions': True, 'showOwnDelete': False,
              'showArrows': False, 'showTransitions': False, 'edit_action_class': 'dg_edit_action',
              'edit_action_target': '_blank'}
    cssClasses = {'td': 'actions-column'}


class UseridColumn(LinkColumn):
    """Personnel table. xss ok"""

    header = _cez("header_userid")
    weight = 15
    cssClasses = {'td': 'userid-column'}
    linkTarget = '_blank'

    def __init__(self, context, request, table):
        super(UseridColumn, self).__init__(context, request, table)
        self.purl = api.portal.get_tool('portal_url')()

    def getLinkURL(self, item):
        """Setup link url."""
        return '{}/@@usergroup-usermembership?userid={}'.format(self.purl, item.userid)

    def getLinkContent(self, item):
        return item.userid

    def renderCell(self, item):
        if item.userid:
            return super(UseridColumn, self).renderCell(item)
        return '-'


class PrimaryOrganizationColumn(VocabularyColumn):
    """Personnel table. xss ok"""

    header = _cez("header_primary_org")
    weight = 20
    attrName = 'primary_organization'
    vocabulary = u'collective.contact.plonegroup.browser.settings.SelectedOrganizationsElephantVocabulary'
