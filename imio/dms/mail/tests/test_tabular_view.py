# -*- coding: utf-8 -*-
import unittest2 as unittest
from zope.component import getMultiAdapter, getUtility
from plone.app.testing import setRoles, TEST_USER_ID, TEST_USER_NAME, login, logout
#from plone.dexterity.utils import createContentInContainer
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING


class TestTabularView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_render_field(self):
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        view = self.portal.unrestrictedTraverse('incoming-mail/mail-searches/all_mails/@@tabular_view')
