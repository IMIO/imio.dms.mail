# -*- coding: utf-8 -*-

"""
    This module contains the sign_request type (a simplified document used as
    a signing request) and its add/edit forms.
"""
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from collective.contact.plonegroup.utils import voc_selected_org_suffix_userids
from collective.dms.basecontent.browser.views import DmsDocumentEdit
from collective.dms.basecontent.browser.views import DmsDocumentView
from collective.dms.basecontent.dmsdocument import DmsDocument
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.mailcontent.dmsmail import evaluateInternalReference
from collective.dms.mailcontent.dmsmail import InternalReferenceBaseValidator
from collective.task.field import LocalRoleMasterSelectField
from datetime import datetime
from dexterity.localrolesfield.field import LocalRolesField
from imio.dms.mail import _
from imio.dms.mail.interfaces import ISignRequestApproval
from imio.dms.mail.interfaces import ISignRequestWfConditions
from imio.dms.mail.utils import add_content_in_subfolder
from imio.dms.mail.utils import manage_fields
from imio.dms.mail.vocabularies import signrequest_active_orgs
from plone import api
from plone.autoform import directives
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives.form.value import default_value
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from Products.PluginIndexes.common.UnIndex import _marker
from z3c.form import validator
from zope import schema
from zope.component import adapts
from zope.component import getUtility
from zope.interface import implements
from zope.schema.fieldproperty import FieldProperty

import copy


# registry records holding the signing request auto-numbering configuration
# (added to the mailcontent IDmsMailConfig configlet, see browser/mailcontentsettings.py)
SIGNREQUEST_NUMBER_RECORD = "collective.dms.mailcontent.browser.settings.IDmsMailConfig.signrequest_number"
SIGNREQUEST_TALEXPRESSION_RECORD = (
    "collective.dms.mailcontent.browser.settings.IDmsMailConfig.signrequest_talexpression"
)


def filter_signrequest_assigned_users(org_uid):
    """
    Filter assigned_user in signing request: only propose users belonging to the
    '<org_uid>_demand_sign' Plone group.
    No need to manage '_default_assigned_user_' because assigned_user is here mandatory:
    the first voc value is selected
    """
    return voc_selected_org_suffix_userids(org_uid, [u"demand_sign"], api.user.get_current().getId())


class IImioDmsSignRequest(IDmsDocument):
    """Signing request schema."""

    # rich treating_groups with master/slave on the assigned_user (same as outgoing mail)
    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        source=signrequest_active_orgs,
        slave_fields=(
            {
                "name": "ITask.assigned_user",
                "slaveID": "#form-widgets-ITask-assigned_user",
                "action": "vocabulary",
                "vocab_method": filter_signrequest_assigned_users,
                "control_param": "org_uid",
                "initial_trigger": True,
            },
        ),
    )

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u"collective.dms.basecontent.recipient_groups"),
    )

    internal_reference_no = schema.TextLine(
        title=_(u"Internal Reference Number"),
        required=False,
    )

    # fields inherited from IDmsDocument that are not wanted on a signing request
    directives.omitted("notes", "related_docs")


class ImioDmsSignRequestSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):  # noqa
        return (IImioDmsSignRequest,)


class ImioDmsSignRequest(DmsDocument):
    """Signing request content type."""

    implements(IImioDmsSignRequest)
    # disable local roles inheritance
    __ac_local_roles_block__ = True

    # Needed by collective.z3cform.rolefield. Need to be overriden here
    treating_groups = FieldProperty(IImioDmsSignRequest[u"treating_groups"])
    recipient_groups = FieldProperty(IImioDmsSignRequest[u"recipient_groups"])

    def get_mainfiles(self):
        """A signing request only contains annexes, no main file."""
        return []

    def has_approvings(self, all_done=False):
        """Check if the signing request must be approved.

        :param all_done: if True, check if all approvings are done
        :return: boolean
        """
        approval = ISignRequestApproval(self)
        if not approval.approvers:
            return False
        elif not approval.files_uids:
            return False
        elif not all_done:
            return True
        else:  # has approvals and all done
            return approval.current_nb == -1

    def wf_conditions(self):
        """Returns the adapter providing workflow conditions"""
        return ISignRequestWfConditions(self)


class SignRequestWfConditionsAdapter(object):
    implements(ISignRequestWfConditions)
    adapts(IImioDmsSignRequest)
    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    security.declarePublic("can_be_approved")

    def can_be_approved(self):
        """Used in guard expression for propose_to_approve transition."""
        # at least one annex must be present before requesting a signature
        brains = self.context.portal_catalog.unrestrictedSearchResults(
            portal_type="dmsappendixfile", path="/".join(self.context.getPhysicalPath()), b_size=1
        )
        if not bool(brains):
            return False
        return self.context.has_approvings()

    security.declarePublic("can_be_signed")

    def can_be_signed(self):
        """Used in guard expression for propose_to_be_signed transition."""
        # if there are approvings, they must all be done before signing
        if self.context.has_approvings() and not self.context.has_approvings(all_done=True):
            return False
        return True

    security.declarePublic("can_mark_as_signed")

    def can_mark_as_signed(self):
        """Used in guard expression for mark_as_signed transition."""
        # TODO esign: check if the esign process is terminated
        return True

    security.declarePublic("can_close")

    def can_close(self):
        """Used in guard expression for close transition."""
        return True


InitializeClass(SignRequestWfConditionsAdapter)


def sign_request_updatefields(the_form):
    """Make assigned_user mandatory."""
    if "ITask.assigned_user" in the_form.fields:
        the_form.fields["ITask.assigned_user"].field = copy.copy(the_form.fields["ITask.assigned_user"].field)
        the_form.fields["ITask.assigned_user"].field.required = True


class SignRequestAddForm(DefaultAddForm):
    portal_type = "sign_request"

    def updateFields(self):
        super(SignRequestAddForm, self).updateFields()
        manage_fields(self, "request_fields", "edit")
        sign_request_updatefields(self)

    def updateWidgets(self):
        super(SignRequestAddForm, self).updateWidgets()
        # disable left column
        self.request.set("disable_plone.leftcolumn", 1)
        # a selected value will be reused by masterselect
        if "ITask.assigned_user" in self.widgets:
            self.widgets["ITask.assigned_user"].value = [api.user.get_current().getId()]

    def add(self, obj):
        # if not self.request.get("_auto_ref", True):
        #     setattr(obj, "_auto_ref", False)
        container, new_object = add_content_in_subfolder(self, obj, datetime.now())
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        if fti.immediate_view:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id, fti.immediate_view])
        else:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id])


class AddSignRequest(DefaultAddView):
    form = SignRequestAddForm


class SignRequestEdit(DmsDocumentEdit):
    """Edit form redefinition to customize fields."""

    def updateFields(self):
        super(SignRequestEdit, self).updateFields()
        manage_fields(self, "request_fields", "edit")
        sign_request_updatefields(self)

    def updateWidgets(self):
        super(SignRequestEdit, self).updateWidgets()
        self.request.set("disable_plone.leftcolumn", 1)


class SignRequestView(DmsDocumentView):
    """View form redefinition to keep only configured fields."""

    def updateFieldsFromSchemata(self):
        super(SignRequestView, self).updateFieldsFromSchemata()
        manage_fields(self, "request_fields", "view")


###################################################################
# internal_reference_no auto-numbering (same mechanism as outgoing mail)
###################################################################


@default_value(field=IImioDmsSignRequest["internal_reference_no"])
def internalReferenceSignRequestDefaultValue(data):
    """Default value of internal_reference_no for a signing request."""
    return evaluateInternalReference(
        data.context,
        data.request,
        SIGNREQUEST_NUMBER_RECORD,
        SIGNREQUEST_TALEXPRESSION_RECORD,
    ).decode("utf8")


class InternalReferenceSignRequestValidator(InternalReferenceBaseValidator):

    type_interface = IImioDmsSignRequest

    def good_value(self):
        return internalReferenceSignRequestDefaultValue(self)


validator.WidgetValidatorDiscriminators(
    InternalReferenceSignRequestValidator, field=IImioDmsSignRequest["internal_reference_no"]
)


@indexer(IImioDmsSignRequest)
def signrequest_internal_reference_number_indexer(obj):
    """Indexer of 'internal_reference_number' for a signing request.
    Specific indexer method to avoid acquisition of contained elements.
    """
    if obj.internal_reference_no:
        return obj.internal_reference_no
    return _marker


def incrementSignRequestNumber(signrequest, event):
    """Set the internal reference if empty and increment the registry number."""
    if not signrequest.internal_reference_no:
        signrequest.internal_reference_no = evaluateInternalReference(
            signrequest,
            signrequest.REQUEST,
            SIGNREQUEST_NUMBER_RECORD,
            SIGNREQUEST_TALEXPRESSION_RECORD,
        )
        signrequest.reindexObject(
            idxs=("Title", "internal_reference_number", "SearchableText", "sortable_title")
        )
    if getattr(signrequest, "_auto_ref", True):
        registry = getUtility(IRegistry)
        registry[SIGNREQUEST_NUMBER_RECORD] += 1
