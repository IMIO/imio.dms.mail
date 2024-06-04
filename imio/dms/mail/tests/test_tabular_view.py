# -*- coding: utf-8 -*-
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING

import unittest


class TestTabularView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_render_field(self):
        change_user(self.portal)
        self.portal.unrestrictedTraverse("incoming-mail/mail-searches/all_mails/@@tabular_view")
