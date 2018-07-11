# -*- coding: utf-8 -*-
"""Reply form."""
# from collections import Counter
# from z3c.form.interfaces import DISPLAY_MODE
from zope.component import getUtility
from plone.dexterity.browser.add import DefaultAddForm
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer
from Products.CMFPlone.utils import safe_unicode

from imio.dms.mail import _
from ..dmsmail import ImioDmsOutgoingMailUpdateFields, ImioDmsOutgoingMailUpdateWidgets
from imio.dms.mail.browser.batchactions import brains_from_uids


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
        form["form.widgets.recipients"] = tuple([sd.to_path for sd in imail.sender])
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
        prefix = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                'omail_response_prefix', default='') or ''
        self.widgets["IDublinCore.title"].value = u"%s%s" % (prefix, safe_unicode(imail.title))
        self.widgets["treating_groups"].value = imail.treating_groups
        self.widgets["reply_to"].value = ('/'.join(imail.getPhysicalPath()),)
        self.widgets["recipients"].value = tuple([sd.to_path for sd in imail.sender])
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


class MultipleReplyForm(ReplyForm):

    """Form to reply to multiple incoming mails."""

    def __init__(self, context, request):
        super(MultipleReplyForm, self).__init__(context, request)
        self.uids = self.request.get('uids', '')
        self.brains = brains_from_uids(self.uids)

    @property
    def label(self):
        return _(u"Reply to ${ref}", mapping={'ref': u'%d %s' % (len(self.brains),
                                                                 api.portal.translate('incoming mails',
                                                                                      'imio.dms.mail'))})

    def updateFields(self):
        super(ReplyForm, self).updateFields()
        form = self.request.form
        # Completing form values wasn't working anymore, but relations must be set here too !
        if self.uids:  # view is called a second time by masterselect. uids is empty.
                       # We don't want to change request form values
            form["form.widgets.reply_to"] = tuple([b.getPath() for b in self.brains])
            sender_uids = set([sender for b in self.brains for sender in b.sender_index if not sender.startswith('l:')])
            form["form.widgets.recipients"] = [b.getPath() for b in brains_from_uids(list(sender_uids))]
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(ReplyForm, self).updateWidgets()
        if self.uids:  # see upper comment
            first = self.brains and self.brains[0] or None
            form = self.request.form
            prefix = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                    'omail_response_prefix', default='') or ''
            self.widgets["IDublinCore.title"].value = u"%s%s" % (prefix, safe_unicode(first and
                                                                 self.brains[0].get_full_title or ''))
            # self.widgets["treating_groups"].value = Counter([b.treating_groups
            #                                                  for b in self.brains]).most_common(1)[0][0]
            self.widgets["treating_groups"].value = first and self.brains[0].treating_groups or []
            self.widgets["reply_to"].value = form["form.widgets.reply_to"]
            self.widgets["recipients"].value = form["form.widgets.recipients"]
            self.widgets["recipient_groups"].value = list(set([uid for b in self.brains for uid in b.recipient_groups
                                                               if b.recipient_groups]))
        ImioDmsOutgoingMailUpdateWidgets(self)
