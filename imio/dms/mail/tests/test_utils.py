# -*- coding: utf-8 -*-
import unittest2 as unittest
from zope.component import getUtility
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..utils import highest_review_level, organizations_with_suffixes, voc_selected_org_suffix_users
from ..utils import IdmUtilsMethods
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

    def test_IdmUtilsMethodsReviewLevel(self):
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

    def test_IdmUtilsMethodsAssignedUser(self):
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

    def test_voc_selected_org_suffix_users(self):
        self.assertEqual(voc_selected_org_suffix_users(None, []).by_token, {})
        self.assertEqual(voc_selected_org_suffix_users(u'--NOVALUE--', []).by_token, {})
        registry = getUtility(IRegistry)
        org0 = registry[ORGANIZATIONS_REGISTRY][0]
        self.assertEqual(voc_selected_org_suffix_users(org0, []).by_token, {})
        self.assertEqual(voc_selected_org_suffix_users(org0, ['encodeur']).by_token, {})
        api.group.add_user(groupname='%s_encodeur' % org0, username=TEST_USER_ID)
        self.assertEqual(voc_selected_org_suffix_users(org0, ['encodeur']).by_token.keys(), [TEST_USER_ID])
