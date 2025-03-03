# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api

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
            "Review portal content",
            "View",
            "collective.dms.basecontent: Add DmsFile",
            "imio.dms.mail: Write mail base fields",
            "imio.dms.mail: Write treating group field",
        )
        perms = {perm: api.user.has_permission(perm, userid, obj=obj) for perm in perms}
        return perms

    def assertHasAllPerms(self, userid, obj):
        self.assertTrue(all(self.get_perms(userid, obj).values()))

    def assertHasNoPerms(self, userid, obj):
        self.assertFalse(any(self.get_perms(userid, obj).values()))
