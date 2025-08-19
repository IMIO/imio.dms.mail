# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseOutgoingMail


class TestPermissionsOutgoingMail(TestPermissionsBaseOutgoingMail):
    def test_permissions_outgoing_mail(self):
        self.permissions_outgoing_mail()