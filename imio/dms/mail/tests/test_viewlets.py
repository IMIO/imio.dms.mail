# -*- coding: utf-8 -*-
"""Test views."""
from collective.messagesviewlet.message import PseudoMessage
from imio.dms.mail.browser.viewlets import ContactContentBackrefsViewlet
from imio.dms.mail.browser.viewlets import ContextInformationViewlet
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import login

import unittest


class TestContactContentBackrefsViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.ctct = self.portal['contacts']
        self.elec = self.ctct['electrabel']
        self.jean = self.ctct['jeancourant']
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def test_backrefs(self):
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        # configure to see all refs
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view', True)
        self.assertListEqual([self.portal.unrestrictedTraverse(b.getPath()) for b in viewlet.backrefs()],
                             [self.omf['reponse7'], self.omf['reponse1'], self.imf['courrier7'], self.imf['courrier1']])
        # configure to see only permitted refs
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view', False)
        self.assertListEqual(viewlet.backrefs(), [])
        # login to get view permission
        login(self.portal, 'encodeur')
        self.assertListEqual([b.getObject() for b in viewlet.backrefs()],
                             [self.imf['courrier7'], self.imf['courrier1']])

    def test_find_relations(self):
        login(self.portal, 'encodeur')
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        ret = viewlet.find_relations(from_attribute='sender')
        self.assertSetEqual(set([b.getObject() for b in ret]), {self.imf['courrier7'], self.imf['courrier1']})
        ret = viewlet.find_relations(from_interfaces_flattened=IImioDmsIncomingMail)
        self.assertSetEqual(set([b.getObject() for b in ret]), {self.imf['courrier7'], self.imf['courrier1']})
        # call on person
        viewlet = ContactContentBackrefsViewlet(self.jean, self.jean.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]), {self.imf['courrier3'], self.imf['courrier9']})
        # call on held position
        agent = self.jean['agent-electrabel']
        viewlet = ContactContentBackrefsViewlet(agent, agent.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]), {self.imf['courrier5']})

    def test_ContextInformationViewlet(self):
        login(self.portal, 'encodeur')
        org_v = ContextInformationViewlet(self.elec, self.elec.REQUEST, None)
        self.assertListEqual(org_v.getAllMessages(), [])
        sorg_v = ContextInformationViewlet(self.elec['travaux'], self.elec.REQUEST, None)
        self.assertTrue(self.elec['travaux'].use_parent_address)
        self.assertListEqual(sorg_v.getAllMessages(), [])
        pers_v = ContextInformationViewlet(self.jean, self.elec.REQUEST, None)
        self.assertEqual(len(pers_v.getAllMessages()), 1)  # no address
        hp_v = ContextInformationViewlet(self.jean['agent-electrabel'], self.elec.REQUEST, None)
        self.assertTrue(self.jean['agent-electrabel'].use_parent_address)
        self.assertListEqual(hp_v.getAllMessages(), [])
        om_v = ContextInformationViewlet(self.omf['reponse1'], self.elec.REQUEST, None)
        self.assertListEqual(om_v.getAllMessages(), [])
        # removing street from electrabel org
        self.elec.street = None
        msgs = org_v.getAllMessages()
        self.assertEqual(len(msgs), 1)
        self.assertTrue(isinstance(msgs[0], PseudoMessage))
        self.assertIn('missing address fields: street', msgs[0].text.output)
        self.assertEqual(len(sorg_v.getAllMessages()), 1)  # suborganization has missing street too
        self.assertEqual(len(hp_v.getAllMessages()), 1)  # held position has missing street too
        self.assertEqual(len(om_v.getAllMessages()), 1)  # outgoing mail has missing street too
