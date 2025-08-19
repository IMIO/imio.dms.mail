# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseIncomingMail


class TestPermissionsIncomingMail(TestPermissionsBaseIncomingMail):
    def test_permissions_incoming_mail(self):
        self.permissions_incoming_mail()
