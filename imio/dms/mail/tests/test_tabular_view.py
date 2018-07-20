# -*- coding: utf-8 -*-
#from plone.dexterity.utils import createContentInContainer
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestTabularView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_render_field(self):
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        view = self.portal.unrestrictedTraverse('incoming-mail/mail-searches/all_mails/@@tabular_view')
