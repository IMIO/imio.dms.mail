# -*- coding: utf-8 -*-
"""Batch actions views."""
import json

from zope import schema
from zope.lifecycleevent import modified

from plone import api
from plone.supermodel import model
from z3c.form.form import Form
from z3c.form import button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from collective.task.behaviors import ITask

from imio.dms.mail import _


class IIMBatchActionsFormSchema(model.Schema):

    uids = schema.TextLine(
        title=_("uids"),
        description=u''
        )


class IMBatchactionsForm(Form):

    label = _(u"Batch actions form")
    fields = Fields(IIMBatchActionsFormSchema)
    fields['uids'].mode = HIDDEN_MODE
    ignoreContext = True

    def update(self):
        form = self.request.form
        if 'form.widgets.uids' in form:
            uids = form['form.widgets.uids']
        else:
            uids = self.request.get('select_item', [])
            form['form.widgets.uids'] = json.dumps(uids)

        task_fields = Fields(ITask)
        self.fields += task_fields.select('assigned_user')
        im_fields = Fields(IImioDmsIncomingMail)
        self.fields += im_fields.select('treating_groups')
        # TODO: workflow state
        super(IMBatchactionsForm, self).update()

    @button.buttonAndHandler(_(u'Execute these actions'), name='execute')
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # we execute the changes on all items
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(UID=json.loads(data['uids']))
        for brain in brains:
            obj = brain.getObject()
            obj.assigned_user = data['assigned_user']
            obj.treating_groups = data['treating_groups']
            modified(obj)

    def nextURL(self):
        """Redirect to dashboard."""
        return self.context.getParentNode().absolute_url()
