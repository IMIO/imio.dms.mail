from zope import schema
from zope.interface import Interface
from z3c.form import form
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.autoform.directives import widget
from plone.registry.interfaces import IRecordModifiedEvent
from plone.z3cform import layout

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from imio.helpers.cache import invalidate_cachekey_volatile_for

from .. import _


class IMailTypeSchema(Interface):
    mt_value = schema.TextLine(title=_("Mail type value"), required=True)
    mt_title = schema.TextLine(title=_("Mail type title"), required=True)
    mt_active = schema.Bool(title=_("Active"), required=False)


class IImioDmsMailConfig(Interface):
    """
    Configuration of dms mail
    """

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


class SettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    form.extends(RegistryEditForm)
    schema = IImioDmsMailConfig

SettingsView = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)


def manageIImioDmsMailConfigChange(event):
    """ Manage a record change """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interface == IImioDmsMailConfig
            and event.record.fieldName == 'mail_types'):
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMMailTypesVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMActiveMailTypesVocabulary')
