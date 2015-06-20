# -*- coding: utf-8 -*-
import unittest2 as unittest
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.adapters import highest_review_level
from imio.dms.mail.adapters import IncomingMailHighestValidationCriterion
from imio.dms.mail.adapters import organizations_with_suffixes
from imio.dms.mail.adapters import IncomingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import IncomingMailInCopyGroupCriterion
from imio.dms.mail.adapters import ScanSearchableExtender


class TestAdapters(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_highest_review_level(self):
        self.assertIsNone(highest_review_level('a_type', ""))
        self.assertIsNone(highest_review_level('dmsincomingmail', ""))
        self.assertEquals(highest_review_level('dmsincomingmail', "['dir_general']"), 'dir_general')
        self.assertEquals(highest_review_level('dmsincomingmail', "['111_validateur']"), '_validateur')

    def test_IncomingMailHighestValidationCriterion(self):
        crit = IncomingMailHighestValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {})
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        # in a group _validateur
        self.assertEqual(crit.query, {'review_state': 'proposed_to_service_chief',
                                      'treating_groups': ['111']})
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        # in a group dir_general
        self.assertEqual(crit.query, {'review_state': 'proposed_to_manager'})

    def test_organizations_with_suffixes(self):
        g1 = api.group.create(groupname='111_suf1')
        g2 = api.group.create(groupname='112_suf1')
        g3 = api.group.create(groupname='112_suf2')
        self.assertEqual(organizations_with_suffixes([], []), [])
        self.assertEqual(organizations_with_suffixes([g1, g2], []), [])
        self.assertEqual(organizations_with_suffixes([], ['suf1']), [])
        self.assertEqual(organizations_with_suffixes([g1, g2], ['suf1']),
                         ['111', '112'])
        self.assertEqual(organizations_with_suffixes([g1, g3], ['suf1', 'suf2']),
                         ['111', '112'])

    def test_IncomingMailInTreatingGroupCriterion(self):
        crit = IncomingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'treating_groups': []})
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'treating_groups': ['111']})

    def test_IncomingMailInCopyGroupCriterion(self):
        crit = IncomingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'recipient_groups': []})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'recipient_groups': ['111']})

    def test_ScanSearchableExtender(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1', title='title', description='description',
                                       scan_id='IMIO123456789')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title 123456789 description')
        fh = open('testfile.txt', 'w+')
        fh.write("One word\n")
        fh.seek(0)
        file_object = NamedBlobFile(fh.read(), filename=u'testfile.txt')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2', title='title', description='description',
                                       file=file_object, scan_id='IMIO123456789')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 title 123456789 description One word\n')
