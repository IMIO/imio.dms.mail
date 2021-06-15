# -*- coding: utf-8 -*-
from __future__ import print_function

from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from imio.dms.mail.testing import add_user_in_groups
from imio.dms.mail.testing import create_groups
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone import api

import time
import unittest


def timed(f, nb=100):
    start = time.time()
    for i in range(nb):
        ret = f()
    elapsed = time.time() - start
    return elapsed/nb, ret


# Commons

def check_catalog_following_groups(self):
    user = api.user.create('test@test.be', 'newuser', 'Password#1')
    nb = 100
    pc = self.portal.portal_catalog
    criterias = {'portal_type': 'dmsincomingmail'}
    # starting with normal groups
    groups_nb = len(api.group.get_groups(user=user))
    login(self.portal, 'newuser')
    print(u'catalog._listAllowedRolesAndUsers ({}): {} groups, in {}'.format(
        nb, groups_nb, timed(lambda: pc._listAllowedRolesAndUsers(user), nb)))
    print(u'catalog.searchResults ({}): {} groups, in {}'.format(
        nb, groups_nb, timed(lambda: pc.searchResults(criterias), nb)))
    login(self.portal, TEST_USER_NAME)
    # adding new groups
    create_groups(self, 500)
    for j in range(0, 10):
        login(self.portal, TEST_USER_NAME)
        add_user_in_groups(self, 'newuser', (10*j)+10, (10*j)+1)
        # groups_nb = len(api.group.get_groups(user=user))
        groups_nb = (j+1)*10+1
        login(self.portal, 'newuser')
        user = self.portal.acl_users.getUserById('newuser')
        print(u'catalog._listAllowedRolesAndUsers ({}): {} groups, in {}'.format(
            nb, groups_nb, timed(lambda: pc._listAllowedRolesAndUsers(user), nb)[0]))
        print(u'catalog.searchResults ({}): {} groups, in {}'.format(
            nb, groups_nb, timed(lambda: pc.searchResults(criterias), nb)[0]))


class TestPerformance(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_voc_selected_org_suffix_users(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(u'voc_selected_org_suffix_users ({}) without n_plus: in {}'.format(
            nb, timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur']), nb)[0]))
        print(u'voc_selected_org_suffix_users ({}) with 5 n_plus: in {}'.format(
            nb, timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'n_plus_1', 'n_plus_2',
                                                                      'n_plus_3', 'n_plus_4', 'n_plus_5']), nb)[0]))

    def test_organizations_with_suffixes(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        suffixes = ('editeur', 'lecteur')
        groups = ['{}_{}'.format(org_uid, suffix) for suffix in suffixes]
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(u'organizations_with_suffixes ({}) without n_plus: in {}'.format(
            nb, timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)))
        suffixes = ('editeur', 'lecteur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5')
        # __builtin__.__dict__.update(locals())
        print(u'organizations_with_suffixes ({}) with 5 n_plus: in {}'.format(
            nb, timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)))

    def test_catalog_following_groups(self):
        check_catalog_following_groups(self)
