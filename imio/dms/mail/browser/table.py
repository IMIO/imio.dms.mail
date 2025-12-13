# -*- coding: utf-8 -*-
from collective.contact.plonegroup.browser.tables import OrgaPrettyLinkWithAdditionalInfosColumn as opl_base
from collective.dms.basecontent.browser.listing import VersionsTable
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.iconifiedcategory import utils as ic_utils
from collective.iconifiedcategory.browser.tabview import CategorizedContent
from collective.task import _ as _task
from html import escape
from imio.dms.mail import _
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.helpers.content import uuidToObject
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.table.column import Column
from z3c.table.table import Table
from zope.cachedescriptors.property import CachedProperty
from zope.component import getUtility
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory


# z3c.table standard columns


class IMVersionsTitleColumn(VersionsTitleColumn):
    """Supplants original base table title. xss ok"""

    def getLinkTitle(self, item):
        obj = item.getObject()
        if not IScanFields.providedBy(obj):
            return ""
        scan_infos = [
            ("scan_id", obj.scan_id and escape(obj.scan_id) or ""),
            ("scan_date", obj.scan_date and obj.toLocalizedTime(obj.scan_date, long_format=1) or ""),
            ("Version", obj.version or ""),
        ]
        scan_infos = [
            "%s: %s" % (translate(name, domain="collective.dms.scanbehavior", context=item.REQUEST), value)
            for (name, value) in scan_infos
        ]

        return "\n".join(scan_infos)

    def renderCell(self, content):
        pattern = (
            u'<a class="version-link" href="{link}" alt="{title}" title="{title}">'
            u'<img src="{icon}" alt="{category}" title="{category}" />'
            # u'{signed}'
            u' {text}</a><p class="discreet">{description}</p>'
        )
        url = content.getURL()
        # signed = u''
        # if base_getattr(content, "signed"):
        #     iconName = "++resource++imio.dms.mail/itemIsSignedYes.png"
        #     signed = u"""<img title="%s" src="%s" />""" % (
        #         translate(u"Signed version", domain="collective.dms.basecontent", context=content.REQUEST),
        #         "%s/%s" % (self.table.portal_url, iconName),
        #     )
        return pattern.format(
            text=safe_unicode(content.title),
            link=url,
            title=self.getLinkTitle(content),
            icon=content.icon_url,
            category=escape(safe_unicode(content.category_title)),
            description=escape(safe_unicode(content.Description)),
            # signed=signed,
        )


class EnquirerColumn(Column):
    """Tasks table viewlet. xss ok"""

    header = _task("Enquirer")
    weight = 30

    def renderCell(self, item):
        if not item.enquirer:
            return ""
        factory = getUtility(IVocabularyFactory, "collective.task.Enquirer")
        voc = factory(item)
        return escape(safe_unicode(voc.getTerm(item.enquirer).title))


class AssignedGroupColumn(Column):
    """Tasks table viewlet. xss ok"""

    header = _("Treating groups")
    weight = 30

    def renderCell(self, item):
        if not item.assigned_group:
            return ""
        factory = getUtility(IVocabularyFactory, "collective.task.AssignedGroups")
        voc = factory(item)
        return escape(safe_unicode(voc.getTerm(item.assigned_group).title))


class BaseVersionsTable(VersionsTable):
    portal_types = []

    @property
    def values(self):
        if not getattr(self, '_v_stored_values', []):
            sort_on = 'getObjPositionInParent'
            data = []
            for portal_type in self.portal_types:
                data.extend([
                    CategorizedContent(self.context, content) for content in
                    ic_utils.get_categorized_elements(
                        self.context,
                        result_type='dict',
                        portal_type=portal_type,
                        sort_on=sort_on,
                    )
                ][::-1])
            self._v_stored_values = data
        return self._v_stored_values


class IMVersionsTable(BaseVersionsTable):
    portal_types = ["dmsmainfile", "dmsappendixfile"]


class OMVersionsTable(BaseVersionsTable):
    portal_types = ["dmsommainfile", "dmsappendixfile"]


class OrgaPrettyLinkWithAdditionalInfosColumn(opl_base):
    """Plonegroup organizations: removed additional infos. xss ok"""

    ai_excluded_fields = ["organization_type"]
    ai_extra_fields = []


class CKTemplatesTable(Table):
    """Table that displays templates listing."""

    cssClassEven = u"even"
    cssClassOdd = u"odd"
    cssClasses = {"table": "listing nosort templates-listing icons-on"}

    # ?table-batchSize=10&table-batchStart=30
    batchSize = 200
    startBatchingAt = 200
    sortOn = None
    results = []

    def __init__(self, context, request):
        super(CKTemplatesTable, self).__init__(context, request)
        self.portal = api.portal.getSite()
        self.context_path = self.context.absolute_url_path()
        self.context_path_level = len(self.context_path.split("/"))
        self.paths = {".": "-"}

    @CachedProperty
    def wtool(self):
        return api.portal.get_tool("portal_workflow")

    @CachedProperty
    def values(self):
        return self.results


class PersonnelTable(Table):
    """Table that displays personnel listing."""

    cssClassEven = u"even"
    cssClassOdd = u"odd"
    cssClasses = {"table": "listing nosort personnel-listing icons-on"}

    # ?table-batchSize=10&table-batchStart=30
    batchSize = 100
    startBatchingAt = 100
    sortOn = None
    results = []

    @CachedProperty
    def values(self):
        return self.results


class FileNameColumn(Column):
    """Column displaying file name."""

    header = _(u"File name")

    def renderCell(self, item):
        return item.title


class SignerColumn(Column):
    """Column with checkboxes for each signer."""

    def __init__(self, context, request, table, signer):
        super(SignerColumn, self).__init__(context, request, table)
        self.userid, signer_name = signer
        self.header = signer_name or self.userid

    def renderCell(self, item):
        signer_index = self.table.approval.signers.index(self.userid)
        checked = self.table.approval.is_file_approved(item.UID(), nb=signer_index)
        name = "approvals.%s.%s" % (item.UID(), self.userid)
        checked_attr = 'checked="checked"' if checked else ""
        return u'<input type="checkbox" name="%s" %s />' % (name, checked_attr)


class ApprovalTable(Table):
    """Table displaying approval state for admins."""

    cssClassEven = u"even"
    cssClassOdd = u"odd"
    cssClasses = {"table": "listing"}
    sortOn = None

    def __init__(self, context, request):
        super(ApprovalTable, self).__init__(context, request)
        self.approval = OMApprovalAdapter(self.context)
        self.portal = api.portal.getSite()

    def setUpColumns(self):
        cols = super(ApprovalTable, self).setUpColumns()

        # Add approving columns
        for nb, signer_name, signer_label in self.approval.signers_details:
            signer_userid = self.approval.signers[nb]
            col = SignerColumn(self.context, self.request, self, (signer_userid, signer_name))
            cols.append(col)

        return cols

    @property
    def values(self):
        results = list()
        for file_uid in self.approval.files_uids:
            file = uuidToObject(file_uid)
            results.append(file)
        return results


class ApprovalTableView(BrowserView):
    """Main view for approvals table."""

    index = ViewPageTemplateFile("templates/approvals.pt")
    __table__ = ApprovalTable

    def __init__(self, context, request):
        super(ApprovalTableView, self).__init__(context, request)
        self.table = self.__table__(context, request)

    def __call__(self):
        self.update()
        self.handle_form()
        return self.index()

    def update(self):
        self.table.update()

    def handle_form(self):
        form = self.request.form
        save_button = form.get("form.button.Save", None) is not None
        cancel_button = form.get("form.button.Cancel", None) is not None
        if save_button and not cancel_button:
            approval = OMApprovalAdapter(self.context)
            to_approve = []
            for i_signer, signer in enumerate(approval.signers):
                for i_fuid, fuid in enumerate(approval.files_uids):
                    key = "approvals.%s.%s" % (fuid, signer)
                    if key in form:
                        if not approval.is_file_approved(fuid, nb=i_signer):
                            to_approve.append((uuidToObject(fuid), signer, i_signer))
                    else:
                        if approval.is_file_approved(fuid, nb=i_signer):
                            approval.unapprove_file(uuidToObject(fuid), signer)

            # Approve only now to avoid unwanted transition
            for fobj, signer, i_signer in to_approve:
                approval.approve_file(fobj, signer, c_a=i_signer, transition="propose_to_be_signed")

            IStatusMessage(self.request).addStatusMessage(_(u"Changes saved."), type="info")
