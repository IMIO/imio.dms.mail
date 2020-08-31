# -*- coding: utf-8 -*-
""" workflow tests for this package."""
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import get_dms_config
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestWorkflows(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.imw = self.pw['incomingmail_workflow']
        self.omw = self.pw['outgoingmail_workflow']

    def test_im_workflow0(self):
        """ Check workflow """
        self.assertSetEqual(set(self.imw.states),
                            {'created', 'proposed_to_manager', 'proposed_to_agent', 'in_treatment', 'closed'})
        self.assertSetEqual(set(self.imw.transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_agent', 'back_to_treatment',
                             'propose_to_manager', 'propose_to_agent', 'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['created'].transitions),
                            {'propose_to_manager', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_manager'].transitions),
                            {'back_to_creation', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_agent'].transitions),
                            {'back_to_creation', 'back_to_manager', 'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['in_treatment'].transitions),
                            {'back_to_agent', 'close'})
        self.assertSetEqual(set(self.imw.states['closed'].transitions),
                            {'back_to_treatment', 'back_to_agent'})
        # default annotations
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        self.assertListEqual(wf_from_to['to'], [('proposed_to_agent', 'propose_to_agent')])

    def test_om_workflow0(self):
        """ Check workflow """
        self.assertSetEqual(set(self.omw.states),
                            {'created', 'scanned', 'to_be_signed', 'sent'})
        self.assertSetEqual(set(self.omw.transitions),
                            {'back_to_creation', 'back_to_agent', 'back_to_scanned', 'back_to_be_signed',
                             'set_scanned', 'propose_to_be_signed', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['created'].transitions),
                            {'set_scanned', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['scanned'].transitions),
                            {'mark_as_sent', 'back_to_agent'})
        self.assertSetEqual(set(self.omw.states['to_be_signed'].transitions),
                            {'mark_as_sent', 'back_to_creation'})
        self.assertSetEqual(set(self.omw.states['sent'].transitions),
                            {'back_to_be_signed', 'back_to_scanned'})
