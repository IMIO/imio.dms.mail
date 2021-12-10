# -*- coding: utf-8 -*-
"""Reply form."""
# from collections import Counter
from collective.dms.mailcontent.browser.reply_form import ReplyForm as BaseReplyForm
from collective.eeafaceted.batchactions.browser.views import brains_from_uids
from imio.dms.mail import _
from imio.dms.mail.utils import manage_fields
from imio.dms.mail.dmsmail import imio_dmsoutgoingmail_updatefields
from imio.dms.mail.dmsmail import imio_dmsoutgoingmail_updatewidgets
from imio.dms.mail.dmsmail import manage_email_fields
from plone import api
from Products.CMFPlone.utils import safe_unicode
from z3c.form.form import applyChanges


class ReplyForm(BaseReplyForm):

    """Form to reply to an incoming mail."""
    IMMODES = {'dmsincomingmail': u'post', 'dmsincoming_email': u'email'}

    def updateFields(self):
        super(ReplyForm, self).updateFields()
        manage_email_fields(self, 'add')
        manage_fields(self, 'omail_fields', 'edit')
        imio_dmsoutgoingmail_updatefields(self)

    def updateWidgets(self):
        super(ReplyForm, self).updateWidgets()
        if self.request.get('masterID'):  # in MS anonymous call, no need to go further
            return
        prefix = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                'omail_response_prefix', default='') or ''
        self.widgets['IDublinCore.title'].value = u"%s%s" % (prefix, safe_unicode(self.context.title))
        self.widgets['send_modes'].value = self.get_send_modes()
        if self.context.orig_sender_email:
            self.widgets['orig_sender_email'].value = self.context.orig_sender_email

        for fieldname in ("classification_categories", "classification_folders"):
            widgetname = "IClassificationFolder.{0}".format(fieldname)
            if getattr(self.context, fieldname, None):
                widget = self.widgets[widgetname]
                widget.value = getattr(self.context, fieldname)
                # Terms must be updated to ensure that `displayValue` work correctly
                terms = []
                for key in widget.value:
                    terms.append(widget.source.getTerm(key))
                widget.terms = widget.terms.__class__(
                    widget.context,
                    widget.request,
                    widget.form,
                    widget.field,
                    widget,
                    terms,
                )

        imio_dmsoutgoingmail_updatewidgets(self)

    def create(self, data):
        """Overrides to set IClassificationFolder fields"""
        content = super(ReplyForm, self).create(data)
        # we have to apply changes again because the base method wraps acquisition around the content
        # the classification fields are then considered as unchanged
        # we do it again without this wrap and only on classification data
        filtered_data = {key: value for key, value in data.items() if key.startswith('IClassificationFolder')}
        applyChanges(self, content, filtered_data)
        return content

    def get_send_modes(self):
        immode = self.IMMODES[self.context.portal_type]
        res = [term.value for term in self.widgets['send_modes'].terms if term.value.startswith(immode)]
        return res[0:1]


class MultipleReplyForm(BaseReplyForm):

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
        super(BaseReplyForm, self).updateFields()  # skipping BaseReplyForm itself
        self.update_fields_irn()
        # Completing form values wasn't working anymore, but relations must be set here too !
        if self.uids:  # view is called a 2d time by MS. uids is empty. We don't want to change request form values
            form = self.request.form
            if "form.widgets.reply_to" not in form:
                form["form.widgets.reply_to"] = tuple([b.getPath() for b in self.brains])
            if "form.widgets.recipients" not in form:
                sender_uids = set([sender for b in self.brains for sender in b.sender_index
                                   if not sender.startswith('l:')])
                form["form.widgets.recipients"] = [b.getPath() for b in brains_from_uids(list(sender_uids))]
        imio_dmsoutgoingmail_updatefields(self)

    def updateWidgets(self):
        super(BaseReplyForm, self).updateWidgets()  # skipping BaseReplyForm itself
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
            self.widgets["recipient_groups"].value = list(set([uid for b in self.brains if b.recipient_groups
                                                               for uid in b.recipient_groups]))
        imio_dmsoutgoingmail_updatewidgets(self)
