# -*- coding: utf-8 -*-

from collective.contact.plonegroup import _ as _ccp
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from imio.dms.mail import _
from imio.dms.mail.browser.settings import validate_approvings
from imio.dms.mail.utils import vocabularyname_to_terms
from plone.autoform import directives as form
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import directives
from plone.supermodel import model
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface
from zope.interface import provider
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


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
    )
    form.widget("approvings", CheckBoxFieldWidget, multiple="multiple", size=5)


@provider(IFormFieldProvider)
class ISigningBehavior(model.Schema):

    # directives.fieldset(
    #     "signing",
    #     label=_(u"Signing"),
    #     fields=[
    #         "signers",
    #         "seal",
    #     ],
    # )

    signers = schema.List(
        title=_(u"Signers"),
        description=_("List of users who have to sign this document"),
        value_type=DictRow(title=_("Signer"), schema=ISignerSchema),
        required=False,
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
