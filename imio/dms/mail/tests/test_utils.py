# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import OdmUtilsMethods
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.dms.mail.utils import UtilsMethods
from imio.helpers.cache import invalidate_cachekey_volatile_for
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from z3c.relationfield import RelationValue
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.intid import IIntIds

import unittest


class TestUtils(unittest.TestCase):
    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        api.group.create('abc_group_encoder', 'ABC group encoder')
        self.pgof = self.portal['contacts']['plonegroup-organization']

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_dms_config(self):
        annot = IAnnotations(self.portal)
        set_dms_config(['a'], value='dict')
        lst = set_dms_config(['a', 'b'], value='list')
        self.assertTrue(isinstance(annot['imio.dms.mail'], PersistentDict))
        self.assertTrue(isinstance(annot['imio.dms.mail']['a'], PersistentDict))
        self.assertTrue(isinstance(annot['imio.dms.mail']['a']['b'], PersistentList))
        lst.append(1)
        self.assertEqual(get_dms_config(['a', 'b']), [1])
        set_dms_config(['a', 'b'], value='plone')
        self.assertTrue(isinstance(annot['imio.dms.mail']['a']['b'], str))
        self.assertEqual(get_dms_config(['a', 'b']), 'plone')

    def test_group_has_user(self):
        self.assertFalse(group_has_user('xxx', 'delete'))
        self.assertFalse(group_has_user('xxx'))  # group not found
        self.assertFalse(group_has_user('abc_group_encoder'))  # no user
        self.assertTrue(group_has_user('abc_group_encoder', 'add'))  # we are adding a user
        api.group.add_user(groupname='abc_group_encoder', username='chef')
        self.assertTrue(group_has_user('abc_group_encoder'))  # group has one user
        self.assertFalse(group_has_user('abc_group_encoder', 'remove'))  # we are removing the only one user

    def test_update_transitions_levels_config(self):
        # dmsincomingmail #
        config = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        self.assertSetEqual(set(config.keys()), {'created', 'proposed_to_manager', 'proposed_to_agent', 'closed'})
        self.assertEqual(config['created'], config['proposed_to_manager'])
        self.assertEqual(config['created'], config['proposed_to_agent'])
        self.assertEqual(config['created'], config['closed'])
        for state in config:
            for org in config[state]:
                self.assertEqual(config[state][org], ('propose_to_agent', 'from_states'))
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create('{}_n_plus_1'.format(org1), 'N+1')
        set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],
                       [('closed', 'close'), ('proposed_to_agent', 'propose_to_agent'),
                        ('proposed_to_n_plus_1', 'propose_to_n_plus_1')])
        update_transitions_levels_config(['dmsincomingmail'])
        config = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        self.assertEqual(config['proposed_to_n_plus_1'][org1], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['proposed_to_manager'][org1], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['proposed_to_manager'][org2], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['proposed_to_agent'][org1], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['closed'][org1], ('propose_to_agent', 'from_states'))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(['dmsincomingmail'], 'add', '{}_n_plus_1'.format(org1))
        config = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        self.assertEqual(config['proposed_to_n_plus_1'][org1], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['proposed_to_manager'][org1], ('propose_to_n_plus_1', 'from_states'))
        self.assertEqual(config['proposed_to_manager'][org2], ('propose_to_agent', 'from_states'))
        self.assertEqual(config['proposed_to_agent'][org1], ('propose_to_agent', 'back_to_n_plus_1'))
        self.assertEqual(config['proposed_to_agent'][org2], ('propose_to_agent', 'from_states'))

        # dmsoutgoingmail #
        config = get_dms_config(['transitions_levels', 'dmsoutgoingmail'])
        self.assertSetEqual(set(config.keys()), {'created', 'to_be_signed', 'sent'})
        self.assertEqual(config['created'], config['to_be_signed'])
        for state in config:
            for org in config[state]:
                self.assertEqual(config[state][org], ('', ''))
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create('{}_n_plus_1'.format(org1), 'N+1')
        update_transitions_levels_config(['dmsoutgoingmail'])
        config = get_dms_config(['transitions_levels', 'dmsoutgoingmail'])
        self.assertEqual(config['created'][org1], ('', ''))
        self.assertEqual(config['to_be_signed'][org1], ('', ''))
        self.assertEqual(config['created'][org2], ('', ''))
        self.assertEqual(config['to_be_signed'][org2], ('', ''))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(['dmsoutgoingmail'], 'add', '{}_n_plus_1'.format(org1))
        config = get_dms_config(['transitions_levels', 'dmsoutgoingmail'])
        self.assertEqual(config['created'][org1], ('propose_to_n_plus_1', ''))
        self.assertEqual(config['to_be_signed'][org1], ('', 'back_to_n_plus_1'))
        self.assertEqual(config['created'][org2], ('', ''))
        self.assertEqual(config['to_be_signed'][org2], ('', ''))

        # task #
        config = get_dms_config(['transitions_levels', 'task'])
        for org in config['created']:
            self.assertEqual(config['created'][org], ('', ''))
        for org in config['to_do']:
            self.assertEqual(config['to_do'][org], ('', 'back_in_created2'))
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create('{}_n_plus_1'.format(org1), 'N+1')
        update_transitions_levels_config(['task'])
        config = get_dms_config(['transitions_levels', 'task'])
        self.assertEqual(config['to_do'][org1], ('', 'back_in_created2'))
        self.assertEqual(config['to_do'][org2], ('', 'back_in_created2'))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(['task'], 'add', '{}_n_plus_1'.format(org1))
        config = get_dms_config(['transitions_levels', 'task'])
        self.assertEqual(config['created'][org1], ('do_to_assign', ''))
        self.assertEqual(config['to_do'][org1], ('', 'back_in_to_assign'))
        self.assertEqual(config['created'][org2], ('', ''))
        self.assertEqual(config['to_do'][org2], ('', 'back_in_created2'))

    def test_update_transitions_auc_config(self):
        api.portal.set_registry_record(AUC_RECORD, u'no_check')
        # no check
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertSetEqual(set(config.keys()), {'close', 'propose_to_agent'})
        self.assertTrue(all(config['propose_to_agent'].values()))  # can always do transition
        self.assertTrue(all(config['close'].values()))  # can always do transition
        # n_plus_1
        api.portal.set_registry_record(AUC_RECORD, u'n_plus_1')
        # only one transition
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertSetEqual(set(config.keys()), {'close', 'propose_to_agent'})
        self.assertTrue(all(config['propose_to_agent'].values()))
        self.assertTrue(all(config['close'].values()))
        # we simulate the adding of a level without user
        org1, org2 = get_registry_organizations()[0:2]
        api.group.create('{}_n_plus_1'.format(org1), 'N+1')
        set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],
                       [('closed', 'close'), ('proposed_to_agent', 'propose_to_agent'),
                        ('proposed_to_n_plus_1', 'propose_to_n_plus_1')])
        update_transitions_auc_config('dmsincomingmail')
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertSetEqual(set(config.keys()), {'close', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertTrue(all(config['propose_to_n_plus_1'].values()))
        self.assertTrue(all(config['propose_to_agent'].values()))
        self.assertTrue(all(config['close'].values()))
        # we simulate the adding of a level and a user
        update_transitions_auc_config('dmsincomingmail', 'add', '{}_n_plus_1'.format(org1))
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertTrue(config['propose_to_n_plus_1'][org1])
        self.assertFalse(config['propose_to_agent'][org1])  # cannot do transition because user
        self.assertTrue(config['propose_to_agent'][org2])
        # mandatory
        # reset config
        set_dms_config(['transitions_auc', 'dmsincomingmail'], value='dict')
        set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'], [('closed', 'close'),
                                                                           ('proposed_to_agent', 'propose_to_agent')])
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertFalse(any(config['propose_to_agent'].values()))  # all is False
        self.assertTrue(all(config['close'].values()))
        # we simulate the adding of a level without user
        set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],
                       [('closed', 'close'), ('proposed_to_agent', 'propose_to_agent'),
                        ('proposed_to_n_plus_1', 'propose_to_n_plus_1')])
        update_transitions_auc_config('dmsincomingmail')
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertSetEqual(set(config.keys()), {'close', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertFalse(any(config['propose_to_n_plus_1'].values()))  # all is False
        self.assertFalse(any(config['propose_to_agent'].values()))  # all is False
        self.assertTrue(all(config['close'].values()))
        # we simulate the adding of a level and a user
        update_transitions_auc_config('dmsincomingmail', 'add', '{}_n_plus_1'.format(org1))
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertTrue(config['propose_to_n_plus_1'][org1])  # can do transition because user
        self.assertFalse(config['propose_to_n_plus_1'][org2])
        self.assertFalse(config['propose_to_agent'][org1])
        self.assertFalse(config['propose_to_agent'][org2])

    def test_highest_review_level(self):
        self.assertIsNone(highest_review_level('a_type', ""))
        self.assertIsNone(highest_review_level('dmsincomingmail', ""))
        self.assertEquals(highest_review_level('dmsincomingmail', "['dir_general']"), 'dir_general')
        set_dms_config(['review_levels', 'dmsincomingmail'],
                       OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                    ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
        self.assertEquals(highest_review_level('dmsincomingmail', "['111_n_plus_1']"), '_n_plus_1')

    def test_list_wf_states(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(list_wf_states(imail, 'unknown'), [])
        self.assertEqual([s_id for s_id, s_tit in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'])
        # We rename a state id
        states = imail.portal_workflow.task_workflow.states
        states.manage_renameObject('to_do', 'NEW')
        # use cache
        self.assertEqual([s_id for s_id, s_tit in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'])
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.task')
        # 'imio.dms.mail.utils.list_wf_states
        self.assertEqual([s_id for s_id, s_tit in list_wf_states(imail, 'task')],
                         ['created', 'to_assign', 'in_progress', 'realized', 'closed', 'NEW'])

    def test_back_or_again_state(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', assigned_user='agent',
                                         treating_groups=self.pgof['direction-generale']['secretariat'].UID(),
                                         title='test')
        self.assertEqual(back_or_again_state(imail), '')  # initial state: no action
        api.content.transition(obj=imail, transition='propose_to_manager')
        self.assertEqual(back_or_again_state(imail), '')  # second state: empty
        api.content.transition(obj=imail, transition='propose_to_agent')
        self.assertEqual(back_or_again_state(imail), '')  # third state: empty
        api.content.transition(obj=imail, transition='back_to_manager')
        self.assertEqual(back_or_again_state(imail), 'back')  # we have a back action starting with back_
        api.content.transition(obj=imail, transition='back_to_creation')
        self.assertEqual(back_or_again_state(imail), 'back')  # we have a back action starting with back_
        self.assertEqual(back_or_again_state(imail, transitions=['back_to_creation']),
                         'back')  # we have a back action found in transitions parameter
        api.content.transition(obj=imail, transition='propose_to_agent')
        self.assertEqual(back_or_again_state(imail), 'again')  # third state again

    def test_get_scan_id(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', scan_id=u'010999900000690')
        self.assertListEqual(get_scan_id(obj), [u'010999900000690', u'IMIO010999900000690', u'690'])

    def test_UtilsMethods_current_user_groups_ids(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = UtilsMethods(imail, imail.REQUEST)
        login(self.portal, 'dirg')
        self.assertSetEqual(set(view.current_user_groups_ids(api.user.get_current())),
                            {'AuthenticatedUsers', 'createurs_dossier', 'dir_general'})

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
        self.assertFalse(view.is_in_user_groups(groups=['abc'], admin=False, suffixes=['general']))
        # current user is not Manager
        login(self.portal, 'dirg')
        self.assertSetEqual(set(view.current_user_groups_ids(api.user.get_current())),
                            {'AuthenticatedUsers', 'createurs_dossier', 'dir_general'})
        # with groups
        self.assertFalse(view.is_in_user_groups(groups=['abc']))
        self.assertTrue(view.is_in_user_groups(groups=['abc', 'dir_general']))
        self.assertFalse(view.is_in_user_groups(groups=['abc', 'dir_general'], test='all'))
        self.assertTrue(view.is_in_user_groups(groups=['AuthenticatedUsers', 'dir_general'], test='all'))
        self.assertFalse(view.is_in_user_groups(groups=['dir_general'], test='other'))
        # with suffixes
        self.assertTrue(view.is_in_user_groups(suffixes=['general']))
        self.assertTrue(view.is_in_user_groups(groups=['abc'], suffixes=['general']))
        self.assertFalse(view.is_in_user_groups(groups=['abc'], suffixes=['general'], test='all'))
        self.assertTrue(view.is_in_user_groups(groups=['AuthenticatedUsers'], suffixes=['general'], test='all'))
        # with org_uid, but without suffixes: not considered
        self.assertFalse(view.is_in_user_groups(groups=['abc'], org_uid='dir'))
        self.assertTrue(view.is_in_user_groups(groups=['abc', 'dir_general'], org_uid='dir'))
        self.assertFalse(view.is_in_user_groups(groups=['abc', 'dir_general'], test='all', org_uid='dir'))
        self.assertFalse(view.is_in_user_groups(groups=['dir_general'], test='other', org_uid='dir'))
        # with org_uid and suffixes
        self.assertTrue(view.is_in_user_groups(suffixes=['general'], org_uid='dir'))
        self.assertFalse(view.is_in_user_groups(suffixes=['general'], org_uid='wrong'))
        self.assertTrue(view.is_in_user_groups(groups=['abc'], suffixes=['general'], org_uid='dir'))
        self.assertFalse(view.is_in_user_groups(groups=['abc'], suffixes=['general'], org_uid='wrong'))
        self.assertTrue(view.is_in_user_groups(groups=['dir_general'], suffixes=['general'], org_uid='wrong'))
        self.assertFalse(view.is_in_user_groups(groups=['abc'], test='all', suffixes=['general'], org_uid='dir'))
        self.assertTrue(view.is_in_user_groups(groups=['dir_general'], test='all', suffixes=['general'], org_uid='dir'))
        logout()
        login(self.portal, 'agent')
        self.assertFalse(view.is_in_user_groups(suffixes=['general'], org_uid='dir'))
        self.assertTrue(view.is_in_user_groups(suffixes=['general'], org_uid='dir', user=api.user.get('dirg')))

    def test_IdmUtilsMethods_get_im_folder(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.get_im_folder(), self.portal['incoming-mail'])

    def test_IdmUtilsMethods_user_has_review_level(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.user_has_review_level())
        self.assertFalse(view.user_has_review_level('dmsincomingmail'))
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        set_dms_config(['review_levels', 'dmsincomingmail'],
                       OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                    ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
        self.assertTrue(view.user_has_review_level('dmsincomingmail'))
        api.group.remove_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        self.assertFalse(view.user_has_review_level('dmsincomingmail'))
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertTrue(view.user_has_review_level('dmsincomingmail'))

    def test_IdmUtilsMethods_can_do_transition0(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(api.content.get_state(imail), 'created')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        # no treating_group nor title: NOK
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        imail.title = u'test'
        # tg ok, state ok, assigner_user nok but auc ok: OK
        imail.treating_groups = get_registry_organizations()[0]
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user nok, auc nok: NOK
        setRoles(self.portal, TEST_USER_ID, ['Reviewer'])
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user nok, auc ok: OK
        api.portal.set_registry_record(AUC_RECORD, 'no_check')
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user ok, auc nok: OK
        imail.assigned_user = 'chef'
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # WE DO TRANSITION
        api.content.transition(imail, 'propose_to_agent')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_agent')
        # tg ok, state ok, (assigner_user nok, auc nok): OK
        imail.assigned_user = None
        self.assertTrue(view.can_do_transition('back_to_creation'))
        self.assertTrue(view.can_do_transition('back_to_manager'))
        self.assertFalse(view.can_do_transition('unknown'))

    def test_IdmUtilsMethods_can_close(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', title=u'test')
        self.assertEqual(api.content.get_state(imail), 'created')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        imail.treating_groups = get_registry_organizations()[0]  # direction-generale
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        api.content.transition(imail, 'propose_to_agent')
        login(self.portal, 'agent')
        self.assertIsNone(imail.sender)
        self.assertIsNone(imail.mail_type)
        self.assertFalse(view.can_close())
        intids = getUtility(IIntIds)
        imail.sender = [RelationValue(intids.getId(self.portal.contacts['electrabel']))]
        imail.mail_type = u'courrier'
        self.assertFalse(view.can_close())  # not part of treating group editors
        api.group.add_user(groupname='{}_editeur'.format(imail.treating_groups), username='agent')
        self.assertTrue(view.can_close())

    def test_IdmUtilsMethods_created_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.created_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.created_col_cond())
        login(self.portal, 'agent')
        self.assertFalse(view.created_col_cond())
        api.group.add_user(groupname='abc_group_encoder', username='agent')
        self.assertTrue(view.created_col_cond())

    def test_IdmUtilsMethods_proposed_to_manager_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_manager_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.proposed_to_manager_col_cond())
        login(self.portal, 'agent')
        self.assertFalse(view.proposed_to_manager_col_cond())
        api.group.add_user(groupname='abc_group_encoder', username='agent')
        self.assertTrue(view.proposed_to_manager_col_cond())
        login(self.portal, 'dirg')
        self.assertTrue(view.proposed_to_manager_col_cond())

    def test_IdmUtilsMethods_proposed_to_premanager_col_cond(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        login(self.portal, 'agent')
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        api.group.add_user(groupname='abc_group_encoder', username='agent')
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        login(self.portal, 'dirg')
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        login(self.portal, 'agent1')
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        api.group.create('pre_manager', 'Pre manager')
        api.group.add_user(groupname='pre_manager', username='agent1')
        self.assertTrue(view.proposed_to_pre_manager_col_cond())

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond0(self):
        im_folder = self.portal['incoming-mail']['mail-searches']
        self.assertFalse('searchfor_proposed_to_n_plus_1' in im_folder)
        self.assertTrue('See test_wfadaptations_imservicevalidation.py')

    def test_OdmUtilsMethods_can_be_handsigned(self):
        omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail')
        self.assertEqual(api.content.get_state(omail), 'created')
        view = OdmUtilsMethods(omail, omail.REQUEST)
        self.assertFalse(view.can_be_handsigned())
        createContentInContainer(omail, 'task')
        self.assertFalse(view.can_be_handsigned())
        createContentInContainer(omail, 'dmsappendixfile')
        self.assertFalse(view.can_be_handsigned())
        createContentInContainer(omail, 'dmsommainfile')
        self.assertTrue(view.can_be_handsigned())

    def test_OdmUtilsMethods_can_be_sent(self):
        omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail', title=u'test')
        self.assertEqual(api.content.get_state(omail), 'created')
        view = OdmUtilsMethods(omail, omail.REQUEST)
        # no treating_groups
        self.assertFalse(view.can_be_sent())
        omail.treating_groups = get_registry_organizations()[0]  # direction-generale
        # admin
        self.assertTrue(view.can_be_sent())
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        # define as email
        omail.send_modes = [u'email']
        self.assertTrue(omail.is_email())
        self.assertFalse(view.can_be_sent())
        omail.email_status = u'sent at ...'
        self.assertTrue(view.can_be_sent())
        # define as normal mail
        omail.send_modes = [u'post']
        self.assertFalse(omail.is_email())
        self.assertFalse(view.can_be_sent())
        createContentInContainer(omail, 'dmsommainfile')
        self.assertTrue(view.can_be_sent())
