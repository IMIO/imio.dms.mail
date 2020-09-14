# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail import AUC_RECORD
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.browser.reply_form import ReplyForm
from imio.dms.mail.browser.task import TaskEdit
from imio.dms.mail.dmsmail import AssignedUserValidator
from imio.dms.mail.dmsmail import creating_group_filter
from imio.dms.mail.dmsmail import creating_group_filter_default
from imio.dms.mail.dmsmail import CustomAddForm
from imio.dms.mail.dmsmail import IMEdit
from imio.dms.mail.dmsmail import IMView
from imio.dms.mail.dmsmail import OMCustomAddForm
from imio.dms.mail.dmsmail import OMEdit
from imio.dms.mail.dmsmail import recipients_filter_default
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from z3c.relationfield.relation import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.interface import Invalid
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import unittest


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pgof = self.portal['contacts']['plonegroup-organization']

    def test_creating_group_filter(self):
        login(self.portal, 'encodeur')
        self.assertIsNone(creating_group_filter(self.portal))
        self.assertIsNone(creating_group_filter_default(self.portal))
        # we activate contact group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder', True)
        self.assertEqual(len(creating_group_filter(self.portal)), 0)
        self.assertIsNone(creating_group_filter_default(self.portal))
        # we add a user in groups
        selected_orgs = get_registry_organizations()[0:2]
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[0], CREATING_GROUP_SUFFIX), username='chef')
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CREATING_GROUP_SUFFIX), username='chef')
        self.assertEqual(creating_group_filter(self.portal)._terms[0].value,
                         u'{{"assigned_group": "{}"}}'.format(selected_orgs[0]))
        self.assertIsNone(creating_group_filter_default(self.portal))
        # we add the connected user in group
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CREATING_GROUP_SUFFIX), username='encodeur')
        self.assertEqual(creating_group_filter_default(self.portal),
                         u'{{"assigned_group": "{}"}}'.format(selected_orgs[1]))
        # user logout
        logout()
        self.assertIsNone(creating_group_filter_default(self.portal))

    def test_TreatingGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import TreatingGroupsVocabulary
        voc_inst = TreatingGroupsVocabulary()
        voc = voc_inst(self.portal)
        self.assertEquals(len([t for t in voc]), 11)
        self.assertNotEqual(len(voc), 11)  # len = full vocabulary with hidden terms

    def test_RecipientGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import RecipientGroupsVocabulary
        voc_inst = RecipientGroupsVocabulary()
        voc = voc_inst(self.portal)
        self.assertEquals(len([t for t in voc]), 11)
        self.assertNotEqual(len(voc), 11)  # len = full vocabulary with hidden terms

    def test_Title(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        self.assertEquals(imail1.Title(), 'E0001 - Courrier 1')
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         **{'title': 'Test with auto ref'})
        self.assertEquals(imail.Title(), 'E0010 - Test with auto ref')

    def test_reply_to(self):
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        imail1 = self.portal['incoming-mail']['courrier1']
        imail2 = self.portal['incoming-mail']['courrier2']
        omail1 = self.portal['outgoing-mail']['reponse1']
        omail2 = self.portal['outgoing-mail']['reponse2']
        omail1.reply_to = [
            RelationValue(intids.getId(imail1)),
            RelationValue(intids.getId(imail2)),
            RelationValue(intids.getId(omail2)),
        ]
        modified(omail1)
        self.assertEqual(len(omail1.reply_to), 3)
        omail_intid = intids.queryId(omail1)
        query = {
            'from_id': omail_intid,
            'from_attribute': 'reply_to'
        }

        linked = set([rel.to_object for rel in catalog.findRelations(query)])
        self.assertSetEqual(set([imail1, imail2, omail2]), linked)

    def clean_request(self):
        for key in ('_hide_irn', '_auto_ref'):
            if key in self.request:
                self.request.other.pop(key)

    def om_params(self, view):
        return {
            'IDublinCore.title': u'test', 'internal_reference_no': view.widgets['internal_reference_no'].value,
            # 'sender': self.c1, 'recipients': [self.c1]
        }

    def test_add_edit(self):
        # Based on test_settings from collective.dms.mailcontent
        setRoles(self.portal, TEST_USER_ID, ['Contributor'])
        # check default config
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 10)
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_talexpression'), u"python:'S%04d'%int(number)")
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_edit_irn'), u'hide')
        self.assertTrue(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                       'outgoingmail_increment_number'))
        self.assertTrue(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                       'outgoingmail_today_mail_date'))
        self.assertEquals(api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                         'due_date_extension'), 0)

        # testing IM views: default parameters
        self.request = self.portal['incoming-mail'].REQUEST
        add = CustomAddForm(self.portal['incoming-mail'], self.request)
        add.portal_type = 'dmsincomingmail'
        add.update()
        self.assertEquals(add.widgets['ITask.due_date'].value, ('', '', ''))
        # set due_date_extension to 15
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                       'due_date_extension', 15)
        self.request = self.portal['incoming-mail'].REQUEST
        add = CustomAddForm(self.portal['incoming-mail'], self.request)
        add.portal_type = 'dmsincomingmail'
        add.update()
        self.assertNotEquals(add.widgets['ITask.due_date'].value, ('', '', ''))

        # testing OM views: default parameters
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'show')
        self.request = self.portal['outgoing-mail'].REQUEST
        add = OMCustomAddForm(self.portal['outgoing-mail'], self.request)
        add.portal_type = 'dmsoutgoingmail'
        add.update()
        self.assertNotIn('_hide_irn', self.request.keys())
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(add.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.assertEquals(add.widgets['internal_reference_no'].value, u'S0010')
        obj = add.createAndAdd(self.om_params(add))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertFalse(hasattr(om, '_auto_ref'))
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 11)
        self.clean_request()
        edit = OMEdit(om, self.request)
        edit.update()
        self.assertNotIn('_hide_irn', self.request.keys())
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.clean_request()

        # set outgoingmail_increment_number to False
        # => no number incrementation because irn field is editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_increment_number', False)
        add.update()
        self.assertNotIn('_hide_irn', self.request.keys())
        self.assertEquals(self.request['_auto_ref'], False)
        self.assertEquals(add.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.assertEquals(add.widgets['internal_reference_no'].value, u'S0011')
        obj = add.createAndAdd(self.om_params(add))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om._auto_ref, False)
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 11)  # No increment
        self.clean_request()
        edit = OMEdit(om, self.request)
        edit.update()
        self.assertNotIn('_hide_irn', self.request.keys())
        self.assertEquals(self.request['_auto_ref'], False)
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.clean_request()

        # set outgoingmail_increment_number to False and outgoingmail_edit_irn to hide
        # => number incrementation because irn field is not editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'hide')
        add.update()
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(add.widgets['internal_reference_no'].mode, 'hidden')
        self.assertEquals(add.widgets['internal_reference_no'].value, u'')
        obj = add.createAndAdd(self.om_params(add))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om.internal_reference_no, u'S0011')
        self.assertFalse(hasattr(om, '_auto_ref'))
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 12)
        self.clean_request()
        edit = OMEdit(om, self.request)
        edit.update()
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'hidden')
        self.clean_request()

        # set outgoingmail_increment_number to False and outgoingmail_edit_irn to reply
        # => number incrementation because irn field is not editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'reply')
        add.update()
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(add.widgets['internal_reference_no'].mode, 'hidden')
        self.assertEquals(add.widgets['internal_reference_no'].value, u'')
        obj = add.createAndAdd(self.om_params(add))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om.internal_reference_no, u'S0012')
        self.assertFalse(hasattr(om, '_auto_ref'))
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 13)
        self.clean_request()
        edit = OMEdit(om, self.request)
        edit.update()
        # is not a response
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'hidden')
        self.clean_request()
        # is a response, workflow and initial state
        setattr(om, '_is_response', True)
        edit.update()
        self.assertEquals(api.content.get_state(om), 'created')
        self.assertEquals(edit.is_initial_state(), True)
        self.assertNotIn('_hide_irn', self.request.keys())
        self.assertEquals(self.request['_auto_ref'], False)
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.clean_request()
        # is a response, workflow and not initial state
        api.content.transition(om, 'propose_to_be_signed')
        edit.update()
        self.assertEquals(api.content.get_state(om), 'to_be_signed')
        self.assertEquals(edit.is_initial_state(), False)
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'hidden')
        self.clean_request()

        # Testing reply view
        intids = getUtility(IIntIds)
        swde = self.portal.contacts['swde']
        tg = get_registry_organizations()[0]
        im = api.content.create(container=self.portal['incoming-mail'], type='dmsincomingmail', id='im',
                                title=u'I mail', sender=[RelationValue(intids.getId(swde))],
                                external_reference_no=u'xx/1', treating_groups=tg)
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'show')
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_increment_number', True)
        reply = ReplyForm(im, self.request)
        reply.update()
        self.assertEquals(self.request['_irn'], 'E0010')
        self.assertEquals(self.request['_hide_irn'], False)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(reply.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.assertEquals(reply.widgets['internal_reference_no'].value, u'S0013')
        obj = reply.createAndAdd(self.om_params(reply))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertFalse(hasattr(om, '_auto_ref'))
        self.assertEquals(om._is_response, True)
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 14)
        self.clean_request()

        # set outgoingmail_increment_number to False
        # => no number incrementation because irn field is editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_increment_number', False)
        reply.update()
        self.assertEquals(self.request['_hide_irn'], False)
        self.assertEquals(self.request['_auto_ref'], False)
        self.assertEquals(reply.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.assertEquals(reply.widgets['internal_reference_no'].value, u'S0014')
        obj = reply.createAndAdd(self.om_params(reply))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om._auto_ref, False)
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 14)  # No increment
        self.clean_request()

        # set outgoingmail_increment_number to False and outgoingmail_edit_irn to hide
        # => number incrementation because irn field is not editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'hide')
        reply.update()
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(reply.widgets['internal_reference_no'].mode, 'hidden')
        self.assertEquals(reply.widgets['internal_reference_no'].value, u'')
        obj = reply.createAndAdd(self.om_params(reply))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om.internal_reference_no, u'S0014')
        self.assertFalse(hasattr(om, '_auto_ref'))
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 15)
        self.clean_request()

        # set outgoingmail_increment_number to False and outgoingmail_edit_irn to reply
        # => number incrementation because irn field is not editable
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_edit_irn', u'reply')
        reply.update()
        self.assertEquals(self.request['_hide_irn'], False)
        self.assertEquals(self.request['_auto_ref'], False)
        self.assertEquals(reply.widgets['internal_reference_no'].mode, 'input')  # not hidden
        self.assertEquals(reply.widgets['internal_reference_no'].value, u'S0015')
        obj = reply.createAndAdd(self.om_params(reply))
        om = api.content.find(self.portal['outgoing-mail'], id=obj.id)[0].getObject()
        self.assertEquals(om._auto_ref, False)
        self.assertEquals(api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                                         'outgoingmail_number'), 15)  # No increment
        self.clean_request()

    def test_view(self):
        setRoles(self.portal, TEST_USER_ID, ['Contributor', 'Reviewer'])
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(api.content.get_state(imail), 'created')
        view = IMView(imail, imail.REQUEST)
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        view.update()  # BEWARE can be called only once (plone.autoform.view.py) !
        # no treating_groups: cannot do anything
        self.assertEquals(view.widgets['ITask.assigned_user'].field.description, u'')
        # no assigned_user but mandatory
        imail.treating_groups = get_registry_organizations()[0]
        view.updateWidgets()  # because update() can be called only once
        self.assertEquals(view.widgets['ITask.assigned_user'].field.description,
                          u'You must select an assigned user before you can propose to an agent !')
        # no assigned user but mandatory only for n_plus_1 level
        api.portal.set_registry_record(AUC_RECORD, 'n_plus_1')
        view.updateWidgets()
        self.assertEquals(view.widgets['ITask.assigned_user'].field.description, u'')

    def test_recipients_filter_default(self):
        self.assertIsNone(recipients_filter_default(self.portal))
        # we activate contact group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder', True)
        self.assertIsNone(recipients_filter_default(self.portal))
        login(self.portal, 'encodeur')
        self.assertIsNone(recipients_filter_default(self.portal))
        # we add a user in groups
        selected_orgs = get_registry_organizations()[0:2]
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[0], CREATING_GROUP_SUFFIX), username='chef')
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CREATING_GROUP_SUFFIX), username='chef')
        self.assertIsNone(recipients_filter_default(self.portal))
        # we add the connected user in group
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CREATING_GROUP_SUFFIX), username='encodeur')
        self.assertEqual(recipients_filter_default(self.portal),
                         u'{{"assigned_group": "{}"}}'.format(selected_orgs[1]))
        login(self.portal, 'agent')
        self.assertIsNone(recipients_filter_default(self.portal))
        # we add the connected user in group
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CONTACTS_PART_SUFFIX), username='agent')
        self.assertEqual(recipients_filter_default(self.portal),
                         u'{{"assigned_group": "{}"}}'.format(selected_orgs[1]))

    def test_AssignedUserValidator(self):
        # im
        obj = self.portal['incoming-mail']['courrier1']
        view = IMEdit(obj, obj.REQUEST)
        auv = AssignedUserValidator(obj, view.request, view, 'fld', 'widget')
        self.assertEqual(obj.treating_groups, self.pgof['direction-generale'].UID())
        obj.assigned_user = 'agent1'
        # we change group: user is in
        view.request.form['form.widgets.treating_groups'] = [self.pgof['evenements'].UID()]
        self.assertIsNone(auv.validate('agent1'))
        # we change group but user is not in
        view.request.form['form.widgets.treating_groups'] = [self.pgof['direction-financiere'].UID()]
        self.assertRaises(Invalid, auv.validate, 'agent1')
        # om
        obj = self.portal['outgoing-mail']['reponse1']
        view = OMEdit(obj, obj.REQUEST)
        auv = AssignedUserValidator(obj, view.request, view, 'fld', 'widget')
        self.assertEqual(obj.treating_groups, self.pgof['direction-generale'].UID())
        obj.assigned_user = 'agent1'
        # we change group: user is in
        view.request.form['form.widgets.treating_groups'] = [self.pgof['evenements'].UID()]
        self.assertIsNone(auv.validate('agent1'))
        # we change group but user is not in
        view.request.form['form.widgets.treating_groups'] = [self.pgof['direction-financiere'].UID()]
        self.assertRaises(Invalid, auv.validate, 'agent1')
        # task
        obj = self.portal['incoming-mail']['courrier1']['tache1']
        view = TaskEdit(obj, obj.REQUEST)
        auv = AssignedUserValidator(obj, view.request, view, 'fld', 'widget')
        self.assertEqual(obj.assigned_group, self.pgof['direction-generale'].UID())
        obj.assigned_user = 'agent1'
        # we change group: user is in
        view.request.form['form.widgets.ITask.assigned_group'] = [self.pgof['evenements'].UID()]
        self.assertIsNone(auv.validate('agent1'))
        # we change group but user is not in
        view.request.form['form.widgets.ITask.assigned_group'] = [self.pgof['direction-financiere'].UID()]
        self.assertRaises(Invalid, auv.validate, 'agent1')
