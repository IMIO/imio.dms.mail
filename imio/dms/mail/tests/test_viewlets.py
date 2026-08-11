# -*- coding: utf-8 -*-
"""Test views."""
from collective.messagesviewlet.message import PseudoMessage
from imio.dms.mail.browser.viewlets import ContactContentBackrefsViewlet
from imio.dms.mail.browser.viewlets import ContextInformationViewlet
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.tests.utils import create_om_with_tags
from imio.dms.mail.tests.utils import odt_with_tags
from imio.helpers.content import get_object
from plone import api
from plone.app.testing import login

import unittest


class TestContactContentBackrefsViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.ctct = self.portal["contacts"]
        self.elec = self.ctct["electrabel"]
        self.jean = self.ctct["jeancourant"]
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]

    def test_backrefs(self):
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        # configure to see all refs
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view", True)
        self.assertListEqual(
            [self.portal.unrestrictedTraverse(b.getPath()) for b in viewlet.backrefs()],
            [
                get_object(oid="reponse7", ptype="dmsoutgoingmail"),
                get_object(oid="reponse1", ptype="dmsoutgoingmail"),
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            ],
        )
        # configure to see only permitted refs
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view", False)
        self.assertListEqual(viewlet.backrefs(), [])
        # login to get view permission
        login(self.portal, "encodeur")
        self.assertListEqual(
            [b.getObject() for b in viewlet.backrefs()],
            [
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            ],
        )

    def test_find_relations(self):
        login(self.portal, "encodeur")
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        ret = viewlet.find_relations(from_attribute="sender")
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            },
        )
        ret = viewlet.find_relations(from_interfaces_flattened=IImioDmsIncomingMail)
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            },
        )
        # call on person
        viewlet = ContactContentBackrefsViewlet(self.jean, self.jean.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier3", ptype="dmsincomingmail"),
                get_object(oid="courrier9", ptype="dmsincomingmail"),
            },
        )
        # call on held position
        agent = self.jean["agent-electrabel"]
        viewlet = ContactContentBackrefsViewlet(agent, agent.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]), {get_object(oid="courrier5", ptype="dmsincomingmail")})

    def test_ContextInformationViewlet(self):
        login(self.portal, "encodeur")
        org_v = ContextInformationViewlet(self.elec, self.elec.REQUEST, None)
        self.assertListEqual(org_v.getAllMessages(), [])
        sorg_v = ContextInformationViewlet(self.elec["travaux"], self.elec.REQUEST, None)
        self.assertTrue(self.elec["travaux"].use_parent_address)
        self.assertListEqual(sorg_v.getAllMessages(), [])
        pers_v = ContextInformationViewlet(self.jean, self.elec.REQUEST, None)
        self.assertEqual(len(pers_v.getAllMessages()), 1)  # no address
        hp_v = ContextInformationViewlet(self.jean["agent-electrabel"], self.elec.REQUEST, None)
        self.assertTrue(self.jean["agent-electrabel"].use_parent_address)
        self.assertListEqual(hp_v.getAllMessages(), [])
        om_v = ContextInformationViewlet(get_object(oid="reponse1", ptype="dmsoutgoingmail"), self.elec.REQUEST, None)
        self.assertListEqual(om_v.getAllMessages(), [])
        # removing street from electrabel org
        self.elec.street = None
        msgs = org_v.getAllMessages()
        self.assertEqual(len(msgs), 1)
        self.assertTrue(isinstance(msgs[0], PseudoMessage))
        self.assertIn("missing address fields: street", msgs[0].text.output)
        self.assertEqual(len(sorg_v.getAllMessages()), 1)  # suborganization has missing street too
        self.assertEqual(len(hp_v.getAllMessages()), 1)  # held position has missing street too
        self.assertEqual(len(om_v.getAllMessages()), 1)  # outgoing mail has missing street too

    def test_get_acroform_messages(self):
        """Acroform tag errors are shown while the mail can still be corrected."""
        login(self.portal, "siteadmin")
        omail, afile = create_om_with_tags(self.portal, "omail-acroform-viewlet",
                                           tag_ids=(1,), nb_signers=2)
        viewlet = ContextInformationViewlet(omail, omail.REQUEST, None)
        msgs = viewlet.get_acroform_messages()
        self.assertEqual(len(msgs), 1)
        self.assertTrue(isinstance(msgs[0], PseudoMessage))
        self.assertIn("signature or seal tags of file", msgs[0].text.output)
        self.assertIn("Signer2", msgs[0].text.output)
        self.assertEqual(len(viewlet.getAllMessages()), 1)

        # --- a complete set of tags: no message ---
        afile.file = odt_with_tags(1, 2)
        self.assertEqual(viewlet.get_acroform_messages(), [])

        # --- a seal tag while no seal is defined ---
        afile.file = odt_with_tags(1, 2, u"SCEAU")
        msgs = viewlet.get_acroform_messages()
        self.assertEqual(len(msgs), 1)
        self.assertIn("no seal is defined", msgs[0].text.output)
        omail.seal = True
        self.assertEqual(viewlet.get_acroform_messages(), [])
        afile.file = odt_with_tags(1, 2)

        # --- once the mail left the correctable states, nothing is shown any more ---
        afile.file = odt_with_tags(1)
        self.assertEqual(len(viewlet.get_acroform_messages()), 1)
        api.content.transition(obj=omail, transition="mark_as_sent")
        self.assertEqual(api.content.get_state(omail), "sent")
        self.assertEqual(viewlet.get_acroform_messages(), [])
