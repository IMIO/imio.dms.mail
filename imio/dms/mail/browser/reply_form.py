# -*- coding: utf-8 -*-
"""Reply form."""
# from z3c.form.interfaces import DISPLAY_MODE
from zope.component import getUtility
from plone.dexterity.browser.add import DefaultAddForm
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer

from imio.dms.mail import _


class ReplyForm(DefaultAddForm):

    """Form to reply to an incoming mail."""

    description = u""
    portal_type = "dmsoutgoingmail"

    @property
    def label(self):
        return _(u"Reply to ${ref}", mapping={'ref': self.context.Title()})

    def updateFields(self):
        super(ReplyForm, self).updateFields()
        value = ('/'.join(self.context.getPhysicalPath()),)
        self.request.form["linked_mails"] = value
        self.request.form["form.widgets.linked_mails"] = value
        # self.fields['linked_mails'].mode = DISPLAY_MODE

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
