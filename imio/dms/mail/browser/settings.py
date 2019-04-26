from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from imio.dms.mail import _
from imio.dms.mail.setuphandlers import configure_group_encoder
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.autoform.directives import widget
from plone.registry.interfaces import IRecordModifiedEvent
from plone.supermodel import model
from plone.z3cform import layout
from z3c.form import form
#from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.interface import Interface
from zope.interface import Invalid

import logging


logger = logging.getLogger('imio.dms.mail: settings')


class IMailTypeSchema(Interface):
    mt_value = schema.TextLine(title=_("Mail type value"), required=True)
    mt_title = schema.TextLine(title=_("Mail type title"), required=True)
    mt_active = schema.Bool(title=_("Active"), required=False)


class IImioDmsMailConfig(model.Schema):
    """
    Configuration of dms mail
    """

    model.fieldset(
        'incomingmail',
        label=_(u"Incoming mail"),
        fields=['mail_types', 'assigned_user_check', 'original_mail_date_required', 'imail_remark_states',
                'imail_group_encoder']
    )

    mail_types = schema.List(
        title=_(u'Types of incoming mail'),
        description=_(u"Once created and used, value doesn't be changed anymore."),
        value_type=DictRow(title=_("Mail type"),
                           schema=IMailTypeSchema))

    widget('mail_types', DataGridFieldFactory, allow_reorder=True)

    assigned_user_check = schema.Bool(
        title=_(u'Assigned user check'),
        description=_(u'Check if there is an assigned user before proposing incoming mail to an agent.'),
        default=True
    )

    original_mail_date_required = schema.Bool(
        title=_(u'Original mail date requirement'),
        description=_(u"Check if the incoming mail 'original mail date' field must be required."),
        default=True
    )

    imail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.IMReviewStatesVocabulary'),
    )

    imail_group_encoder = schema.Bool(
        title=_(u'Activate group encoder'),
        description=_(u"When activating this option, a group encoder function is added to manage incoming mails "
                      u"in creation. A new field is added to the mail to choose the creating group. "
                      u"Mails are then only visible by the creating group, no more by the global 'encoder' group. "
                      u"A list of 'encoder' groups, can be generated to be used in 'scanner program'. "
                      u"UNLESS ACTIVATED, THIS OPTION CAN'T BE UNDONE !!"),
        default=False
    )

    model.fieldset(
        'outgoingmail',
        label=_(u"Outgoing mail"),
        fields=['omail_types', 'omail_remark_states', 'omail_response_prefix', 'omail_odt_mainfile',
                'omail_sender_firstname_sorting', 'org_templates_encoder_can_edit']
    )

    omail_types = schema.List(
        title=_(u'Types of outgoing mail'),
        description=_(u"Once created and used, value doesn't be changed anymore."),
        value_type=DictRow(title=_("Mail type"),
                           schema=IMailTypeSchema))

    widget('omail_types', DataGridFieldFactory, allow_reorder=True)

    omail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.OMReviewStatesVocabulary'),
    )

    omail_response_prefix = schema.TextLine(
        title=_("Response prefix"),
        required=False
    )

    omail_odt_mainfile = schema.Bool(
        title=_(u'Dms file must be an odt format'),
        default=True
    )

    omail_sender_firstname_sorting = schema.Bool(
        title=_(u'Sender list is sorted on firstname'),
        default=True
    )

    org_templates_encoder_can_edit = schema.Bool(
        title=_(u'Enable edition of service templates for encoder'),
        description=_(u"Check if a service encoder can edit his service templates."),
        default=True
    )

    model.fieldset(
        'contact',
        label=_(u"Contacts"),
        fields=['all_backrefs_view']
    )

    all_backrefs_view = schema.Bool(
        title=_(u'A user can see all mail titles linked to a contact.'),
        default=False
    )


class SettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    form.extends(RegistryEditForm)
    schema = IImioDmsMailConfig

SettingsView = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)


def imiodmsmail_settings_changed(event):
    """ Manage a record change """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName and
            event.record.interface != IImioDmsMailConfig):
        return
    if event.record.fieldName == 'mail_types':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMMailTypesVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMActiveMailTypesVocabulary')
    if event.record.fieldName == 'omail_types':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMMailTypesVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMActiveMailTypesVocabulary')
    if event.record.fieldName == 'imail_group_encoder':
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'):
            configure_group_encoder('dmsincomingmail')
        else:
            logger.exception('Unchecking the imail_group_encoder setting is not expected !!')
            from imio.dms.mail import _tr as _
            raise Invalid(_(u'Unchecking the imail_group_encoder setting is not expected !!'))
