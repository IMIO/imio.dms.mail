# -*- coding: utf-8 -*-
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import __builtin__
import time
import unittest


def timed(f, number=1000):
    start = time.time()
    for i in range(number):
        ret = f()
    elapsed = time.time() - start
    return elapsed/number, ret


class TestPerformance(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_voc_selected_org_suffix_users(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        __builtin__.__dict__.update(locals())
        t0 = timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur']))[0]
        t1 = timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur', 'n_plus_1', 'n_plus_2',
                                                                   'n_plus_3', 'n_plus_4', 'n_plus_5']))[0]
