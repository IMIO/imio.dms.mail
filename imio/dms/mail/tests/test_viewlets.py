# -*- coding: utf-8 -*-
"""Test views."""
from collective.iconifiedcategory.utils import calculate_category_id
from collective.messagesviewlet.message import PseudoMessage
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.viewlets import ContactContentBackrefsViewlet
from imio.dms.mail.browser.viewlets import ContextInformationViewlet
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from plone import api
from plone.app.testing import login
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile

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
        # outgoing mail with approvers + an invalid sign/approve combination => warning banner
        login(self.portal, "siteadmin")
        pf = self.portal["contacts"]["personnel-folder"]
        om = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "om-viewlet",
            title=u"Courrier sortant test",
            mail_type="courrier",
            treating_groups=self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            sender=self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            send_modes=u"post",
            signers=[
                {"number": 1, "signer": pf["dirg"]["directeur-general"].UID(),
                 "approvings": [u"_themself_"], "editor": True}
            ],
        )
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/batchimport/toprocess/outgoing-mail/Réponse salle.odt" % PRODUCT_DIR, "rb") as fo:
            afile = createContentInContainer(
                om,
                "dmsommainfile",
                id="file1",
                scan_id="012999900000900",
                file=NamedBlobFile(fo.read(), filename=u"Réponse salle.odt"),
                content_category=calculate_category_id(ct),
            )
        afile.to_sign, afile.to_approve = True, False  # eligible but not approved => invalid
        om_inv_v = ContextInformationViewlet(om, self.elec.REQUEST, None)
        combo = [m for m in om_inv_v.getAllMessages() if u"invalid signature/approval combination" in m.text.output]
        self.assertEqual(len(combo), 1)
        self.assertTrue(isinstance(combo[0], PseudoMessage))
        afile.to_approve = True  # valid combination now => no banner
        combo = [m for m in om_inv_v.getAllMessages() if u"invalid signature/approval combination" in m.text.output]
        self.assertEqual(combo, [])
        # render() wraps the (possibly empty) banner in an AJAX-refreshable container
        om_inv_v.index = lambda: u"BODY"
        self.assertEqual(om_inv_v.render(), u'<div id="dms-context-messages">BODY</div>')
