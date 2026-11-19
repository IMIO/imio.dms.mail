# -*- coding: utf-8 -*-
from imio.dms.mail.Extensions.maintenance import DISABLED_OM_TEMPLATES_KEY
from imio.dms.mail.Extensions.maintenance import MAINTENANCE_MSG_ID
from imio.dms.mail.Extensions.maintenance import OM_ADD_PERMISSION
from imio.dms.mail.Extensions.maintenance import om_add_roles
from imio.dms.mail.Extensions.maintenance import om_temp_deactivation
from imio.dms.mail.Extensions.maintenance import REMOVED_OM_ADD_ROLES_KEY
from imio.dms.mail.Extensions.maintenance import set_om_add_roles
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from zope.annotation.interfaces import IAnnotations

import unittest


class TestMaintenance(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.om_folder = self.portal["templates"]["om"]

    def test_om_temp_deactivation(self):
        self.change_user("agent")
        self.assertEqual(om_temp_deactivation(self.portal), "You must be a zope administrator to run this script")
        self.change_user("admin")
        main = self.om_folder["main"]
        mailing = self.om_folder["mailing"]
        receipt = self.om_folder["common"]["receipt"]
        self.assertTrue(main.enabled)
        self.assertEqual(om_add_roles(self.portal), ["Contributor", "Manager", "Site Administrator"])
        set_om_add_roles(self.portal, ["Contributor", "Editor", "Manager", "Site Administrator"])
        receipt.enabled = False  # disabled before: must stay disabled
        self.assertIn("action parameter must be 'disable' or 'enable'",
                      om_temp_deactivation(self.portal, action="bad"))
        # disable
        out = om_temp_deactivation(self.portal, action="disable")
        self.assertIn("Disabled: {}".format("/".join(main.getPhysicalPath())), out)
        self.assertFalse(main.enabled)
        self.assertFalse(mailing.enabled)
        self.assertFalse(api.content.find(UID=main.UID(), enabled=True))
        msg = self.portal["messages-config"][MAINTENANCE_MSG_ID]
        self.assertEqual(api.content.get_state(msg), "activated")
        stored = IAnnotations(self.portal)[DISABLED_OM_TEMPLATES_KEY]
        self.assertIn(main.UID(), stored)
        self.assertNotIn(receipt.UID(), stored)
        self.assertIn("disabled (not handled by script): {}".format("/".join(receipt.getPhysicalPath())), out)
        self.assertEqual(om_add_roles(self.portal), ["Manager"])
        self.assertEqual(IAnnotations(self.portal)[REMOVED_OM_ADD_ROLES_KEY],
                         ["Contributor", "Editor", "Site Administrator"])
        self.assertTrue(self.portal.acquiredRolesAreUsedBy(OM_ADD_PERMISSION))
        self.change_user("agent")
        self.assertFalse(api.user.has_permission(OM_ADD_PERMISSION, obj=self.portal["outgoing-mail"]))
        self.change_user("admin")
        # a role re-added manually in between
        set_om_add_roles(self.portal, ["Manager", "Site Administrator"])
        # a template is created since: shown as enabled, then caught by a new disabling
        new = api.content.copy(source=main, target=self.om_folder, id="new-main")
        new.enabled = True
        new.reindexObject()
        self.assertIn("ENABLED: {}".format("/".join(new.getPhysicalPath())), om_temp_deactivation(self.portal))
        om_temp_deactivation(self.portal, action="disable")
        self.assertFalse(new.enabled)
        self.assertIn(new.UID(), stored)
        # a template is deleted since
        new_path = "/".join(new.getPhysicalPath())
        api.content.delete(new)
        # enable
        out = om_temp_deactivation(self.portal, action="enable")
        self.assertIn("Deleted since disabling, ignored: {}".format(new_path), out)
        self.assertTrue(main.enabled)
        self.assertTrue(api.content.find(UID=main.UID(), enabled=True))
        self.assertTrue(mailing.enabled)
        self.assertFalse(receipt.enabled)
        self.assertNotIn(DISABLED_OM_TEMPLATES_KEY, IAnnotations(self.portal))
        self.assertEqual(api.content.get_state(msg), "inactive")
        # message reactivated on a new disabling
        om_temp_deactivation(self.portal, action="disable")
        self.assertEqual(api.content.get_state(msg), "activated")
        om_temp_deactivation(self.portal, action="enable")
        self.assertEqual(om_add_roles(self.portal), ["Contributor", "Editor", "Manager", "Site Administrator"])
        self.assertNotIn(REMOVED_OM_ADD_ROLES_KEY, IAnnotations(self.portal))
        self.change_user("agent")
        self.assertTrue(api.user.has_permission(OM_ADD_PERMISSION, obj=self.portal["outgoing-mail"]))
