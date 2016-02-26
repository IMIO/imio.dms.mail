# -*- coding: utf-8 -*-
"""Reply form."""
# from z3c.form.interfaces import DISPLAY_MODE
from plone.dexterity.browser.add import DefaultAddForm

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
