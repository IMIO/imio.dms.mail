# -*- coding: utf-8 -*-
from AccessControl import getSecurityManager
from AccessControl import Unauthorized
from Acquisition import aq_inner
from datetime import datetime
from eea.facetednavigation.vocabularies.autocomplete import IAutocompleteSuggest
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import PLUS_MENU_TABS
from imio.dms.mail import PMH_ENABLED
from imio.dms.mail.browser.table import ApprovalTable
from imio.dms.mail.dmsfile import IImioDmsFile
from imio.dms.mail.utils import current_user_groups_ids
from imio.dms.mail.utils import get_dms_config
from imio.esign import manage_session_perm
from imio.esign.browser.actions import RecreateSessionView
from imio.esign.browser.actions import RemoveItemFromSessionView
from imio.esign.browser.actions import SessionAnnotationInfoView as BaseSessionAnnotationInfoView
from imio.esign.browser.views import ExternalSessionCreateView
from imio.esign.browser.views import SessionsListingView
from imio.esign.config import get_esign_registry_enabled
from imio.esign.utils import get_session_annotation
from imio.esign.utils import get_session_info
from imio.esign.utils import persistent_to_native
from imio.esign.utils import remove_files_from_session
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
from plone.protect import CheckAuthenticator
from plone.protect import createToken
from Products.CMFPlone.browser.navigation import CatalogNavigationTabs
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PageTemplates.Expressions import getTrustedEngine
from Products.PageTemplates.Expressions import SecureModuleImporter
from Products.PageTemplates.PageTemplate import PageTemplate
from Products.statusmessages.interfaces import IStatusMessage
from unidecode import unidecode  # unidecode_expect_nonascii not yet available in used version
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.interface import implementer
from zope.lifecycleevent import modified

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
            "_authenticator={}".format(createToken()),  # the generation writes on this GET (plone.protect)
        ]
        return "{}/persistent-document-generation?{}".format(url, "&".join(params))


def parse_query(text):
    """Copied from plone.app.vocabularies.catalog.parse_query but cleaned."""
    for char in "?-+*()":
        text = text.replace(char, " ")
    query = {"SearchableText": " AND ".join(x + "*" for x in text.split())}
    return query


def clean_query(query):
    """An empty SearchableText matches nothing since ZCatalog 4 (ignored before): drop it."""
    if not query.get("SearchableText"):
        query.pop("SearchableText", None)
    return query


@implementer(IAutocompleteSuggest)
class ContactSuggest(BrowserView):
    """Contact Autocomplete view"""

    label = u"Contact"

    def __call__(self):
        result = []
        query = self.request.get("term")
        if not query:
            return json.dumps(result)

        self.request.response.setHeader("Content-type", "application/json")
        query = clean_query(parse_query(query))
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


@implementer(IAutocompleteSuggest)
class SenderSuggest(BrowserView):
    """Contact Autocomplete view"""

    label = u"Sender"

    def __call__(self):
        result = []
        query = self.request.get("term")
        if not query:
            return json.dumps(result)
        self.request.response.setHeader("Content-type", "application/json")
        query = clean_query(parse_query(query))
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
                sender = api.portal.get_registry_record("plone.email_from_address")
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


class TrustedPageTemplate(PageTemplate):
    """Page template rendered with the trusted (unrestricted) engine: the signature model is a manager setting."""

    def pt_getEngine(self):
        return getTrustedEngine()


class RenderEmailSignature(BrowserView):
    """Render an email signature."""

    def __init__(self, context, request):
        super(RenderEmailSignature, self).__init__(context, request)
        model = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature"
        )
        self.pt = TrustedPageTemplate()
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
        rendered = self.pt.pt_render(extra_context=self.namespace)
        return richtextval(rendered)


class PlusPortaltabContent(BrowserView):
    """View used in sub portal tab 'plus' to get sub menu items"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()

    def get_tabs(self):
        displayed = api.portal.get_registry_record("imio.dms.mail.displayed_tabs", default=[]) or []
        res = self.portal.portal_catalog(
            id=PLUS_MENU_TABS,
            path={"query": "/".join(self.portal.getPhysicalPath()), "depth": 1},
            sort_on="getObjPositionInParent",
        )
        return [(b.Title, b.getURL()) for b in res if b.getId in displayed]


class DmsMailRestClientView(BrowserView):
    """Adapts an incomingmail to prepare data to exchange within imio.pm.wsclient"""

    def detailed_description(self):
        """Return a link to current object"""
        return u"<p>Fiche courrier liée: %s</p>" % object_link(self.context, target="_blank")


class ImioSessionsListingView(SessionsListingView):

    def session_portal_type(self, session):
        """Content type concerned by a session."""
        discriminators = tuple(session.get("discriminators", ()))
        return discriminators[0] if discriminators else "dmsoutgoingmail"

    def get_dashboard_link(self, session):
        portal = api.portal.get()
        # a session holds files of a single content type: point to the matching dashboard
        if self.session_portal_type(get_session_info(session["id"])) == "sign_request":
            folder_id, searches_id = "requests", "requests-searches"
        else:
            folder_id, searches_id = "outgoing-mail", "mail-searches"
        collection_uid = portal[folder_id][searches_id]["in_esign_sessions"].UID()
        return "{portal_url}/{folder_id}/{searches_id}#c3=20&b_start=0&c1={collection_uid}" \
            "&esign_session_id={session_id}".format(
                portal_url=portal.absolute_url(),
                folder_id=folder_id,
                searches_id=searches_id,
                collection_uid=collection_uid,
                session_id=session["id"],
            )

    def get_sessions(self):
        """Only list the sessions matching the dashboard type (set on the request by the viewlet)."""
        sessions = super(ImioSessionsListingView, self).get_sessions()
        portal_type = self.request.get("esign_portal_type", None)
        if not portal_type:
            return sessions
        return [session for session in sessions if self.session_portal_type(session) == portal_type]

    def available(self):
        # check if esign is disabled
        if not get_esign_registry_enabled():
            return False
        # check if user has manage_session_perm on context
        if api.user.has_permission(manage_session_perm, obj=self.context):
            return True
        # check if user is an approver
        user = api.user.get_current()
        if user.getId() in get_dms_config(["approvings"], missing_key_handling=True, missing_key_value=[]):
            return True
        # check if user is in esign_watchers group
        if "esign_watchers" in current_user_groups_ids(user=user):
            return True
        return False


class ImioExternalSessionCreateView(ExternalSessionCreateView):

    def may_create_external_sessions(self):
        # check if esign is disabled
        if not get_esign_registry_enabled():
            return False
        # check if user has manage_session_perm on context
        if api.user.has_permission(manage_session_perm, obj=self.context):
            return True
        # check if user is an approver
        user = api.user.get_current()
        if user.getId() in get_dms_config(["approvings"], missing_key_handling=True, missing_key_value=[]):
            return True
        # check if user is in esign_watchers group
        if "esign_watchers" in current_user_groups_ids(user=user):
            return True
        return False


class ImioRemoveItemFromSessionView(RemoveItemFromSessionView):

    def index(self):
        if not self.available():
            return None
        self.actions()
        self._finished()

    def actions(self):
        # remove from mail approval annotation
        approval = self.context.__parent__.approval()
        approval.remove_pdf_file_from_approval(self.context.UID())
        # remove from global esign annotation
        remove_files_from_session([self.context.UID()])

    def available(self):
        # only outgoing mail and signing request have an approval process
        if self.context.__parent__.portal_type not in ("dmsoutgoingmail", "sign_request"):
            return False
        approval = self.context.__parent__.approval()
        return self.context.UID() in [uid for pdf_files in approval.pdf_files_uids for uid in pdf_files]


class ImioRecreateSessionView(RecreateSessionView):
    """Recreate session and sync OMApprovalAdapter session_ids for impacted mails."""

    def __call__(self):
        result = super(ImioRecreateSessionView, self).__call__()
        new_id = self._new_session_id
        if new_id is None:
            return result
        annot = get_session_annotation()
        new_session = annot["sessions"][new_id]
        context_uids = set(f["context_uid"] for f in new_session["files"])
        pc = api.portal.get_tool("portal_catalog")
        for c_uid in context_uids:
            obj = uuidToObject(c_uid, unrestricted=True)
            if obj is None:
                continue
            approval = obj.approval()
            if new_id not in approval.annot["session_ids"]:
                approval.annot["session_ids"].append(new_id)
            pc.reindexObject(obj, idxs=("approvings",), update_metadata=0)
        return result

    def get_new_session_title(self, old, old_session_id):
        obj = uuidToObject(old["files"][0]["context_uid"])
        type_label = translate(
            api.portal.get_tool("portal_types")[obj.portal_type].Title(),
            domain="plone",
            context=self.context.REQUEST,
        )
        return u"[iA.Docs] {} - {{sign_id}}".format(type_label)


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
        # only available while the approval process is running (not after it)
        if self.context.approval().is_state_after_approve():
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
            approval = self.context.approval()
            to_approve = []
            for i_signer, signer in enumerate(approval.signers):
                for fuid in approval.files_uids:
                    key = "approvals.%s.%s" % (fuid, signer)
                    if key in form:
                        if not approval.is_file_approved(fuid, nb=i_signer):
                            to_approve.append((uuidToObject(fuid), i_signer))
                    else:
                        if approval.is_file_approved(fuid, nb=i_signer):
                            approval.unapprove_file(uuidToObject(fuid), signer)

            # Approve only now to avoid unwanted transition
            userid = api.user.get_current().getId()
            for fobj, i_signer in to_approve:
                approval.approve_file(fobj, userid, c_a=i_signer, transition=True)

            IStatusMessage(self.request).addStatusMessage(_(u"Changes saved."), type="info")
            self.request.response.redirect(self.context.absolute_url())

        elif cancel_button:
            self.request.response.redirect(self.context.absolute_url())


class ImioCatalogNavigationTabs(CatalogNavigationTabs):
    """Content tabs first, then the actions, the "plus" tab as the last one."""

    def topLevelTabs(self, actions=None, category="portal_tabs"):
        if actions is None:
            context_state = getMultiAdapter((aq_inner(self.context), self.request), name=u"plone_context_state")
            actions = context_state.actions(category)
        result = super(ImioCatalogNavigationTabs, self).topLevelTabs(actions=[], category=category)
        for action_info in actions:
            data = action_info.copy()
            data["name"] = data["title"]
            result.append(data)
        return sorted(result, key=lambda x: x["id"] == "plus")


class SessionAnnotationInfoView(BaseSessionAnnotationInfoView):
    """Admin-only view displaying approval and imio.esign session annotations for an outgoing mail or sign request."""

    index = ViewPageTemplateFile("templates/session_annotation_info.pt")

    @property
    def approval_annot_html(self):
        """Renders approval annot in HTML"""
        approval = self.context.approval()
        native = persistent_to_native(approval.annot)
        return self._render_value(native)


class ObjectRenameTitleView(BrowserView):
    """Single-object title rename form."""

    def __call__(self):
        sm = getSecurityManager()
        if not sm.checkPermission("Modify portal content", self.context):
            raise Unauthorized(
                _(u"Permission denied to rename «${title}».",
                  mapping={u"title": safe_unicode(self.context.title_or_id())})
            )

        form = self.request.form
        if form.get("form.submitted"):
            CheckAuthenticator(self.request)
            target = form.get("orig_template") or self.context.absolute_url()
            if "form.button.Cancel" in form:
                return self.request.response.redirect(target)
            new_title = safe_unicode(form.get("new_title", u"")).strip()
            if not new_title:
                IStatusMessage(self.request).addStatusMessage(
                    _(u"Please provide a title."), type="error"
                )
                self.error = True
                self.title = safe_unicode(self.context.Title())
                self.orig_template = target
                return self.index()
            self.context.setTitle(new_title)
            self.context.reindexObject(idxs=["Title", "sortable_title", "SearchableText"])
            modified(self.context)
            IStatusMessage(self.request).addStatusMessage(
                _(u"Title changed."), type="info"
            )
            return self.request.response.redirect(target)

        self.error = False
        self.title = safe_unicode(self.context.Title())
        self.orig_template = self.request.get("HTTP_REFERER", "").split("?")[0]
        return self.index()
