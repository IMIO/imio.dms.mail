# -*- coding: utf-8 -*-

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from imio.dms.mail import _
from plone.autoform import directives as form
from plone.autoform.directives import widget
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface
from zope.interface import provider
from zope.schema.vocabulary import SimpleVocabulary


@provider(IFormFieldProvider)
class ISignerBehavior(model.Schema):

    usages = schema.List(
        title=_("Usages"),
        value_type=schema.Choice(
            vocabulary="imio.dms.mail.HeldPositionUsagesVocabulary"),
        required=False,
        default=[],
    )
    form.widget('usages', CheckBoxFieldWidget, multiple='multiple')


class ITableSignersSchema(Interface):
    """Schema for the table of signers in the DataGridField."""

    number = schema.Choice(
        title=_(u'Number'),
        vocabulary=SimpleVocabulary.fromValues(range(1, 10)),
    )

    seal = schema.Bool(
        title=_(u'Seal'),
        description=_(u'Indicate if the signer should seal the document'),
    )

    validator = schema.Choice(
        title=_(u'Validateur'),
        vocabulary=u"imio.dms.mail.OMSignersVocabulary",  # TODO Define the list of validators
    )

    signer = schema.Choice(
        title=_(u'Signer'),
        vocabulary=u"imio.dms.mail.OMSignersVocabulary",
    )


@provider(IFormFieldProvider)
class ISignersBehavior(model.Schema):

    signers = schema.List(
        title=_(u'Signers'),
        description=_("List of users who have to sign this document"),
        value_type=DictRow(title=_("Signer"), schema=ITableSignersSchema),
    )
    widget("signers", DataGridFieldFactory)
