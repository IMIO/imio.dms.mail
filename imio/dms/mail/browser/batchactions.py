# -*- coding: utf-8 -*-
"""Batch actions views."""

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone import api
from plone.supermodel import model
from z3c.form.form import Form
from z3c.form import button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from Products.CMFPlone import PloneMessageFactory as PMF
from Products.CMFPlone.utils import safe_unicode

from .. import _


class IIMBatchActionsFormSchema(model.Schema):

    uids = schema.TextLine(
        title=u"uids",
        description=u''
    )

    referer = schema.TextLine(
        title=u'referer',
        required=False,
    )


class DashboardBatchActionForm(Form):

    label = _(u"Batch action form")
    fields = Fields(IIMBatchActionsFormSchema)
    fields['uids'].mode = HIDDEN_MODE
    fields['referer'].mode = HIDDEN_MODE
    ignoreContext = True
    brains = []

    def update(self):
        form = self.request.form
        if 'form.widgets.uids' in form:
            uids = form['form.widgets.uids']
        else:
            uids = self.request.get('uids', '')
            form['form.widgets.uids'] = uids

        if 'form.widgets.referer' not in form:
            form['form.widgets.referer'] = self.request.get('referer', '').replace('@', '&').replace('!', '#')

        self.brains = self.brains or brains_from_uids(uids)

#    @button.buttonAndHandler(PMF(u'Cancel'), name='cancel')
#    def handleCancel(self, action):
#        self.request.response.redirect(self.request.get('HTTP_REFERER'))


def brains_from_uids(uids):
    """ Returns a list of brains from a string containing uids separated by comma """
    uids = uids.split(',')
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(UID=uids)
    return brains


def getAvailableTransitionsVoc(brains):
    """ Returns available transitions common for all brains """
    wtool = api.portal.get_tool(name='portal_workflow')
    terms = []
    transitions = set()
    for brain in brains:
        obj = brain.getObject()
        if not transitions:
            transitions = set([tr['id'] for tr in wtool.getTransitionsFor(obj)])
        else:
            transitions &= set([tr['id'] for tr in wtool.getTransitionsFor(obj)])
    for tr in transitions:
        terms.append(SimpleTerm(tr, tr, PMF(safe_unicode(tr))))
    return SimpleVocabulary(terms)


class TransitionBatchActionForm(DashboardBatchActionForm):

    buttons = DashboardBatchActionForm.buttons.copy()
    label = _(u"Batch state change")

    def update(self):
        super(TransitionBatchActionForm, self).update()
        self.fields += Fields(schema.Choice(
            __name__='transition',
            title=u'Transition',
            vocabulary=getAvailableTransitionsVoc(brains_from_uids(self.request.form['form.widgets.uids'])),
            required=True))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply')
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        for brain in self.brains:
            obj = brain.getObject()
            api.content.transition(obj=obj, transition=data['transition'])
        self.request.response.redirect(self.request.form['form.widgets.referer'])
