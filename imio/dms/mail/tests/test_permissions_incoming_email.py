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
    def test_permissions_incoming_email(self):
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

        self.assertHasNoPerms("chef", iemail)
        self.assertHasNoPerms("lecteur", iemail)
        self.assertHasNoPerms("dirg", iemail)
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertHasAllPerms("encodeur", iemail)

        self.assertHasNoPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertHasNoPerms("dirg", file)
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertHasAllPerms("encodeur", file)

        self.assertHasNoPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertHasNoPerms("dirg", annex)
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertHasAllPerms("encodeur", annex)

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
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

        self.assertHasNoPerms("chef", iemail)
        self.assertHasNoPerms("lecteur", iemail)
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
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

        self.assertHasNoPerms("chef", iemail)
        self.assertHasNoPerms("lecteur", iemail)
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
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

        self.assertHasNoPerms("chef", iemail)
        self.assertHasNoPerms("lecteur", iemail)
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
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

        self.assertHasNoPerms("chef", iemail)
        self.assertHasNoPerms("lecteur", iemail)
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
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
