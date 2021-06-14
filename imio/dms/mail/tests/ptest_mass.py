# -*- coding: utf-8 -*-
from __future__ import print_function

from imio.dms.mail.testing import create_im_mails
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from profilehooks import timecall

import unittest


class TestMass(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_mass0(self):
        nb = 100
        print('Creating {} incoming mails'.format(nb))
        login(self.portal, 'encodeur')
        create_im_mails(self, nb, start=1, senders=[], transitions=['propose_to_agent'])
        logout()
