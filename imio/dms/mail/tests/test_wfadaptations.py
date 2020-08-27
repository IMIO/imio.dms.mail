# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from collective.contact.plonegroup.config import get_registry_functions
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.vocabularies import encodeur_active_orgs
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContentInContainer
from zope.component import getUtility

import unittest

from zope.schema.interfaces import IVocabularyFactory


class TestWFAdaptations(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pw = self.portal.portal_workflow
        self.omw = self.pw['outgoingmail_workflow']

    def tearDown(self):
        # the modified dmsconfig is kept globally
        set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], [('to_be_signed', 'propose_to_be_signed')])

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
        set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], [('to_be_signed', 'propose_to_be_signed')])

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

    def test_encodeur_active_orgs1(self):
        factory = getUtility(IVocabularyFactory, u'collective.dms.basecontent.treating_groups')
        all_titles = [t.title for t in factory(self.omail)]
        login(self.portal, 'agent')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)],
                             [t for i, t in enumerate(all_titles) if i not in (0, 4, 7)])
        with api.env.adopt_roles(['Manager']):
            api.content.transition(obj=self.omail, transition='propose_to_n_plus_1')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
