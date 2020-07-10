# -*- coding: utf-8 -*-
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import __builtin__
import time
import unittest


def timed(f, number=100):
    start = time.time()
    for i in range(number):
        ret = f()
    elapsed = time.time() - start
    return elapsed/number, ret


def pt(comment, elapsed):
    print u"{}: '{}' sec".format(comment, elapsed[0])
    return elapsed[0]


class TestPerformance(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_voc_selected_org_suffix_users(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        __builtin__.__dict__.update(locals())
        t0 = pt(u'voc_selected_org_suffix_users without n_plus',
                timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur'])))
        t1 = pt(u'voc_selected_org_suffix_users with 5 n_plus',
                timed(lambda: voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur', 'n_plus_1', 'n_plus_2',
                                                                      'n_plus_3', 'n_plus_4', 'n_plus_5'])))

    def test_organizations_with_suffixes(self):
        org_uid = self.portal.contacts['plonegroup-organization']['direction-generale']['secretariat'].UID()
        suffixes = ('validateur', 'editeur', 'lecteur')
        groups = ['{}_{}'.format(org_uid, suffix) for suffix in suffixes]
        __builtin__.__dict__.update(locals())
        t0 = pt(u'organizations_with_suffixes without n_plus',
                timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True)))
        suffixes = ('validateur', 'editeur', 'lecteur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5')
        __builtin__.__dict__.update(locals())
        t1 = pt(u'organizations_with_suffixes with 5 n_plus',
                timed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True)))
