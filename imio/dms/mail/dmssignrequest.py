# -*- coding: utf-8 -*-

"""
    This module contains the sign_request type (a simplified document used as
    a signing request) and its add/edit forms.
"""
from collective.dms.basecontent.browser.views import DmsDocumentEdit
from collective.dms.basecontent.browser.views import DmsDocumentView
from collective.dms.basecontent.dmsdocument import DmsDocument
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.mailcontent.dmsmail import evaluateInternalReference
from collective.dms.mailcontent.dmsmail import InternalReferenceBaseValidator
from collective.task.field import LocalRoleMasterSelectField
from dexterity.localrolesfield.field import LocalRolesField
from imio.dms.mail import _
from imio.dms.mail.dmsmail import filter_dmsoutgoingmail_assigned_users
from imio.dms.mail.utils import manage_fields
from imio.dms.mail.vocabularies import encodeur_active_orgs
from plone import api
from plone.autoform import directives
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives.form.value import default_value
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from Products.PluginIndexes.common.UnIndex import _marker
from z3c.form import validator
from zope import schema
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


class IImioDmsSignRequest(IDmsDocument):
    """Signing request schema."""

    # rich treating_groups with master/slave on the assigned_user (same as outgoing mail)
    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        source=encodeur_active_orgs,
        slave_fields=(
            {
                "name": "ITask.assigned_user",
                "slaveID": "#form-widgets-ITask-assigned_user",
                "action": "vocabulary",
                "vocab_method": filter_dmsoutgoingmail_assigned_users,
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
