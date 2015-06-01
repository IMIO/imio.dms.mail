from zope import schema
from zope.interface import Interface
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.autoform.directives import widget
from plone.z3cform import layout
from z3c.form import form
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
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

    widget(mail_types=DataGridFieldFactory)

    assigned_user_check = schema.Bool(
        title=_(u'Assigned user check'),
        description=_(u'Check if there is an assigned user before proposing incoming mail to the agents.'),
        default=True
    )


class SettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    form.extends(RegistryEditForm)
    schema = IImioDmsMailConfig

SettingsView = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)
