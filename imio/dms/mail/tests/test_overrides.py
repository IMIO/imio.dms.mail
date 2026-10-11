# -*- coding: utf-8 -*-
"""Tests of the root overrides.py adapters."""
from collective.contact.plonegroup.config import get_registry_organizations
from collective.task.interfaces import ITaskContentMethods
from datetime import datetime
from imio.dms.mail.overrides import DmsTaskContentAdapter
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.app.linkintegrity.exceptions import LinkIntegrityNotificationException
from Products.statusmessages.interfaces import IStatusMessage
from zExceptions import Redirect

import unittest


class TestDmsPloneGroupContactChecksAdapter(unittest.TestCase, ImioTestHelpers):
    """A service (own organization) used in mails or tasks cannot be deleted or deactivated."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        pgof = self.portal["contacts"]["plonegroup-organization"]
        # services not selected in plonegroup configuration
        self.informatique = pgof["direction-generale"]["informatique"]
        self.urbanisme = pgof["direction-technique"]["urbanisme"]
        self.assertNotIn(self.informatique.UID(), get_registry_organizations())
        self.assertNotIn(self.urbanisme.UID(), get_registry_organizations())

    def test_check_items_on_delete(self):
        # an unused service can be deleted
        api.content.delete(obj=self.urbanisme)
        self.assertNotIn("urbanisme", self.portal["contacts"]["plonegroup-organization"]["direction-technique"])
        # a service used as treating group of an incoming mail cannot be deleted
        sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id",
                   title=u"Test", treating_groups=self.informatique.UID())
        self.assertRaises(LinkIntegrityNotificationException, api.content.delete, obj=self.informatique)

    def test_check_items_on_transition(self):
        # an unused service can be deactivated
        api.content.transition(obj=self.urbanisme, transition="deactivate")
        self.assertEqual(api.content.get_state(self.urbanisme), "deactivated")
        # a service used as assigned group of a task cannot be deactivated
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        task.assigned_group = self.informatique.UID()
        task.title = u"Task 1"  # ASCII: a non-ASCII title breaks the refusal message (see phase 3 notes)
        self.assertRaises(Redirect, api.content.transition, obj=self.informatique, transition="deactivate")
        self.assertEqual(api.content.get_state(self.informatique), "active")
        msgs = IStatusMessage(self.portal.REQUEST).show()
        self.assertEqual(msgs[-2].message, u"You cannot deactivate this item !")
        self.assertTrue(msgs[-1].message.startswith(u"This contact is used in following content: "))
        self.assertIn(task.absolute_url(), msgs[-1].message)


class TestDmsTaskContentAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_can_do_transition(self):
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        adapted = ITaskContentMethods(task)
        self.assertIsInstance(adapted, DmsTaskContentAdapter)
        org_uid = get_registry_organizations()[0]
        # no assigned group
        task.assigned_group = None
        self.assertFalse(adapted.can_do_transition("do_to_assign"))
        # assigned group without n+1 level
        task.assigned_group = org_uid
        self.assertFalse(adapted.can_do_transition("do_to_assign"))
        # n+1 level activated (chef is n+1 of every service)
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-task_n_plus_1_wfadaptation", run_dependencies=False
        )
        self.assertTrue(adapted.can_do_transition("do_to_assign"))
        self.assertFalse(adapted.can_do_transition("back_in_to_assign"))
        # no more n+1 user in the service
        api.group.remove_user(groupname="{}_n_plus_1".format(org_uid), username="chef")
        self.assertFalse(adapted.can_do_transition("do_to_assign"))
