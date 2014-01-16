# -*- coding: utf-8 -*-
from zope import schema
from zope.component.hooks import getSite
from zope.component import getUtility, queryUtility
from zope.interface import implements, alsoProvides
from plone import api
from plone.directives import dexterity
#from plone.autoform.interfaces import IFormFieldProvider
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IVocabularyFactory, IContextSourceBinder
from five import grok
from plone.autoform import directives
from collective.dms.mailcontent.dmsmail import IDmsIncomingMail, DmsIncomingMail, IDmsOutgoingMail
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize import forever
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import getToolByName
from browser.settings import IImioDmsMailConfig
from collective.contact.plonegroup.browser.settings import selectedOrganizationsPloneGroupsVocabulary
from z3c.form.browser.select import SelectFieldWidget

from . import _


def registeredMailTypes(context):
    """
        Use the mail_types variable from the registry
    """
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    terms = [SimpleTerm(None, token='', title=_("Choose a value !"))]
    id_utility = queryUtility(IIDNormalizer)
    for mail_type in settings.mail_types:
        #value (stored), token (request), title
        if mail_type['mt_active']:
            terms.append(SimpleVocabulary.createTerm(mail_type['mt_value'],
                         id_utility.normalize(mail_type['mt_value']), mail_type['mt_title']))
    return SimpleVocabulary(terms)

alsoProvides(registeredMailTypes, IContextSourceBinder)


class IImioDmsIncomingMail(IDmsIncomingMail):
    """
        Extended schema for mail type field
    """
    mail_type = schema.Choice(
        title=_("Mail type"),
#        description = _("help_mail_type",
#            default=u"Enter the mail type"),
        required=True,
        source=registeredMailTypes,
        default=None,
    )

    # doesn't work well if IImioDmsIncomingMail is a behavior instead a subclass
#    directives.order_after(mail_type='sender')
    directives.order_before(sender='treating_groups')  # temporary when removing *_groups
    directives.order_before(mail_type='treating_groups')
    directives.order_before(original_mail_date='treating_groups')  # temporary when removing *_groups
    directives.order_before(reception_date='treating_groups')  # temporary when removing *_groups
    directives.order_before(internal_reference_no='treating_groups')  # temporary when removing *_groups
    directives.order_before(external_reference_no='treating_groups')  # temporary when removing *_groups
    directives.order_before(in_reply_to='treating_groups')  # temporary when removing *_groups
#    directives.order_before(treating_groups='related_docs')  # temporary when removing *_groups
#    directives.order_after(related_docs='recipient_groups')  # temporary when removing *_groups
    directives.order_after(notes='treating_groups')  # temporary when removing *_groups

    directives.omitted('recipient_groups', 'in_reply_to', 'related_docs')
    directives.widget(treating_groups=SelectFieldWidget)


class TreatingGroupsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return selectedOrganizationsPloneGroupsVocabulary(functions=['editeur'], group_title=False)


class RecipientGroupsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return selectedOrganizationsPloneGroupsVocabulary(functions=['lecteur'], group_title=False)


class ImioDmsIncomingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsIncomingMail, )

#alsoProvides(IImioDmsIncomingMail, IFormFieldProvider) #needed for behavior


class ImioDmsIncomingMail(DmsIncomingMail):
    """
    """
    implements(IImioDmsIncomingMail)
    __ac_local_roles_block__ = False

    def Title(self):
        if self.internal_reference_no is None:
            return self.title.encode('utf8')
        return "%s - %s" % (self.internal_reference_no.encode('utf8'), self.title.encode('utf8'))


def ImioDmsIncomingMailUpdateWidgets(the_form):
    """
        Widgets update method for add and edit
    """
    the_form.widgets['treating_groups'].multiple = 'multiple'
    the_form.widgets['treating_groups'].size = 5
    current_user = api.user.get_current()
    if not current_user.has_role('Manager') and not current_user.has_role('Site Administrator'):
        the_form.widgets['internal_reference_no'].mode = 'hidden'
        # we empty value to bypass validator
        the_form.widgets['internal_reference_no'].value = ''


class Edit(dexterity.EditForm):
    """
        Edit form redefinition to customize fields.
    """
    grok.context(IImioDmsIncomingMail)

    def updateWidgets(self):
        dexterity.EditForm.updateWidgets(self)
        ImioDmsIncomingMailUpdateWidgets(self)


class Add(dexterity.AddForm):
    """
        Add form redefinition to customize fields.
    """
    #grok.context(IImioDmsIncomingMail)
    grok.name('dmsincomingmail')

    def updateWidgets(self):
        dexterity.AddForm.updateWidgets(self)
        ImioDmsIncomingMailUpdateWidgets(self)


class IImioDmsOutgoingMail(IDmsOutgoingMail):
    """
        Extended schema for mail type field
    """
    directives.order_before(recipients='related_docs')  # temporary when removing *_groups
    directives.order_before(mail_date='related_docs')  # temporary when removing *_groups
    directives.order_before(internal_reference_no='related_docs')  # temporary when removing *_groups
    directives.order_before(in_reply_to='related_docs')  # temporary when removing *_groups
    directives.order_after(notes='related_docs')  # temporary when removing *_groups

    directives.omitted('treating_groups', 'recipient_groups')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsOutgoingMail, )
