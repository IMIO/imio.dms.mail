# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.test_permissions_base import TestPermissionsBase
from imio.dms.mail.utils import sub_create
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class TestPermissionsIncomingEmail(TestPermissionsBase):
    def test_incoming_email_permissions(self):
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "email",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "description": "Ceci est la description du courrier",
            "mail_date": datetime.today(),
        }
        iemail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)

        change_user(self.portal, "encodeur")
        annex = api.content.create(container=iemail, id="annex", type="dmsappendixfile")
        file = api.content.create(container=iemail, id="file", type="dmsmainfile")
        task = api.content.create(container=iemail, id="task", type="task")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertFalse(any(iemail_perms["dirg"]))
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertTrue(all(iemail_perms["encodeur"]))
        self.assertTrue(api.user.has_permission("Delete objects", "encodeur", obj=iemail))  # should be False ?
        self.assertTrue(api.user.has_permission("Review portal content", "encodeur", obj=iemail))  # should be False ?

        self.assertFalse(any(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertFalse(any(self.get_perms("dirg", file).values()))
        self.assertFalse(any(self.get_perms("agent", file).values()))
        self.assertFalse(any(self.get_perms("agent1", file).values()))
        self.assertTrue(all(self.get_perms("encodeur", file).values()))

        self.assertFalse(any(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertFalse(any(self.get_perms("dirg", annex).values()))
        self.assertFalse(any(self.get_perms("agent", annex).values()))
        self.assertFalse(any(self.get_perms("agent1", annex).values()))
        self.assertTrue(all(self.get_perms("encodeur", annex).values()))

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertFalse(any(self.get_perms("agent", task).values()))
        self.assertFalse(any(self.get_perms("agent1", task).values()))
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.pw.doActionFor(iemail, "propose_to_manager")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", file).values()))
        self.assertFalse(any(self.get_perms("agent1", file).values()))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])

        self.assertFalse(any(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", annex).values()))
        self.assertFalse(any(self.get_perms("agent1", annex).values()))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertFalse(any(self.get_perms("agent", task).values()))
        self.assertFalse(any(self.get_perms("agent1", task).values()))
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        change_user(self.portal, "dirg")
        self.pw.doActionFor(iemail, "propose_to_agent")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", file).values()))
        self.assertFalse(any(self.get_perms("agent1", file).values()))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])

        self.assertFalse(any(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", annex).values()))
        self.assertFalse(any(self.get_perms("agent1", annex).values()))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertFalse(any(self.get_perms("agent", task).values()))
        self.assertFalse(any(self.get_perms("agent1", task).values()))
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        # change_user(self.portal, "agent")
        # FIXME agent does not have permission to treat the mail
        self.pw.doActionFor(iemail, "treat")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", file).values()))
        self.assertFalse(any(self.get_perms("agent1", file).values()))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])

        self.assertFalse(any(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", annex).values()))
        self.assertFalse(any(self.get_perms("agent1", annex).values()))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertFalse(any(self.get_perms("agent", task).values()))
        self.assertFalse(any(self.get_perms("agent1", task).values()))
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.pw.doActionFor(iemail, "close")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, True, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, False, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", file).values()))
        self.assertFalse(any(self.get_perms("lecteur", file).values()))
        self.assertEqual(file_perms["dirg"], [True, True, False, False, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", file).values()))
        self.assertFalse(any(self.get_perms("agent1", file).values()))
        self.assertEqual(file_perms["encodeur"], [True, False, False, True, False, True, True, True, False])

        self.assertFalse(any(self.get_perms("chef", annex).values()))
        self.assertFalse(any(self.get_perms("lecteur", annex).values()))
        self.assertEqual(annex_perms["dirg"], [True, True, True, True, True, True, False, True, True])
        self.assertFalse(any(self.get_perms("agent", annex).values()))
        self.assertFalse(any(self.get_perms("agent1", annex).values()))
        self.assertEqual(annex_perms["encodeur"], [True, False, False, False, False, True, False, True, False])

        self.assertFalse(any(self.get_perms("chef", task).values()))
        self.assertFalse(any(self.get_perms("lecteur", task).values()))
        self.assertFalse(any(self.get_perms("dirg", task).values()))
        self.assertFalse(any(self.get_perms("agent", task).values()))
        self.assertFalse(any(self.get_perms("agent1", task).values()))
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
