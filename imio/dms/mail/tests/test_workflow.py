# -*- coding: utf-8 -*-
""" workflow tests for this package."""
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestIMWorkflow(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.imw = self.pw['incomingmail_workflow']

    def test_im_workflow0(self):
        """ Check workflow """
        self.assertSetEqual(set(self.imw.states), set(['created', 'proposed_to_manager',
                                                       'proposed_to_agent', 'in_treatment', 'closed']))
        self.assertSetEqual(set(self.imw.transitions),
                            set(['back_to_creation', 'back_to_manager', 'back_to_agent', 'back_to_treatment',
                                 'propose_to_manager', 'propose_to_agent', 'treat', 'close']))
        self.assertSetEqual(set(self.imw.states['created'].transitions),
                            set(['propose_to_manager', 'propose_to_agent']))
        self.assertSetEqual(set(self.imw.states['proposed_to_manager'].transitions),
                            set(['back_to_creation', 'propose_to_agent']))
        self.assertSetEqual(set(self.imw.states['proposed_to_agent'].transitions),
                            set(['back_to_creation', 'back_to_manager', 'treat', 'close']))
        self.assertSetEqual(set(self.imw.states['in_treatment'].transitions),
                            set(['back_to_agent', 'close']))
        self.assertSetEqual(set(self.imw.states['closed'].transitions),
                            set(['back_to_treatment', 'back_to_agent']))
