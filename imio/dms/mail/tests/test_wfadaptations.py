# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.wfadaptations import EmergencyZoneAdaptation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import IMSkipProposeToServiceChief
from imio.dms.mail.wfadaptations import OMSkipProposeToServiceChief
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import getUtility

import unittest


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
        eza.patch_workflow('incomingmail_workflow', manager_suffix='_zs')
        self.assertEqual(imw.states['proposed_to_manager'].title, 'proposed_to_manager_zs')
        self.assertEqual(imw.transitions['back_to_manager'].title, 'back_to_manager_zs')
        self.assertEqual(imw.transitions['propose_to_manager'].title, 'propose_to_manager_zs')
        collection = self.portal.restrictedTraverse('incoming-mail/mail-searches/searchfor_proposed_to_manager')
        self.assertEqual(collection.title, u'État: à valider par le CZ')

    def test_OMToPrintAdaptation(self):
        """
            Test all methods of OMToPrintAdaptation class
        """
        tpa = OMToPrintAdaptation()
        omw = self.pw['outgoingmail_workflow']
        self.assertTrue(tpa.check_state_in_workflow(omw, 'to_print'))
        tpa.patch_workflow('outgoingmail_workflow')
        self.assertEqual(tpa.check_state_in_workflow(omw, 'to_print'), '')
        self.assertEqual(tpa.check_transition_in_workflow(omw, 'set_to_print'), '')
        self.assertEqual(tpa.check_transition_in_workflow(omw, 'back_to_print'), '')
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('to_print', lr['static_config'])
        self.assertIn('to_print', lr['treating_groups'])
        self.assertIn('to_print', lr['recipient_groups'])
        self.assertIn('searchfor_to_print', self.portal['outgoing-mail']['mail-searches'])

    def test_IMSkipProposeToServiceChiefWithUserCheck(self):
        """
            Test all methods of IMSkipProposeToServiceChief class with assigned_user_check parameter as True
        """
        imsp = IMSkipProposeToServiceChief()
        im_workflow = self.pw['incomingmail_workflow']
        self.assertFalse(imsp.check_state_in_workflow(im_workflow, 'proposed_to_service_chief'))
        self.assertTrue(api.portal.get_registry_record('assigned_user_check', IImioDmsMailConfig))
        imsp.patch_workflow('incomingmail_workflow', assigned_user_check=True)
        self.assertNotEqual(imsp.check_state_in_workflow(im_workflow, 'proposed_to_service_chief'), '')
        self.assertNotEqual(imsp.check_transition_in_workflow(im_workflow, 'propose_to_service_chief'), '')
        self.assertNotEqual(imsp.check_transition_in_workflow(im_workflow, 'back_to_service_chief'), '')
        self.assertIn('propose_to_agent', im_workflow.states['created'].transitions)
        self.assertIn('propose_to_agent', im_workflow.states['proposed_to_manager'].transitions)
        self.assertIn('back_to_manager', im_workflow.states['proposed_to_agent'].transitions)
        self.assertIn('back_to_creation', im_workflow.states['proposed_to_agent'].transitions)
        self.assertTrue(api.portal.get_registry_record('assigned_user_check', IImioDmsMailConfig))
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertNotIn('proposed_to_service_chief', lr['static_config'])
        self.assertNotIn('proposed_to_service_chief', lr['treating_groups'])
        self.assertNotIn('proposed_to_service_chief', lr['recipient_groups'])
        self.assertFalse(self.portal['incoming-mail']['mail-searches']['searchfor_proposed_to_service_chief'].enabled)

    def test_IMSkipProposeToServiceChiefWithoutUserCheck(self):
        """
            Test all methods of IMSkipProposeToServiceChief class with assigned_user_check parameter as False
        """
        imsp = IMSkipProposeToServiceChief()
        im_workflow = self.pw['incomingmail_workflow']
        self.assertFalse(imsp.check_state_in_workflow(im_workflow, 'proposed_to_service_chief'))
        self.assertTrue(api.portal.get_registry_record('assigned_user_check', IImioDmsMailConfig))
        imsp.patch_workflow('incomingmail_workflow', assigned_user_check=False)
        self.assertNotEqual(imsp.check_state_in_workflow(im_workflow, 'proposed_to_service_chief'), '')
        self.assertNotEqual(imsp.check_transition_in_workflow(im_workflow, 'propose_to_service_chief'), '')
        self.assertNotEqual(imsp.check_transition_in_workflow(im_workflow, 'back_to_service_chief'), '')
        self.assertIn('propose_to_agent', im_workflow.states['created'].transitions)
        self.assertIn('propose_to_agent', im_workflow.states['proposed_to_manager'].transitions)
        self.assertIn('back_to_manager', im_workflow.states['proposed_to_agent'].transitions)
        self.assertIn('back_to_creation', im_workflow.states['proposed_to_agent'].transitions)
        self.assertFalse(api.portal.get_registry_record('assigned_user_check', IImioDmsMailConfig))
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertNotIn('proposed_to_service_chief', lr['static_config'])
        self.assertNotIn('proposed_to_service_chief', lr['treating_groups'])
        self.assertNotIn('proposed_to_service_chief', lr['recipient_groups'])
        self.assertFalse(self.portal['incoming-mail']['mail-searches']['searchfor_proposed_to_service_chief'].enabled)

    def test_OMSkipProposeToServiceChief(self):
        """
            Test all methods of OMSkipProposeToServiceChief class
        """
        omsp = OMSkipProposeToServiceChief()
        om_workflow = self.pw['outgoingmail_workflow']
        self.assertFalse(omsp.check_state_in_workflow(om_workflow, 'proposed_to_service_chief'))
        omsp.patch_workflow('outgoingmail_workflow')
        self.assertNotEqual(omsp.check_state_in_workflow(om_workflow, 'proposed_to_service_chief'), '')
        self.assertNotEqual(omsp.check_transition_in_workflow(om_workflow, 'propose_to_service_chief'), '')
        self.assertNotEqual(omsp.check_transition_in_workflow(om_workflow, 'back_to_service_chief'), '')
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        self.assertNotIn('proposed_to_service_chief', lr['static_config'])
        self.assertNotIn('proposed_to_service_chief', lr['treating_groups'])
        self.assertNotIn('proposed_to_service_chief', lr['recipient_groups'])
        self.assertFalse(self.portal['outgoing-mail']['mail-searches']['searchfor_proposed_to_service_chief'].enabled)
