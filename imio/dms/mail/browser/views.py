# -*- coding: utf-8 -*-
from AccessControl import getSecurityManager
from collective.ckeditortemplates.cktemplate import ICKTemplate
from datetime import datetime
from eea.faceted.vocabularies.autocomplete import IAutocompleteSuggest
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import PMH_ENABLED
from imio.dms.mail.browser.table import ApprovalTable
from imio.dms.mail.browser.table import CKTemplatesTable
from imio.dms.mail.browser.table import PersonnelTable
from imio.dms.mail.dmsfile import IImioDmsFile
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.interfaces import IPersonnelContact
from imio.esign.browser.views import SessionsListingView
from imio.esign.browser.views import SigningUsersCsv as BaseSigningUsersCsv
from imio.helpers.content import richtextval
from imio.helpers.content import uuidToObject
from imio.helpers.emailer import add_attachment
from imio.helpers.emailer import create_html_email
from imio.helpers.emailer import get_mail_host
from imio.helpers.emailer import send_email
from imio.helpers.fancytree.views import BaseRenderFancyTree
from imio.helpers.workflow import do_transitions
from imio.helpers.xhtml import object_link
from plone import api
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PageTemplates.Expressions import SecureModuleImporter
from Products.statusmessages.interfaces import IStatusMessage
from unidecode import unidecode  # unidecode_expect_nonascii not yet available in used version
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.interface import implements
from zope.lifecycleevent import modified
from zope.pagetemplate.pagetemplate import PageTemplate

import json


class CreateFromTemplateForm(BaseRenderFancyTree):

    """Create a document from a collective.documentgenerator template."""

    root = "/templates/om"

    def label(self):
        return translate(
            _(u"${title}: create from template", mapping={"title": safe_unicode(self.context.Title())}),
            context=self.request,
        )

    def get_action_name(self):
        return translate(_("Choose this template"), context=self.request)

    def get_query(self):
        path = self.root_path
        return {
            "path": {"query": path, "depth": -1},
            "portal_type": (
                "Folder",
                "ConfigurablePODTemplate",
            ),
            "enabled": True,
        }

    def redirect_url(self, uid):
        """Redirect to document generation from selected template."""
        url = self.context.absolute_url()
        params = [
            "template_uid={}".format(uid),
            "output_format=odt",
        ]
        return "{}/persistent-document-generation?{}".format(url, "&".join(params))


def parse_query(text):
    """Copied from plone.app.vocabularies.catalog.parse_query but cleaned."""
    for char in "?-+*()":
        text = text.replace(char, " ")
    query = {"SearchableText": " AND ".join(x + "*" for x in text.split())}
    return query


class ContactSuggest(BrowserView):
    """Contact Autocomplete view"""

    implements(IAutocompleteSuggest)

    label = u"Contact"

    def __call__(self):
        result = []
        query = self.request.get("term")
        if not query:
            return json.dumps(result)

        self.request.response.setHeader("Content-type", "application/json")
        query = parse_query(query)
        hp, org_bis = [], []
        all_str = _tr("All under")
        # search held_positions
        crit = {"portal_type": "held_position", "sort_on": "sortable_title"}
        crit.update(query)
        pc = self.context.portal_catalog
        brains = pc(**crit)
        for brain in brains:
            hp.append({"id": brain.UID, "text": brain.get_full_title})
        # search organizations
        crit = {"portal_type": ("organization", ), "sort_on": "sortable_title"}
        crit.update(query)
        brains = pc(**crit)
        make_bis = (len(hp) + len(brains)) > 1 and True or False
        for brain in brains:
            result.append({"id": brain.UID, "text": brain.get_full_title})
            if make_bis:
                org_bis.append({"id": "l:%s" % brain.UID, "text": "%s [%s]" % (brain.get_full_title, all_str)})
        result += hp
        # search persons
        crit = {"portal_type": ("person", ), "sort_on": "sortable_title"}
        crit.update(query)
        brains = pc(**crit)
        for brain in brains:
            result.append({"id": brain.UID, "text": brain.get_full_title})
        # add organizations bis
        result += org_bis
        return json.dumps(result)


class SenderSuggest(BrowserView):
    """Contact Autocomplete view"""

    implements(IAutocompleteSuggest)

    label = u"Sender"

    def __call__(self):
        result = []
        query = self.request.get("term")
        if not query:
            return json.dumps(result)
        self.request.response.setHeader("Content-type", "application/json")
        query = parse_query(query)
        hp, org_bis = [], []
        all_str = _tr("All under")
        portal_path = "/".join(api.portal.get().getPhysicalPath())
        # search held_positions in personnel-folder
        crit = {
            "portal_type": "held_position",
            "path": "%s/contacts/personnel-folder" % portal_path,
            "sort_on": "sortable_title",
            "sort_order": "ascending"
            # 'sort_on': ['end', 'sortable_title'], 'sort_order': ['descending', 'ascending']  # solr error
        }
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            hp.append({"id": brain.UID, "text": brain.get_full_title})
        # search organizations in plonegroup-organization folder
        crit = {
            "portal_type": ("organization", ),
            "sort_on": "sortable_title",
            "path": "%s/contacts/plonegroup-organization" % portal_path,
        }
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        make_bis = (len(hp) + len(brains)) > 1 and True or False
        for brain in brains:
            result.append({"id": brain.UID, "text": brain.get_full_title})
            if make_bis:
                org_bis.append({"id": "l:%s" % brain.UID, "text": "%s [%s]" % (brain.get_full_title, all_str)})
        result += hp
        result += org_bis
        return json.dumps(result)


class ServerSentEvents(BrowserView):
    """Send SSE for all file in this context that have just finished its documentviewer conversion.
    See https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events.

    This view is called by javascript every 2 seconds. The javascript is available on dmsoutgooingmail.
    """

    def __call__(self):
        self.request.response.setHeader("Content-Type", "text/event-stream")
        self.request.response.setHeader("Cache-Control", "no-cache")
        self.request.response.setHeader("Pragma", "no-cache")
        response = u""
        for child in self.context.listFolderContents():
            if IImioDmsFile.providedBy(child) and getattr(child, "conversion_finished", False):
                # generated is added by creation subscriber, only when file is generated
                # generated <= 2: wait to be sure zopedit redirection has been made
                # generated > 3 and locked: wait else: refresh
                if hasattr(child, "generated") and child.generated <= 2:
                    child.generated += 1
                    continue
                view = getMultiAdapter((child, self.request), name="externalEditorEnabled")
                if view.isObjectLocked():
                    # a manually or generated file is edited a second time: like it was generated
                    if not hasattr(child, "generated"):
                        child.generated = 3
                    # object is locked we wait
                    continue
                elif not hasattr(child, "generated"):
                    # avoid to refresh if file was added manually and we return on the parent
                    delattr(child, "conversion_finished")
                    continue
                info = {u"id": child.getId(), u"path": u"/".join(child.getPhysicalPath()), u"refresh": True}
                line = u"data: {}\n\n".format(json.dumps(info))
                response = u"{}{}".format(response, line)
                delattr(child, "conversion_finished")
                delattr(child, "generated")
        return response


class UpdateItem(BrowserView):
    """
    update attribute of an item
    """

    def __call__(self):
        if "assigned_user" in self.request:
            self.context.assigned_user = self.request.get("assigned_user")
            modified(self.context)


class SendEmail(BrowserView):
    """Send an email and update email_status field."""

    def __call__(self):
        # 1 send email
        body = self.context.email_body
        msg = create_html_email(body.raw)
        for a_uid in self.context.email_attachments or []:
            a_obj = uuidToObject(a_uid, unrestricted=True)
            if a_obj:
                title = a_obj.title
                if a_obj.file.filename:
                    title = a_obj.file.filename
                if PMH_ENABLED:
                    title = unidecode(title)
                add_attachment(msg, title, content=a_obj.file.data)
        mailhost = get_mail_host(check=False)
        replyto_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_replyto_email_send"
        if mailhost.smtp_host == u"localhost" and not PMH_ENABLED:
            api.portal.show_message(
                _("Your email has not been sent: ${error}.", mapping={"error": _(u"Cannot use localhost as smtp")}),
                self.request,
                type="error",
            )
            return
        elif api.portal.get_registry_record(replyto_key, default=False):
            sender = mailhost.smtp_uid
            if not sender:
                sender = api.portal.get().email_from_address
            ret, error = send_email(
                msg,
                self.context.email_subject,
                sender,
                self.context.email_recipient,
                mcc=self.context.email_cc,
                mbcc=self.context.email_bcc,
                replyto=self.context.email_sender,
            )
        else:
            ret, error = send_email(
                msg,
                self.context.email_subject,
                self.context.email_sender,
                self.context.email_recipient,
                mcc=self.context.email_cc,
                mbcc=self.context.email_bcc,
            )
        if ret:
            api.portal.show_message(_("Your email has been sent."), self.request)
        else:
            api.portal.show_message(
                _("Your email has not been sent: ${error}.", mapping={"error": error}), self.request, type="error"
            )
            return

        # 2 Update status on omail
        now = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M")
        status = _tr(u"Email sent at ${date_hour}.", mapping={"date_hour": now})
        if not self.context.email_status:
            self.context.email_status = status
        else:
            self.context.email_status += u" {}".format(status)
        modified(self.context)

        # 3 Close if necessary
        close = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_close_on_email_send"
        )
        if close:
            trans = {
                "created": ["mark_as_sent", "propose_to_be_signed", "set_validated", "propose_to_n_plus_1"],
                "scanned": ["mark_as_sent"],
                "to_print": ["propose_to_be_signed"],
                "proposed_to_n_plus_1": ["mark_as_sent", "propose_to_be_signed", "set_validated"],
                "validated": ["propose_to_be_signed", "mark_as_sent"],
                "to_approve": ["propose_to_be_signed", "mark_as_sent"],
                "to_be_signed": ["mark_as_sent"],
                "signed": ["mark_as_sent"],
            }
            state = api.content.get_state(self.context)
            i = 0
            while state != "sent" and i < 10:
                do_transitions(self.context, trans.get(state, []))
                state = api.content.get_state(self.context)
                i += 1


class CKTemplatesListing(BrowserView):

    __table__ = CKTemplatesTable
    provides = [ICKTemplate.__identifier__]
    depth = None
    local_search = True

    def __init__(self, context, request):
        super(CKTemplatesListing, self).__init__(context, request)

    def query_dict(self):
        crit = {"object_provides": self.provides}
        if self.local_search:
            container_path = "/".join(self.context.getPhysicalPath())
            crit["path"] = {"query": container_path}
            if self.depth is not None:
                crit["path"]["depth"] = self.depth
        # crit['sort_on'] = ['path', 'getObjPositionInParent']
        # how to sort by parent path
        # crit['sort_on'] = 'path'
        return crit

    def update(self):
        self.table = self.__table__(self.context, self.request)
        self.table.__name__ = u"ck-templates-listing"
        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.searchResults(**self.query_dict())
        res = [brain.getObject() for brain in brains]

        self.table.results = [
            obj for obj in sorted(res, key=lambda tp: IAnnotations(tp).get("dmsmail.cke_tpl_tit", u""))
        ]
        self.table.update()

    def __call__(self, local_search=None, search_depth=None):
        """
        search_depth = int value (0)
        local_search = bool value
        """
        if search_depth is not None:
            self.depth = search_depth
        else:
            sd = self.request.get("search_depth", "")
            if sd:
                self.depth = int(sd)
        if local_search is not None:
            self.local_search = local_search
        else:
            self.local_search = "local_search" in self.request or self.local_search
        self.update()
        return self.index()


class PersonnelListing(BrowserView):

    __table__ = PersonnelTable
    provides = [IPersonnelContact.__identifier__]
    depth = None
    local_search = True

    def __init__(self, context, request):
        super(PersonnelListing, self).__init__(context, request)
        self.table = self.__table__(self.context, self.request)

    def query_dict(self):
        # crit = {'portal_type': ['person'], 'object_provides': self.provides}
        crit = {"portal_type": ["person"]}
        if self.local_search:
            container_path = "/".join(self.context.getPhysicalPath())
            crit["path"] = {"query": container_path}
            if self.depth is not None:
                crit["path"]["depth"] = self.depth
        crit["sort_on"] = "sortable_title"
        return crit

    def update(self):
        self.table.__name__ = u"personnel-listing"
        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.searchResults(**self.query_dict())
        self.table.results = [brain.getObject() for brain in brains]
        self.table.update()

    def __call__(self, local_search=None, search_depth=None):
        """
        search_depth = int value (0)
        local_search = bool value
        """
        # if search_depth is not None:
        #     self.depth = search_depth
        # else:
        #     sd = self.request.get('search_depth', '')
        #     if sd:
        #         self.depth = int(sd)
        # if local_search is not None:
        #     self.local_search = local_search
        # else:
        #     self.local_search = 'local_search' in self.request or self.local_search
        self.update()
        return self.index()


class RenderEmailSignature(BrowserView):
    """Render an email signature."""

    def __init__(self, context, request):
        super(RenderEmailSignature, self).__init__(context, request)
        model = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature"
        )
        self.pt = PageTemplate()
        self.pt.pt_source_file = lambda: "none"
        self.pt.write(model)
        self.namespace = self.pt.pt_getContext()
        self.namespace.update(
            {
                "request": self.request,
                "view": self,
                "context": self.context,
                "user": getSecurityManager().getUser(),
                "modules": SecureModuleImporter,
            }
        )
        dg_helper = getMultiAdapter((self.context, self.request), name="document_generation_helper_view")
        self.namespace["dghv"] = dg_helper
        self.namespace["sender"] = dg_helper.get_sender()

    def __call__(self):
        rendered = self.pt.pt_render(self.namespace)
        return richtextval(rendered)


class PlusPortaltabContent(BrowserView):
    """View used in sub portal tab 'plus' to get sub menu items"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()
        self.excluded_types = self.portal.portal_properties.navtree_properties.metaTypesNotToList

    def get_tabs(self):
        res = self.portal.portal_catalog(
            id=("contacts", "templates", "tree", "annexes_types", "sessions"),
            path={"query": "/".join(self.portal.getPhysicalPath()), "depth": 1},
            sort_on="getObjPositionInParent",
        )
        return [(b.Title, b.getURL()) for b in res if b.portal_type not in self.excluded_types]


class DmsMailRestClientView(BrowserView):
    """Adapts an incomingmail to prepare data to exchange within imio.pm.wsclient"""

    def detailed_description(self):
        """Return a link to current object"""
        return u"<p>Fiche courrier liée: %s</p>" % object_link(self.context, target="_blank")


class ImioSessionsListingView(SessionsListingView):

    def get_dashboard_link(self, session):
        collection_uid = api.portal.get()["outgoing-mail"]["mail-searches"]["in_esign_sessions"].UID()
        return "{portal_url}/outgoing-mail/mail-searches#c3=20&b_start=0&c1={collection_uid}" \
            "&esign_session_id={session_id}".format(
                portal_url=api.portal.get().absolute_url(),
                collection_uid=collection_uid,
                session_id=session["id"],
            )

    def get_sessions_url(self):
        return api.portal.get()["sessions"].absolute_url()


class SigningUsersCsv(BaseSigningUsersCsv):

    def filter_user(self, user_data):
        """Filter users that are signers."""
        hps = api.content.find(
            portal_type="held_position",
            userid=user_data["userid"],
        )
        if not hps:
            return False
        for hp in hps:
            hp_obj = hp.getObject()
            if base_hasattr(hp_obj, "usages") and "signer" in hp_obj.usages:
                return True
        return False


class ApprovalTableView(BrowserView):
    """Main view for approvals table."""

    index = ViewPageTemplateFile("templates/approvals.pt")  # also needed here for tests
    __table__ = ApprovalTable

    def __init__(self, context, request):
        super(ApprovalTableView, self).__init__(context, request)
        self.table = self.__table__(context, request)

    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        # if not getSecurityManager().checkPermission("Manage portal", self.context):
        #     return False
        if not self.context.has_approvings():
            return False
        state = api.content.get_state(self.context)
        if state in ("to_print", "to_be_signed", "signed", "sent"):
            return False
        return True

    def __call__(self):
        if not self.available():
            return ""
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
            approval = IOMApproval(self.context)
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

        elif cancel_button:
            self.request.response.redirect(self.context.absolute_url())
