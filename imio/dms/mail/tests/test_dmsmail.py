# -*- coding: utf-8 -*-
import unittest
from z3c.relationfield.relation import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified
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

    def test_linked_mails(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        imail2 = self.portal['incoming-mail']['courrier2']
        omail1 = self.portal['outgoing-mail']['reponse1']
        omail2 = self.portal['outgoing-mail']['reponse2']
        intids = getUtility(IIntIds)
        omail1.linked_mails = [
            RelationValue(intids.getId(imail1)),
            RelationValue(intids.getId(imail2)),
            RelationValue(intids.getId(omail2)),
        ]
        modified(omail1)
        self.assertEqual(len(omail1.linked_mails), 3)
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        omail_intid = intids.queryId(omail1)
        query = {
            'from_id': omail_intid,
            'from_attribute': 'linked_mails'
        }

        linked = set([rel.to_object for rel in catalog.findRelations(query)])
        self.assertSetEqual(set([imail1, imail2, omail2]), linked)
