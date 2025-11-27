# -*- coding: utf-8 -*-
from collective.contact.plonegroup import _ as _ccp
from collective.contact.plonegroup.behaviors import IPlonegroupUserLink
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from imio.dms.mail.browser.settings import default_creating_group
from imio.dms.mail.browser.settings import validate_approvings
from imio.dms.mail.browser.settings import validate_signer_approvings
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import vocabularyname_to_terms
from imio.helpers.content import find
from imio.helpers.content import uuidToObject
from operator import itemgetter
from plone import api
from plone.autoform import directives as form
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import directives
from plone.supermodel import model
from Products.CMFPlone.utils import safe_unicode
from z3c.form import validator
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.interface import provider
from zope.schema import Text
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class IDmsMailCreatingGroup(model.Schema):

    creating_group = LocalRoleField(
        title=_(u"Creating group"),
        required=True,
        vocabulary=u"imio.dms.mail.ActiveCreatingGroupVocabulary",
        defaultFactory=default_creating_group,
    )

    # directives.write_permission(creating_group='imio.dms.mail.write_creating_group_field')
    # if set, the field is not visible at creation: we handle this in edit form
    # directives.write_permission(creating_group="imio.dms.mail.write_base_fields")


alsoProvides(IDmsMailCreatingGroup, IFormFieldProvider)


class IDmsMailDataTransfer(model.Schema):

    data_transfer = Text(
        title=_(u"Data transfer"),
        required=False,
        #        readonly=True,
    )


alsoProvides(IDmsMailDataTransfer, IFormFieldProvider)


@provider(IFormFieldProvider)
class IUsagesBehavior(model.Schema):

    usages = schema.List(
        title=_("Usages"),
        value_type=schema.Choice(vocabulary="imio.dms.mail.HeldPositionUsagesVocabulary"),
        required=False,
        default=[],
    )
    form.widget("usages", CheckBoxFieldWidget, multiple="multiple")

    form.read_permission(usages="collective.contact.plonegroup.read_userlink_fields")
    form.write_permission(usages="collective.contact.plonegroup.write_userlink_fields")

    directives.fieldset("app_parameters",
                        label=_ccp(u"Application parameters"),
                        fields=["usages"])

    # TODO: add invariant to check that userid is defined


@provider(IContextSourceBinder)
def signing_signers(context):
    """Return held positions vocabulary for signing."""
    terms = [
        SimpleTerm(value=None, title=_("Choose a value !")),
        SimpleTerm(value=u"_empty_", title=_("* No signature")),
    ]
    terms += vocabularyname_to_terms("imio.dms.mail.OMSignersVocabulary", sort_on="title")
    return SimpleVocabulary(terms)


class ISignerSchema(Interface):
    """Schema for the table of signers in the DataGridField."""

    number = schema.Choice(
        title=_(u"Number"),
        description=_(u"Signer number on the document."),
        vocabulary=SimpleVocabulary.fromValues(range(1, 10)),
        required=True,
    )

    signer = schema.Choice(
        title=_(u"Signer"),
        description=_(u"Related userid will be the signer. Position name of the held position will be used."),
        source=signing_signers,
        required=True,
    )

    approvings = schema.List(
        title=_(u"Approvings"),
        description=_(u"User(s) that can approve the item before the signing session."),
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.SigningApprovingsVocabulary"),
        required=True,
        constraint=validate_approvings,
        min_length=1,
    )
    form.widget("approvings", CheckBoxFieldWidget, multiple="multiple", size=5)

    editor = schema.Bool(
        title=_(u"Editor"),
        description=_(u"Enable edition when approving."),
        required=False,
        default=False,
    )


@provider(IFormFieldProvider)
class ISigningBehavior(model.Schema):

    directives.fieldset(
        "signing",
        label=_(u"Signing fieldset"),
        fields=[
            "signers",
            "seal",
            "esign",
        ],
    )

    signers = schema.List(
        title=_(u"Signers"),
        description=_("List of users who have to sign this document"),
        value_type=DictRow(title=_("Signer"), schema=ISignerSchema),
        required=False,
        default=None,
    )
    form.widget(
        "signers",
        DataGridFieldFactory,
        allow_reorder=False,
        auto_append=False,
    )

    seal = schema.Bool(
        title=_(u"Seal"),
        required=False,
    )

    esign = schema.Bool(
        title=_(u"Electronic signature"),
        required=False,
    )

    @invariant
    def validate_signing(data):
        if data.seal and not data.esign and any([s["signer"] != u"_empty_" for s in data.signers]):
            raise Invalid(_(u"You cannot have a seal and signers but no electronic signature !"))

        if not data.signers or []:
            return
        persons = []
        for i, signer in enumerate(data.signers, start=1):
            validate_signer_approvings(signer, _("Signer line ${nb} has a duplicate approver with themself.",
                                                 mapping={"nb": i}))
            if signer["signer"] == "_empty_":
                continue
            person = uuidToObject(signer["signer"], unrestricted=True).get_person()
            if person in persons:
                raise Invalid(
                    _(
                        u"You cannot have the same signer (${signer_title}) multiple times !",
                        mapping={"signer_title": person.get_title()},
                    )
                )
            if not person.userid:
                raise Invalid(
                    _(
                        u"The signer '${signer_title}' has no userid, you cannot use it !",
                        mapping={"signer_title": person.get_title()},
                    )
                )
            persons.append(person)

        numbers = sorted(map(itemgetter("number"), data.signers))
        if numbers:
            # Check for missing numbers in sequence
            expected_numbers = list(range(1, max(numbers) + 1))
            missing_numbers = [num for num in expected_numbers if num not in numbers]
            if missing_numbers:
                raise Invalid(
                    _(
                        u"A signer is missing at position: ${positions} !",
                        mapping={"positions": safe_unicode(", ".join(map(str, missing_numbers)))},
                    )
                )
            # check if there are no approvings at all
            if all(u"_empty_" in s["approvings"] for s in data.signers):
                if data.esign:
                    raise Invalid(_(u"You have to define approvings for each signer if electronic signature is used !"))
            elif any(u"_empty_" in s["approvings"] for s in data.signers):
                raise Invalid(_(u"You cannot have empty and defined approvings at the same time !"))


class PlonegroupUserLinkUseridValidator(validator.SimpleFieldValidator):

    def validate(self, value, force=False):
        # if old value is None, nothing to do
        if not hasattr(self.context, "userid") or getattr(self.context, "userid", None) is None:
            return

        # Raise if trying to remove an existing userid
        if not value:
            raise Invalid(_(u"You cannot remove a userid once it is set."))

        if not IPersonnelContact.providedBy(self.context):
            return

        # Raise if changing person userid when held positions are used but user has pending esign approvals
        if value != self.context.userid:
            catalog = api.portal.get_tool("portal_catalog")

            # Get held positions for this person
            hps = find(context=self.context, portal_type="held_position", unrestricted=True)
            signer_uids = set()
            person_uid = None
            for b in hps:
                hp = b._unrestrictedGetObject()
                if "signer" in hp.usages:
                    signer_uids.add(hp.UID())
                if "approving" in hp.usages:
                    person_uid = self.context.UID()

            if not signer_uids and not person_uid:
                return

            # Get all potential mails with pending esign approvals
            mails = catalog.unrestrictedSearchResults(
                portal_type="dmsoutgoingmail",
                review_state=["created", "proposed_to_n_plus_1", "validated", "to_approve"],
            )
            pending_approvings = set()
            found = 0
            for b in mails:
                mail = b._unrestrictedGetObject()
                if found >= 10:
                    break
                mail_added = False
                for signer_dic in mail.signers:
                    if not signer_dic.get("signer") or signer_dic.get("signer") == "_empty_":
                        continue
                    for approving in signer_dic.get("approvings", []):
                        if (approving == "_themself_" and signer_dic["signer"] in signer_uids) or \
                                approving == person_uid:
                            pending_approvings.add(b.getPath())
                            found += 1
                            mail_added = True
                            break
                    if mail_added:
                        break
            if pending_approvings:
                raise Invalid(_(u"You cannot change the userid because the user is in approvals on "
                                u"following objects ${paths}",
                                mapping={"paths": safe_unicode(", ".join(pending_approvings))}))


validator.WidgetValidatorDiscriminators(PlonegroupUserLinkUseridValidator, field=IPlonegroupUserLink['userid'])


@provider(IFormFieldProvider)
class IDefaultContentCategoryBehavior(model.Schema):

    default_content_category = schema.Choice(
        title=_(u"Default content category"),
        description=_("Category to apply on generated documents from this template."),
        vocabulary=u"imio.dms.mail.PODTemplateContentCategoriesVocabulary",
        required=True,
    )
