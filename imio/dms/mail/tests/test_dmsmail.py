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
        voc_dic = registeredMailTypes(self).by_token
        voc_list = [(voc_dic[key].value, voc_dic[key].title) for key in voc_dic.keys()]
        self.assertEquals(voc_list, [(None, 'Choose a value !'), (u'Courrier', u'Courrier'), (u'Facture', u'Facture'),
                                (u'Retour recommandé', u'Retour recommandé')])

    def test_TreatingGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import TreatingGroupsVocabulary
        voc_inst = TreatingGroupsVocabulary()
        voc_dic = voc_inst(self.portal).by_token
        self.assertEquals(len(voc_dic), 4)

    def test_RecipientGroupsVocabulary(self):
        from imio.dms.mail.dmsmail import RecipientGroupsVocabulary
        voc_inst = RecipientGroupsVocabulary()
        voc_dic = voc_inst(self.portal).by_token
        self.assertEquals(len(voc_dic), 4)

    def test_Title(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        self.assertEquals(imail1.Title(), 'in/1 - Courrier 1')
        imail = createContentInContainer(self.portal, 'dmsincomingmail', **{'title': 'Test with auto ref'})
        self.assertEquals(imail.Title(), 'in/10 - Test with auto ref')
