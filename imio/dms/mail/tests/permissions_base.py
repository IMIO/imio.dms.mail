# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestPermissionsBase(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.pw = api.portal.get_tool("portal_workflow")
        change_user(self.portal)

    def get_perms(self, userid, obj):
        perms = (
            "Access contents information",
            "Add portal content",
            "Delete objects",
            "Modify portal content",
            "Request review",
            "Review portal content",
            "View",
            "collective.dms.basecontent: Add DmsFile",
            "imio.dms.mail: Write mail base fields",
            "imio.dms.mail: Write treating group field",
        )
        return {perm: api.user.has_permission(perm, userid, obj=obj) for perm in perms}

    def assertHasAllPerms(self, userid, obj):
        self.assertTrue(all(self.get_perms(userid, obj).values()))

    def assertHasNoPerms(self, userid, obj):
        self.assertFalse(any(self.get_perms(userid, obj).values()))

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()


class TestPermissionsBaseIncomingMail(TestPermissionsBase):
    def setUp(self):
        super(TestPermissionsBaseIncomingMail, self).setUp()
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "courrier",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
        }
        change_user(self.portal, "encodeur")
        self.imail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)
        self.annex = api.content.create(container=self.imail, id="annex", type="dmsappendixfile")
        self.file = api.content.create(container=self.imail, id="file", type="dmsmainfile")
        self.task = api.content.create(container=self.imail, id="task", type="task", assigned_group=self.imail.treating_groups)

    def permissions_incoming_mail(self):
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.imail)
        self.assertHasNoPerms("dirg", self.imail)
        self.assertHasNoPerms("agent", self.imail)
        self.assertHasNoPerms("agent1", self.imail)
        self.assertHasAllPerms("encodeur", self.imail)

        self.assertHasNoPerms("lecteur", self.file)
        self.assertHasNoPerms("dirg", self.file)
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertHasAllPerms("encodeur", self.file)

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertHasNoPerms("dirg", self.annex)
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertHasAllPerms("encodeur", self.annex)

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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

        self.pw.doActionFor(self.imail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.imail)
        self.assertEqual(
            self.get_perms("dirg", self.imail),
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
        self.assertHasNoPerms("agent", self.imail)
        self.assertHasNoPerms("agent1", self.imail)
        self.assertEqual(
            self.get_perms("encodeur", self.imail),
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

        self.assertHasNoPerms("lecteur", self.file)
        self.assertEqual(
            self.get_perms("dirg", self.file),
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
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertEqual(
            self.get_perms("dirg", self.annex),
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
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
        self.pw.doActionFor(self.imail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.imail),
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
            self.get_perms("dirg", self.imail),
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
            self.get_perms("agent", self.imail),
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
        self.assertHasNoPerms("agent1", self.imail)
        self.assertEqual(
            self.get_perms("encodeur", self.imail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
        self.pw.doActionFor(self.imail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.imail),
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
            self.get_perms("dirg", self.imail),
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
            self.get_perms("agent", self.imail),
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
        self.assertHasNoPerms("agent1", self.imail)
        self.assertEqual(
            self.get_perms("encodeur", self.imail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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

        self.pw.doActionFor(self.imail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.imail),
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
            self.get_perms("dirg", self.imail),
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
            self.get_perms("agent", self.imail),
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
        self.assertHasNoPerms("agent1", self.imail)
        self.assertEqual(
            self.get_perms("encodeur", self.imail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
    

class TestPermissionsBaseOutgoingMail(TestPermissionsBase):
    def setUp(self):
        super(TestPermissionsBaseOutgoingMail, self).setUp()
        intids = getUtility(IIntIds)
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "type1",
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
        }
        change_user(self.portal, "agent")
        self.omail = sub_create(self.omf, "dmsoutgoingmail", datetime.today(), "my-id", **params)
        self.annex = api.content.create(container=self.omail, id="annex", type="dmsappendixfile")
        self.file = api.content.create(container=self.omail, id="file", type="dmsommainfile")
        self.task = api.content.create(container=self.omail, id="task", type="task", assigned_group=self.omail.treating_groups)

    def permissions_outgoing_mail(self):
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("dirg", self.omail)
        self.assertHasAllPerms("agent", self.omail)
        self.assertHasNoPerms("agent1", self.omail)
        self.assertHasNoPerms("encodeur", self.omail)

        self.assertEqual(
            self.get_perms("lecteur", self.file),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("dirg", self.file)
        self.assertHasAllPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertHasNoPerms("encodeur", self.file)

        self.assertEqual(
            self.get_perms("lecteur", self.annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("dirg", self.annex)
        self.assertHasAllPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertHasNoPerms("encodeur", self.annex)

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertEqual(
            self.get_perms("agent", self.task),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent1", self.task)
        self.assertHasNoPerms("encodeur", self.annex)

        self.pw.doActionFor(self.omail, "propose_to_be_signed")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.omail),
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
            self.get_perms("dirg", self.omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.omail),
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
        self.assertHasNoPerms("agent1", self.omail)
        self.assertEqual(
            self.get_perms("encodeur", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
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

        self.assertEqual(
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
            {
                "Access contents information": True,
                "Add portal content": False,
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

        self.assertEqual(
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
            {
                "Access contents information": True,
                "Add portal content": False,
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertEqual(
            self.get_perms("agent", self.task),
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
        self.assertHasNoPerms("agent1", self.omail)
        self.assertHasNoPerms("encodeur", self.task)

        self.pw.doActionFor(self.omail, "back_to_creation")
        clean_borg_cache(self.portal.REQUEST)
        change_user(self.portal, "scanner")
        self.pw.doActionFor(self.omail, "set_scanned")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", self.omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.omail),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", self.omail)
        self.assertEqual(
            self.get_perms("encodeur", self.omail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", self.file),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", self.file),
            # TODO check for "all false" perms and replace with hasNoPerms
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.file),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertEqual(
            self.get_perms("lecteur", self.annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", self.annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.annex),
            {
                "Access contents information": False,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": False,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": True,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertEqual(
            self.get_perms("agent", self.task),
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
        self.assertHasNoPerms("agent1", self.task)
        self.assertHasNoPerms("encodeur", self.task)

        self.pw.doActionFor(self.omail, "mark_as_sent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.omail),
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
            self.get_perms("dirg", self.omail),
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
        self.assertEqual(
            self.get_perms("agent", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
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
        self.assertHasNoPerms("agent1", self.omail)
        self.assertEqual(
            self.get_perms("encodeur", self.omail),
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

        self.assertEqual(
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
        self.assertEqual(
            self.get_perms("agent", self.file),
            {
                "Access contents information": True,
                "Add portal content": False,
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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

        self.assertEqual(
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
        self.assertEqual(
            self.get_perms("agent", self.annex),
            {
                "Access contents information": True,
                "Add portal content": False,
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertEqual(
            self.get_perms("agent", self.task),
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
        self.assertHasNoPerms("agent1", self.task)
        self.assertHasNoPerms("encodeur", self.task)


class TestPermissionsBaseIncomingEmail(TestPermissionsBase):
    def setUp(self):
        super(TestPermissionsBaseIncomingEmail, self).setUp()
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "email",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
        }
        change_user(self.portal, "encodeur")
        self.iemail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)
        self.annex = api.content.create(container=self.iemail, id="annex", type="dmsappendixfile")
        self.file = api.content.create(container=self.iemail, id="file", type="dmsmainfile")
        self.task = api.content.create(container=self.iemail, id="task", type="task", assigned_group=self.iemail.treating_groups)

    def permissions_incoming_email(self):
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.iemail)
        self.assertHasNoPerms("dirg", self.iemail)
        self.assertHasNoPerms("agent", self.iemail)
        self.assertHasNoPerms("agent1", self.iemail)
        self.assertHasAllPerms("encodeur", self.iemail)

        self.assertHasNoPerms("lecteur", self.file)
        self.assertHasNoPerms("dirg", self.file)
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertHasAllPerms("encodeur", self.file)

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertHasNoPerms("dirg", self.annex)
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertHasAllPerms("encodeur", self.annex)

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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

        self.pw.doActionFor(self.iemail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.iemail)
        self.assertEqual(
            self.get_perms("dirg", self.iemail),
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
        self.assertHasNoPerms("agent", self.iemail)
        self.assertHasNoPerms("agent1", self.iemail)
        self.assertEqual(
            self.get_perms("encodeur", self.iemail),
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

        self.assertHasNoPerms("lecteur", self.file)
        self.assertEqual(
            self.get_perms("dirg", self.file),
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
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertEqual(
            self.get_perms("dirg", self.annex),
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
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
        self.pw.doActionFor(self.iemail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.iemail),
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
            self.get_perms("dirg", self.iemail),
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
            self.get_perms("agent", self.iemail),
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
        self.assertHasNoPerms("agent1", self.iemail)
        self.assertEqual(
            self.get_perms("encodeur", self.iemail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
        self.pw.doActionFor(self.iemail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.iemail),
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
            self.get_perms("dirg", self.iemail),
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
            self.get_perms("agent", self.iemail),
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
        self.assertHasNoPerms("agent1", self.iemail)
        self.assertEqual(
            self.get_perms("encodeur", self.iemail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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

        self.pw.doActionFor(self.iemail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("lecteur", self.iemail),
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
            self.get_perms("dirg", self.iemail),
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
            self.get_perms("agent", self.iemail),
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
        self.assertHasNoPerms("agent1", self.iemail)
        self.assertEqual(
            self.get_perms("encodeur", self.iemail),
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
            self.get_perms("lecteur", self.file),
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
            self.get_perms("dirg", self.file),
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
            self.get_perms("agent", self.file),
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
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("lecteur", self.annex),
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
            self.get_perms("dirg", self.annex),
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
            self.get_perms("agent", self.annex),
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
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
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
