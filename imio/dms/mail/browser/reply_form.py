# -*- coding: utf-8 -*-
"""Reply form."""
# from z3c.form.interfaces import DISPLAY_MODE
from zope.component import getUtility
from plone.dexterity.browser.add import DefaultAddForm
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer
from Products.CMFPlone.utils import safe_unicode

from imio.dms.mail import _
from ..dmsmail import ImioDmsOutgoingMailUpdateFields, ImioDmsOutgoingMailUpdateWidgets


class ReplyForm(DefaultAddForm):

    """Form to reply to an incoming mail."""

    description = u""
    portal_type = "dmsoutgoingmail"

    @property
    def label(self):
        return _(u"Reply to ${ref}", mapping={'ref': safe_unicode(self.context.Title())})

    def updateFields(self):

        super(ReplyForm, self).updateFields()
        imail = self.context
        form = self.request.form
        # Completing form values wasn't working anymore, but relations must be set here too !
        form["form.widgets.reply_to"] = ('/'.join(imail.getPhysicalPath()),)
        form["form.widgets.recipients"] = (imail.sender.to_path, )
        # form["form.widgets.IDublinCore.title"] = "Réponse: %s" % safe_encode(imail.title)
        # form["form.widgets.treating_groups"] = imail.treating_groups
        # if imail.external_reference_no:
        #     form["form.widgets.external_reference_no"] = imail.external_reference_no
        # if imail.recipient_groups:
        #     form["form.widgets.recipient_groups"] = imail.recipient_groups
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(ReplyForm, self).updateWidgets()
        imail = self.context
        self.widgets["IDublinCore.title"].value = u"Réponse: %s" % safe_unicode(imail.title)
        self.widgets["treating_groups"].value = imail.treating_groups
        self.widgets["reply_to"].value = ('/'.join(imail.getPhysicalPath()),)
        self.widgets["recipients"].value = (imail.sender.to_path, )
        if imail.external_reference_no:
            self.widgets["external_reference_no"].value = imail.external_reference_no
        if imail.recipient_groups:
            self.widgets["recipient_groups"].value = imail.recipient_groups
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
