# -*- coding: utf-8 -*-
import unittest2 as unittest
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_registeredMailTypes(self):
        from imio.dms.mail.dmsmail import registeredMailTypes
        voc_list = [(t.value, t.title) for t in registeredMailTypes(self)]
        self.assertEquals(voc_list, [(None, 'Choose a value !'), (u'courrier', u'Courrier'),
                                     (u'recommande', u'Recommandé'), (u'email', u'E-mail'), (u'fax', u'Fax'),
                                     (u'retour-recommande', u'Retour recommandé'), (u'facture', u'Facture')])

    def test_TreatingGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import TreatingGroupsVocabulary
        voc_inst = TreatingGroupsVocabulary()
        voc = voc_inst(self.portal)
        self.assertEquals(len([t for t in voc]), 6)
        self.assertNotEqual(len(voc), 6)  # len = full vocabulary with hidden terms

    def test_RecipientGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import RecipientGroupsVocabulary
        voc_inst = RecipientGroupsVocabulary()
        voc = voc_inst(self.portal)
        self.assertEquals(len([t for t in voc]), 6)
        self.assertNotEqual(len(voc), 6)  # len = full vocabulary with hidden terms

    def test_Title(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        self.assertEquals(imail1.Title(), 'E0001 - Courrier 1')
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         **{'title': 'Test with auto ref'})
        self.assertEquals(imail.Title(), 'E0010 - Test with auto ref')
