# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import EMPTY_STRING
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.browser.settings import configure_group_encoder
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
from imio.dms.mail.vocabularies import AssignedUsersVocabulary
from imio.dms.mail.vocabularies import CreatingGroupVocabulary
from imio.dms.mail.vocabularies import EmptyAssignedUsersVocabulary
from imio.dms.mail.vocabularies import encodeur_active_orgs
from imio.dms.mail.vocabularies import get_mail_types
from imio.dms.mail.vocabularies import IMReviewStatesVocabulary
from imio.dms.mail.vocabularies import LabelsVocabulary
from imio.dms.mail.vocabularies import OMActiveMailTypesVocabulary
from imio.dms.mail.vocabularies import OMMailTypesVocabulary
from imio.dms.mail.vocabularies import OMSenderVocabulary
from imio.dms.mail.vocabularies import PloneGroupInterfacesVocabulary
from imio.dms.mail.vocabularies import TaskReviewStatesVocabulary
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestVocabularies(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        self.omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail')
        self.maxDiff = None

    def test_IMReviewStatesVocabulary(self):
        voc_inst = IMReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'En création'), ('proposed_to_manager', u'À valider par le DG'),
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
        self.assertSetEqual(set(voc_list), {('agent', 'Fred Agent'), ('chef', 'Michel Chef'), ('agent1', 'Stef Agent')})

    def test_EmptyAssignedUsersVocabulary(self):
        voc_inst = EmptyAssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list),
                            {(EMPTY_STRING, 'Empty value'), ('agent', 'Fred Agent'), ('chef', 'Michel Chef'),
                             ('agent1', 'Stef Agent')})

    def test_get_mail_types(self):
        voc_list = [(t.value, t.title) for t in get_mail_types()]
        self.assertEquals(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommandé'), (u'email', u'E-mail'),
                                     (u'certificat', u'Certificat médical'), (u'fax', u'Fax'),
                                     (u'retour-recommande', u'Retour recommandé'), (u'facture', u'Facture')])

    def test_IMMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommandé'),
                                        (u'email', u'E-mail'), (u'certificat', u'Certificat médical'), (u'fax', u'Fax'),
                                        (u'retour-recommande', u'Retour recommandé'), (u'facture', u'Facture')])

    def test_IMActiveMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMActiveMailTypesVocabulary')
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'courrier', u'recommande', u'email', u'certificat', u'fax',
                                        u'retour-recommande', u'facture'])
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]['mt_active'] = False
        settings.mail_types = mail_types
        # After a registry change, the vocabulary cache has been cleared
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'recommande', u'email', u'certificat', u'fax', u'retour-recommande',
                                        u'facture'])

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
        self.assertEqual(len(voc_inst(self.omail)), 22)
        # get first part, as unique value, keeping order
        res = OrderedDict.fromkeys([' '.join(s.title.split()[:3]).strip(',') for s in voc_inst(self.omail)]).keys()
        # res is sorted by firstname
        self.assertEqual(res, [u'Monsieur Fred Agent', u'Monsieur Maxime DG', u'Monsieur Michel Chef',
                               u'Monsieur Stef Agent'])
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                       'omail_sender_firstname_sorting', False)
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')
        res = OrderedDict.fromkeys([' '.join(s.title.split()[:3]).strip(',') for s in voc_inst(self.omail)]).keys()
        # res is sorted by lastname
        self.assertEqual(res, [u'Monsieur Fred Agent', u'Monsieur Stef Agent', u'Monsieur Michel Chef',
                               u'Monsieur Maxime DG'])

    def test_OMMailTypesVocabulary(self):
        voc_inst = OMMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u'courrier', u'recommande'])

    def test_OMActiveMailTypesVocabulary(self):
        voc_inst = OMActiveMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u'courrier', u'recommande'])

    def test_encodeur_active_orgs0(self):
        factory = getUtility(IVocabularyFactory, u'collective.dms.basecontent.treating_groups')
        all_titles = [t.title for t in factory(self.omail)]
        login(self.portal, 'encodeur')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
        logout()
        login(self.portal, 'agent')
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)],
                             [t for i, t in enumerate(all_titles) if i not in (0, 4, 7)])

    def test_LabelsVocabulary(self):
        login(self.portal, 'agent')
        voc_inst = LabelsVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, ['agent:lu', 'agent:suivi'])

    def test_CreatingGroupVocabulary(self):
        voc_inst1 = CreatingGroupVocabulary()
        voc_inst2 = ActiveCreatingGroupVocabulary()
        self.assertEqual(len(voc_inst1(self.imail)), 0)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        configure_group_encoder(['dmsincomingmail'])
        self.assertEqual(len(voc_inst1(self.imail)), 11)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        # defining specific group_encoder orgs
        selected_orgs = [t.value for i, t in enumerate(voc_inst1(self.imail)) if i <= 1]
        functions = api.portal.get_registry_record(FUNCTIONS_REGISTRY)
        functions[-1]['fct_orgs'] = selected_orgs
        api.portal.set_registry_record(FUNCTIONS_REGISTRY, functions)
        self.assertEqual(len(voc_inst1(self.imail)), 2)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        # adding user to group_encoder plone groups
        for org_uid in selected_orgs:
            api.group.add_user(groupname='{}_{}'.format(org_uid, CREATING_GROUP_SUFFIX), username='agent')
        self.assertEqual(len(voc_inst1(self.imail)), 2)
        self.assertEqual(len(voc_inst2(self.imail)), 2)
