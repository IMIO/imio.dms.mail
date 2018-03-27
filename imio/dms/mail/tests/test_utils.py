# -*- coding: utf-8 -*-
import unittest
from zope.component import getUtility
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID, login, TEST_USER_NAME
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from imio.helpers.cache import invalidate_cachekey_volatile_for

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..utils import highest_review_level, voc_selected_org_suffix_users, list_wf_states
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

    def test_voc_selected_org_suffix_users(self):
        self.assertEqual(voc_selected_org_suffix_users(None, []).by_token, {})
        self.assertEqual(voc_selected_org_suffix_users(u'--NOVALUE--', []).by_token, {})
        registry = getUtility(IRegistry)
        org1 = registry[ORGANIZATIONS_REGISTRY][1]
        self.assertEqual(voc_selected_org_suffix_users(org1, []).by_token, {})
        self.assertListEqual([t.value for t in voc_selected_org_suffix_users(org1, ['editeur'])], ['agent'])
        api.group.add_user(groupname='%s_editeur' % org1, username=TEST_USER_ID)
        self.assertListEqual([t.value for t in voc_selected_org_suffix_users(org1, ['editeur'])],
                             ['agent', TEST_USER_NAME])
        self.assertEqual([t.title for t in voc_selected_org_suffix_users(org1, ['editeur', 'validateur', 'lecteur'])],
                         ['Fred Agent', 'Jef Lecteur', 'Michel Chef', 'test-user'])
        self.assertEqual([t.title for t in voc_selected_org_suffix_users(org1, ['editeur', 'validateur', 'lecteur'],
                                                                         first_member=api.user.get_current())],
                         ['test-user', 'Fred Agent', 'Jef Lecteur', 'Michel Chef'])

    def test_list_wf_states(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(list_wf_states(imail, 'unknown'), [])
        self.assertEqual([s.id for s in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'])
        # We rename a state id
        states = imail.portal_workflow.task_workflow.states
        states.manage_renameObject('to_do', 'NEW')
        # test cache (objects are cached)
        self.assertEqual([s.id for s in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'NEW', 'in_progress', 'realized', 'closed'])
        invalidate_cachekey_volatile_for('imio-dms-mail-utils-list_wf_states.task')
        self.assertEqual([s.id for s in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'in_progress', 'realized', 'closed', 'NEW'])

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
        self.assertSetEqual(set(view.current_user_groups_ids(api.user.get_current())),
                            set(['AuthenticatedUsers', 'dir_general']))

    def test_UtilsMethods_highest_scan_id(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.highest_scan_id(), "dmsmainfiles: '9', highest scan_id: '050999900000009'")

    def test_UtilsMethods_is_in_user_groups(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertListEqual(view.current_user_groups_ids(api.user.get_current()), ['AuthenticatedUsers'])
        # current user is Manager
        self.assertTrue(view.is_in_user_groups(groups=['abc']))
        self.assertFalse(view.is_in_user_groups(groups=['abc'], admin=False))
        self.assertFalse(view.is_in_user_groups(groups=['abc'], admin=False, test='all'))
        # current user is not Manager
        login(self.portal, 'dirg')
        self.assertSetEqual(set(view.current_user_groups_ids(api.user.get_current())),
                            set(['AuthenticatedUsers', 'dir_general']))
        self.assertFalse(view.is_in_user_groups(groups=['abc']))
        self.assertTrue(view.is_in_user_groups(groups=['abc', 'dir_general']))
        self.assertFalse(view.is_in_user_groups(groups=['abc', 'dir_general'], test='all'))
        self.assertTrue(view.is_in_user_groups(groups=['AuthenticatedUsers', 'dir_general']))
        self.assertFalse(view.is_in_user_groups(groups=['dir_general'], test='other'))

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
