# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from datetime import datetime
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
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
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
        change_user(self.portal)
        self.pgof = self.portal['contacts']['plonegroup-organization']
        self.intids = getUtility(IIntIds)

    def test_creating_group_filter(self):
        login(self.portal, 'encodeur')
        self.assertIsNone(creating_group_filter(self.portal))
        self.assertIsNone(creating_group_filter_default(self.portal))
        # we activate contact group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder', True)
        self.assertEqual(len(creating_group_filter(self.portal)), 1)
        self.assertEqual(creating_group_filter(self.portal)._terms[0].value, None)
        self.assertIsNone(creating_group_filter_default(self.portal))
        # we add a user in groups
        selected_orgs = get_registry_organizations()[0:2]
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[0], CREATING_GROUP_SUFFIX), username='chef')
        api.group.add_user(groupname='{}_{}'.format(selected_orgs[1], CREATING_GROUP_SUFFIX), username='chef')
        self.assertEqual(creating_group_filter(self.portal)._terms[1].value,
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

    def test_IM_Title(self):
        imail1 = get_object(oid='courrier1', ptype='dmsincomingmail')
        self.assertEquals(imail1.Title(), 'E0001 - Courrier 1')
        imail = sub_create(self.portal['incoming-mail'], 'dmsincomingmail', datetime.now(), 'my-id',
                           **{'title': u'Test with auto ref'})
        self.assertEquals(imail.Title(), 'E0010 - Test with auto ref')

    def test_ImioDmsIncomingMailWfConditionsAdapter_can_do_transition0(self):
        imail = sub_create(self.portal['incoming-mail'], 'dmsincomingmail', datetime.now(), 'my-id')
        self.assertEqual(api.content.get_state(imail), 'created')
        adapted = imail.wf_conditions()
        # no treating_group nor title: NOK
        self.assertFalse(adapted.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user nok but auc ok: OK
        imail.title = u'test'
        imail.treating_groups = get_registry_organizations()[0]
        self.assertTrue(adapted.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user nok, auc nok: NOK
        change_user(self.portal, 'encodeur')
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertFalse(adapted.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user nok, auc ok: OK
        api.portal.set_registry_record(AUC_RECORD, 'no_check')
        self.assertTrue(adapted.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user ok, auc nok: OK
        imail.assigned_user = 'chef'
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertTrue(adapted.can_do_transition('propose_to_agent'))
        # WE DO TRANSITION
        api.content.transition(imail, 'propose_to_agent')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_agent')
        # tg ok, state ok, (assigner_user nok, auc nok): OK
        imail.assigned_user = None
        self.assertTrue(adapted.can_do_transition('back_to_creation'))
        self.assertTrue(adapted.can_do_transition('back_to_manager'))
        self.assertFalse(adapted.can_do_transition('unknown'))

    def test_ImioDmsIncomingMailWfConditionsAdapter_can_close(self):
        imail = sub_create(self.portal['incoming-mail'], 'dmsincomingmail', datetime.now(), 'my-id',
                           **{'title': u'test'})
        self.assertEqual(api.content.get_state(imail), 'created')
        adapted = imail.wf_conditions()
        imail.treating_groups = get_registry_organizations()[0]  # direction-generale
        self.assertTrue(adapted.can_do_transition('propose_to_agent'))
        api.content.transition(imail, 'propose_to_agent')
        login(self.portal, 'agent')
        self.assertIsNone(imail.sender)
        self.assertIsNone(imail.mail_type)
        self.assertFalse(adapted.can_close())
        intids = getUtility(IIntIds)
        imail.sender = [RelationValue(intids.getId(self.portal.contacts['electrabel']))]
        imail.mail_type = u'courrier'
        self.assertFalse(adapted.can_close())  # not part of treating group editors
        api.group.add_user(groupname='{}_editeur'.format(imail.treating_groups), username='agent')
        self.assertTrue(adapted.can_close())

    def test_reply_to(self):
        catalog = getUtility(ICatalog)
        imail1 = get_object(oid='courrier1', ptype='dmsincomingmail')
        imail2 = get_object(oid='courrier2', ptype='dmsincomingmail')
        omail1 = get_object(oid='reponse1', ptype='dmsoutgoingmail')
        omail2 = get_object(oid='reponse2', ptype='dmsoutgoingmail')
        omail1.reply_to = [
            RelationValue(self.intids.getId(imail1)),
            RelationValue(self.intids.getId(imail2)),
            RelationValue(self.intids.getId(omail2)),
        ]
        modified(omail1)
        self.assertEqual(len(omail1.reply_to), 3)
        omail_intid = self.intids.queryId(omail1)
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
        change_user(self.portal, 'encodeur')
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
        createContentInContainer(om, 'dmsommainfile')  # add a file so it's possible to do transition
        api.content.transition(om, 'propose_to_be_signed')
        edit.update()
        self.assertEquals(api.content.get_state(om), 'to_be_signed')
        self.assertEquals(edit.is_initial_state(), False)
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'hidden')
        self.clean_request()

        # Testing reply view
        swde = self.portal.contacts['swde']
        tg = get_registry_organizations()[0]
        im = api.content.create(container=self.portal['incoming-mail'], type='dmsincomingmail', id='im',
                                title=u'I mail', sender=[RelationValue(self.intids.getId(swde))],
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
        change_user(self.portal, 'encodeur')
        imail = sub_create(self.portal['incoming-mail'], 'dmsincomingmail', datetime.now(), 'my-id')
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

    def test_OM_get_sender_email(self):
        om = get_object(oid='reponse1', ptype='dmsoutgoingmail')
        # default option is getting agent email
        self.assertEqual(om.get_sender_email(), u'"Michel Chef" <michel.chef@macommune.be>')
        # get service email
        replyto_key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_sender_email_default'
        api.portal.set_registry_record(replyto_key, u'service_email')
        self.assertEqual(om.get_sender_email(), u'contact@macommune.be')  # get higher email
        org = om.get_sender_info()['org']
        org.email = u'grh@macommune.be'
        self.assertEqual(om.get_sender_email(), u'grh@macommune.be')  # get nearest email

    def test_OM_get_recipient_emails(self):
        om = get_object(oid='reponse1', ptype='dmsoutgoingmail')
        self.assertIsNone(om.orig_sender_email)
        recip1 = self.portal.unrestrictedTraverse(om.recipients[0].to_path)
        # recip1 is electrabel org
        self.assertEqual(recip1.email, u'contak@electrabel.eb')
        self.assertEqual(om.get_recipient_emails(), u'contak@electrabel.eb')
        # we add an orig_email_sender
        om.orig_sender_email = u'"Dexter Morgan" <dexter.morgan@mpd.am>'
        self.assertEqual(om.get_recipient_emails(), u'"Dexter Morgan" <dexter.morgan@mpd.am>, contak@electrabel.eb')
        # we use the same email
        om.orig_sender_email = u'"Dexter Morgan" <contak@electrabel.eb>'
        self.assertEqual(om.get_recipient_emails(), u'"Dexter Morgan" <contak@electrabel.eb>')
        # we add a recipient
        hp = self.portal['contacts']['jeancourant']['agent-electrabel']
        om.recipients.append(RelationValue(self.intids.getId(hp)))
        self.assertEqual(om.get_recipient_emails(), u'"Dexter Morgan" <contak@electrabel.eb>, '
                                                    u'"Jean Courant" <jean.courant@electrabel.eb>')

    def test_ImioDmsOutgoingMailWfConditionsAdapter_can_be_handsigned(self):
        omail = sub_create(self.portal['outgoing-mail'], 'dmsoutgoingmail', datetime.now(), 'test-id')
        self.assertEqual(api.content.get_state(omail), 'created')
        adapted = omail.wf_conditions()
        self.assertFalse(adapted.can_be_handsigned())
        createContentInContainer(omail, 'task')
        self.assertFalse(adapted.can_be_handsigned())
        createContentInContainer(omail, 'dmsappendixfile')
        self.assertFalse(adapted.can_be_handsigned())
        createContentInContainer(omail, 'dmsommainfile')
        self.assertTrue(adapted.can_be_handsigned())

    def test_ImioDmsOutgoingMailWfConditionsAdapter_can_be_sent(self):
        omail = sub_create(self.portal['outgoing-mail'], 'dmsoutgoingmail', datetime.now(), 'test-id', title=u'test')
        self.assertEqual(api.content.get_state(omail), 'created')
        adapted = omail.wf_conditions()
        # no treating_groups
        self.assertFalse(adapted.can_be_sent())
        omail.treating_groups = get_registry_organizations()[0]  # direction-generale
        # admin
        self.assertTrue(adapted.can_be_sent())
        change_user(self.portal, 'chef')
        # define as email
        omail.send_modes = [u'email']
        self.assertTrue(omail.is_email())
        self.assertFalse(adapted.can_be_sent())
        omail.email_status = u'sent at ...'
        self.assertTrue(adapted.can_be_sent())
        # define as normal mail
        omail.send_modes = [u'post']
        self.assertFalse(omail.is_email())
        self.assertTrue(adapted.can_be_sent())
        # createContentInContainer(omail, 'dmsommainfile')  # no more depend on a dmsommainfile
        # self.assertTrue(adapted.can_be_sent())

    def test_AssignedUserValidator(self):
        # im
        obj = get_object(oid='courrier1', ptype='dmsincomingmail')
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
        obj = get_object(oid='reponse1', ptype='dmsoutgoingmail')
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
        obj = get_object(oid='courrier1', ptype='dmsincomingmail')['tache1']
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
        # we check assigned_user requirement if the imail state will be changed
        # this test is done in im wfadaptation test
