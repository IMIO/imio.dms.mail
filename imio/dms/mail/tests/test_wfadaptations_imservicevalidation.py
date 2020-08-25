# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.wfadaptations.api import add_applied_adaptation
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.wfadaptations import IMServiceValidation
from plone import api
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContentInContainer
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestIMServiceValidation1(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.imw = self.pw['incomingmail_workflow']
        api.group.create('abc_group_encoder', 'ABC group encoder')
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-apply_n_plus_1_wfadaptation',
                                                          run_dependencies=False)

    def test_im_workflow1(self):
        """ Check workflow """
        self.assertSetEqual(set(self.imw.states),
                            {'created', 'proposed_to_manager', 'proposed_to_n_plus_1', 'proposed_to_agent',
                             'in_treatment', 'closed'})
        self.assertSetEqual(set(self.imw.transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_n_plus_1', 'back_to_agent',
                             'back_to_treatment', 'propose_to_manager', 'propose_to_n_plus_1', 'propose_to_agent',
                             'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['created'].transitions),
                            {'propose_to_manager', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_manager'].transitions),
                            {'back_to_creation', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_n_plus_1'].transitions),
                            {'back_to_creation', 'back_to_manager', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_agent'].transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_n_plus_1', 'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['in_treatment'].transitions),
                            {'back_to_agent', 'close'})
        self.assertSetEqual(set(self.imw.states['closed'].transitions),
                            {'back_to_treatment', 'back_to_agent'})

    def test_IMServiceValidation1(self):
        """
            Test IMServiceValidation adaptations
        """
        # is function added
        self.assertIn('n_plus_1', [fct['fct_id'] for fct in get_registry_functions()])
        # is local roles modified
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('proposed_to_n_plus_1', lr['static_config'])
        self.assertIn('proposed_to_n_plus_1', lr['treating_groups'])
        self.assertIn('proposed_to_n_plus_1', lr['recipient_groups'])
        # check collection
        folder = self.portal['incoming-mail']['mail-searches']
        self.assertIn('searchfor_proposed_to_n_plus_1', folder)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_agent'), 13)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_n_plus_1'), 12)
        self.assertFalse(folder['to_treat_in_my_group'].showNumberOfItems)
        # check annotations
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        self.assertIn('_n_plus_1', config)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        self.assertIn('proposed_to_n_plus_1', config)
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertIn('propose_to_n_plus_1', config)
        config = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        self.assertEqual(config['proposed_to_manager'].values()[0][0], 'propose_to_n_plus_1')
        self.assertEqual(config['proposed_to_agent'].values()[0][1], 'back_to_n_plus_1')
        # check vocabularies
        factory = getUtility(IVocabularyFactory, u'collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        self.assertEqual(len(factory(folder, folder)), 16)
        factory = getUtility(IVocabularyFactory, u'imio.dms.mail.IMReviewStatesVocabulary')
        self.assertEqual(len(factory(folder)), 6)
        # check configuration
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        self.assertIn('dmsincomingmail.back_to_n_plus_1|', lst)
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states')
        self.assertIn('proposed_to_n_plus_1', lst)

    def test_IdmUtilsMethods_can_do_transition1(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(api.content.get_state(imail), 'created')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        setRoles(self.portal, TEST_USER_ID, ['Reviewer'])
        # no treating_group: NOK
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, following states
        imail.treating_groups = get_registry_organizations()[0]
        api.portal.set_registry_record(AUC_RECORD, 'no_check')
        self.assertFalse(view.can_do_transition('propose_to_agent'))  # has higher level
        self.assertTrue(view.can_do_transition('propose_to_n_plus_1'))
        # tg ok, following states: no more n_plus_1 user
        groupname = '{}_n_plus_1'.format(imail.treating_groups)
        api.group.remove_user(groupname=groupname, username='chef')
        self.assertFalse(group_has_user(groupname))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))  # no user
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # tg ok, assigner_user nok, auc ok
        api.portal.set_registry_record(AUC_RECORD, 'n_plus_1')
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))  # no user
        self.assertTrue(view.can_do_transition('propose_to_agent'))  # ok because no n+1 level
        # tg ok, assigner_user nok, auc nok
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user ok, auc nok
        imail.assigned_user = 'chef'
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname, username='chef')
        api.content.transition(imail, 'propose_to_n_plus_1')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_n_plus_1')
        # tg ok, state ok, assigner_user nok, auc nok
        imail.assigned_user = None
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        self.assertTrue(view.can_do_transition('back_to_creation'))
        self.assertTrue(view.can_do_transition('back_to_manager'))
        self.assertFalse(view.can_do_transition('unknown'))
        # WE DO TRANSITION
        imail.assigned_user = 'chef'
        api.content.transition(imail, 'propose_to_agent')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_agent')
        self.assertTrue(view.can_do_transition('back_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('back_to_creation'))
        self.assertFalse(view.can_do_transition('back_to_manager'))
        # we remove n+1 users
        api.group.remove_user(groupname=groupname, username='chef')
        self.assertFalse(view.can_do_transition('back_to_n_plus_1'))
        self.assertTrue(view.can_do_transition('back_to_creation'))
        self.assertTrue(view.can_do_transition('back_to_manager'))

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond1(self):
        folder = self.portal['incoming-mail']['mail-searches']
        col = folder['searchfor_proposed_to_n_plus_1']
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


class TestIMServiceValidation2(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.imw = self.pw['incomingmail_workflow']
        api.group.create('abc_group_encoder', 'ABC group encoder')
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-apply_n_plus_1_wfadaptation',
                                                          run_dependencies=False)
        sva = IMServiceValidation()
        n_plus_2_params = {'validation_level': 2,
                           'state_title': u'Valider par le chef de département',
                           'forward_transition_title': u'Proposer au chef de département',
                           'backward_transition_title': u'Renvoyer au chef de département',
                           'function_title': u'chef de département'}
        adapt_is_applied = sva.patch_workflow('incomingmail_workflow', **n_plus_2_params)
        if adapt_is_applied:
            add_applied_adaptation('imio.dms.mail.wfadaptations.IMServiceValidation',
                                   'incomingmail_workflow', True, **n_plus_2_params)
        for uid in get_registry_organizations():
            self.portal.acl_users.source_groups.addPrincipalToGroup('chef', "%s_n_plus_2" % uid)

    def test_im_workflow2(self):
        """ Check workflow """
        self.assertSetEqual(set(self.imw.states),
                            {'created', 'proposed_to_manager', 'proposed_to_n_plus_2', 'proposed_to_n_plus_1',
                             'proposed_to_agent', 'in_treatment', 'closed'})
        self.assertSetEqual(set(self.imw.transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_n_plus_2', 'back_to_n_plus_1',
                             'back_to_agent', 'back_to_treatment', 'propose_to_manager', 'propose_to_n_plus_2',
                             'propose_to_n_plus_1', 'propose_to_agent', 'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['created'].transitions),
                            {'propose_to_manager', 'propose_to_n_plus_2', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_manager'].transitions),
                            {'back_to_creation', 'propose_to_n_plus_2', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_n_plus_2'].transitions),
                            {'back_to_creation', 'back_to_manager', 'propose_to_n_plus_1', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_n_plus_1'].transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_n_plus_2', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_agent'].transitions),
                            {'back_to_creation', 'back_to_manager', 'back_to_n_plus_2', 'back_to_n_plus_1', 'treat',
                             'close'})
        self.assertSetEqual(set(self.imw.states['in_treatment'].transitions),
                            {'back_to_agent', 'close'})
        self.assertSetEqual(set(self.imw.states['closed'].transitions),
                            {'back_to_treatment', 'back_to_agent'})

    def test_IMServiceValidation2(self):
        """
            Test IMServiceValidation adaptations
        """
        # is function added
        self.assertIn('n_plus_2', [fct['fct_id'] for fct in get_registry_functions()])
        # is local roles modified
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('proposed_to_n_plus_2', lr['static_config'])
        self.assertIn('proposed_to_n_plus_2', lr['treating_groups'])
        self.assertIn('proposed_to_n_plus_2', lr['recipient_groups'])
        # check collection
        folder = self.portal['incoming-mail']['mail-searches']
        self.assertIn('searchfor_proposed_to_n_plus_2', folder)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_agent'), 14)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_n_plus_1'), 13)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_n_plus_2'), 12)
        self.assertFalse(folder['to_treat_in_my_group'].showNumberOfItems)
        # check annotations
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        self.assertIn('_n_plus_2', config)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        self.assertIn('proposed_to_n_plus_2', config)
        config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
        self.assertIn('propose_to_n_plus_2', config)
        self.assertTrue(all(config['propose_to_n_plus_2'].values()))  # all is True
        self.assertTrue(all(config['propose_to_n_plus_1'].values()))  # all is True
        self.assertFalse(any(config['propose_to_agent'].values()))  # all is False
        config = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        self.assertEqual(config['proposed_to_manager'].values()[0][0], 'propose_to_n_plus_2')
        self.assertEqual(config['proposed_to_n_plus_2'].values()[0][0], 'propose_to_n_plus_1')
        self.assertEqual(config['proposed_to_n_plus_1'].values()[0][1], 'back_to_n_plus_2')
        self.assertEqual(config['proposed_to_agent'].values()[0][1], 'back_to_n_plus_1')
        # check vocabularies
        factory = getUtility(IVocabularyFactory, u'collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        self.assertEqual(len(factory(folder, folder)), 17)
        factory = getUtility(IVocabularyFactory, u'imio.dms.mail.IMReviewStatesVocabulary')
        self.assertEqual(len(factory(folder)), 7)
        # check configuration
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        self.assertIn('dmsincomingmail.back_to_n_plus_2|', lst)
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states')
        self.assertIn('proposed_to_n_plus_2', lst)

    def test_IdmUtilsMethods_can_do_transition2(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.assertEqual(api.content.get_state(imail), 'created')
        view = IdmUtilsMethods(imail, imail.REQUEST)
        setRoles(self.portal, TEST_USER_ID, ['Reviewer'])
        # no treating_group: NOK
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, following states
        imail.treating_groups = get_registry_organizations()[0]
        api.portal.set_registry_record(AUC_RECORD, 'no_check')
        self.assertTrue(view.can_do_transition('propose_to_n_plus_2'))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, following states: no more n_plus_ user
        groupname2 = '{}_n_plus_2'.format(imail.treating_groups)
        api.group.remove_user(groupname=groupname2, username='chef')
        self.assertFalse(group_has_user(groupname2))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_2'))
        self.assertTrue(view.can_do_transition('propose_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        groupname1 = '{}_n_plus_1'.format(imail.treating_groups)
        api.group.remove_user(groupname=groupname1, username='chef')
        self.assertFalse(group_has_user(groupname1))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_2'))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # tg ok, assigner_user nok, auc ok
        api.portal.set_registry_record(AUC_RECORD, 'n_plus_1')
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))  # no user
        self.assertTrue(view.can_do_transition('propose_to_agent'))  # ok because no n+1 level
        # tg ok, assigner_user nok, auc nok
        api.portal.set_registry_record(AUC_RECORD, 'mandatory')
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        # tg ok, state ok, assigner_user ok, auc nok
        imail.assigned_user = 'chef'
        self.assertTrue(view.can_do_transition('propose_to_agent'))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname2, username='chef')
        api.content.transition(imail, 'propose_to_n_plus_2')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_n_plus_2')
        # tg ok, state ok, assigner_user nok, auc nok
        imail.assigned_user = None
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        self.assertTrue(view.can_do_transition('back_to_creation'))
        self.assertTrue(view.can_do_transition('back_to_manager'))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname1, username='chef')
        api.content.transition(imail, 'propose_to_n_plus_1')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_n_plus_1')
        self.assertFalse(view.can_do_transition('propose_to_agent'))
        self.assertTrue(view.can_do_transition('back_to_n_plus_2'))
        self.assertFalse(view.can_do_transition('back_to_creation'))
        self.assertFalse(view.can_do_transition('back_to_manager'))
        # we remove n+2 users
        api.group.remove_user(groupname=groupname2, username='chef')
        self.assertFalse(view.can_do_transition('back_to_n_plus_2'))
        self.assertTrue(view.can_do_transition('back_to_creation'))
        self.assertTrue(view.can_do_transition('back_to_manager'))
        # WE DO TRANSITION
        imail.assigned_user = 'chef'
        api.content.transition(imail, 'propose_to_agent')
        self.assertEqual(api.content.get_state(imail), 'proposed_to_agent')
        self.assertTrue(view.can_do_transition('back_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('back_to_n_plus_2'))
        self.assertFalse(view.can_do_transition('back_to_creation'))
        self.assertFalse(view.can_do_transition('back_to_manager'))
        # we remove n+1 users
        api.group.remove_user(groupname=groupname1, username='chef')
        api.group.add_user(groupname=groupname2, username='chef')
        self.assertTrue(view.can_do_transition('back_to_n_plus_2'))
        self.assertFalse(view.can_do_transition('back_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('back_to_creation'))
        self.assertFalse(view.can_do_transition('back_to_manager'))

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond2(self):
        folder = self.portal['incoming-mail']['mail-searches']
        col1 = folder['searchfor_proposed_to_n_plus_1']
        n_plus_1_view = IdmUtilsMethods(col1, col1.REQUEST)
        col2 = folder['searchfor_proposed_to_n_plus_2']
        n_plus_2_view = IdmUtilsMethods(col2, col2.REQUEST)
        self.assertFalse(n_plus_2_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'encodeur')
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'agent')
        self.assertFalse(n_plus_2_view.proposed_to_n_plus_col_cond())
        api.group.add_user(groupname='abc_group_encoder', username='agent')
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        api.group.remove_user(groupname='abc_group_encoder', username='agent')
        login(self.portal, 'dirg')
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        login(self.portal, 'chef')
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        # Set N+2 to user, have to get an organization UID first
        contacts = self.portal['contacts']
        own_orga = contacts['plonegroup-organization']
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        self.portal.acl_users.source_groups.addPrincipalToGroup('agent1', "%s_n_plus_2" % departments[5].UID())
        login(self.portal, 'agent1')
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())  # can view lower level collection
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
