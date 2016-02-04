# -*- coding: utf-8 -*-
import unittest
from zope.component import getUtility
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from imio.dms.mail.browser.settings import IImioDmsMailConfig

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..vocabularies import (IMReviewStatesVocabulary, TaskReviewStatesVocabulary, AssignedUsersVocabulary,
                            getMailTypes, IMMailTypesVocabulary, IMActiveMailTypesVocabulary,
                            PloneGroupInterfacesVocabulary)


class TestVocabularies(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')

    def test_IMReviewStatesVocabulary(self):
        voc_inst = IMReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'Created'), ('proposed_to_manager', u'Proposed to manager'),
                                    ('proposed_to_service_chief', u'Proposed to service chief'),
                                    ('proposed_to_agent', u'Proposed to agent'), ('in_treatment', u'In treatment'),
                                    ('closed', u'Closed')])

    def test_TaskReviewStatesVocabulary(self):
        voc_inst = TaskReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'Created'), ('to_assign', u'To assign'), ('to_do', u'To do'),
                                    ('in_progress', u'In progress'), ('realized', u'Realized'),
                                    ('closed', u'Closed')])

    def test_AssignedUsersVocabulary(self):
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef')]))
        # We change the title to set the same fullname
        member = api.user.get(userid='chef')
        member.setMemberProperties({'fullname': 'Fred Agent'})
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Fred Agent')]))

    def test_getMailTypes(self):
        voc_list = [(t.value, t.title) for t in getMailTypes()]
        self.assertEquals(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommandé'), (u'email', u'E-mail'),
                                     (u'fax', u'Fax'), (u'retour-recommande', u'Retour recommandé'),
                                     (u'facture', u'Facture')])

    def test_IMMailTypesVocabulary(self):
        voc_inst = IMMailTypesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [(u'courrier', u'Courrier'), (u'recommande', u'Recommand\xe9'),
                                        (u'email', u'E-mail'), (u'fax', u'Fax'),
                                        (u'retour-recommande', u'Retour recommand\xe9'), (u'facture', u'Facture')])

    def test_IMActiveMailTypesVocabulary(self):
        voc_inst = IMActiveMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'courrier', u'recommande', u'email', u'fax', u'retour-recommande',
                                        u'facture'])
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]['mt_active'] = False
        settings.mail_types = mail_types
        voc_inst = IMActiveMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u'recommande', u'email', u'fax', u'retour-recommande', u'facture'])

    def test_PloneGroupInterfacesVocabulary(self):
        voc_inst = PloneGroupInterfacesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [('collective.contact.plonegroup.interfaces.IPloneGroupContact',
                                         'IPloneGroupContact'),
                                        ('collective.contact.plonegroup.interfaces.INotPloneGroupContact',
                                         'INotPloneGroupContact')])
