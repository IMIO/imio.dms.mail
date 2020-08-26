# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import IMSkipProposeToServiceChief
from imio.dms.mail.wfadaptations import OMSkipProposeToServiceChief
from imio.dms.mail.wfadaptations import IMServiceValidation
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

    def test_OMToPrintAdaptation(self):
        """
            Test all methods of OMToPrintAdaptation class
        """
        return
        # TODO to be corrceted
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
