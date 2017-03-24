# -*- coding: utf-8 -*-
"""Test views."""
import unittest

from ..browser.viewlets import ContactContentBackrefsViewlet
from ..dmsmail import IImioDmsIncomingMail
from ..testing import DMSMAIL_INTEGRATION_TESTING


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
        self.assertListEqual(viewlet.backrefs(),
                             [self.omf['reponse7'], self.omf['reponse1'], self.imf['courrier7'], self.imf['courrier1']])

    def test_find_relations(self):
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        ret = viewlet.find_relations(from_attribute='sender')
        self.assertSetEqual(set(ret),
                            set([self.imf['courrier7'], self.imf['courrier1']]))
        ret = viewlet.find_relations(from_attribute='sender')
        self.assertSetEqual(set(ret),
                            set([self.imf['courrier7'], self.imf['courrier1']]))
        ret = viewlet.find_relations(from_interfaces_flattened=IImioDmsIncomingMail)
        self.assertSetEqual(set(ret),
                            set([self.imf['courrier7'], self.imf['courrier1']]))
        # call on person
        viewlet = ContactContentBackrefsViewlet(self.jean, self.jean.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set(ret),
                            set([self.imf['courrier3'], self.imf['courrier9'], self.omf['reponse3'],
                                 self.omf['reponse9']]))
        # call on held position
        agent = self.jean['agent-electrabel']
        viewlet = ContactContentBackrefsViewlet(agent, agent.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set(ret), set([self.imf['courrier5'], self.omf['reponse5']]))
