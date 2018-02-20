# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
import unittest

from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.wfadaptations import EmergencyZoneAdaptation, OMToPrintAdaptation
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import getUtility


class TestWFAdaptations(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow

    def test_EmergencyZoneAdaptation(self):
        """
            Test all methods of EmergencyZoneAdaptation class
        """
        eza = EmergencyZoneAdaptation()
        imw = self.pw['incomingmail_workflow']
        self.assertEqual(imw.states['proposed_to_manager'].title, 'proposed_to_manager')
        self.assertEqual(imw.transitions['back_to_manager'].title, 'back_to_manager')
        eza.patch_workflow('', manager_suffix='_zs')
        self.assertEqual(imw.states['proposed_to_manager'].title, 'proposed_to_manager_zs')
        self.assertEqual(imw.transitions['back_to_manager'].title, 'back_to_manager_zs')
        self.assertEqual(imw.transitions['propose_to_manager'].title, 'propose_to_manager_zs')
        collection = self.portal.restrictedTraverse('incoming-mail/mail-searches/searchfor_proposed_to_manager')
        self.assertEqual(collection.title, u'État: à valider par le CZ')

    def test_OMToPrintAdaptation(self):
        """
            Test all methods of EmergencyZoneAdaptation class
        """
        tpa = OMToPrintAdaptation()
        omw = self.pw['outgoingmail_workflow']
        self.assertTrue(tpa.check_state_in_workflow(omw, 'to_print'))
        tpa.patch_workflow('')
        self.assertEqual(tpa.check_state_in_workflow(omw, 'to_print'), '')
        self.assertEqual(tpa.check_transition_in_workflow(omw, 'set_to_print'), '')
        self.assertEqual(tpa.check_transition_in_workflow(omw, 'back_to_print'), '')
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('to_print', lr['static_config'])
        self.assertIn('to_print', lr['treating_groups'])
        self.assertIn('to_print', lr['recipient_groups'])
        self.assertIn('searchfor_to_print', self.portal['outgoing-mail']['mail-searches'])
