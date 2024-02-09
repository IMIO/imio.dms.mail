# -*- coding: utf-8 -*-
from datetime import datetime
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import create_period_folder
from plone import api
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zExceptions import Redirect
from zope.component import getUtility
from zope.interface import noLongerProvides

import unittest


class TestExamples(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        self.omd = self.portal['outgoing-mail']
        change_user(self.portal)

    def test_add_special_model_mail(self):
        dtm = datetime.now()
        folder = create_period_folder(self.omd, dtm)
        # nothing exist
        self.assertNotIn('test_creation_modele', folder)
        add_special_model_mail(self.portal)
        self.assertIn('test_creation_modele', folder)
        self.assertIn('1', folder['test_creation_modele'])
        self.assertEqual(folder['test_creation_modele']['1'].scan_id, '012999900000000')
        # file doesn't exist
        self.assertRaises(Redirect, api.content.delete, folder['test_creation_modele']['1'])
        noLongerProvides(folder['test_creation_modele']['1'], IProtectedItem)
        api.content.delete(folder['test_creation_modele']['1'])
        self.assertNotIn('1', folder['test_creation_modele'])
        add_special_model_mail(self.portal)
        self.assertIn('1', folder['test_creation_modele'])

    def test_add_test_directory(self):
        # checking directory
        self.assertTrue(hasattr(self.portal, 'contacts'))
        contacts = self.portal['contacts']
        self.assertEquals(len(contacts.position_types), 5)
        self.assertEquals(len(contacts.organization_types), 7)
        self.assertEquals(len(contacts.organization_levels), 3)
        # checking organizations
        organizations = contacts.listFolderContents(contentFilter={'portal_type': 'organization'})
        self.assertEquals(len(organizations), 3)
        # checking positions
        pc = self.portal.portal_catalog
        positions = pc(portal_type=('position',), path={"query": 'plone/contacts'})
        self.assertEquals(len(positions), 0)
        # checking persons
        persons = contacts.listFolderContents(contentFilter={'portal_type': 'person'})
        self.assertEquals(len(persons), 4)
        # checking held positions
        held_positions = pc(portal_type=('held_position',), path={"query": 'plone/contacts'},
                            object_provides='collective.contact.plonegroup.interfaces.INotPloneGroupContact')
        self.assertEquals(len(held_positions), 3)

    def test_add_test_mails(self):
        # checking incoming mails
        pc = self.portal.portal_catalog
        imails = pc(portal_type=('dmsincomingmail',), path={"query": 'plone/incoming-mail'})
        self.assertEquals(len(imails), 9)
        # checking outgoing mails
        omails = pc(portal_type=('dmsoutgoingmail',), path={"query": 'plone/outgoing-mail'})
        self.assertEquals(len(omails), 9)

    def test_add_test_users_and_groups(self):
        # checking groups
        acl_users = getToolByName(self.portal, 'acl_users')
        lecteurs = [gd for gd in acl_users.searchGroups() if gd['groupid'].endswith('_lecteur')]
        self.assertEquals(len(lecteurs), 11)
        # checking users
        mt = getToolByName(self.portal, 'portal_membership')
        users = [member for member in mt.listMembers()
                 if member.getProperty('fullname').find(' ') >= 1]
        self.assertEquals(len(users), 6)

    def test_configure_batch_import(self):
        registry = getUtility(IRegistry)
        fs_root_directory = registry['collective.dms.batchimport.batchimport.ISettings.fs_root_directory']
        self.assertTrue(fs_root_directory.endswith('batchimport/toprocess'))
        code_to_type_mapping = registry['collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping']
        self.assertEquals(len(code_to_type_mapping), 1)
        self.assertEquals(code_to_type_mapping[0]['code'], u'in')
        self.assertEquals(code_to_type_mapping[0]['portal_type'], u'dmsincomingmail')
