# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestPermissions(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING
    perms = (
        "Access contents information",
        "Add portal content",
        "Delete objects",
        "Modify portal content",
        "Review portal content",
        "View",
        "collective.dms.basecontent: Add DmsFile",
        "imio.dms.mail: Write mail base fields",
        "imio.dms.mail: Write treating group field",
    )
    users = (
        "chef",
        "lecteur",
        "dirg",
        "agent",
        "agent1",
        "encodeur",
    )

    def setUp(self):
        self.portal = self.layer["portal"]
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.pw = api.portal.get_tool("portal_workflow")
        change_user(self.portal)

    def get_perms(self, obj):
        perms = {}
        for user in self.users:
            for perm in self.perms:
                perms[user] = perms.get(user, []) + [api.user.has_permission(perm, user, obj=obj)]
        return perms

    def test_incoming_mail_permissions(self):
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "courrier",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "description": "Ceci est la description du courrier",
            "mail_date": datetime.today(),
        }
        imail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)

        change_user(self.portal, "encodeur")
        annex = api.content.create(container=imail, id="annex", type="dmsappendixfile")
        file = api.content.create(container=imail, id="file", type="dmsmainfile")
        task = api.content.create(container=imail, id="task", type="task")

        imail_perms = self.get_perms(imail)
        self.assertFalse(any(imail_perms["chef"]))
        self.assertFalse(any(imail_perms["lecteur"]))
        self.assertFalse(any(imail_perms["dirg"]))
        self.assertFalse(any(imail_perms["agent"]))
        self.assertFalse(any(imail_perms["agent1"]))
        self.assertTrue(all(imail_perms["encodeur"]))
        self.assertTrue(api.user.has_permission("Delete objects", "encodeur", obj=imail))  # should be False ?
        self.assertTrue(api.user.has_permission("Review portal content", "encodeur", obj=imail))  # should be False ?
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertFalse(any(file_perms["dirg"]))
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertTrue(all(file_perms["encodeur"]))
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertFalse(any(annex_perms["dirg"]))
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertTrue(all(annex_perms["encodeur"]))
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        self.pw.doActionFor(imail, "propose_to_manager")

        imail_perms = self.get_perms(imail)
        self.assertFalse(any(imail_perms["chef"]))
        self.assertFalse(any(imail_perms["lecteur"]))
        self.assertEqual(imail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(imail_perms["agent"]))
        self.assertFalse(any(imail_perms["agent1"]))
        self.assertEqual(imail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        change_user(self.portal, "dirg")
        self.pw.doActionFor(imail, "propose_to_agent")

        imail_perms = self.get_perms(imail)
        self.assertFalse(any(imail_perms["chef"]))
        self.assertFalse(any(imail_perms["lecteur"]))
        self.assertEqual(imail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(imail_perms["agent"]))
        self.assertFalse(any(imail_perms["agent1"]))
        self.assertEqual(imail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        # change_user(self.portal, "agent")
        # FIXME agent does not have permission to treat the mail
        self.pw.doActionFor(imail, "treat")

        imail_perms = self.get_perms(imail)
        self.assertFalse(any(imail_perms["chef"]))
        self.assertFalse(any(imail_perms["lecteur"]))
        self.assertEqual(imail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(imail_perms["agent"]))
        self.assertFalse(any(imail_perms["agent1"]))
        self.assertEqual(imail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        self.pw.doActionFor(imail, "close")

        imail_perms = self.get_perms(imail)
        self.assertFalse(any(imail_perms["chef"]))
        self.assertFalse(any(imail_perms["lecteur"]))
        self.assertEqual(imail_perms["dirg"], [True, True, False, True, True, True, False, True, True])
        self.assertFalse(any(imail_perms["agent"]))
        self.assertFalse(any(imail_perms["agent1"]))
        self.assertEqual(imail_perms["encodeur"], [True, False, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, True, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, False, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, True, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, False, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        # Check permissions for every user (agent, encodeur, dirg, reader, chef) and for every state, also test for subelements such as ged file, annex, and task
        # http://localhost:8081/DMS-1066/@@usergroup-userprefs
        # http://localhost:8081/DMS-1066/dexterity-types/dmsincomingmail/@@localroles
        # http://localhost:8081/DMS-1066/portal_workflow/incomingmail_workflow/states/closed/manage_permissions
        # https://github.com/IMIO/Products.PloneMeeting/blob/master/src/Products/PloneMeeting/tests/testWorkflows.py#L18

        # Repeat for incoming email and outgoing email

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
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertFalse(any(file_perms["dirg"]))
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertTrue(all(file_perms["encodeur"]))
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertFalse(any(annex_perms["dirg"]))
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertTrue(all(annex_perms["encodeur"]))
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        self.pw.doActionFor(iemail, "propose_to_manager")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        change_user(self.portal, "dirg")
        self.pw.doActionFor(iemail, "propose_to_agent")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, False, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

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
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, False, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, True, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, False, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, True, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

        self.pw.doActionFor(iemail, "close")

        iemail_perms = self.get_perms(iemail)
        self.assertFalse(any(iemail_perms["chef"]))
        self.assertFalse(any(iemail_perms["lecteur"]))
        self.assertEqual(iemail_perms["dirg"], [True, True, False, True, True, True, False, True, True])
        self.assertFalse(any(iemail_perms["agent"]))
        self.assertFalse(any(iemail_perms["agent1"]))
        self.assertEqual(iemail_perms["encodeur"], [True, False, False, False, False, True, False, True, False])
        file_perms = self.get_perms(file)
        self.assertFalse(any(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [True, True, False, False, True, True, False, True, True])
        self.assertFalse(any(file_perms["agent"]))
        self.assertFalse(any(file_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, False, False, True, False, True, True, True, False])
        annex_perms = self.get_perms(annex)
        self.assertFalse(any(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [True, True, True, True, True, True, False, True, True])
        self.assertFalse(any(annex_perms["agent"]))
        self.assertFalse(any(annex_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, False, False, False, False, True, False, True, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertFalse(any(task_perms["agent"]))
        self.assertFalse(any(task_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [True, False, True, True, False, True, False, False, False])

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
        file_perms = self.get_perms(file)
        self.assertTrue(all(file_perms["chef"]))
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertFalse(any(file_perms["dirg"]))
        self.assertTrue(all(file_perms["agent"]))
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(file_perms["encodeur"]))
        annex_perms = self.get_perms(annex)
        self.assertTrue(all(annex_perms["chef"]))
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertFalse(any(annex_perms["dirg"]))
        self.assertTrue(all(annex_perms["agent"]))
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(annex_perms["encodeur"]))
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertEqual(task_perms["agent"], [True, True, True, True, False, True, True, False, True])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(annex_perms["encodeur"]))

        self.pw.doActionFor(omail, "propose_to_be_signed")

        omail_perms = self.get_perms(omail)
        self.assertEqual(omail_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertEqual(omail_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(omail_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(omail_perms["encodeur"], [False, False, False, True, True, False, False, False, False])
        file_perms = self.get_perms(file)
        self.assertEqual(file_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(file_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [False, False, False, True, True, False, False, False, False])
        annex_perms = self.get_perms(annex)
        self.assertEqual(annex_perms["chef"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [False, True, True, True, True, False, True, False, False])
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [False, False, True, True, True, False, False, False, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(task_perms["encodeur"]))

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
        file_perms = self.get_perms(file)
        self.assertEqual(file_perms["chef"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [False, True, True, True, True, False, False, False, False])
        self.assertEqual(file_perms["agent"], [False, True, True, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [True, False, True, True, True, True, True, False, False])
        annex_perms = self.get_perms(annex)
        self.assertEqual(annex_perms["chef"], [False, True, False, True, True, False, False, True, False])
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [False, True, False, True, True, False, False, False, False])
        self.assertEqual(annex_perms["agent"], [False, True, False, True, True, False, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [True, False, True, True, True, True, True, False, False])
        task_perms = self.get_perms(task)
        self.assertEqual(task_perms["chef"], [False, False, False, False, False, False, False, False, False])
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertEqual(task_perms["dirg"], [False, False, False, False, False, False, False, False, False])
        self.assertEqual(task_perms["agent"], [True, False, True, True, False, True, False, False, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(task_perms["encodeur"], [False, False, False, False, False, False, False, False, False])

        self.pw.doActionFor(omail, "mark_as_sent")

        omail_perms = self.get_perms(omail)
        self.assertEqual(omail_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["lecteur"]))
        self.assertEqual(omail_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(omail_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(omail_perms["encodeur"], [False, False, False, True, True, False, False, False, False])
        file_perms = self.get_perms(file)
        self.assertEqual(file_perms["chef"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(file_perms["lecteur"]))
        self.assertEqual(file_perms["dirg"], [False, True, False, True, True, False, True, False, False])
        self.assertEqual(file_perms["agent"], [True, True, False, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(file_perms["encodeur"], [False, False, False, True, True, False, False, False, False])
        annex_perms = self.get_perms(annex)
        self.assertEqual(annex_perms["chef"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(annex_perms["lecteur"]))
        self.assertEqual(annex_perms["dirg"], [False, True, True, True, True, False, True, False, False])
        self.assertEqual(annex_perms["agent"], [True, True, True, True, True, True, False, True, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertEqual(annex_perms["encodeur"], [False, False, True, True, True, False, False, False, False])
        task_perms = self.get_perms(task)
        self.assertFalse(any(task_perms["chef"]))
        self.assertFalse(any(task_perms["lecteur"]))
        self.assertFalse(any(task_perms["dirg"]))
        self.assertEqual(task_perms["agent"], [True, False, True, True, False, True, False, False, False])
        self.assertFalse(any(omail_perms["agent1"]))
        self.assertFalse(any(task_perms["encodeur"]))
