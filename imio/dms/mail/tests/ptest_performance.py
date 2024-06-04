# -*- coding: utf-8 -*-
from __future__ import print_function
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from imio.dms.mail.testing import add_user_in_groups
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_groups
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.cache import extract_wrapped
from imio.pyutils.utils import ftimed
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone import api
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


# Commons


def check_catalog_following_groups(self, init=False, nb=100):
    # login(self.portal, TEST_USER_NAME)
    if init:
        user = api.user.create("test@test.be", "newuser", "Password#1")
    user = self.portal.acl_users.getUserById("newuser")
    pc = self.portal.portal_catalog
    criterias = {"portal_type": "dmsincomingmail"}
    # starting with normal groups
    groups_nb = len(api.group.get_groups(username="newuser"))
    login(self.portal, "newuser")
    print(
        u"catalog._listAllowedRolesAndUsers ({}): {} groups, in {}".format(
            nb, groups_nb, ftimed(lambda: pc._listAllowedRolesAndUsers(user), nb)
        )
    )
    print(
        u"catalog.searchResults ({}): {} groups, in {}".format(
            nb, groups_nb, ftimed(lambda: pc.searchResults(criterias), nb)
        )
    )
    # adding new groups
    if init:
        create_groups(self, 500)
    for j in range(0, 10):
        if init:
            add_user_in_groups(self, "newuser", 10 * (j + 1), (10 * j) + 1)
        user = self.portal.acl_users.getUserById("newuser")
        groups_nb = len(api.group.get_groups(user=user))
        print(
            u"catalog._listAllowedRolesAndUsers ({}): {} groups, in {}".format(
                nb, groups_nb, ftimed(lambda: pc._listAllowedRolesAndUsers(user), nb)[0]
            )
        )
        print(
            u"catalog.searchResults ({}): {} groups, in {}".format(
                nb, groups_nb, ftimed(lambda: pc.searchResults(criterias), nb)[0]
            )
        )
    self.assertTrue(
        self.portal.portal_catalog._listAllowedRolesAndUsers(self.portal.acl_users.getUserById("newuser")) > 100
    )


class TestPerformance(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_voc_selected_org_suffix_users(self):
        org_uid = self.portal.contacts["plonegroup-organization"]["direction-generale"]["secretariat"].UID()
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(
            u"voc_selected_org_suffix_users ({}) without n_plus: in {}".format(
                nb, ftimed(lambda: voc_selected_org_suffix_users(org_uid, ["editeur"]), nb)[0]
            )
        )
        print(
            u"voc_selected_org_suffix_users ({}) with 5 n_plus: in {}".format(
                nb,
                ftimed(
                    lambda: voc_selected_org_suffix_users(
                        org_uid, ["editeur", "n_plus_1", "n_plus_2", "n_plus_3", "n_plus_4", "n_plus_5"]
                    ),
                    nb,
                )[0],
            )
        )

    def test_organizations_with_suffixes(self):
        org_uid = self.portal.contacts["plonegroup-organization"]["direction-generale"]["secretariat"].UID()
        suffixes = ("editeur", "lecteur")
        groups = ["{}_{}".format(org_uid, suffix) for suffix in suffixes]
        # __builtin__.__dict__.update(locals())
        nb = 100
        print(
            u"organizations_with_suffixes ({}) without n_plus: in {}".format(
                nb, ftimed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)
            )
        )
        suffixes = ("editeur", "lecteur", "n_plus_1", "n_plus_2", "n_plus_3", "n_plus_4", "n_plus_5")
        # __builtin__.__dict__.update(locals())
        print(
            u"organizations_with_suffixes ({}) with 5 n_plus: in {}".format(
                nb, ftimed(lambda: organizations_with_suffixes(groups, suffixes, group_as_str=True), nb)
            )
        )

    def test_catalog_following_groups(self):
        check_catalog_following_groups(self, init=True)

    def test_IMMailTypesVocabulary_caching(self):
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.IMMailTypesVocabulary")
        # this is cached
        print(
            u"vocabularies.IMMailTypesVocabulary cached ({}) in {}".format(
                1, ftimed(lambda: voc_inst(self.portal), 1)[0]
            )
        )
        print(
            u"vocabularies.IMMailTypesVocabulary cached ({}) in {}".format(
                10, ftimed(lambda: voc_inst(self.portal), 10)[0]
            )
        )
        # original function without cache
        orig_func = extract_wrapped(voc_inst.__call__)
        print(
            u"vocabularies.IMMailTypesVocabulary not cached ({}) in {}".format(
                1, ftimed(lambda: orig_func(voc_inst, self.portal), 1)[0]
            )
        )
        print(
            u"vocabularies.IMMailTypesVocabulary not cached ({}) in {}".format(
                10, ftimed(lambda: orig_func(voc_inst, self.portal), 10)[0]
            )
        )
        voc_list = [(t.value, t.title) for t in voc_inst(None)]
        self.assertListEqual(
            voc_list,
            [
                (u"courrier", u"Courrier"),
                (u"recommande", u"Recommandé"),
                (u"certificat", u"Certificat médical"),
                (u"fax", u"Fax"),
                (u"retour-recommande", u"Retour recommandé"),
                (u"facture", u"Facture"),
            ],
        )

    def test_getGroups(self):
        user = api.user.get(userid="dirg")
        print(u"dirg getGroups in {}".format(ftimed(lambda: user.getGroups(), 1)))
        user = api.user.get(userid="chef")
        print(u"chef getGroups in {}".format(ftimed(lambda: user.getGroups(), 1)))
        user = api.user.get(userid="agent")
        print(u"agent getGroups in {}".format(ftimed(lambda: user.getGroups(), 1)))
