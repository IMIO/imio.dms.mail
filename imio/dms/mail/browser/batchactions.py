# -*- coding: utf-8 -*-
"""Batch actions views."""
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.widget.schema import ContactChoice
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.eeafaceted.batchactions.browser.views import BaseARUOBatchActionForm
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.browser.views import ContactBaseBatchActionForm
from collective.eeafaceted.batchactions.utils import filter_on_permission, cannot_modify_field_msg
from collective.eeafaceted.batchactions.utils import is_permitted
from collective.task.browser.batchactions import AssignedGroupBatchActionForm as agbaf
from collective.task.browser.batchactions import AssignedUserBatchActionForm as aubaf
from imio.dms.mail import _
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import EMPTY_STRING
from imio.dms.mail.dmsmail import DmsContactSourceBinder
from imio.dms.mail.utils import is_in_user_groups
from imio.helpers.cache import get_current_user_id
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidsToObjects
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

# IM and OM batch actions


class TreatingGroupBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch treating group change")
    weight = 20

    def _update(self):
        self.do_apply = is_permitted(self.brains, perm='imio.dms.mail: Write treating group field')
        self.fields += Fields(schema.Choice(
            __name__='treating_group',
            title=_(u"Treating groups"),
            description=(not self.do_apply and cannot_modify_field_msg or u''),
            required=self.do_apply,
            vocabulary=(self.do_apply and u'collective.dms.basecontent.treating_groups' or SimpleVocabulary([])),
        ))

    def _apply(self, **data):
        if data['treating_group']:
            for brain in self.brains:
                # check if treating_groups is changed and assigned_user is no more in
                if (brain.treating_groups is not None and brain.assigned_user != EMPTY_STRING and
                    data['treating_group'] != brain.treating_groups and
                    brain.assigned_user not in get_selected_org_suffix_principal_ids(
                        data['treating_group'], IM_EDITOR_SERVICE_FUNCTIONS)):
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


class RecipientGroupBatchActionForm(BaseARUOBatchActionForm):

    label = _(u"Batch recipient groups change")
    modified_attr_name = 'recipient_groups'
    call_modified_event = True
    # id = 'recipientgroup-batchaction-form'
    weight = 40

    def _vocabulary(self):
        return u'collective.dms.basecontent.recipient_groups'

    def _remove_vocabulary(self):
        return u'collective.contact.plonegroup.organization_services'


class AssignedUserBatchActionForm(aubaf):

    master = 'treating_groups'
    weight = 30

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)


class ReplyBatchActionForm(BaseBatchActionForm):

    overlay = False
    weight = 50

    def __call__(self):
        self.request['URL'] = self.request['URL'].replace('/reply-batch-action', '/multiple-reply')
        view = getMultiAdapter((self.context, self.request), name='multiple-reply')
        return view()


class IMSenderBatchActionForm(ContactBaseBatchActionForm):

    label = _(u"Batch sender contact field change")
    weight = 60
    available_permission = 'Modify portal content'
    attribute = 'sender'
    field_value_type = ContactChoice(
        source=DmsContactSourceBinder(portal_type=("organization", 'held_position', 'person', 'contact_list'),
                                      review_state=['active'],
                                      sort_on='sortable_title'))


class OutgoingDateBatchActionForm(BaseBatchActionForm):

    label = _(u"Batch outgoing date change")
    weight = 50

    def _update(self):
        self.do_apply = is_permitted(self.brains)
        self.fields += Fields(schema.Datetime(
            __name__='outgoing_date',
            title=_(u"Outgoing Date"),
            description=(not self.do_apply and cannot_modify_field_msg or u''),
            required=(self.do_apply),
            default=datetime.datetime.now(),
        ))

    def _apply(self, **data):
        if data['outgoing_date']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.outgoing_date = data['outgoing_date']
                modified(obj)


class SendModesBatchActionForm(BaseARUOBatchActionForm):

    label = _(u"Batch send modes change")
    modified_attr_name = 'send_modes'
    call_modified_event = False
    indexes = ['Subject']
    required = True
    weight = 60

    def _vocabulary(self):
        return u'imio.dms.mail.OMActiveSendModesVocabulary'

    def _remove_vocabulary(self):
        return u'imio.dms.mail.OMSendModesVocabulary'

    def _may_apply(self):
        return api.user.has_permission('Manage portal', obj=self.context)


class RecipientsBatchActionForm(ContactBaseBatchActionForm):

    label = _(u"Batch recipients contact field change")
    weight = 60
    available_permission = 'Modify portal content'
    attribute = 'recipients'
    field_value_type = ContactChoice(
        source=DmsContactSourceBinder(portal_type=("organization", 'held_position', 'person', 'contact_list'),
                                      review_state=['active'],
                                      sort_on='sortable_title'))

# Task batch actions


class AssignedGroupBatchActionForm(agbaf):

    weight = 20

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)


class TaskAssignedUserBatchActionForm(aubaf):

    master = 'assigned_group'

    def get_group_users(self, assigned_group):
        return get_selected_org_suffix_users(assigned_group, IM_EDITOR_SERVICE_FUNCTIONS)

# OM Templates Folder batch actions


class CopyToBatchActionForm(BaseBatchActionForm):
    """ Button to copy selection to sub folders."""

    label = _(u"Batch copy to")
    weight = 20

    def available_folders_voc(self):
        """ Returns available folders where the current user can paste """
        terms = []
        brains = api.content.find(context=self.context, depth=1, portal_type='Folder')
        objs = filter_on_permission(brains, 'Add portal content')
        for obj in objs:
            terms.append(SimpleTerm(obj.UID(), title=obj.title))
        return SimpleVocabulary(terms)

    def _update(self):
        self.voc = self.available_folders_voc()
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
            self.widgets['folders'].size = 15

    def _apply(self, **data):
        """ """
        if data['folders']:
            targets = uuidsToObjects(data['folders'], unrestricted=True)
            for brain in self.brains:
                obj = brain.getObject()
                for target in targets:
                    api.content.copy(source=obj, target=target, safe_id=True)


class DuplicatedBatchActionForm(BaseBatchActionForm):
    """ Button to manage duplicated contacts """

    overlay = False
    weight = 20

    def available(self):
        return is_in_user_groups(groups=('gestion_contacts', ))

    def __call__(self):
        if not self.available():  # double check
            return ''
        self.request['uids'] = self.request['uids'].split(',')
        self.request['no_redirect'] = 1
        view = getMultiAdapter((self.context.getParentNode(), self.request), name='merge-contacts')
        with api.env.adopt_roles(['Manager']):
            return view()
