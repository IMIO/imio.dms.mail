# -*- coding: utf-8 -*-

"""
    Extension of the collective.dms.mailcontent settings configlet
    (IDmsMailConfig / @@dmsmailcontent-settings).

    We add the internal reference auto-numbering fields for the sign_request
    type. The records are kept under the *original* IDmsMailConfig prefix (see
    ``SettingsEditForm.schema_prefix``) so the whole configlet keeps reading
    and writing a single, consistent set of records.
"""
from collective.dms.mailcontent.browser.settings import IDmsMailConfig as IBaseDmsMailConfig
from collective.dms.mailcontent.browser.settings import SettingsEditForm as BaseSettingsEditForm
from collective.dms.mailcontent.browser.settings import SettingsView as BaseSettingsView
from imio.dms.mail import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.supermodel import model
from plone.z3cform import layout
from zope import schema


#: prefix under which every IDmsMailConfig record (inherited + added here) is stored
DMSMAILCONFIG_PREFIX = "collective.dms.mailcontent.browser.settings.IDmsMailConfig"


class IDmsMailConfig(IBaseDmsMailConfig):
    """Extends the mailcontent IDmsMailConfig with signing request fields."""

    model.fieldset(
        "signrequest",
        label=_(u"Signing request"),
        fields=["signrequest_number", "signrequest_talexpression"],
    )

    signrequest_number = schema.Int(
        title=_(u"Number of next signing request"),
        description=_(u"This value is used as 'number' variable in linked tal expression"),
        default=1,
    )

    signrequest_talexpression = schema.TextLine(
        title=_(u"Signing request internal reference default value expression"),
        description=_(u"Tal expression where you can use portal, number, context, request, date as variable"),
        default=u"python:'D%04d'%int(number)",
    )


class SettingsEditForm(BaseSettingsEditForm):
    """Configlet form using the extended schema, but storing every record
    under the original IDmsMailConfig prefix."""

    schema = IDmsMailConfig
    schema_prefix = DMSMAILCONFIG_PREFIX


class SettingsView(BaseSettingsView):
    """Override of the dmsmailcontent-settings configlet on the imio layer.

    Keeps ``evaluateTalExpression`` (inherited) used by the internal reference
    evaluation, and only swaps the wrapped form for the extended one.
    """

    def __call__(self):
        view_factory = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)
        view = view_factory(self.context, self.request)
        return view()
