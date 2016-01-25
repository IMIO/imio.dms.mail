# -*- coding: utf-8 -*-
import unittest
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..adapters import default_criterias
from ..adapters import IncomingMailHighestValidationCriterion
from ..adapters import IncomingMailInTreatingGroupCriterion
from ..adapters import IncomingMailInCopyGroupCriterion
from ..adapters import ScanSearchableExtender


class TestAdapters(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_IncomingMailHighestValidationCriterion(self):
        crit = IncomingMailHighestValidationCriterion(self.portal)
        # no groups, => default criterias
        self.assertEqual(crit.query, default_criterias['dmsincomingmail'])
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        # in a group _validateur
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_service_chief']},
                                      'treating_groups': {'query': ['111']}})
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        # in a group dir_general
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_manager']}})

    def test_IncomingMailInTreatingGroupCriterion(self):
        crit = IncomingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'treating_groups': {'query': []}})
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'treating_groups': {'query': ['111']}})

    def test_IncomingMailInCopyGroupCriterion(self):
        crit = IncomingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'recipient_groups': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'recipient_groups': {'query': ['111']}})

    def test_ScanSearchableExtender(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', title='title', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1', title='title.pdf', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2.pdf', title='testid2.pdf',
                                       description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900000690.pdf', title='010999900000690.pdf',
                                       description='description', scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900000690 IMIO010999900000690 690 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900000691.pdf', title='title',
                                       description='description', scan_id='010999900000691')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900000691 title IMIO010999900000691 691 description')
        fh = open('testfile.txt', 'w+')
        fh.write("One word\n")
        fh.seek(0)
        file_object = NamedBlobFile(fh.read(), filename=u'testfile.txt')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2', title='title', description='description',
                                       file=file_object, scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 title 010999900000690 IMIO010999900000690 690 description One word\n')
