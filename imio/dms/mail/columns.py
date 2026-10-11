# -*- coding: utf-8 -*-
"""Custom columns."""
from collective.contact.plonegroup.interfaces import IPloneGroupContact
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
from collective.iconifiedcategory import utils as ic_utils
from collective.task.interfaces import ITaskMethods
from html import escape
from imio.annex.columns import ActionsColumn as AnnexActionsColumn
from imio.annex.columns import FilesizeColumn as AnnexFilesizeColumn
from imio.dms.mail import _tr
from imio.helpers.content import uuidToCatalogBrain
from plone import api
from Products.CMFPlone.utils import safe_unicode
from z3c.table import column
from z3c.table.column import LinkColumn
from zope.component import getMultiAdapter
from zope.i18n import translate

import os


class IMTitleColumn(PrettyLinkColumn):
    """IM dashboard. xss ok"""

    params = {"showContentIcon": True, "display_tag_title": False}


class OMColorColumn(ColorColumn):
    """OM dashboard. xss ok"""

    attrName = "printable"
    i18n_domain = "imio.dms.mail"
    sort_index = -1  # not sortable
    header = "&nbsp;&nbsp;"
    header_js = (
        '<script type="text/javascript">jQuery(function($) {'
        '$(".tooltip-title").tooltipster({position: "right", theme: "tooltipster-shadow"});});</script>'
    )

    def is_printable(self, item):
        return bool(item.markers) and "lastDmsFileIsOdt" in item.markers  # Missing.Value is False

    def renderCell(self, item):
        """Display a message."""
        msg = "batch_printable_{}".format(self.is_printable(item))
        translated_msg = translate(msg, domain=self.i18n_domain, context=self.request)
        return '<div class="tooltip-title" title="{0}">&nbsp;</div>'.format(translated_msg)

    def getCSSClasses(self, item):
        """Generate a CSS class to apply on the TD depending on the value."""
        return {
            "tr": "min-height",  # needed so a 100% heigth td div works
            "td": "{0}_{1}_{2}".format(self.cssClassPrefix, str(self.attrName), self.is_printable(item)),
        }


class OMTitleColumn(PrettyLinkColumn):
    """OM dashboard. xss ok"""

    params = {"showContentIcon": True, "display_tag_title": False}


class TreatingGroupsColumn(VocabularyColumn):
    """IM, OM dashboard. xss ok"""

    vocabulary = "collective.dms.basecontent.treating_groups"


class AssignedGroupColumn(VocabularyColumn):
    """Task dashboard. xss ok"""

    vocabulary = "collective.dms.basecontent.treating_groups"


class AssignedUserColumn(MemberIdColumn):
    """IM dashboard. xss ok"""

    attrName = "assigned_user"


class DueDateColumn(DateColumn):
    """Dashboards. xss ok"""

    attrName = "due_date"


class IMActionsColumn(ActionsColumn):
    """IM dashboard. xss ok"""

    params = {"showHistory": True, "showActions": True}


class MailTypeColumn(VocabularyColumn):
    """IM dashboard. xss ok"""

    vocabulary = "imio.dms.mail.IMMailTypesVocabulary"


class Sender2Column(DxWidgetRenderColumn):  # pragma: no cover
    # 3 à 4 fois plus lent que Sender3Column

    field_name = "sender"
    prefix = "escape"


class Sender3Column(RelationPrettyLinkColumn):  # pragma: no cover
    # 3 à 4 fois plus lent que SenderColumn
    attrName = "sender"
    params = {"showContentIcon": True, "target": "_blank"}

    def target_display(self, obj):
        self.params["contentValue"] = obj.get_full_title()
        return PrettyLinkColumn.getPrettyLink(self, obj)


class ContactsColumn(PrettyLinkColumn):
    """Dashboard. xss ok"""

    attrName = ""
    i_cache = {}
    sort_index = -1  # not sortable
    ul_class = "contacts_col"

    def _icons(self, c_brain):
        """See docstring in interfaces.py."""
        if c_brain.portal_type not in self.i_cache:
            icon_link = ""
            purl = api.portal.get_tool("portal_url")()
            typeInfo = api.portal.get_tool("portal_types")[c_brain.portal_type]
            icon_expr = typeInfo.icon_expr
            if icon_expr:
                if "portal_url" in icon_expr:
                    # like string:${portal_url}/++resource++imio.dashboard/dashboardpodtemplate.png
                    contentIcon = "/".join(icon_expr.split("/")[1:])
                else:
                    # Plone 6 iconresolver name like string:contenttype/organization
                    iconresolver = getMultiAdapter((self.context, self.request), name="iconresolver")
                    contentIcon = iconresolver.lookup(icon_expr.split(":", 1)[-1])
                title = translate(typeInfo.title, domain=typeInfo.i18n_domain, context=self.request)
                icon_link = "<img title='%s' src='%s/%s' />" % (safe_unicode(escape(title)), purl, contentIcon)
            self.i_cache[c_brain.portal_type] = icon_link
        return self.i_cache[c_brain.portal_type]

    def renderCell(self, item):
        """ """
        value = self.getValue(item)
        if not value:
            return "-"
        ret = []
        if not isinstance(value, list):
            value = [value]
        for val in value:
            if val.startswith("l:"):
                continue
            c_brain = uuidToCatalogBrain(val, unrestricted=True)
            if not c_brain:
                ret.append("-")
            else:
                ret.append(
                    "<a href='%s' target='_blank' class='pretty_link link-tooltip'>"
                    "<span class='pretty_link_icons'>%s</span>"
                    "<span class='pretty_link_content'>%s</span></a>"
                    % (c_brain.getURL(), self._icons(c_brain), safe_unicode(escape(c_brain.get_full_title)))
                )
        l_ret = len(ret)
        if l_ret == 1:
            return ret[0]
        elif l_ret > 1:
            return '<ul class="%s"><li>%s</li></ul>' % (self.ul_class, "</li>\n<li>".join(ret))
        else:
            return "-"


class SenderColumn(ContactsColumn):
    """IM dashboard. xss ok"""

    attrName = "sender_index"
    header = _cez("header_sender")
    # TODO maybe replace this column with OMSenderVocabulary ?


class TaskParentColumn(PrettyLinkColumn):
    """Task dashboard. xss ok"""

    params = {"showContentIcon": True, "target": "_blank"}
    sort_index = -1  # not sortable
    header = _cez("header_task_parent")

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        parent = ITaskMethods(obj).get_highest_task_parent(task=True)
        return PrettyLinkColumn.getPrettyLink(self, parent)


class RecipientsColumn(ContactsColumn):
    """OM dashboard. xss ok"""

    attrName = "recipients_index"
    header = _cez("header_recipients")


class OutgoingDateColumn(DateColumn):
    """OM dashboard. xss ok"""

    attrName = "in_out_date"
    # long_format = True


class IMSendModesColumn(VocabularyColumn):
    """OM dashboard. xss ok"""

    attrName = "Subject"
    vocabulary = "imio.dms.mail.IMSendModesVocabulary"


class OMSendModesColumn(VocabularyColumn):
    """OM dashboard. xss ok"""

    attrName = "Subject"
    vocabulary = "imio.dms.mail.OMSendModesVocabulary"


class ReviewStateColumn(I18nColumn):
    """Dashboards. xss ok"""

    i18n_domain = "plone"
    weight = 30

    def renderCell(self, item):
        value = self.getValue(item)
        if not value:
            return "-"
        wtool = api.portal.get_tool("portal_workflow")
        state_title = wtool.getTitleForStateOnType(value, item.portal_type)
        return translate(safe_unicode(state_title), domain=self.i18n_domain, context=self.request)


class SessionIdColumn(BaseColumn):
    """Versions table column to display session id when there are multiple sessions"""

    weight = 10
    escape = False

    def renderHeadCell(self):
        return '<img src="{}/++resource++imio.esign/parapheo.svg" style="height:1em;vertical-align:middle"> ID'.format(
            api.portal.get().absolute_url()
        )

    def renderCell(self, content):
        if len(self.table.approval.session_ids) <= 1:
            return ""
        file_uid = content.UID
        sessions_annot = self.table._session_annotation.get("sessions", {})
        session_ids = sorted(
            sid
            for sid, session in sessions_annot.items()
            if any(f["uid"] == file_uid for f in session.get("files", []))
        )
        if not session_ids:
            return ""
        portal = api.portal.get()
        parapheo = getMultiAdapter((portal, portal.REQUEST), name="parapheo")
        badges = []
        for sid in session_ids:
            dashboard_link = parapheo.get_dashboard_link({"id": sid})
            badges.append(
                '<a href={dashboard_link} title="{title}" class="pdf-session-badge">{sid}</a>'.format(
                    dashboard_link=dashboard_link,
                    title=translate(
                        "Paraphéo session ID: ${session_id}",
                        domain="imio.dms.mail",
                        context=content.REQUEST,
                        mapping={"session_id": sid},
                    ),
                    sid=sid,
                )
            )
        return ", ".join(badges)


class FileActionsColumn(AnnexActionsColumn):
    """IM dashboard. xss ok"""

    params = {"showHistory": False, "showActions": True, "showArrows": True}


class PortalTypeColorColumn(ColorColumn):
    """Versions table column"""

    attrName = "portal_type"
    i18n_domain = "imio.dms.mail"
    sort_index = -1  # not sortable
    # msgid_prefix = "portal_type_"
    header = " "
    weight = 10


class FilesizeColumn(AnnexFilesizeColumn):

    def renderHeadCell(self):
        """ """
        total = sum([v.filesize for v in self.table.values if v.filesize is not None])
        header = escape(_tr(self.header, domain="collective.iconifiedcategory"))
        total = ic_utils.render_filesize(total)
        if total.startswith("<span "):
            header += "<p>(Tot: {0})</p>".format(total)
        return header


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
    view_name = "actions_panel"
    attrName = "actions"
    params = {"showHistory": True, "showActions": True}


# Columns for contacts dashboard


class ContactTitleColumn(PrettyLinkColumn):
    """contact dashboards. xss ok"""

    attrName = "get_full_title"
    params = {"target": "_blank", "additionalCSSClasses": ["link-tooltip"], "display_tag_title": False}

    def contentValue(self, item):
        """ """
        return item.get_full_title()


class ContactListTitleColumn(PrettyLinkColumn):
    """contact dashboards. xss ok"""

    params = {"target": "_blank", "additionalCSSClasses": ["link-tooltip", "contact-list"], "display_tag_title": False}


class PathColumn(LinkColumn, BaseColumn):
    """Column that displays path. xss ok"""

    header = "header_relative_path"
    attrName = "title"
    linkTarget = "_blank"
    subPath = "contact-lists-folder"
    sort_index = "path"
    escape = False

    def init_paths(self, item):
        self.root_obj = self.get_root_obj(item)
        self.root_path = "/".join(self.root_obj.getPhysicalPath())
        self.root_path_level = len(self.root_path.split("/"))
        self.paths = {".": "-"}

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
        parts = rel_path.split("/")
        context = self.root_obj
        for i, part in enumerate(parts):
            current_path = "/".join(parts[: i + 1])
            parent_path = "/".join(parts[:i])
            if part == "..":
                current_title = ".."
                context = context.__parent__
            else:
                context = context[part]
                current_title = context.title
            self.paths[current_path] = (
                parent_path and "%s/%s" % (self.paths[parent_path], current_title) or current_title
            )

    def getLinkContent(self, item):
        if not hasattr(self, "paths"):
            self.init_paths(item)
        dir_path = os.path.dirname(item.getPath())
        rel_path = os.path.relpath(dir_path, self.root_path)
        if rel_path not in self.paths:
            self.rel_path_title(rel_path)
        return escape(self.paths[rel_path])


class PersonnelPrimaryOrganisationFacetedColumn(VocabularyColumn):
    """Personnel dashboard: person primary organization. xss ok"""

    header = _cez("header_primary_org")
    weight = 20
    attrName = "primary_organization"
    vocabulary = "collective.contact.plonegroup.browser.settings.SelectedOrganizationsElephantVocabulary"
    the_object = True


class PersonnelUseridFacetedColumn(BaseColumn):
    """Personnel dashboard: person userid as a link to its user-membership view. xss ok"""

    the_object = True
    escape = False
    header = _cez("header_userid")
    weight = 15
    cssClasses = {"td": "userid-column"}

    def renderCell(self, item):
        obj = self._getObject(item)
        if obj.userid:
            return '<a href="{}/@@usergroup-usermembership?userid={}" target="_blank">{}</a>'.format(
                self.table.portal_url, safe_unicode(escape(obj.userid)), safe_unicode(escape(obj.userid))
            )
        return "-"


class PersonnelHPFacetedColumn(BaseColumn):
    """Personnel dashboard: person held positions. xss ok"""

    header = _cez("header_hps")
    weight = 25
    ul_class = "hp_col"
    the_object = True
    escape = False

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        hps = obj.objectValues()
        if not hps:
            return "-"
        ret = []
        signer_usage = "<span class='signer-icon' title='{}'> </span>".format(safe_unicode(escape(_tr("Signer"))))
        approving_usage = "<span class='approving-icon' title='{}'> </span>".format(
            safe_unicode(escape(_tr("Approving")))
        )
        for hp in hps:
            org = hp.get_organization()
            is_plonegroup = IPloneGroupContact.providedBy(org) and 1 or 0
            if org is None:
                ret.append(
                    "<li class='plonegroup_0'>{}</li>".format(
                        _tr("personnel_hp_bad_organization", domain="collective.eeafaceted.z3ctable")
                    )
                )
            else:
                ret.append(
                    "<li class='plonegroup_{}'><a href='{}' target='_blank' class='pretty_link link-tooltip'>"
                    "<span class='pretty_link_content state-{}'>{}</span></a>{}{}</li>".format(
                        is_plonegroup,
                        hp.absolute_url(),
                        api.content.get_state(obj=hp),
                        safe_unicode(escape(org.get_full_title(first_index=is_plonegroup))),
                        signer_usage if "signer" in hp.usages else "",
                        approving_usage if "approving" in hp.usages else "",
                    )
                )
        if ret:
            return '<ul class="%s">%s</ul>' % (self.ul_class, "\n".join(ret))
        else:
            return "-"


class PersonnelActionsFacetedColumn(ActionsColumn):
    """Personnel dashboard: edit action only (no transitions/history). xss ok"""

    weight = 70
    params = {
        "useIcons": True,
        "showHistory": False,
        "showActions": False,
        "showOwnDelete": False,
        "showArrows": False,
        "showTransitions": False,
        "edit_action_class": "dg_edit_action",
        "edit_action_target": "_blank",
    }
    cssClasses = {"td": "actions-column"}
