# -*- coding: utf-8 -*-
"""Reply form."""
# from collections import Counter
from collective.dms.mailcontent.browser.reply_form import ReplyForm as BaseReplyForm
from collective.eeafaceted.batchactions.browser.views import brains_from_uids
from imio.dms.mail import _
from imio.dms.mail.dmsmail import ImioDmsOutgoingMailUpdateFields
from imio.dms.mail.dmsmail import ImioDmsOutgoingMailUpdateWidgets
from plone import api
from Products.CMFPlone.utils import safe_unicode


class ReplyForm(BaseReplyForm):

    """Form to reply to an incoming mail."""

    def updateFields(self):

        super(ReplyForm, self).updateFields()
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(ReplyForm, self).updateWidgets()
        prefix = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                'omail_response_prefix', default='') or ''
        self.widgets["IDublinCore.title"].value = u"%s%s" % (prefix, safe_unicode(self.context.title))
        ImioDmsOutgoingMailUpdateWidgets(self)


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
