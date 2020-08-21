# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import IMSkipProposeToServiceChief
from imio.dms.mail.wfadaptations import OMSkipProposeToServiceChief
from imio.dms.mail.wfadaptations import IMServiceValidation
from plone import api
from plone.app.testing import login
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
        api.group.create('abc_group_encoder', 'ABC group encoder')
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-apply_n_plus_1_wfadaptation',
                                                          run_dependencies=False)

# TODO states vocabulary,

    def test_workflow(self):
        """ """
        pass

    def test_IMServiceValidation(self):
        """
            Test all methods of IMServiceValidation class
        """
        imsv = IMServiceValidation()
        im_workflow = self.pw['incomingmail_workflow']
        self.assertEqual(imsv.check_state_in_workflow(im_workflow, 'proposed_to_n_plus_1'), '')
        self.assertNotEqual(imsv.check_state_in_workflow(im_workflow, 'proposed_to_n_plus_2'), '')
        imsv.patch_workflow('incomingmail_workflow', validation_level=2,
                            state_title=u'Valider par le chef de département',
                            forward_transition_title=u'Proposer au chef de département',
                            backward_transition_title=u'Renvoyer au chef de département',
                            function_title=u'chef de département')
        self.assertEqual(imsv.check_state_in_workflow(im_workflow, 'proposed_to_n_plus_2'), '')
        self.assertEqual(imsv.check_transition_in_workflow(im_workflow, 'propose_to_n_plus_2'), '')
        self.assertEqual(imsv.check_transition_in_workflow(im_workflow, 'back_to_n_plus_2'), '')
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('proposed_to_n_plus_2', lr['static_config'])
        self.assertIn('proposed_to_n_plus_2', lr['treating_groups'])
        self.assertIn('proposed_to_n_plus_2', lr['recipient_groups'])
        self.assertTrue(self.portal['incoming-mail']['mail-searches']['searchfor_proposed_to_n_plus_2'].enabled)

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond(self):
        im_folder = self.portal['incoming-mail']['mail-searches']
        col = im_folder['searchfor_proposed_to_n_plus_1']
        n_plus_1_view = IdmUtilsMethods(col, col.REQUEST)
        self.assertFalse(n_plus_1_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'agent')
        self.assertFalse(n_plus_1_view.proposed_to_n_plus_col_cond())
        api.group.add_user(groupname='abc_group_encoder', username='agent')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        api.group.remove_user(groupname='abc_group_encoder', username='agent')
        login(self.portal, 'dirg')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'chef')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        # create N+2 validation by patching the workflow
        login(self.portal, 'test-user')
        sva = IMServiceValidation()
        sva.patch_workflow('incomingmail_workflow',
                           validation_level=2,
                           state_title=u'Valider par le chef de département',
                           forward_transition_title=u'Proposer au chef de département',
                           backward_transition_title=u'Renvoyer au chef de département',
                           function_title=u'chef de département')
        col = im_folder['searchfor_proposed_to_n_plus_2']
        n_plus_2_view = IdmUtilsMethods(col, col.REQUEST)
        self.assertFalse(n_plus_2_view.proposed_to_n_plus_col_cond())
        # Set N+2 to user, have to get an organization UID first
        contacts = self.portal['contacts']
        own_orga = contacts['plonegroup-organization']
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        self.portal.acl_users.source_groups.addPrincipalToGroup('agent1', "%s_n_plus_2" % departments[5].UID())
        login(self.portal, 'agent1')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
