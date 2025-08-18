# -*- coding: utf-8 -*-

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from imio.dms.mail import _
from plone.autoform import directives as form
from plone.autoform.directives import widget
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import directives
from plone.supermodel import model
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface
from zope.interface import provider
from zope.schema import ValidationError
from zope.schema.vocabulary import SimpleVocabulary


@provider(IFormFieldProvider)
class ISignerBehavior(model.Schema):

    usages = schema.List(
        title=_("Usages"),
        value_type=schema.Choice(vocabulary="imio.dms.mail.HeldPositionUsagesVocabulary"),
        required=False,
        default=[],
    )
    form.widget("usages", CheckBoxFieldWidget, multiple="multiple")


class InvalidValidators(ValidationError):
    __doc__ = _(u"You cannot select validators and no validation at the same time.")


def validate_validators(validators):
    if u"_empty_" in validators and len(validators) > 1:
        raise InvalidValidators(validators)
    return True


class ISignerSchema(Interface):
    """Schema for the table of signers in the DataGridField."""

    number = schema.Choice(
        title=_(u"Number"),
        vocabulary=SimpleVocabulary.fromValues(range(1, 10)),
        required=True,
    )

    held_position = schema.Choice(
        title=_(u"Signer"),
        vocabulary="imio.dms.mail.SigningHeldpositionVocabulary",
        required=True,
    )

    validators = schema.List(
        title=_(u"Validators"),
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.SigningValidatorsVocabulary"),
        required=True,
        constraint=validate_validators,
    )
    widget("validators", CheckBoxFieldWidget, multiple="multiple", size=5)


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
    widget(
        "signers",
        DataGridFieldFactory,
        allow_reorder=False,
        auto_append=False,
    )

    seal = schema.Bool(
        title=_(u"Seal"),
        required=False,
    )
