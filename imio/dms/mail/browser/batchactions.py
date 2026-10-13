# -*- coding: utf-8 -*-
"""Batch actions views."""
from Acquisition import aq_parent
from cgi import escape
from collective.classification.folder.content.classification_folder import IClassificationFolder
from collective.contact.core.content.directory import IDirectory
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.widget.schema import ContactChoice
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.eeafaceted.batchactions.browser.views import BaseARUOBatchActionForm
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.browser.views import ContactBaseBatchActionForm
from collective.eeafaceted.batchactions.utils import cannot_modify_field_msg
from collective.eeafaceted.batchactions.utils import filter_on_permission
from collective.eeafaceted.batchactions.utils import is_permitted
from collective.eeafaceted.collectionwidget.interfaces import NotDashboardContextException
from collective.eeafaceted.collectionwidget.utils import getCurrentCollection
from collective.task.browser.batchactions import AssignedGroupBatchActionForm as agbaf
from collective.task.browser.batchactions import AssignedUserBatchActionForm as aubaf
from imio.dms.mail import _
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.dmsmail import DmsContactSourceBinder
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.utils import is_in_user_groups
from imio.esign.audit import audit as esign_audit
from imio.helpers import EMPTY_STRING
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToObject
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.statusmessages import STATUSMESSAGEKEY
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form.browser.select import SelectFieldWidget
from z3c.form.field import Fields
from ZODB.POSException import ConflictError
from zope import schema
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import datetime
import logging
import transaction


logger = logging.getLogger("imio.dms.mail: batchactions")
BATCH_APPROVAL_LIMIT_RECORD = "imio.dms.mail.browser.settings.IImioDmsMailConfig.batch_approval_limit"
BATCH_APPROVAL_SIGNERS_RECORD = "imio.dms.mail.browser.settings.IImioDmsMailConfig.batch_approval_signers"


# IM and OM batch actions


class TreatingGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch treating group change")
    weight = 20

    def _update(self):
        self.do_apply = is_permitted(self.brains, perm="imio.dms.mail: Write treating group field")
        self.fields += Fields(
            schema.Choice(
                __name__="treating_group",
                title=_(u"Treating groups"),
                description=(not self.do_apply and cannot_modify_field_msg or u""),
                required=self.do_apply,
                vocabulary=(self.do_apply and u"collective.dms.basecontent.treating_groups" or SimpleVocabulary([])),
            )
        )

    def _apply(self, **data):
        if data["treating_group"]:
            for brain in self.brains:
                # check if treating_groups is changed and assigned_user is no more in
                if (
                    brain.treating_groups is not None
                    and brain.assigned_user != EMPTY_STRING
                    and data["treating_group"] != brain.treating_groups
                    and brain.assigned_user
                    not in get_selected_org_suffix_principal_ids(data["treating_group"], IM_EDITOR_SERVICE_FUNCTIONS)
                ):
                    # self.status not good here because it needs to stay on the same form
                    api.portal.show_message(
                        _(
                            u"An assigned user is not in this new treating group. " u'Mail "${mail}" !',
                            mapping={"mail": brain.Title.decode("utf8")},
                        ),
                        self.request,
                        "error",
                    )
                    break
            else:  # here if no break !
                for brain in self.brains:
                    obj = brain.getObject()
                    obj.treating_groups = data["treating_group"]
                    modified(obj, Attributes(IDmsDocument, "treating_groups"))


class RecipientGroupBatchActionForm(BaseARUOBatchActionForm):

    label = _(u"Batch recipient groups change")
    modified_attr_name = "recipient_groups"
    call_modified_event = True
    # id = 'recipientgroup-batchaction-form'
    weight = 40

    def _vocabulary(self):
        return u"collective.dms.basecontent.recipient_groups"

    def _remove_vocabulary(self):
        return u"collective.contact.plonegroup.organization_services"


class AssignedUserBatchActionForm(aubaf):

    master = "treating_groups"
    weight = 30

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)


class ReplyBatchActionForm(BaseBatchActionForm):

    overlay = False
    weight = 50

    def __call__(self):
        self.request["URL"] = self.request["URL"].replace("/reply-batch-action", "/multiple-reply")
        view = getMultiAdapter((self.context, self.request), name="multiple-reply")
        return view()


class IMSenderBatchActionForm(ContactBaseBatchActionForm):

    label = _(u"Batch sender contact field change")
    weight = 60
    perms = ("imio.dms.mail: Write mail base fields", "Modify portal content")
    attribute = "sender"
    field_value_type = ContactChoice(
        source=DmsContactSourceBinder(
            portal_type=("organization", "held_position", "person", "contact_list"),
            review_state=["active"],
            sort_on="sortable_title",
        )
    )


class OutgoingDateBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch outgoing date change")
    weight = 50

    def _update(self):
        self.do_apply = is_permitted(self.brains)
        self.fields += Fields(
            schema.Datetime(
                __name__="outgoing_date",
                title=_(u"Outgoing Date"),
                description=(not self.do_apply and cannot_modify_field_msg or u""),
                required=(self.do_apply),
                default=datetime.datetime.now(),
            )
        )

    def _apply(self, **data):
        if data["outgoing_date"]:
            for brain in self.brains:
                obj = brain.getObject()
                obj.outgoing_date = data["outgoing_date"]
                modified(obj, Attributes(IImioDmsOutgoingMail, "outgoing_date"))


class SendModesBatchActionForm(BaseARUOBatchActionForm):

    label = _(u"Batch send modes change")
    modified_attr_name = "send_modes"
    call_modified_event = False
    indexes = ["Subject"]
    required = True
    weight = 60

    def _vocabulary(self):
        return u"imio.dms.mail.OMActiveSendModesVocabulary"

    def _remove_vocabulary(self):
        return u"imio.dms.mail.OMSendModesVocabulary"

    def _may_apply(self):
        return api.user.has_permission("Manage portal", obj=self.context)


class RecipientsBatchActionForm(ContactBaseBatchActionForm):

    label = _(u"Batch recipients contact field change")
    weight = 60
    perms = ("imio.dms.mail: Write mail base fields", "Modify portal content")
    attribute = "recipients"
    field_value_type = ContactChoice(
        source=DmsContactSourceBinder(
            portal_type=("organization", "held_position", "person", "contact_list"),
            review_state=["active"],
            sort_on="sortable_title",
        )
    )


# Task batch actions


class AssignedGroupBatchActionForm(agbaf):

    weight = 20

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)


class TaskAssignedUserBatchActionForm(aubaf):

    master = "assigned_group"

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)


# OM Templates Folder batch actions


class CopyToBatchActionForm(BaseBatchActionForm):
    """Button to copy selection to sub folders."""

    label = _(u"Batch copy to")
    weight = 20

    def available_folders_voc(self):
        """Returns available folders where the current user can paste"""
        terms = []
        brains = api.content.find(context=self.context, depth=1, portal_type="Folder")
        objs = filter_on_permission(brains, "Add portal content")
        for obj in objs:
            terms.append(SimpleTerm(obj.UID(), title=obj.title))
        return SimpleVocabulary(terms)

    def _update(self):
        self.voc = self.available_folders_voc()
        self.do_apply = len(self.voc) > 0
        self.fields += Fields(
            schema.List(
                __name__="folders",
                title=_(u"Folders"),
                value_type=schema.Choice(vocabulary=self.voc),
                description=(
                    self.do_apply
                    and _(u"Select multiple values (CTRL+click)")
                    or _(u"No folder available where you can add templates.")
                ),
                required=self.do_apply,
            )
        )
        self.fields["folders"].widgetFactory = SelectFieldWidget

    def _update_widgets(self):
        if self.do_apply:
            self.widgets["folders"].multiple = "multiple"
            self.widgets["folders"].size = 15

    def _apply(self, **data):
        """ """
        if data["folders"]:
            targets = uuidsToObjects(data["folders"], unrestricted=True)
            for brain in self.brains:
                obj = brain.getObject()
                for target in targets:
                    api.content.copy(source=obj, target=target, safe_id=True)


class DuplicatedBatchActionForm(BaseBatchActionForm):
    """Button to manage duplicated contacts"""

    overlay = False
    weight = 20

    def available(self):
        return is_in_user_groups(groups=("gestion_contacts",))

    def __call__(self):
        if not self.available():  # double check
            return ""
        self.request["uids"] = self.request["uids"].split(",")
        self.request["no_redirect"] = 1
        directory = self.context
        while directory is not None and not IDirectory.providedBy(directory):
            directory = aq_parent(directory)
        view = getMultiAdapter((directory, self.request), name="merge-contacts")
        with api.env.adopt_roles(["Manager"]):
            return view()


class FoldersTreatingGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch treating group change")
    weight = 20

    def _update(self):
        self.do_apply = is_permitted(self.brains)
        self.fields += Fields(
            schema.Choice(
                __name__="treating_group",
                title=_(u"Treating groups"),
                description=(not self.do_apply and cannot_modify_field_msg or u""),
                required=self.do_apply,
                vocabulary=(self.do_apply and u"collective.dms.basecontent.treating_groups" or SimpleVocabulary([])),
            )
        )

    def _apply(self, **data):
        if data["treating_group"]:
            for brain in self.brains:
                obj = brain.getObject()
                obj.treating_groups = data["treating_group"]
                modified(obj, Attributes(IClassificationFolder, "treating_groups"))


class ApproveBatchActionForm(BaseBatchActionForm):
    """Approve the files of the selected elements, for the signers enabled in the settings."""

    label = _(u"Batch files approval")
    weight = 15

    def available(self):
        if not api.portal.get_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, default=None):
            return False
        if self.request.get("uids") or "form.widgets.uids" in self.request.form:
            # ponytail: the form itself is not checked against the collection, the button is only shown where needed
            return True
        try:
            collection = getCurrentCollection(self.context)
        except NotDashboardContextException:
            return False
        return collection is not None and collection.getId() == "to_approve"

    def _update(self):
        self.limit = api.portal.get_registry_record(BATCH_APPROVAL_LIMIT_RECORD, default=0)
        self.excluded = self._excluded_mails()
        nb_mails = len(self.brains) - len(self.excluded)
        self.over_limit = bool(self.limit) and nb_mails > self.limit
        self.do_apply = not self.over_limit and nb_mails > 0

    def _excluded_mails(self):
        """The selected mails the current user cannot batch approve now."""
        userid = api.user.get_current().getId()
        signers = api.portal.get_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, default=None) or []
        objs = [brain.getObject() for brain in self.brains]
        return [obj for obj in objs if not self._files_to_approve(obj, userid, signers)]

    def _message(self, msg_type, msg, mails=()):
        """A portal message, listing mails, to append to the description."""
        items = u"".join(u'<li><a href="{}" target="_blank">{}</a></li>'.format(
            obj.absolute_url(), escape(safe_unicode(obj.Title()))) for obj in mails)
        return u'<div class="portalMessage {}"><p>{}</p>{}</div>'.format(
            msg_type, translate(msg, context=self.request), items and u"<ul>{}</ul>".format(items))

    @property
    def description(self):
        descr = translate(super(ApproveBatchActionForm, self).description, context=self.request)
        if self.over_limit:
            return descr + self._message("error", _(
                u"You can approve at most ${limit} element(s) at once: select fewer elements.",
                mapping={"limit": self.limit}))
        if not self.do_apply:
            return descr + self._message("error", _(
                u"None of the selected mails can be batch approved due to site settings."))
        if not self.limit:
            descr += self._message("warning", _(u"Approving too many files at once may take a long time"))
        if self.excluded:
            descr += self._message("warning", _(u"These mails will be skipped due to site settings:"), self.excluded)
        return descr

    def _files_to_approve(self, obj, userid, signers):
        """The files of obj that userid can approve now, for a signer in signers."""
        approval = obj.approval()
        nb = approval.get_approver_nb(userid)
        if api.content.get_state(obj) not in approval.approval_states or nb is None or nb != approval.current_nb:
            return []
        # same order as the approval levels
        obj_signers = [s["signer"] for s in sorted(obj.signers, key=lambda s: s["number"]) if s["signer"] != "_empty_"]
        if obj_signers[nb] not in signers:
            return []
        return [uuidToObject(f_uid, unrestricted=True) for f_uid in approval.files_uids
                if not approval.is_file_approved(f_uid, nb=nb)]

    def _approve(self, obj, userid, signers):
        """Approve the files of obj as the approval icon does. Return the number of approved files."""
        afiles = self._files_to_approve(obj, userid, signers)
        views = [getMultiAdapter((afile, self.request), name="iconified-approved") for afile in afiles]
        # status 0 when the signing session cannot be created, the reason is in the error messages
        if not all([view.set_values(None)[0] for view in views]):
            raise ValueError(u", ".join(msg.message for msg in IStatusMessage(self.request).show()
                                        if msg.type == u"error"))
        return len(afiles)

    def _apply(self, **data):
        userid = api.user.get_current().getId()
        signers = api.portal.get_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, default=None) or []
        nb_files = nb_mails = skipped = 0
        failed = []
        for brain in self.brains:
            obj = brain.getObject()
            savepoint = transaction.savepoint()
            try:
                approved = self._approve(obj, userid, signers)
            except ConflictError:
                raise
            except Exception as exc:
                logger.exception("Batch approval of %s failed", obj.absolute_url())
                savepoint.rollback()
                reason = translate(safe_unicode(exc.args[0] if exc.args else repr(exc)), context=self.request)
                esign_audit(
                    "batch_approval_rolled_back", u"mail={} approver={} reason={}".format(obj.UID(), userid, reason)
                )
                failed.append(u"{} ({})".format(safe_unicode(obj.Title()), reason))
                continue
            nb_files += approved
            nb_mails += bool(approved)
            skipped += not approved
        # the messages of each approval are replaced by a summary
        IStatusMessage(self.request).show()
        # show() expires the messages cookie and a later setCookie keeps that expiry: start a new one
        self.request.response.cookies.pop(STATUSMESSAGEKEY, None)
        mapping = {"files": nb_files, "elements": nb_mails, "skipped": skipped}
        if skipped:
            summary = _(u"${files} file(s) approved on ${elements} element(s). ${skipped} element(s) skipped due to "
                        u"site settings.", mapping=mapping)
        else:
            summary = _(u"${files} file(s) approved on ${elements} element(s).", mapping=mapping)
        api.portal.show_message(summary, request=self.request)
        if failed:
            api.portal.show_message(
                _(u"Approval cancelled for: ${elements}", mapping={"elements": u", ".join(failed)}),
                request=self.request,
                type="error",
            )
