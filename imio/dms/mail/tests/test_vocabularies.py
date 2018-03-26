# -*- coding: utf-8 -*-
import unittest
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID, login, logout
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.helpers.cache import invalidate_cachekey_volatile_for

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..vocabularies import (IMReviewStatesVocabulary, TaskReviewStatesVocabulary, AssignedUsersVocabulary,
                            getMailTypes, PloneGroupInterfacesVocabulary, OMSenderVocabulary, OMMailTypesVocabulary,
                            OMActiveMailTypesVocabulary, encodeur_active_orgs, EmptyAssignedUsersVocabulary)
from .. import EMPTY_STRING


class TestVocabularies(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail')

    def test_IMReviewStatesVocabulary(self):
        voc_inst = IMReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'En création'), ('proposed_to_manager', u'À valider par le DG'),
                                    ('proposed_to_service_chief', u'À valider par le chef de service'),
                                    ('proposed_to_agent', u'À traiter'), ('in_treatment', u'En cours de traitement'),
                                    ('closed', u'Clôturé')])

    def test_TaskReviewStatesVocabulary(self):
        voc_inst = TaskReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'Created'), ('to_assign', u'To assign'), ('to_do', u'To do'),
                                    ('in_progress', u'In progress'), ('realized', u'Realized'),
                                    ('closed', u'Closed')])

    def test_AssignedUsersVocabulary(self):
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef'),
                                                ('agent1', 'Stef Agent')]))

    def test_EmptyAssignedUsersVocabulary(self):
        voc_inst = EmptyAssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([(EMPTY_STRING, 'Empty value'), ('agent', 'Fred Agent'),
                                                ('chef', 'Michel Chef'), ('agent1', 'Stef Agent')]))

    def test_getMailTypes(self):
        voc_list = [(t.value, t.title) for t in getMailTypes()]
        self.assertEquals(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommandé'), (u'email', u'E-mail'),
                                     (u'fax', u'Fax'), (u'retour-recommande', u'Retour recommandé'),
                                     (u'facture', u'Facture')])

    def test_IMMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommandé'),
                                        (u'email', u'E-mail'), (u'fax', u'Fax'),
                                        (u'retour-recommande', u'Retour recommandé'), (u'facture', u'Facture')])

    def test_IMActiveMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMActiveMailTypesVocabulary')
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'courrier', u'recommande', u'email', u'fax', u'retour-recommande',
                                        u'facture'])
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]['mt_active'] = False
        settings.mail_types = mail_types
        # After a registry change, the vocabulary cache has been cleared
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'recommande', u'email', u'fax', u'retour-recommande', u'facture'])

    def test_PloneGroupInterfacesVocabulary(self):
        voc_inst = PloneGroupInterfacesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [('collective.contact.plonegroup.interfaces.IPloneGroupContact',
                                         'IPloneGroupContact'),
                                        ('collective.contact.plonegroup.interfaces.INotPloneGroupContact',
                                         'INotPloneGroupContact'),
                                        ('imio.dms.mail.interfaces.IPersonnelContact',
                                         'IPersonnelContact')])

    def test_OMSenderVocabulary(self):
        voc_inst = OMSenderVocabulary()
        self.assertEqual(len(voc_inst(self.omail)), 6)
        self.assertEqual([s.title for s in voc_inst(self.omail)],
                         [u'Monsieur Fred Agent (Direction générale / GRH, Agent GRH)',
                          u'Monsieur Fred Agent (Direction générale / Secrétariat, Agent secrétariat)',
                          u'Monsieur Maxime DG (Direction générale / GRH, Directeur du personnel)',
                          u'Monsieur Maxime DG (Direction générale, Directeur général)',
                          u'Monsieur Michel Chef (Direction générale / GRH, Responsable GRH)',
                          u'Monsieur Michel Chef (Direction générale / Secrétariat, Responsable secrétariat)'])
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                       'omail_sender_firstname_sorting', False)
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')
        self.assertEqual([s.title for s in voc_inst(self.omail)],
                         [u'Monsieur Fred Agent (Direction générale / GRH, Agent GRH)',
                          u'Monsieur Fred Agent (Direction générale / Secrétariat, Agent secrétariat)',
                          u'Monsieur Michel Chef (Direction générale / GRH, Responsable GRH)',
                          u'Monsieur Michel Chef (Direction générale / Secrétariat, Responsable secrétariat)',
                          u'Monsieur Maxime DG (Direction générale / GRH, Directeur du personnel)',
                          u'Monsieur Maxime DG (Direction générale, Directeur général)'])

    def test_OMMailTypesVocabulary(self):
        voc_inst = OMMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u'courrier', u'recommande'])

    def test_OMActiveMailTypesVocabulary(self):
        voc_inst = OMActiveMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u'courrier', u'recommande'])

    def test_encodeur_active_orgs(self):
        factory = getUtility(IVocabularyFactory, u'collective.dms.basecontent.treating_groups')
        all_titles = [t.title for t in factory(self.omail)]
        login(self.portal, 'encodeur')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
        logout()
        login(self.portal, 'agent')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)],
                             [t for i, t in enumerate(all_titles) if i not in (0, 4, 7)])
        with api.env.adopt_roles(['Manager']):
            api.content.transition(obj=self.omail, transition='propose_to_service_chief')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
