# -*- coding: utf-8 -*-
"""Batch actions views."""

from AccessControl import getSecurityManager
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.task import _ as TMF
from collective.task.behaviors import ITask
from collective.task.interfaces import ITaskContent
from imio.dms.mail import _
from imio.dms.mail import DOC_ASSIGNED_USER_FUNCTIONS
from imio.dms.mail import EMPTY_STRING
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from operator import methodcaller
from plone import api
from plone.formwidget.masterselect import MasterSelectField
from plone.supermodel import model
from Products.CMFPlone import PloneMessageFactory as PMF
from Products.CMFPlone.utils import safe_unicode
from z3c.form import button
from z3c.form.browser.select import SelectFieldWidget
from z3c.form.field import Fields
from z3c.form.form import Form
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getMultiAdapter
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import datetime


class IDashboardBatchActionsFormSchema(model.Schema):

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
    fields = Fields(IDashboardBatchActionsFormSchema)
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
    if isinstance(uids, basestring):
        uids = uids.split(',')
    if not uids:
        return []
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(UID=uids)
    return brains


def canNotModify(brains, perm='Modify portal content'):
    """ Check all brains to verify change permission """
    pb = False
    sm = getSecurityManager()
    for brain in brains:
        obj = brain.getObject()
        if not sm.checkPermission(perm, obj):
            pb = True
            break
    return pb

cannot_modify_msg = _(u"You can't change this field on selected items. Modify your selection.")


def filter_on_permission(brains, perm='Modify portal content'):
    """ Return only objects where current user has the permission """
    ret = []
    sm = getSecurityManager()
    for brain in brains:
        obj = brain.getObject()
        if sm.checkPermission(perm, obj):
            ret.append(obj)
    return ret

# IM batch actions


def getAvailableTransitionsVoc(db, brains):
    """ Returns available transitions common for all brains """
    wtool = api.portal.get_tool(name='portal_workflow')
    terms = []
    transitions = None
    for brain in brains:
        obj = brain.getObject()
        if transitions is None:
            transitions = set([(tr['id'], tr['title']) for tr in wtool.getTransitionsFor(obj)])
        else:
            transitions &= set([(tr['id'], tr['title']) for tr in wtool.getTransitionsFor(obj)])
    if transitions:
        for (id, tit) in transitions:
            terms.append(SimpleTerm(id, id, PMF(safe_unicode(tit))))
    return SimpleVocabulary(terms)


class TransitionBatchActionForm(DashboardBatchActionForm):

    buttons = DashboardBatchActionForm.buttons.copy()
    label = _(u"Batch state change")

    def update(self):
        super(TransitionBatchActionForm, self).update()
        self.voc = getAvailableTransitionsVoc(self.context, self.brains)
        self.fields += Fields(schema.Choice(
            __name__='transition',
            title=_(u'Transition'),
            vocabulary=self.voc,
            description=(len(self.voc) == 0 and
                         _(u'No common or available transition. Modify your selection.') or u''),
            required=len(self.voc) > 0))
        self.fields += Fields(schema.Text(
            __name__='comment',
            title=_(u'Comment'),
            description=_(u'Optional comment to display in history'),
            required=False))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: len(fi.voc))
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif data['transition']:
            for brain in self.brains:
                obj = brain.getObject()
                api.content.transition(obj=obj, transition=data['transition'],
                                       comment=self.request.form.get('form.widgets.comment', ''))
            self.request.response.redirect(self.request.form['form.widgets.referer'])


class OldTreatingGroupBatchActionForm(DashboardBatchActionForm):

    def update(self):  # pragma: no cover
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


class TreatingGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch treating group change")

    def update(self):
        super(TreatingGroupBatchActionForm, self).update()
        self.pb = canNotModify(self.brains, perm='imio.dms.mail: Write treating group field')
        self.fields += Fields(schema.Choice(
            __name__='treating_group',
            title=_(u"Treating groups"),
            description=(self.pb and cannot_modify_msg or u''),
            required=(self.pb and False or True),
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif data['treating_group']:
            for brain in self.brains:
                # check if treating_groups is changed and assigned_user is no more in
                if (brain.treating_groups is not None and brain.assigned_user != EMPTY_STRING and
                    data['treating_group'] != brain.treating_groups and
                    brain.assigned_user not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                        data['treating_group'], DOC_ASSIGNED_USER_FUNCTIONS)]):
                        # self.status not good here because it needs to stay on the same form
                        api.portal.show_message(_(u'An assigned user is not in this new treating group. '
                                                  u'Mail "${mail}" !', mapping={'mail': brain.Title.decode('utf8')}),
                                                self.request, 'error')
                        self.request.response.redirect(self.request.form['form.widgets.referer'])
                        break
            else:  # here if no break !
                for brain in self.brains:
                    obj = brain.getObject()
                    obj.treating_groups = data['treating_group']
                    modified(obj, Attributes(IDmsDocument, 'treating_groups'))
                self.request.response.redirect(self.request.form['form.widgets.referer'])


class RecipientGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch recipient groups change")
    id = 'recipientgroup-batchaction-form'

    def update(self):
        super(RecipientGroupBatchActionForm, self).update()
        self.pb = canNotModify(self.brains)
        self.fields += Fields(MasterSelectField(
            __name__='action_choice',
            title=_(u'Batch action choice'),
            description=(self.pb and cannot_modify_msg or u''),
            vocabulary=SimpleVocabulary([SimpleTerm(value=u'add', title=_(u'Add items')),
                                         SimpleTerm(value=u'remove', title=_(u'Remove items')),
                                         SimpleTerm(value=u'replace', title=_(u'Replace some items by others')),
                                         SimpleTerm(value=u'overwrite', title=_(u'Overwrite'))]),
            slave_fields=(
                {'name': 'removed_values',
                 'slaveID': '#form-widgets-removed_values',
                 'action': 'hide',
                 'hide_values': (u'add', u'overwrite'),
                 'siblings': True,
                 },
                {'name': 'added_values',
                 'slaveID': '#form-widgets-added_values',
                 'action': 'hide',
                 'hide_values': (u'remove'),
                 'siblings': True,
                 },
            ),
            required=(self.pb and False or True),
            default=u'add'
        ))
        if not self.pb:
            self.fields += Fields(schema.List(
                __name__='removed_values',
                title=_(u"Removed values"),
                description=_(u"Select the values to remove (CTRL+click)"),
                required=False,
                value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups'),
            ))
            self.fields += Fields(schema.List(
                __name__='added_values',
                title=_(u"Added values"),
                description=_(u"Select the values to add (CTRL+click)"),
                required=False,
                value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups'),
            ))
            self.fields["removed_values"].widgetFactory = SelectFieldWidget
            self.fields["added_values"].widgetFactory = SelectFieldWidget

        super(DashboardBatchActionForm, self).update()

        if not self.pb:
            #        self.widgets['action_choice'].size = 4
            self.widgets['removed_values'].multiple = 'multiple'
            self.widgets['removed_values'].size = 5
            self.widgets['added_values'].multiple = 'multiple'
            self.widgets['added_values'].size = 5

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif ((data.get('removed_values', None) and data['action_choice'] in ('remove', 'replace')) or
                (data.get('added_values', None)) and data['action_choice'] in ('add', 'replace', 'overwrite')):
            for brain in self.brains:
                obj = brain.getObject()
                if data['action_choice'] in ('overwrite'):
                    items = set(data['added_values'])
                else:
                    items = set(obj.recipient_groups or [])
                    if data['action_choice'] in ('remove', 'replace'):
                        items = items.difference(data['removed_values'])
                    if data['action_choice'] in ('add', 'replace'):
                        items = items.union(data['added_values'])
                obj.recipient_groups = list(items)
                modified(obj)
            self.request.response.redirect(self.request.form['form.widgets.referer'])


def getAvailableAssignedUserVoc(brains, attribute):
    """ Returns available assigned users common for all brains. """
    terms = [SimpleTerm(value='__none__', token='no_value', title=_('Set to no value'))]
    users = None
    for brain in brains:
        #obj = brain.getObject()
        if not getattr(brain, attribute):
            return SimpleVocabulary([])
        if users is None:
            users = set(get_selected_org_suffix_users(getattr(brain, attribute), DOC_ASSIGNED_USER_FUNCTIONS))
        else:
            users &= set(get_selected_org_suffix_users(getattr(brain, attribute), DOC_ASSIGNED_USER_FUNCTIONS))
    if users:
        for member in sorted(users, key=methodcaller('getUserName')):
            terms.append(SimpleTerm(
                value=member.getUserName(),  # login
                token=member.getId(),  # id
                title=member.getUser().getProperty('fullname') or member.getUserName()))  # title
    return SimpleVocabulary(terms)


class AssignedUserBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch assigned user change")
    master = 'treating_groups'
    err_msg = _(u'No common or available treating group, or no available assigned user. '
                'Modify your selection.')

    def update(self):
        super(AssignedUserBatchActionForm, self).update()
        self.voc = getAvailableAssignedUserVoc(self.brains, self.master)
        self.pb = canNotModify(self.brains)
        self.fields += Fields(schema.Choice(
            __name__='assigned_user',
            title=TMF(u'Assigned user'),
            vocabulary=self.voc,
            description=((len(self.voc) == 0 and self.err_msg) or (self.pb and cannot_modify_msg) or u''),
            required=(len(self.voc) and not self.pb and True or False)))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: len(fi.voc) and not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif data['assigned_user']:
            if data['assigned_user'] == '__none__':
                data['assigned_user'] = None
            for brain in self.brains:
                obj = brain.getObject()
                obj.assigned_user = data['assigned_user']
                modified(obj)
            self.request.response.redirect(self.request.form['form.widgets.referer'])


class ReplyBatchActionForm(DashboardBatchActionForm):

    def __call__(self):
        self.request['URL'] = self.request['URL'].replace('/reply-batch-action', '/multiple-reply')
        view = getMultiAdapter((self.context, self.request), name='multiple-reply')
        return view()


class OutgoingDateBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch outgoing date change")

    def update(self):
        super(OutgoingDateBatchActionForm, self).update()
        self.pb = canNotModify(self.brains)
        self.fields += Fields(schema.Datetime(
            __name__='outgoing_date',
            title=_(u"Outgoing Date"),
            description=(self.pb and cannot_modify_msg or u''),
            required=(self.pb and False or True),
            default=datetime.datetime.now(),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif data['outgoing_date']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.outgoing_date = data['outgoing_date']
                modified(obj)
            self.request.response.redirect(self.request.form['form.widgets.referer'])

# Task batch actions


class AssignedGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch assigned group change")

    def update(self):
        super(AssignedGroupBatchActionForm, self).update()
        #self.pb = checkSelectionAboutTreatingGroup(brains_from_uids(self.request.form['form.widgets.uids']))
        self.pb = canNotModify(self.brains)
        self.fields += Fields(schema.Choice(
            __name__='assigned_group',
            title=TMF(u"Assigned group"),
            description=(self.pb and cannot_modify_msg or u''),
            required=(self.pb and False or True),
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        elif data['assigned_group']:
            for brain in self.brains:
                # check if assigned_group is changed and assigned_user is no more in
                if (brain.assigned_group is not None and brain.assigned_user != EMPTY_STRING and
                    data['assigned_group'] != brain.assigned_group and
                    brain.assigned_user not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                        data['assigned_group'], DOC_ASSIGNED_USER_FUNCTIONS)]):
                        api.portal.show_message(_(u'An assigned user is not in this new assigned group. '
                                                  u'Task "${task}" !', mapping={'task': brain.getURL().decode('utf8')}),
                                                self.request, 'error')
                        self.request.response.redirect(self.request.form['form.widgets.referer'])
                        break
            else:  # here if no break !
                for brain in self.brains:
                    obj = brain.getObject()
                    obj.assigned_group = data['assigned_group']
                    modified(obj, Attributes(ITaskContent, 'ITask.assigned_group'))
                self.request.response.redirect(self.request.form['form.widgets.referer'])


class TaskAssignedUserBatchActionForm(AssignedUserBatchActionForm):

    master = 'assigned_group'
    err_msg = _(u'No common or available assigned group, or no available assigned user. '
                'Modify your selection.')

# OM Templates Folder batch actions


class CopyToBatchActionForm(BaseBatchActionForm):
    """ Button to move selection to a folder """

    label = _(u"Batch copy to")

    def getAvailableFoldersVoc(self):
        """ Returns available transitions common for all brains """
        terms = []
        brains = api.content.find(context=self.context, depth=1, portal_type='Folder')
        objs = filter_on_permission(brains, 'Add portal content')
        for obj in objs:
            terms.append(SimpleTerm(obj.UID(), title=obj.title))
        return SimpleVocabulary(terms)

    def _update(self):
        self.voc = self.getAvailableFoldersVoc()
        self.do_apply = len(self.voc) > 0
        self.fields += Fields(schema.List(
            __name__='folders',
            title=_(u'Folders'),
            value_type=schema.Choice(vocabulary=self.voc),
            description=(self.do_apply and
                         _(u'Select multiple values (CTRL+click)') or
                         _(u'No folder available where you can add templates.')),
            required=self.do_apply))
        self.fields["folders"].widgetFactory = SelectFieldWidget

    def _update_widgets(self):
        if self.do_apply:
            self.widgets['folders'].multiple = 'multiple'
            self.widgets['folders'].size = 5

    def _apply(self, **data):
        """ """
        if data['folders']:
            targets = [b.getObject() for b in api.content.find(UID=data['folders'])]
            for brain in self.brains:
                obj = brain.getObject()
                for target in targets:
                    api.content.copy(source=obj, target=target, safe_id=True)


class DuplicatedBatchActionForm(BaseBatchActionForm):
    """ Button to manage duplicated contacts """

    overlay = False

    def __call__(self):
        self.request['uids'] = self.request['uids'].split(',')
        self.request['no_redirect'] = 1
        view = getMultiAdapter((self.context.getParentNode(), self.request), name='merge-contacts')
        with api.env.adopt_roles(['Manager']):  # not sure it's working
            return view()
