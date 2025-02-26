# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.test_permissions_base import TestPermissionsBase
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class TestPermissionsOutgoingMail(TestPermissionsBase):
    def test_outgoing_mail_permissions(self):
        intids = getUtility(IIntIds)
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_date": datetime.today(),
            "mail_type": "type1",
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
        }
        omail = sub_create(self.omf, "dmsoutgoingmail", datetime.today(), "my-id", **params)

        change_user(self.portal, "agent")
        annex = api.content.create(container=omail, id="annex", type="dmsappendixfile")
        file = api.content.create(container=omail, id="file", type="dmsommainfile")
        task = api.content.create(container=omail, id="task", type="task")

        omail_perms = self.get_perms(omail)
        self.assertTrue(all(omail_perms["chef"]))
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertFalse(any(omail_perms["dirg"]))
        self.assertTrue(all(omail_perms["agent"]))
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(omail_perms["encodeur"]))

        self.assertTrue(all(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertFalse(any(self.get_perms("dirg", file).values()))
        self.assertTrue(all(self.get_perms("agent", file).values()))
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(self.get_perms("encodeur", file).values()))

        self.assertTrue(all(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertFalse(any(self.get_perms("dirg", annex).values()))
        self.assertTrue(all(self.get_perms("agent", annex).values()))
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(self.get_perms("encodeur", annex).values()))

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertEqual(task_perms["agent"], [True, True, True, True, False, True, True, False, True])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(self.get_perms("encodeur", annex).values()))

        self.pw.doActionFor(omail, "propose_to_be_signed")

        omail_perms = self.get_perms(omail)
        self.assertEqual(omail_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertEqual(omail_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(omail_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(omail_perms["encodeur"], [False, False, False, True, True, False, False, False, False])

        self.assertEqual(file_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(file_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [False, False, False, True, True, False, False, False, False])

        self.assertEqual(annex_perms["chef"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [False, True, True, True, True, False, True, False, False])
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [False, False, True, True, True, False, False, False, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(self.get_perms("encodeur", task).values()))

        self.pw.doActionFor(omail, "back_to_creation")
        change_user(self.portal, "scanner")
        self.pw.doActionFor(omail, "set_scanned")

        omail_perms = self.get_perms(omail)
        self.assertEqual(omail_perms["chef"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertEqual(omail_perms["dirg"], [False, True, True, True, True, False, False, False, False])
        self.assertEqual(omail_perms["agent"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(omail_perms["encodeur"], [True, False, True, True, True, True, True, False, False])

        self.assertEqual(file_perms["chef"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [False, True, True, True, True, False, False, False, False])
        self.assertEqual(file_perms["agent"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, False, True, True, True, True, True, False, False])

        self.assertEqual(annex_perms["chef"], [False, True, False, True, True, False, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [False, True, False, True, True, False, False, False, False])
        self.assertEqual(annex_perms["agent"], [False, True, False, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, False, True, True, True, True, True, False, False])

        self.assertEqual(task_perms["chef"], [False, False, False, False, False, False, False, False, False])
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertEqual(task_perms["dirg"], [False, False, False, False, False, False, False, False, False])
        self.assertEqual(task_perms["agent"], [True, False, True, True, False, True, False, False, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(omail_perms["encodeur"]))

        self.pw.doActionFor(omail, "mark_as_sent")

        omail_perms = self.get_perms(omail)
        self.assertEqual(omail_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertEqual(omail_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(omail_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(omail_perms["encodeur"], [False, False, False, True, True, False, False, False, False])

        self.assertEqual(file_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(file_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [False, False, False, True, True, False, False, False, False])

        self.assertEqual(annex_perms["chef"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [False, True, True, True, True, False, True, False, False])
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [False, False, True, True, True, False, False, False, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertEqual(task_perms["agent"], [True, False, True, True, False, True, False, False, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(self.get_perms("encodeur", task).values()))
