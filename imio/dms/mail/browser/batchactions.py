# -*- coding: utf-8 -*-
"""Batch actions views."""

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.lifecycleevent import modified

from AccessControl import getSecurityManager
from plone import api
from plone.supermodel import model
from z3c.form.form import Form
from z3c.form import button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from Products.CMFPlone import PloneMessageFactory as PMF
from Products.CMFPlone.utils import safe_unicode

from collective.task.behaviors import ITask
from imio.dms.mail.dmsmail import IImioDmsIncomingMail

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
        voc = getAvailableTransitionsVoc(brains_from_uids(self.request.form['form.widgets.uids']))
        self.fields += Fields(schema.Choice(
            __name__='transition',
            title=_(u'Transition'),
            vocabulary=voc,
            description=(len(voc) == 0 and _(u'No common or available transition. Close this and modify your selection.') or u''),
            required=(len(voc) and True or False)))
        self.fields += Fields(schema.Text(
            __name__='comment',
            title=_(u'Comment'),
            description=_(u'Optional comment to display in history'),
            required=False))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply')
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        for brain in self.brains:
            obj = brain.getObject()
            api.content.transition(obj=obj, transition=data['transition'],
                                   comment=self.request.form.get('form.widgets.comment', ''))
        self.request.response.redirect(self.request.form['form.widgets.referer'])


class OldTreatingGroupBatchActionForm(DashboardBatchActionForm):

    def update(self):
        super(TreatingGroupBatchActionForm, self).update()
        #voc = getAvailableTreatingGroupVoc(brains_from_uids(self.request.form['form.widgets.uids']))
        im_fields = Fields(IImioDmsIncomingMail)
        self.fields += im_fields.select('treating_groups')
        task_fields = Fields(ITask)
        self.fields += task_fields.select('assigned_user')
        fld = self.fields['treating_groups'].field
        fld.slave_fields[0]['name'] = 'assigned_user'
        fld.slave_fields[0]['slaveID'] = '#form-widgets-assigned_user'

        super(DashboardBatchActionForm, self).update()

#    def updateWidgets(self):
#        super(TreatingGroupBatchActionForm, self).updateWidgets()


def checkSelectionAboutTreatingGroup(brains):
    """ Check all brains to verify treating_groups change permission """
    ret = []
    sm = getSecurityManager()
    for brain in brains:
        obj = brain.getObject()
        if not sm.checkPermission('imio.dms.mail : Write treating group field', obj):
            ret.append(obj)
    return ret


class TreatingGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch treating group change")

    def update(self):
        super(TreatingGroupBatchActionForm, self).update()
        pb = checkSelectionAboutTreatingGroup(brains_from_uids(self.request.form['form.widgets.uids']))
        self.fields += Fields(schema.Choice(
            __name__='treating_group',
            title=_(u"Treating groups"),
            description=(len(pb) and _(u"You can't change this field on selected items. Modify your selection.") or u''),
            required=(len(pb) == 0 and True or False),
            vocabulary=(len(pb) == 0 and u'collective.dms.basecontent.treating_groups' or SimpleVocabulary([])),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply')
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        for brain in self.brains:
            obj = brain.getObject()
            obj.treating_groups = data['treating_group']
            modified(obj)
        self.request.response.redirect(self.request.form['form.widgets.referer'])
