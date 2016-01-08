# -*- coding: utf-8 -*-
import copy

from zope import schema
from zope.component import getUtility, queryUtility
from zope.interface import implements, alsoProvides
from zope.schema.fieldproperty import FieldProperty
#from plone.autoform.interfaces import IFormFieldProvider
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IContextSourceBinder
from z3c.form.interfaces import HIDDEN_MODE
from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.autoform import directives
from plone.dexterity.browser.add import DefaultAddView, DefaultAddForm
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.registry.interfaces import IRegistry
from plone.app.dexterity.behaviors.metadata import IDublinCore
from plone.app.dexterity.behaviors.metadata import IBasic
from AccessControl import getSecurityManager

from collective.contact.plonegroup.browser.settings import SelectedOrganizationsElephantVocabulary
from collective.dms.basecontent.browser.views import DmsDocumentEdit, DmsDocumentView
from collective.dms.mailcontent.dmsmail import (IDmsIncomingMail, DmsIncomingMail, IDmsOutgoingMail,
                                                originalMailDateDefaultValue)
from collective.task.field import LocalRoleMasterSelectField
from dexterity.localrolesfield.field import LocalRolesField

from browser.settings import IImioDmsMailConfig
from utils import voc_selected_org_suffix_users

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


def filter_dmsincomingmail_assigned_users(org_uid):
    """
        Filter assigned_user in dms incoming mail
    """
    return voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur'])


class IImioDmsIncomingMail(IDmsIncomingMail):
    """
        Extended schema for mail type field
    """

    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        vocabulary=u'collective.dms.basecontent.treating_groups',
        slave_fields=(
            {'name': 'ITask.assigned_user',
             'slaveID': '#form-widgets-ITask-assigned_user',
             'action': 'vocabulary',
             'vocab_method': filter_dmsincomingmail_assigned_users,
             'control_param': 'org_uid',
             'initial_trigger': True,
             },
        )
    )
    # Using write_permission hides field. Using display in edit view is preferred
    # directives.write_permission(treating_groups='imio.dms.mail.write_treating_group_field')

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups')
    )

    mail_type = schema.Choice(
        title=_("Mail type"),
#        description = _("help_mail_type",
#            default=u"Enter the mail type"),
        required=True,
        source=registeredMailTypes,
        default=None,
    )

    #password = schema.Password(
    #    title=_(u"Password"),
    #    description=_(u"Your password."),
    #    required=True,
    #    default='password'
    #)

    # doesn't work well if IImioDmsIncomingMail is a behavior instead a subclass
    directives.order_before(sender='recipient_groups')
    directives.order_before(mail_type='recipient_groups')
    directives.order_before(original_mail_date='recipient_groups')
    directives.order_before(reception_date='recipient_groups')
    directives.order_before(internal_reference_no='recipient_groups')
    directives.order_before(external_reference_no='recipient_groups')
    directives.order_before(notes='recipient_groups')
    directives.order_before(treating_groups='recipient_groups')

    directives.omitted('reply_to', 'related_docs', 'recipients', 'notes')
    #directives.widget(recipient_groups=SelectFieldWidget)

# Compatibility with old vocabularies
TreatingGroupsVocabulary = SelectedOrganizationsElephantVocabulary
RecipientGroupsVocabulary = SelectedOrganizationsElephantVocabulary


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

    treating_groups = FieldProperty(IImioDmsIncomingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsIncomingMail[u'recipient_groups'])


def ImioDmsIncomingMailUpdateWidgets(the_form):
    """
        Widgets update method for add and edit
    """
    current_user = api.user.get_current()
    if not current_user.has_role('Manager') and not current_user.has_role('Site Administrator'):
        the_form.widgets['internal_reference_no'].mode = 'hidden'
        # we empty value to bypass validator when creating object
        if the_form.context.portal_type != 'dmsincomingmail':
            the_form.widgets['internal_reference_no'].value = ''

    for field in ['ITask.assigned_group', 'ITask.enquirer', 'IVersionable.changeNote']:
        the_form.widgets[field].mode = HIDDEN_MODE

    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    if settings.original_mail_date_required:
        the_form.widgets['original_mail_date'].required = True
        if the_form.widgets['original_mail_date'].value == ('', '', ''):  # field value is None
            date = originalMailDateDefaultValue(None)
            the_form.widgets['original_mail_date'].value = (date.year, date.month, date.day)
    else:
        the_form.widgets['original_mail_date'].required = False
        # if the context original_mail_date is already set, the widget value is good and must be kept
        if not base_hasattr(the_form.context, 'original_mail_date') or the_form.context.original_mail_date is None:
            the_form.widgets['original_mail_date'].value = ('', '', '')


class IMEdit(DmsDocumentEdit):
    """
        Edit form redefinition to customize fields.
    """

    def updateWidgets(self):
        super(IMEdit, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)
        sm = getSecurityManager()
        incomingmail_fti = api.portal.get_tool('portal_types').dmsincomingmail
        behaviors = incomingmail_fti.behaviors
        display_fields = []
        if not sm.checkPermission('imio.dms.mail : Write incoming mail field', self.context):
            if IDublinCore.__identifier__ in behaviors:
                display_fields = [
                    'IDublinCore.title',
                    'IDublinCore.description']
            elif IBasic.__identifier__ in behaviors:
                display_fields = [
                    'IBasic.title',
                    'IBasic.description']

            display_fields.extend([
                'sender',
                'mail_type',
                'reception_date',
                'original_mail_date',
            ])
        if not sm.checkPermission('imio.dms.mail : Write treating group field', self.context):
            display_fields.append('treating_groups')

        for field in display_fields:
            self.widgets[field].mode = 'display'

        # disable left column
        self.request.set('disable_plone.leftcolumn', 1)

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.assigned_user_check and not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')
        else:
            self.widgets['ITask.assigned_user'].field.description = u''


class IMView(DmsDocumentView):
    """
        View form redefinition to customize fields.
    """

    def updateWidgets(self):
        super(IMView, self).updateWidgets()
        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.assigned_user_check and not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')


class CustomAddForm(DefaultAddForm):

    portal_type = 'dmsincomingmail'

    def updateWidgets(self):
        super(CustomAddForm, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)


class AddIM(DefaultAddView):

    form = CustomAddForm


class IImioDmsOutgoingMail(IDmsOutgoingMail):
    """
        Extended schema for mail type field
    """
    directives.order_before(recipients='related_docs')  # temporary when removing *_groups
    directives.order_before(mail_date='related_docs')  # temporary when removing *_groups
    directives.order_before(internal_reference_no='related_docs')  # temporary when removing *_groups
    directives.order_before(reply_to='related_docs')  # temporary when removing *_groups
    directives.order_after(notes='related_docs')  # temporary when removing *_groups

    directives.omitted('treating_groups', 'recipient_groups')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsOutgoingMail, )
