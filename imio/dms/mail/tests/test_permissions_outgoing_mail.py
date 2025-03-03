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
    def test_permissions_outgoing_mail(self):
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

        self.assertHasAllPerms("chef", omail)
        self.assertHasNoPerms("lecteur", omail)
        self.assertHasNoPerms("dirg", omail)
        self.assertHasAllPerms("agent", omail)
        self.assertHasNoPerms("agent1", omail)
        self.assertHasNoPerms("encodeur", omail)

        self.assertHasAllPerms("chef", file)
        self.assertHasNoPerms("lecteur", file)
        self.assertHasNoPerms("dirg", file)
        self.assertHasAllPerms("agent", file)
        self.assertHasNoPerms("agent1", file)
        self.assertHasNoPerms("encodeur", file)

        self.assertHasAllPerms("chef", annex)
        self.assertHasNoPerms("lecteur", annex)
        self.assertHasNoPerms("dirg", annex)
        self.assertHasAllPerms("agent", annex)
        self.assertHasNoPerms("agent1", annex)
        self.assertHasNoPerms("encodeur", annex)

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertEqual(
            self.get_perms("agent", task),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent1", task)
        self.assertHasNoPerms("encodeur", annex)

        self.pw.doActionFor(omail, "propose_to_be_signed")

        self.assertEqual(
            self.get_perms("chef", omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("lecteur", omail)
        self.assertEqual(
            self.get_perms("dirg", omail),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", omail)
        self.assertEqual(
            self.get_perms("encodeur", omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
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
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
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
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertEqual(
            self.get_perms("agent", task),
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
        self.assertHasNoPerms("agent1", omail)
        self.assertHasNoPerms("encodeur", task)

        self.pw.doActionFor(omail, "back_to_creation")
        change_user(self.portal, "scanner")
        self.pw.doActionFor(omail, "set_scanned")

        self.assertEqual(
            self.get_perms("chef", omail),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("lecteur", omail)
        self.assertEqual(
            self.get_perms("dirg", omail),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", omail),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", omail)
        self.assertEqual(
            self.get_perms("encodeur", omail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", file),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("lecteur", file)
        self.assertEqual(
            self.get_perms("dirg", file),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", annex),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("lecteur", annex)
        self.assertEqual(
            self.get_perms("dirg", annex),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertEqual(
            self.get_perms("agent", task),
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
        self.assertHasNoPerms("agent1", task)
        self.assertHasNoPerms("encodeur", task)

        self.pw.doActionFor(omail, "mark_as_sent")

        self.assertEqual(
            self.get_perms("chef", omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("lecteur", omail)
        self.assertEqual(
            self.get_perms("dirg", omail),
            {
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", omail)
        self.assertEqual(
            self.get_perms("encodeur", omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
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
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", file)
        self.assertEqual(
            self.get_perms("encodeur", file),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertEqual(
            self.get_perms("chef", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
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
                "Access contents information": False,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", annex)
        self.assertEqual(
            self.get_perms("encodeur", annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Review portal content": True,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("chef", task)
        self.assertHasNoPerms("lecteur", task)
        self.assertHasNoPerms("dirg", task)
        self.assertEqual(
            self.get_perms("agent", task),
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
        self.assertHasNoPerms("agent1", task)
        self.assertHasNoPerms("encodeur", task)
