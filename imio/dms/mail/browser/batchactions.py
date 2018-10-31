# -*- coding: utf-8 -*-
"""Batch actions views."""

from AccessControl import getSecurityManager
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.task import _ as TMF
from collective.task.interfaces import ITaskContent
from imio.dms.mail import _
from imio.dms.mail import DOC_ASSIGNED_USER_FUNCTIONS
from imio.dms.mail import EMPTY_STRING
from operator import methodcaller
from plone import api
from plone.formwidget.masterselect import MasterSelectField
from z3c.form.browser.select import SelectFieldWidget
from z3c.form.field import Fields
from zope import schema
from zope.component import getMultiAdapter
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import datetime


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


class TreatingGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch treating group change")
    weight = 20

    def _update(self):
        self.pb = canNotModify(self.brains, perm='imio.dms.mail: Write treating group field')
        self.do_apply = not self.pb
        self.fields += Fields(schema.Choice(
            __name__='treating_group',
            title=_(u"Treating groups"),
            description=(self.pb and cannot_modify_msg or u''),
            required=self.do_apply,
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

    def _apply(self, **data):
        if data['treating_group']:
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
                        break
            else:  # here if no break !
                for brain in self.brains:
                    obj = brain.getObject()
                    obj.treating_groups = data['treating_group']
                    modified(obj, Attributes(IDmsDocument, 'treating_groups'))


class RecipientGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch recipient groups change")
    # id = 'recipientgroup-batchaction-form'
    weight = 40

    def _update(self):
        self.pb = canNotModify(self.brains)
        self.do_apply = not self.pb
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
            required=self.do_apply,
            default=u'add'
        ))
        if self.do_apply:
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

    def _update_widgets(self):
        if self.do_apply:
            #        self.widgets['action_choice'].size = 4
            self.widgets['removed_values'].multiple = 'multiple'
            self.widgets['removed_values'].size = 5
            self.widgets['added_values'].multiple = 'multiple'
            self.widgets['added_values'].size = 5

    def _apply(self, **data):
        if ((data.get('removed_values', None) and data['action_choice'] in ('remove', 'replace')) or
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


class AssignedUserBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch assigned user change")
    master = 'treating_groups'
    err_msg = _(u'No common or available treating group, or no available assigned user. '
                'Modify your selection.')
    weight = 30

    def _update(self):
        self.voc = getAvailableAssignedUserVoc(self.brains, self.master)
        self.pb = canNotModify(self.brains)
        self.do_apply = not self.pb
        self.fields += Fields(schema.Choice(
            __name__='assigned_user',
            title=TMF(u'Assigned user'),
            vocabulary=self.voc,
            description=((len(self.voc) == 0 and self.err_msg) or (self.pb and cannot_modify_msg) or u''),
            required=(len(self.voc) and self.do_apply)))

    def _apply(self, **data):
        if data['assigned_user']:
            if data['assigned_user'] == '__none__':
                data['assigned_user'] = None
            for brain in self.brains:
                obj = brain.getObject()
                obj.assigned_user = data['assigned_user']
                modified(obj)


class ReplyBatchActionForm(BaseBatchActionForm):

    overlay = False
    weight = 50

    def __call__(self):
        self.request['URL'] = self.request['URL'].replace('/reply-batch-action', '/multiple-reply')
        view = getMultiAdapter((self.context, self.request), name='multiple-reply')
        return view()


class OutgoingDateBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch outgoing date change")
    weight = 50

    def _update(self):
        self.pb = canNotModify(self.brains)
        self.do_apply = not self.pb
        self.fields += Fields(schema.Datetime(
            __name__='outgoing_date',
            title=_(u"Outgoing Date"),
            description=(self.pb and cannot_modify_msg or u''),
            required=(self.do_apply),
            default=datetime.datetime.now(),
        ))

    def _apply(self, **data):
        if data['outgoing_date']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.outgoing_date = data['outgoing_date']
                modified(obj)

# Task batch actions


class AssignedGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch assigned group change")
    weight = 20

    def _update(self):
        self.pb = canNotModify(self.brains)
        self.do_apply = not self.pb
        self.fields += Fields(schema.Choice(
            __name__='assigned_group',
            title=TMF(u"Assigned group"),
            description=(self.pb and cannot_modify_msg or u''),
            required=(self.do_apply),
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

    def _apply(self, **data):
        if data['assigned_group']:
            for brain in self.brains:
                # check if assigned_group is changed and assigned_user is no more in
                if (brain.assigned_group is not None and brain.assigned_user != EMPTY_STRING and
                    data['assigned_group'] != brain.assigned_group and
                    brain.assigned_user not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                        data['assigned_group'], DOC_ASSIGNED_USER_FUNCTIONS)]):
                        api.portal.show_message(_(u'An assigned user is not in this new assigned group. '
                                                  u'Task "${task}" !', mapping={'task': brain.getURL().decode('utf8')}),
                                                self.request, 'error')
                        break
            else:  # here if no break !
                for brain in self.brains:
                    obj = brain.getObject()
                    obj.assigned_group = data['assigned_group']
                    modified(obj, Attributes(ITaskContent, 'ITask.assigned_group'))


class TaskAssignedUserBatchActionForm(AssignedUserBatchActionForm):

    master = 'assigned_group'
    err_msg = _(u'No common or available assigned group, or no available assigned user. '
                'Modify your selection.')

# OM Templates Folder batch actions


class CopyToBatchActionForm(BaseBatchActionForm):
    """ Button to copy selection to a folder """

    label = _(u"Batch copy to")
    weight = 20

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
    weight = 20

    def __call__(self):
        self.request['uids'] = self.request['uids'].split(',')
        self.request['no_redirect'] = 1
        view = getMultiAdapter((self.context.getParentNode(), self.request), name='merge-contacts')
        with api.env.adopt_roles(['Manager']):  # not sure it's working
            return view()
