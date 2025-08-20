# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseIncomingEmail


class TestPermissionsIncomingEmail(TestPermissionsBaseIncomingEmail):
    def test_permissions_incoming_email(self):
        self.permissions_incoming_email()