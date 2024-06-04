# -*- coding: utf-8 -*-
from __future__ import print_function

from imio.dms.mail.testing import create_im_mails
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.tests.ptest_performance import check_catalog_following_groups
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestMass(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_mass0(self):
        return  # avoid long test if not needed
        for j in range(0, 10):
            nb = 1000
            create_im_mails(self, start=nb * j + 1, end=nb * (j + 1), senders=[], transitions=["propose_to_agent"])
            check_catalog_following_groups(self, init=(j == 0))

    def test_mass1(self):
        """Test creation time in one or multiple folders"""
        return  # avoid long test if not needed
        nb = 5000
        create_im_mails(self, start=1, end=nb, by_days=200)  # in multiple directories
        create_im_mails(self, start=nb + 1, end=2 * nb, by_days=20000)  # in one directory
