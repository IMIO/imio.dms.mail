# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.test_permissions_base import TestPermissionsBase
from imio.dms.mail.utils import clean_borg_cache
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
        }
        change_user(self.portal, "encodeur")
        iemail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)
        annex = api.content.create(container=iemail, id="annex", type="dmsappendixfile")
        file = api.content.create(container=iemail, id="file", type="dmsmainfile")
        task = api.content.create(container=iemail, id="task", type="task", assigned_group=iemail.treating_groups)
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", iemail)
        self.assertHasNoPerms("dirg", iemail)
        self.assertHasNoPerms("agent", iemail)
        self.assertHasNoPerms("agent1", iemail)
        self.assertHasAllPerms("encodeur", iemail)

        self.assertHasNoPerms("lecteur", file)
        self.assertHasNoPerms("dirg", file)
        self.assertHasNoPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertHasAllPerms("encodeur", file)

        self.assertHasNoPerms("lecteur", annex)
        self.assertHasNoPerms("dirg", annex)
        self.assertHasNoPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertHasAllPerms("encodeur", annex)

        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertHasNoPerms("agent", task)
        self.assertHasNoPerms("agent1", task)
        self.assertEqual(
            self.get_perms("encodeur", task),
            {
                "Access contents information": True,
                # apc not handled in workflow. Permission inherited from im for Contributor.
                # encodeur cannot add subtask !!  Only owner role. TODO: to be improved
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.pw.doActionFor(iemail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", iemail)
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                # First error: apc is given to Contributor role and manager is Contributor
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
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
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )

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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        change_user(self.portal, "dirg")
        self.pw.doActionFor(iemail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        change_user(self.portal, "agent")
        self.pw.doActionFor(iemail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.pw.doActionFor(iemail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", iemail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", iemail)
        self.assertEqual(
            self.get_perms("encodeur", iemail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

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
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
