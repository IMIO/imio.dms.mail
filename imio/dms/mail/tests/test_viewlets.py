# -*- coding: utf-8 -*-
"""Test views."""
import unittest
from plone import api
from plone.app.testing import login

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
        self.assertSetEqual(set([b.getObject() for b in ret]),
                            set([self.imf['courrier7'], self.imf['courrier1']]))
        ret = viewlet.find_relations(from_interfaces_flattened=IImioDmsIncomingMail)
        self.assertSetEqual(set([b.getObject() for b in ret]),
                            set([self.imf['courrier7'], self.imf['courrier1']]))
        # call on person
        viewlet = ContactContentBackrefsViewlet(self.jean, self.jean.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]),
                            set([self.imf['courrier3'], self.imf['courrier9']]))
        # call on held position
        agent = self.jean['agent-electrabel']
        viewlet = ContactContentBackrefsViewlet(agent, agent.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]), set([self.imf['courrier5']]))
