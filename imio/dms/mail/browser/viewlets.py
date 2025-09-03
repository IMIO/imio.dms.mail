# -*- coding: utf-8 -*-
from collective.contact.core.browser.address import get_address
from collective.contact.widget.interfaces import IContactContent
from collective.dms.basecontent.browser.viewlets import VersionsViewlet
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from collective.messagesviewlet.browser.messagesviewlet import GlobalMessagesViewlet
from collective.messagesviewlet.message import generate_uid
from collective.messagesviewlet.message import PseudoMessage
from collective.task.browser.viewlets import TaskParentViewlet
from imio.dms.mail.browser.table import OMVersionsTable
from imio.dms.mail.browser.views import ImioSessionsListingView
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.esign.browser.views import FacetedSessionInfoViewlet
from imio.helpers.content import richtextval
from imio.helpers.xhtml import object_link
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from plone.app.layout.viewlets import ViewletBase
from plone.app.layout.viewlets.common import FooterViewlet
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.i18n import translate
from zope.intid.interfaces import IIntIds


class ContactContentBackrefsViewlet(ViewletBase):
    # def update(self):
    #    super(ContactContentBackrefsViewlet, self).update()

    def backrefs(self):
        # indirection method added to be easier overrided
        return sorted(self.find_relations(), key=lambda brain: brain.created, reverse=True)

    def find_relations(self, from_attribute=None, from_interfaces_flattened=None):
        """
        Parameters:
        - from_attribute: schema attribute string
        - from_interfaces_flattened: Interface class (only one)
        """
        ret = []
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        query = {"to_id": intids.getId(self.context)}
        if from_attribute is not None:
            query["from_attribute"] = from_attribute
        if from_interfaces_flattened is not None:
            query["from_interfaces_flattened"] = from_interfaces_flattened
        for relation in catalog.findRelations(query):
            # we skip relations between contacts (already shown)
            # nevertheless what about heldposition references for a person: subquery ?
            if IContactContent.providedBy(relation.from_object):
                continue
            # PERF TEST TODO: use directly objects or use the path as request in the portal_catalog to find brain
            ret.append(relation.from_path)
        all_obj = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view", default=False
        )
        pc = api.portal.get_tool("portal_catalog")
        method = all_obj and pc.unrestrictedSearchResults or pc.searchResults
        return method(path={"query": ret, "depth": 0})

    index = ViewPageTemplateFile("templates/contactcontent_backrefs.pt")

    def render(self):
        if not self.request.get("ajax_load", False):
            return self.index()
        return ""


class DMSTaskParentViewlet(TaskParentViewlet):

    display_above_element = False


class OMVersionsViewlet(VersionsViewlet):

    portal_type = "dmsommainfile"
    __table__ = OMVersionsTable


class PrettyLinkTitleViewlet(ViewletBase):
    """
    Viewlet displaying a pretty link title
    """

    def adapted(self, showColors=False, display_tag_title=False, isViewable=False):
        plo = IPrettyLink(self.context)
        plo.showContentIcon = True
        plo.showColors = showColors
        plo.display_tag_title = display_tag_title
        plo.isViewable = isViewable
        plo.notViewableHelpMessage = ""
        return plo


class ContextInformationViewlet(GlobalMessagesViewlet):
    """
    Viewlet displaying context information
    """

    def getAllMessages(self):
        """Check if an address field is empty"""
        if IContactContent.providedBy(self.context):
            contacts = [self.context]
        elif IImioDmsOutgoingMail.providedBy(self.context):
            contacts = []
            for rv in self.context.recipients or []:
                if not rv.isBroken() and rv.to_path:
                    contacts.append(self.context.restrictedTraverse(rv.to_path))
        if not contacts:
            return []
        errors = []
        for contact in contacts:
            address = get_address(contact)
            empty_keys = []
            for key in (
                "street",
                "number",
                "zip_code",
                "city",
            ):
                if not address.get(key, ""):
                    empty_keys.append(translate(key, domain="imio.dms.mail", context=self.request))
            if empty_keys:
                errors.append((contact, empty_keys))

        ret = []
        for (contact, keys) in errors:
            msg = translate(
                u"This contact '${title}' has missing address fields: ${keys}",
                domain="imio.dms.mail",
                context=self.request,
                mapping={
                    "title": object_link(contact, view="edit", attribute="get_full_title"),
                    "keys": ", ".join(keys),
                },
            )
            ret.append(
                PseudoMessage(msg_type="significant", text=richtextval(msg), hidden_uid=generate_uid(), can_hide=False)
            )
        return ret


class CKBatchActionsViewlet(BatchActionsViewlet):
    """Made this specific viewlet only available on right view."""

    def available(self):
        """Global availability of the viewlet."""
        return self.view.__name__ == "ck-templates-listing"


class ImioFooterViewlet(FooterViewlet):
    def update(self):
        super(FooterViewlet, self).update()
        self.version = api.portal.get_registry_record("imio.dms.mail.product_version", default="3.0") or "unknown"
        self.dashversion = self.version.replace(".", "-")


class ImioFacetedSessionInfoViewlet(FacetedSessionInfoViewlet):
    sessions_listing_view = ImioSessionsListingView

    @property
    def sessions_collection_uid(self):
        return api.portal.get()["outgoing-mail"]["mail-searches"]["esign_sessions"].UID()
