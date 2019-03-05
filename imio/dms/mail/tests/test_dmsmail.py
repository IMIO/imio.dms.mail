# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from imio.dms.mail.browser.reply_form import ReplyForm
from imio.dms.mail.dmsmail import OMCustomAddForm
from imio.dms.mail.dmsmail import OMEdit
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from z3c.relationfield.relation import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import unittest


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

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
        api.content.transition(om, 'propose_to_service_chief')
        edit.update()
        self.assertEquals(api.content.get_state(om), 'proposed_to_service_chief')
        self.assertEquals(edit.is_initial_state(), False)
        self.assertEquals(self.request['_hide_irn'], True)
        self.assertNotIn('_auto_ref', self.request.keys())
        self.assertEquals(edit.widgets['internal_reference_no'].mode, 'hidden')
        self.clean_request()

        # Testing reply view
        intids = getUtility(IIntIds)
        swde = self.portal.contacts['swde']
        tg = api.portal.get_registry_record(ORGANIZATIONS_REGISTRY)[0]
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
