# -*- coding: utf-8 -*-
from collective.contact.plonegroup.browser.tables import OrgaPrettyLinkWithAdditionalInfosColumn as opl_base
from collective.dms.basecontent.browser.listing import VersionsTable
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task import _ as _task
from html import escape
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail.utils import add_file_to_approval
from imio.dms.mail.utils import approve_file
from imio.dms.mail.utils import change_approval_user_status
from imio.dms.mail.utils import get_approval_annot
from imio.dms.mail.utils import remove_file_from_approval
from imio.helpers.adapters import NoEscapeLinkColumn
from imio.helpers.content import base_getattr
from imio.helpers.content import uuidToObject
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from z3c.table.column import Column
from z3c.table.table import Table
from zope.annotation.interfaces import IAnnotations
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
            return
        scan_infos = [
            ("scan_id", obj.scan_id and escape(obj.scan_id) or ""),
            ("scan_date", obj.scan_date and obj.toLocalizedTime(obj.scan_date, long_format=1) or ""),
            ("Version", obj.version or ""),
        ]
        scan_infos = [
            "%s: %s" % (translate(name, domain="collective.dms.scanbehavior", context=item.REQUEST), value)
            for (name, value) in scan_infos
        ]

        return 'title="%s"' % "\n".join(scan_infos)

    def getLinkContent(self, item):
        iconName = "++resource++imio.dms.mail/itemIsSignedYes.png"
        content = super(VersionsTitleColumn, self).getLinkContent(item)  # escaped
        obj = item.getObject()
        if base_getattr(obj, "signed"):
            return u"""%s <img title="%s" src="%s" />""" % (
                content,
                translate(u"Signed version", domain="collective.dms.basecontent", context=item.REQUEST),
                "%s/%s" % (self.table.portal_url, iconName),
            )
        else:
            return content


'''
Choose to add icon at end of filename
class OMSignedColumn(Column):

    weight = 25  # before author = 30

    def renderCell(self, item):
        iconName = "++resource++imio.dms.mail/itemIsSignedYes.png"
        if item.signed:
            return u"""<img title="%s" src="%s" />""" % (
                translate(u"Signed version", domain='collective.dms.basecontent', context=item.REQUEST),
                '%s/%s' % (self.table.portal_url, iconName))
        else:
            return ""
'''


class GenerationColumn(NoEscapeLinkColumn):
    """Mailing icon column. xss ok"""

    header = ""
    weight = 12  # before label = 15
    iconName = "++resource++imio.dms.mail/mailing.gif"

    def getLinkURL(self, item):
        """Setup link url."""
        url = item.getURL()
        om_url = url.rsplit("/", 1)[0]
        # must use new view with title given and reference to mailing template
        return "%s/@@mailing-loop-persistent-document-generation?document_uid=%s" % (om_url, item.UID)

    def getLinkContent(self, item):
        return u"""<img title="%s" src="%s" />""" % (_tr(u"Mailing"), "%s/%s" % (self.table.portal_url, self.iconName))

    def has_mailing(self, item):
        obj = item.getObject()
        annot = IAnnotations(obj)
        if "documentgenerator" in annot and annot["documentgenerator"]["need_mailing"]:
            return True
        return False

    def renderCell(self, item):
        if not self.has_mailing(item):
            return ""
        return super(GenerationColumn, self).renderCell(item)


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


class OMVersionsTable(VersionsTable):
    pass


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
        self.userid, self.signer = signer
        if self.signer:
            self.header = self.signer["name"]

    def renderCell(self, item):
        row_id = item.title
        order = self.signer["order"]
        checked = False
        if item.UID() in self.table.annot["files"]:
            checked = self.table.annot["files"].get(item.UID())[order]["status"] == "a"
        name = "approvals.%s.%s" % (item.UID(), self.userid)
        checked_attr = 'checked="checked"' if checked else ''
        return u'<input type="checkbox" name="%s" %s />' % (name, checked_attr)


class NoApprobationColumn(SignerColumn):
    """Special column for 'No approbation'."""
    header = _(u"* No validation")

    def renderCell(self, item):
        row_id = item.title
        name = "approvals.%s.no_approval" % item.UID()
        checked = item.UID() not in self.table.annot["files"]
        checked_attr = 'checked="checked"' if checked else ''
        return u'<input type="checkbox" name="%s" %s />' % (name, checked_attr)


class ApprovalTable(Table):
    """Table displaying approval state for admins."""

    cssClassEven = u"even"
    cssClassOdd = u"odd"
    cssClasses = {'table': 'listing'}
    sortOn = None

    def __init__(self, context, request):
        super(ApprovalTable, self).__init__(context, request)
        self.annot = get_approval_annot(self.context)

    def setUpColumns(self):
        cols = []

        # First column: file name
        cols.append(FileNameColumn(self.context, self.request, self))

        # Second column: no approbation
        cols.append(NoApprobationColumn(self.context, self.request, self, (None, None)))

        # Add approving columns
        for signer in self.annot["users"].items():
            col = SignerColumn(self.context, self.request, self, signer)
            cols.append(col)

        return cols


class ApprovalTableView(BrowserView):
    """Main view for approvals table."""

    __table__ = ApprovalTable

    def __init__(self, context, request):
        super(ApprovalTableView, self).__init__(context, request)
        self.table = self.__table__(context, request)

    def __call__(self):
        self.update()
        self.handle_form()
        return self.index()

    def update(self):
        self.table.results = self.context.listFolderContents({'portal_type': ['dmsommainfile', 'dmsappendixfile']})
        self.table.update()

    def handle_form(self):
        def is_file_approved_by(annot, file_uid, userid):
            if file_uid not in annot["files"]:
                add_file_to_approval(annot, file_uid)
            order = annot["users"][userid]["order"]
            return annot["files"][file_uid][order]["status"] == "a"

        form = self.request.form
        save_button = form.get('form.button.Save', None) is not None
        cancel_button = form.get('form.button.Cancel', None) is not None
        if save_button and not cancel_button:
            if not self.validate(form):
                IStatusMessage(self.request).addStatusMessage(
                    _(u"You cannot select approvings and no validation at the same time."), type='error')
                return
            # TODO Process form data here

            annot = self.table.annot
            current_userid = api.user.get_current().getId()
            print(form)
            print(annot)
            for key, value in form.items():
                if not key.startswith("approvals."):
                    continue
                prefix, file_uid, userid = key.split(".")
                if userid == "no_approval":
                    remove_file_from_approval(annot, file_uid)
                elif not is_file_approved_by(annot, file_uid, userid):  # FIXME Fix approval number changes (KeyError: 99)
                    approve_file(annot, self.context, uuidToObject(file_uid), current_userid)
                # TODO Manage removing approvals
            print(annot)
            print ""

            IStatusMessage(self.request).addStatusMessage(
                _(u"Changes saved."), type='info')

    def validate(self, form):
        """Validator: no_approval and signer's approval cannot both be checked."""
        res = {}
        for key in form.keys():
            if not key.startswith("approvals."):
                continue
            prefix, file_uid, userid = key.split(".")
            if file_uid not in res:
                res[file_uid] = userid != "no_approval"
            elif userid == "no_approval" and res[file_uid]:
                return False
        return True
