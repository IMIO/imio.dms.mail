# -*- coding: utf-8 -*-
"""Reply form."""
# from z3c.form.interfaces import DISPLAY_MODE
from zope.component import getUtility
from plone.dexterity.browser.add import DefaultAddForm
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer

from Products.CPUtils.Extensions.utils import safe_encode

from imio.dms.mail import _
from ..dmsmail import ImioDmsOutgoingMailUpdateFields, ImioDmsOutgoingMailUpdateWidgets


class ReplyForm(DefaultAddForm):

    """Form to reply to an incoming mail."""

    description = u""
    portal_type = "dmsoutgoingmail"

    @property
    def label(self):
        return _(u"Reply to ${ref}", mapping={'ref': self.context.Title()})

    def updateFields(self):
        super(ReplyForm, self).updateFields()
        imail = self.context
        form = self.request.form
        form["form.widgets.IDublinCore.title"] = "Réponse: %s" % safe_encode(imail.title)
        form["form.widgets.reply_to"] = ('/'.join(imail.getPhysicalPath()),)
        form["form.widgets.recipients"] = ('/'.join(imail.sender.to_object.getPhysicalPath()), )
        if imail.external_reference_no:
            form["form.widgets.external_reference_no"] = imail.external_reference_no
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(ReplyForm, self).updateWidgets()
        ImioDmsOutgoingMailUpdateWidgets(self)

    def add(self, obj):
        """Create outgoing mail in outgoing-mail folder."""
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        container = api.portal.get()['outgoing-mail']
        new_object = addContentToContainer(container, obj)

        if fti.immediate_view:
            self.immediate_view = "/".join(
                [container.absolute_url(), new_object.id, fti.immediate_view]
            )
        else:
            self.immediate_view = "/".join(
                [container.absolute_url(), new_object.id]
            )
