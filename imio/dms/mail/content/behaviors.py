# -*- coding: utf-8 -*-
from collective.contact.plonegroup import _ as _ccp
from collective.contact.plonegroup.behaviors import IPlonegroupUserLink
from collective.z3cform.datagridfield.registry import DictRow
from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from imio.dms.mail.browser.settings import default_creating_group
from imio.dms.mail.browser.settings import ExpandableDataGridFieldFactory
from imio.dms.mail.browser.settings import OMFileFormatsVocabulary
from imio.dms.mail.browser.settings import validate_approvings
from imio.dms.mail.browser.settings import validate_signer_approvings
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.dmssignrequest import IImioDmsSignRequest
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import get_allowed_content_types
from imio.dms.mail.utils import has_real_signers
from imio.dms.mail.utils import is_esign
from imio.dms.mail.utils import is_hp_used_in_signer_rules
from imio.dms.mail.utils import vocabularyname_to_terms
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import find
from imio.helpers.content import uuidToObject
from operator import itemgetter
from plone import api
from plone.autoform import directives as form
from plone.autoform.interfaces import IFormFieldProvider
from plone.namedfile.utils import get_contenttype
from plone.supermodel import directives
from plone.supermodel import model
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from z3c.form import validator
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.interfaces import IAddForm
from z3c.form.interfaces import IEditForm
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


# Signing configuration (signers / esign / seal) of an outgoing mail, a signing request or a pod template.
# "Signing values" (has_signing_values) = non empty signers or a seal: when present, rules and templates are not
# applied. "Real signer" (has_real_signers) = a signer other than the _empty_ placeholder.
# Validated by check_signing_combination (edit invariant and after signer rules application).
#
# | # | signers          | esign | seal | valid | meaning and processing                                              |
# |---|------------------|-------|------|-------|---------------------------------------------------------------------|
# | 0 | empty grid       | any   | no   | yes   | not yet defined: filled by rules or template (sign_request: esign)  |
# | 1 | _empty_ only     | no    | no   | yes   | no signature, printable                                             |
# | 2 | _empty_ only     | yes   | no   | NO    | esign needs a real signer or a seal                                 |
# | 3 | no real signer   | no    | yes  | NO    | a seal is always electronic                                         |
# | 4 | no real signer   | yes   | yes  | yes   | seal only: no approval, seal session at propose_to_be_signed        |
# | 5 | real signers     | no    | no   | yes   | handwritten: optional approvals, no session, printable              |
# | 6 | real signers     | yes   | no   | yes   | e-signature: approvals required, session created at last approval   |
# | 7 | real signers     | yes   | yes  | yes   | e-signature + seal: as 6, the seal is added to the session          |
# | 8 | real signers     | no    | yes  | NO    | a seal is always electronic                                         |
#
# Electronic cases (is_esign: 4, 6, 7): print transition blocked, file formats checked.
# A signing request is always electronic: only cases 0, 4, 6 and 7 apply.
# Signer rules: rule 0 "_seal_" without real signer gives case 4; with rule 1 esign signer, case 7.
# Templates: signers, seal and esign are copied together (a seal-only template gives _empty_ + its flags).
def check_signing_combination(obj):
    """Raise Invalid on an incoherent seal / esign / signers combination of obj (or form data).

    A seal is always electronic. An electronic signature needs real signers or a seal; an empty signers grid
    means "not yet defined" (e.g. a new signing request, always esign) and is not checked.
    """
    if obj.seal and not obj.esign:
        raise Invalid(_(u"A seal can only be used with electronic signature !"))
    if obj.esign and not obj.seal and obj.signers and not has_real_signers(obj.signers):
        raise Invalid(_(u"An electronic signature needs at least one real signer or a seal !"))


@provider(IContextSourceBinder)
def signing_signers(context):
    """Return held positions vocabulary for signing."""
    terms = [
        SimpleTerm(value=None, title=_("Choose a value !")),
        SimpleTerm(value=u"_empty_", title=_("* No signature")),
    ]
    terms += vocabularyname_to_terms("imio.dms.mail.OMSignersVocabulary", sort_on="title")
    return SimpleVocabulary(terms)


@provider(IContextSourceBinder)
def signing_request_signers(context):
    """Like signing_signers but a signature is mandatory: no "_empty_" choice."""
    terms = [SimpleTerm(value=None, title=_("Choose a value !"))]
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
        ExpandableDataGridFieldFactory,
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
        context = data.__context__
        if context and context.portal_type in ("dmsoutgoingmail", "sign_request"):
            is_user_admin = api.user.has_permission("Manage portal")
            approval = context.approval()
            if not is_user_admin and (approval.is_state_after_or_approve() or approval.current_nb == -1):
                fields_have_changed = (bool(context.esign) != bool(data.esign)
                                       or bool(context.seal) != bool(data.seal)
                                       or (context.signers or []) != (data.signers or []))
                if fields_have_changed:
                    raise Invalid(_(u"You cannot modify signers once the approval process has started or is done. "
                                    u"You may go back to a previous state or ask your admin."))

        check_signing_combination(data)

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
            # Check for duplicate numbers
            if len(numbers) != len(set(numbers)):
                raise Invalid(
                    _(
                        u"You cannot have the same number for multiple signers !",
                    )
                )

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
                # a seal alone (no real signer) is electronic but has no approvings
                if data.esign and has_real_signers(data.signers):
                    raise Invalid(_(u"You have to define approvings for each signer if electronic signature is used !"))
            elif any(u"_empty_" in s["approvings"] for s in data.signers):
                raise Invalid(_(u"You cannot have empty and defined approvings at the same time !"))

        signer_emails = set()
        approvers = {}
        signers = sorted(data.signers, key=lambda s: s["number"])
        for signer in signers:
            if signer["signer"] == "_empty_":
                continue
            signer_hp = uuidToObject(signer["signer"], unrestricted=True)
            signer_person = signer_hp.get_person()
            user_email = api.user.get(signer_person.userid).getProperty("email")
            if user_email in signer_emails:
                raise Invalid(
                    _(
                        u"You cannot have the same email (${email}) for multiple signers !",
                        mapping={"email": user_email},
                    )
                )
            signer_emails.add(user_email)

            for approving in signer["approvings"] or []:
                if approving == "_empty_":
                    continue
                if approving == "_themself_":
                    person = signer_person
                else:
                    person = uuidToObject(approving, unrestricted=True)
                if person is None:
                    raise Invalid(
                        _(
                            u"The approving with UID ${uid} does not exist !",
                            mapping={"uid": approving},
                        )
                    )
                userid = person.userid
                if userid in approvers:
                    raise Invalid(
                        _(
                            "The ${userid} already exists in the approvings with another order ${o} <=> ${c}",
                            mapping={
                                "userid": userid,
                                "o": approvers[userid],
                                "c": signer["number"],
                            },
                        )
                    )
                approvers[userid] = signer["number"]

        # Validate file formats if eSignature is enabled (only on outgoing mail or sign request, not on templates)
        if context and is_esign(data) and (IImioDmsOutgoingMail.providedBy(context)
                                           or IImioDmsSignRequest.providedBy(context)):
            for afile in context.values():
                # Skip files already converted for esign
                if base_hasattr(afile, "conv_from_uid"):
                    continue
                # Skip files that do not need to be signed
                if not afile.to_sign:
                    continue
                mimetype = get_contenttype(afile.file)
                if mimetype not in get_allowed_content_types(esign=True, portal_type=context.portal_type):
                    raise Invalid(
                        _(
                            "You cannot enable electronic signature because the file '${filename}' "
                            "is of type '${mimetype}' which is not allowed. Allowed formats are: ${formats}.",
                            mapping={
                                "filename": afile.title,
                                "mimetype": mimetype,
                                "formats": u", ".join(
                                    [
                                        v.title
                                        for v in OMFileFormatsVocabulary()(None)
                                        if v.token
                                        in api.portal.get_registry_record(
                                            "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}_esign_formats"
                                            .format("omail" if context.portal_type == "dmsoutgoingmail" else "request")
                                        )
                                    ]
                                ),
                            },
                        )
                    )


class ISignRequestSignerSchema(ISignerSchema):
    """Signer row for sign_request: a signature is mandatory, so no "_empty_" choice."""

    signer = schema.Choice(
        title=_(u"Signer"),
        description=_(u"Related userid will be the signer. Position name of the held position will be used."),
        source=signing_request_signers,
        required=True,
    )

    approvings = schema.List(
        title=_(u"Approvings"),
        description=_(u"User(s) that can approve the item before the signing session."),
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.SigningRequestApprovingsVocabulary"),
        required=True,
        constraint=validate_approvings,
        min_length=1,
    )
    form.widget("approvings", CheckBoxFieldWidget, multiple="multiple", size=5)


# keep original column order despite redeclaring the fields
# (the DataGridField orders columns by field.order, not by plone.autoform order directives)
ISignRequestSignerSchema["signer"].order = ISignerSchema["signer"].order
ISignRequestSignerSchema["approvings"].order = ISignerSchema["approvings"].order


@provider(IFormFieldProvider)
class ISignRequestSigningBehavior(ISigningBehavior):
    """Signing behavior for sign_request: mandatory signature (no "_empty_" for signer/approvings)."""

    signers = schema.List(
        title=_(u"Signers"),
        description=_("List of users who have to sign this document"),
        value_type=DictRow(title=_("Signer"), schema=ISignRequestSignerSchema),
        required=False,
        default=None,
    )
    form.widget(
        "signers",
        ExpandableDataGridFieldFactory,
        allow_reorder=False,
        auto_append=False,
    )

    # a signing request is always an electronic signature request: always True, hidden on add / edit forms
    esign = schema.Bool(
        title=_(u"Electronic signature"),
        required=False,
        default=True,
    )
    form.mode(IAddForm, esign="hidden")
    form.mode(IEditForm, esign="hidden")


class PlonegroupUserLinkUseridValidator(validator.SimpleFieldValidator):
    def validate(self, value, force=False):
        # if old value is None, nothing to do
        if not hasattr(self.context, "userid") or getattr(self.context, "userid", None) is None:
            return

        # Raise if trying to remove an existing userid while the linked user is still in a group
        if not value:
            user = api.user.get(self.context.userid)
            groups = user and [g for g in get_plone_groups_for_user(user=user)
                               if g not in ("AuthenticatedUsers", "Anonymous")] or []
            if groups:
                raise Invalid(_(u"You cannot remove a userid from the person while the user is still in a group."))
            return

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
                for signer_dic in (mail.signers or []):
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


class UsagesSignerRulesValidator(validator.SimpleFieldValidator):
    """Raise Invalid when removing a signer/approving usage that is still
    referenced in omail_signer_rules or omail_signer_substitutes."""

    def validate(self, value, force=False):
        super(UsagesSignerRulesValidator, self).validate(value, force=force)
        if self.context.portal_type == "person" or not IPersonnelContact.providedBy(self.context):
            # on addition or outside personnel, we skip check
            return
        if is_hp_used_in_signer_rules(self.context, value or []):
            raise Invalid(_(
                u"This position is still referenced in the outgoing mail signer configuration. "
                u"Please update the rules and substitutes before removing this usage."
            ))


validator.WidgetValidatorDiscriminators(UsagesSignerRulesValidator, field=IUsagesBehavior['usages'])


@provider(IFormFieldProvider)
class IDefaultContentCategoryBehavior(model.Schema):

    default_content_category = schema.Choice(
        title=_(u"Default content category"),
        description=_("Category to apply on generated documents from this template."),
        vocabulary=u"imio.dms.mail.PODTemplateContentCategoriesVocabulary",
        required=True,
    )
