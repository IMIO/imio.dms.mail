# -*- coding: utf-8 -*-
from __future__ import print_function

from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone import api
from profilehooks import timecall


import __builtin__
import time
import unittest


def timed(f, nb=100):
    start = time.time()
    for i in range(nb):
        ret = f()
    elapsed = time.time() - start
    return elapsed/nb, ret


class TestPerformance(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_voc_selected_org_suffix_users(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(u'voc_selected_org_suffix_users without n_plus: called {} times in {}'.format(
            nb, timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur']), nb)))
        print(u'voc_selected_org_suffix_users with 5 n_plus: called {} times in {}'.format(
            nb, timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'n_plus_1', 'n_plus_2',
                                                                      'n_plus_3', 'n_plus_4', 'n_plus_5']), nb)))

    def test_organizations_with_suffixes(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        suffixes = ('editeur', 'lecteur')
        groups = ['{}_{}'.format(org_uid, suffix) for suffix in suffixes]
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(u'organizations_with_suffixes without n_plus: called {} times in {}'.format(
            nb, timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)))
        suffixes = ('editeur', 'lecteur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5')
        # __builtin__.__dict__.update(locals())
        print(u'organizations_with_suffixes with 5 n_plus: called {} times in {}'.format(
            nb, timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)))

    def test_listAllowedRolesAndUsers(self):
        nb = 100
        user = api.user.get(userid='agent')
        pc = self.portal.portal_catalog
        print(u'portal_catalog._listAllowedRolesAndUsers for agent: called {} times in {}'.format(
            nb, timed(lambda: pc._listAllowedRolesAndUsers(user), nb)))
