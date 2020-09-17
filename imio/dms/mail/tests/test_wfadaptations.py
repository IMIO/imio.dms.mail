# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.wfadaptations.api import add_applied_adaptation
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import OdmUtilsMethods
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import TaskUtilsMethods
from imio.dms.mail.vocabularies import encodeur_active_orgs
from imio.dms.mail.wfadaptations import IMPreManagerValidation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import TaskServiceValidation
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContentInContainer
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestOMToPrintAdaptation(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.omw = self.pw['outgoingmail_workflow']

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_OMToPrintAdaptation(self):
        """ Test wf adaptation modifications """
        tpa = OMToPrintAdaptation()
        tpa.patch_workflow('outgoingmail_workflow')
        # check workflow
        self.assertSetEqual(set(self.omw.states),
                            {'created', 'scanned', 'to_print', 'to_be_signed', 'sent'})
        self.assertSetEqual(set(self.omw.transitions),
                            {'back_to_creation', 'back_to_agent', 'back_to_scanned', 'back_to_print',
                             'back_to_be_signed', 'set_scanned', 'set_to_print', 'propose_to_be_signed',
                             'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['created'].transitions),
                            {'set_scanned', 'set_to_print', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['scanned'].transitions),
                            {'back_to_agent', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['to_print'].transitions),
                            {'back_to_creation', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['to_be_signed'].transitions),
                            {'back_to_creation', 'back_to_print', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['sent'].transitions),
                            {'back_to_be_signed', 'back_to_scanned'})
        # various
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('to_print', lr['static_config'])
        self.assertIn('to_print', lr['treating_groups'])
        self.assertIn('to_print', lr['recipient_groups'])
        self.assertIn('searchfor_to_print', self.portal['outgoing-mail']['mail-searches'])
        folder = self.portal['outgoing-mail']['mail-searches']
        self.assertIn('to_print', [dic['v'] for dic in folder['om_treating'].query if dic['i'] == 'review_state'][0])
        self.assertEqual(folder.getObjectPosition('searchfor_to_be_signed'), 10)
        self.assertEqual(folder.getObjectPosition('searchfor_to_print'), 9)
        factory = getUtility(IVocabularyFactory, u'imio.dms.mail.OMReviewStatesVocabulary')
        self.assertEqual(len(factory(self.portal)), 5)

    def common_tests(self):
        # check workflow
        self.assertSetEqual(set(self.omw.states),
                            {'created', 'scanned', 'proposed_to_n_plus_1', 'to_print', 'to_be_signed', 'sent'})
        self.assertSetEqual(set(self.omw.transitions),
                            {'back_to_creation', 'back_to_agent', 'back_to_scanned', 'back_to_n_plus_1',
                             'back_to_print', 'back_to_be_signed', 'set_scanned', 'propose_to_n_plus_1', 'set_to_print',
                             'propose_to_be_signed', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['created'].transitions),
                            {'set_scanned', 'propose_to_n_plus_1', 'set_to_print', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['scanned'].transitions),
                            {'back_to_agent', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['proposed_to_n_plus_1'].transitions),
                            {'back_to_creation', 'set_to_print', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['to_print'].transitions),
                            {'back_to_creation', 'back_to_n_plus_1', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['to_be_signed'].transitions),
                            {'back_to_creation', 'back_to_n_plus_1', 'back_to_print', 'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['sent'].transitions),
                            {'back_to_be_signed', 'back_to_scanned'})
        # check collection position
        folder = self.portal['outgoing-mail']['mail-searches']
        self.assertEqual(folder.getObjectPosition('searchfor_to_be_signed'), 11)
        self.assertEqual(folder.getObjectPosition('searchfor_to_print'), 10)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_n_plus_1'), 9)
        res = [dic['v'] for dic in folder['om_treating'].query if dic['i'] == 'review_state'][0]
        self.assertIn('to_print', res)
        self.assertIn('proposed_to_n_plus_1', res)

    def test_OMToPrintAdaptationBeforeNp1(self):
        """ Test wf adaptation modifications """
        tpa = OMToPrintAdaptation()
        tpa.patch_workflow('outgoingmail_workflow')
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-om_n_plus_1_wfadaptation',
                                                          run_dependencies=False)
        self.common_tests()

    def test_OMToPrintAdaptationAfterNp1(self):
        """ Test wf adaptation modifications """
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-om_n_plus_1_wfadaptation',
                                                          run_dependencies=False)
        tpa = OMToPrintAdaptation()
        tpa.patch_workflow('outgoingmail_workflow')
        self.common_tests()


class TestOMServiceValidation1(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.omw = self.pw['outgoingmail_workflow']
        api.group.create('abc_group_encoder', 'ABC group encoder')
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-om_n_plus_1_wfadaptation',
                                                          run_dependencies=False)
        self.omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail')

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_om_workflow1(self):
        """ Check workflow """
        self.assertSetEqual(set(self.omw.states),
                            {'created', 'scanned', 'proposed_to_n_plus_1', 'to_be_signed', 'sent'})
        self.assertSetEqual(set(self.omw.transitions),
                            {'back_to_creation', 'back_to_agent', 'back_to_scanned', 'back_to_n_plus_1',
                             'back_to_be_signed', 'propose_to_n_plus_1', 'set_scanned', 'propose_to_be_signed',
                             'mark_as_sent'})
        self.assertSetEqual(set(self.omw.states['created'].transitions),
                            {'set_scanned', 'propose_to_n_plus_1', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['scanned'].transitions),
                            {'mark_as_sent', 'back_to_agent'})
        self.assertSetEqual(set(self.omw.states['proposed_to_n_plus_1'].transitions),
                            {'back_to_creation', 'propose_to_be_signed'})
        self.assertSetEqual(set(self.omw.states['to_be_signed'].transitions),
                            {'mark_as_sent', 'back_to_n_plus_1', 'back_to_creation'})
        self.assertSetEqual(set(self.omw.states['sent'].transitions),
                            {'back_to_be_signed', 'back_to_scanned'})

    def test_OMServiceValidation1(self):
        """
            Test OMServiceValidation adaptations
        """
        # is function added
        self.assertIn('n_plus_1', [fct['fct_id'] for fct in get_registry_functions()])
        # is local roles modified
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('proposed_to_n_plus_1', lr['treating_groups'])
        self.assertIn('proposed_to_n_plus_1', lr['recipient_groups'])
        # check collection
        folder = self.portal['outgoing-mail']['mail-searches']
        self.assertIn('searchfor_proposed_to_n_plus_1', folder)
        self.assertEqual(folder.getObjectPosition('searchfor_to_be_signed'), 10)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_n_plus_1'), 9)
        self.assertIn('proposed_to_n_plus_1',
                      [dic['v'] for dic in folder['om_treating'].query if dic['i'] == 'review_state'][0])
        self.assertTrue(folder['to_validate'].enabled)
        # check annotations
        config = get_dms_config(['review_levels', 'dmsoutgoingmail'])
        self.assertIn('_n_plus_1', config)
        config = get_dms_config(['review_states', 'dmsoutgoingmail'])
        self.assertIn('proposed_to_n_plus_1', config)
        # check vocabularies
        factory = getUtility(IVocabularyFactory, u'collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        self.assertEqual(len(factory(folder, folder)), 12)
        factory = getUtility(IVocabularyFactory, u'imio.dms.mail.OMReviewStatesVocabulary')
        self.assertEqual(len(factory(folder)), 5)
        # check configuration
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        self.assertIn('dmsoutgoingmail.back_to_n_plus_1|', lst)
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states')
        self.assertIn('proposed_to_n_plus_1', lst)

    def test_OdmUtilsMethods_can_do_transition1(self):
        # self.assertEqual(api.content.get_state(self.omail), 'created')
        view = OdmUtilsMethods(self.omail, self.omail.REQUEST)
        setRoles(self.portal, TEST_USER_ID, ['Reviewer', 'Manager'])
        # no treating_groups: NOK
        self.assertIsNone(self.omail.treating_groups)
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))
        self.assertFalse(view.can_do_transition('back_to_n_plus_1'))
        # tg ok, no user in group
        self.omail.treating_groups = get_registry_organizations()[0]
        groupname = '{}_n_plus_1'.format(self.omail.treating_groups)
        api.group.remove_user(groupname=groupname, username='chef')
        self.assertFalse(group_has_user(groupname))
        self.assertFalse(view.can_do_transition('propose_to_n_plus_1'))
        # tg ok, user in group
        api.group.add_user(groupname=groupname, username='chef')
        self.assertTrue(group_has_user(groupname))
        self.assertTrue(view.can_do_transition('propose_to_n_plus_1'))
        # we do transition
        api.content.transition(self.omail, transition='propose_to_n_plus_1')
        api.content.transition(self.omail, transition='propose_to_be_signed')
        self.assertEqual(api.content.get_state(self.omail), 'to_be_signed')
        # tg ok, user in group
        self.assertTrue(view.can_do_transition('back_to_n_plus_1'))
        # tg ok, no user in group
        api.group.remove_user(groupname=groupname, username='chef')
        self.assertFalse(group_has_user(groupname))
        self.assertFalse(view.can_do_transition('back_to_n_plus_1'))

    def test_encodeur_active_orgs1(self):
        factory = getUtility(IVocabularyFactory, u'collective.dms.basecontent.treating_groups')
        all_titles = [t.title for t in factory(self.omail)]
        login(self.portal, 'agent')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)],
                             [t for i, t in enumerate(all_titles) if i not in (0, 4, 7)])
        org1, org2 = get_registry_organizations()[0:2]
        with api.env.adopt_roles(['Manager']):
            self.omail.treating_groups = org2
            api.group.add_user(groupname='{}_n_plus_1'.format(org2), username=TEST_USER_ID)
            api.content.transition(obj=self.omail, transition='propose_to_n_plus_1')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)


class TestIMPreManagerValidation(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.imw = self.pw['incomingmail_workflow']
        params = {'state_title': u'À valider avant le DG',
                  'forward_transition_title': u'Proposer pour prévalidation DG',
                  'backward_transition_title': u'Renvoyer pour prévalidation DG'}
        pmva = IMPreManagerValidation()
        pmva.patch_workflow('incomingmail_workflow', **params)

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_IMPreManagerAdaptation(self):
        """ Test wf adaptation modifications """
        # check workflow
        self.assertSetEqual(set(self.imw.states),
                            {'created', 'proposed_to_pre_manager', 'proposed_to_manager', 'proposed_to_agent',
                             'in_treatment', 'closed'})
        self.assertSetEqual(set(self.imw.transitions),
                            {'back_to_creation', 'back_to_pre_manager', 'back_to_manager', 'back_to_agent',
                             'back_to_treatment', 'propose_to_pre_manager', 'propose_to_manager', 'propose_to_agent',
                             'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['created'].transitions),
                            {'propose_to_pre_manager', 'propose_to_manager', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_pre_manager'].transitions),
                            {'back_to_creation', 'propose_to_manager'})
        self.assertSetEqual(set(self.imw.states['proposed_to_manager'].transitions),
                            {'back_to_creation', 'back_to_pre_manager', 'propose_to_agent'})
        self.assertSetEqual(set(self.imw.states['proposed_to_agent'].transitions),
                            {'back_to_creation', 'back_to_manager', 'treat', 'close'})
        self.assertSetEqual(set(self.imw.states['in_treatment'].transitions),
                            {'back_to_agent', 'close'})
        self.assertSetEqual(set(self.imw.states['closed'].transitions),
                            {'back_to_treatment', 'back_to_agent'})
        # check local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        self.assertIn('proposed_to_pre_manager', lr['static_config'])
        # check collection
        folder = self.portal['incoming-mail']['mail-searches']
        self.assertIn('searchfor_proposed_to_pre_manager', folder)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_manager'), 12)
        self.assertEqual(folder.getObjectPosition('searchfor_proposed_to_pre_manager'), 11)
        # check annotations
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        self.assertIn('pre_manager', config)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        self.assertIn('proposed_to_pre_manager', config)
        # check voc
        factory = getUtility(IVocabularyFactory, u'imio.dms.mail.IMReviewStatesVocabulary')
        self.assertEqual(len(factory(self.portal)), 6)
        # check configuration
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        self.assertIn('dmsincomingmail.back_to_pre_manager|', lst)


class TestTaskServiceValidation1(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.tw = self.pw['task_workflow']
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                          'imiodmsmail-task_n_plus_1_wfadaptation',
                                                          run_dependencies=False)
        for uid in get_registry_organizations():
            groupname = "%s_n_plus_1" % uid
            if group_has_user(groupname):
                api.group.remove_user(groupname=groupname, username='chef')

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_task_workflow1(self):
        """ Check workflow """
        self.assertSetEqual(set(self.tw.states),
                            {'created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'})
        self.assertSetEqual(set(self.tw.transitions),
                            {'back_in_created', 'back_in_created2', 'back_in_to_assign', 'back_in_to_do',
                             'back_in_progress', 'back_in_realized', 'do_to_assign', 'auto_do_to_do', 'do_to_do',
                             'do_in_progress', 'do_realized', 'do_closed'})
        self.assertSetEqual(set(self.tw.states['created'].transitions),
                            {'do_to_assign'})
        self.assertSetEqual(set(self.tw.states['to_assign'].transitions),
                            {'back_in_created', 'auto_do_to_do', 'do_to_do'})
        self.assertSetEqual(set(self.tw.states['to_do'].transitions),
                            {'back_in_created2', 'back_in_to_assign', 'do_in_progress', 'do_realized'})
        self.assertSetEqual(set(self.tw.states['in_progress'].transitions),
                            {'back_in_to_do', 'do_realized'})
        self.assertSetEqual(set(self.tw.states['realized'].transitions),
                            {'back_in_to_do', 'back_in_progress', 'do_closed'})
        self.assertSetEqual(set(self.tw.states['closed'].transitions),
                            {'back_in_realized'})
        self.assertIsNotNone(self.tw.transitions['back_in_created2'].getGuard().expr)
        self.assertIsNotNone(self.tw.transitions['back_in_to_assign'].getGuard().expr)

    def test_TaskServiceValidation1(self):
        """ Test TaskServiceValidation adaptations """
        # is function added
        self.assertIn('n_plus_1', [fct['fct_id'] for fct in get_registry_functions()])
        # is local roles modified
        fti = getUtility(IDexterityFTI, name='task')
        lr = getattr(fti, 'localroles')
        self.assertIn('n_plus_1', lr['assigned_group']['to_do'])
        self.assertIn('n_plus_1', lr['parents_assigned_groups']['to_do'])
        # check collection
        folder = self.portal['tasks']['task-searches']
        self.assertTrue(folder['to_assign'].enabled)
        self.assertTrue(folder['to_close'].enabled)
        self.assertFalse(folder['to_treat_in_my_group'].showNumberOfItems)
        # check annotations
        config = get_dms_config(['review_levels', 'task'])
        self.assertIn('_n_plus_1', config)
        config = get_dms_config(['review_states', 'task'])
        self.assertIn('to_assign', config)
        self.assertIn('realized', config)

    def test_TaskUtilsMethods_can_do_transition1(self):
        task = self.portal['incoming-mail']['courrier1']['tache1']
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_do')
        view = TaskUtilsMethods(task, task.REQUEST)
        setRoles(self.portal, TEST_USER_ID, ['Editor', 'Reviewer'])
        # no assigned_group: NOK
        task.assigned_group = None
        self.assertFalse(view.can_do_transition('back_in_created2'))
        self.assertFalse(view.can_do_transition('back_in_to_assign'))
        # ag ok, no user in group
        task.assigned_group = get_registry_organizations()[0]
        groupname = '{}_n_plus_1'.format(task.assigned_group)
        self.assertFalse(group_has_user(groupname))
        self.assertTrue(view.can_do_transition('back_in_created2'))
        self.assertFalse(view.can_do_transition('back_in_to_assign'))
        # ag ok, user in group
        api.group.add_user(groupname=groupname, username='chef')
        self.assertTrue(group_has_user(groupname))
        self.assertFalse(view.can_do_transition('back_in_created2'))
        self.assertTrue(view.can_do_transition('back_in_to_assign'))
        # we do transition
        api.content.transition(task, transition='back_in_to_assign')
        api.content.transition(task, transition='back_in_created')
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_assign')
