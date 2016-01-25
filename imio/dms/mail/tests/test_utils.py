# -*- coding: utf-8 -*-
import unittest
from zope.component import getUtility
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID, login
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..utils import highest_review_level, organizations_with_suffixes, voc_selected_org_suffix_users, list_wf_states
from ..utils import create_richtextval, get_scan_id, UtilsMethods, IdmUtilsMethods
from ..browser.settings import IImioDmsMailConfig


class TestUtils(unittest.TestCase):

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

    def test_voc_selected_org_suffix_users(self):
        self.assertEqual(voc_selected_org_suffix_users(None, []).by_token, {})
        self.assertEqual(voc_selected_org_suffix_users(u'--NOVALUE--', []).by_token, {})
        registry = getUtility(IRegistry)
        org0 = registry[ORGANIZATIONS_REGISTRY][0]
        self.assertEqual(voc_selected_org_suffix_users(org0, []).by_token, {})
        self.assertEqual(voc_selected_org_suffix_users(org0, ['encodeur']).by_token, {})
        api.group.add_user(groupname='%s_encodeur' % org0, username=TEST_USER_ID)
        self.assertEqual(voc_selected_org_suffix_users(org0, ['encodeur']).by_token.keys(), [TEST_USER_ID])

    def test_list_wf_states(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(list_wf_states(imail, 'unknown'), [])
        self.assertEqual(list_wf_states(imail, 'task'), ['created', 'to_assign', 'to_do', 'in_progress', 'realized',
                                                         'closed'])
        # We rename a state id
        states = imail.portal_workflow.task_workflow.states
        states.manage_renameObject('to_do', 'NEW')
        self.assertEqual(list_wf_states(imail, 'task'), ['created', 'to_assign', 'in_progress', 'realized', 'closed',
                                                         'NEW'])

    def test_create_richtextval(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         task_description=create_richtextval('Text content'))
        self.assertEqual(imail.task_description.output, 'Text content')
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         task_description=create_richtextval(u'Text content'))
        self.assertEqual(imail.task_description.output, 'Text content')

    def test_get_scan_id(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', scan_id=u'010999900000690')
        self.assertListEqual(get_scan_id(obj), [u'010999900000690', u'IMIO010999900000690', u'690'])

    def test_UtilsMethods_current_user_groups_ids(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = UtilsMethods(imail, imail.REQUEST)
        login(self.portal, 'dirg')
        self.assertSetEqual(set(view.current_user_groups_ids()), set(['AuthenticatedUsers', 'dir_general']))

    def test_UtilsMethods_highest_scan_id(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.highest_scan_id(), 'No scan id')
        createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', scan_id='010999900000069')
        self.assertEqual(view.highest_scan_id(), 'dmsmainfiles: 1, highest scanid: 010999900000069')

    def test_IdmUtilsMethods_get_im_folder(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.get_im_folder(), self.portal['incoming-mail'])

    def test_IdmUtilsMethods_user_has_review_level(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.user_has_review_level())
        self.assertFalse(view.user_has_review_level('dmsincomingmail'))
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertTrue(view.user_has_review_level('dmsincomingmail'))
        api.group.remove_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertFalse(view.user_has_review_level('dmsincomingmail'))
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertTrue(view.user_has_review_level('dmsincomingmail'))

    def test_IdmUtilsMethods_idm_has_assigned_user(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', assigned_user='thorgal')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertTrue(view.idm_has_assigned_user())
        imail.assigned_user = None
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        settings.assigned_user_check = False
        self.assertTrue(view.idm_has_assigned_user())
        settings.assigned_user_check = True
        self.assertTrue(view.idm_has_assigned_user())
        self.assertIn('Manager', api.user.get_roles(username=TEST_USER_ID))
        setRoles(self.portal, TEST_USER_ID, [])
        self.assertNotIn('Manager', api.user.get_roles(username=TEST_USER_ID))
        self.assertFalse(view.idm_has_assigned_user())

    def test_IdmUtilsMethods_created_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.created_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.created_col_cond())

    def test_IdmUtilsMethods_proposed_to_manager_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_manager_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.proposed_to_manager_col_cond())
        login(self.portal, 'dirg')
        self.assertTrue(view.proposed_to_manager_col_cond())

    def test_IdmUtilsMethods_proposed_to_serv_chief_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_serv_chief_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.proposed_to_serv_chief_col_cond())
        login(self.portal, 'dirg')
        self.assertTrue(view.proposed_to_serv_chief_col_cond())
        login(self.portal, 'chef')
        self.assertTrue(view.proposed_to_serv_chief_col_cond())
