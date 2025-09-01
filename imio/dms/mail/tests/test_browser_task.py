# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail.browser.task import filter_task_assigned_users
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers
from imio.helpers.vocabularies import SimplySortedUsers
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestBrowserTask(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")

    def test_filter_task_assigned_users(self):
        self.assertEqual(len(filter_task_assigned_users(None)), 0)
        selected_orgs = get_registry_organizations()
        voc = filter_task_assigned_users(selected_orgs[0])
        self.assertListEqual([t.title for t in voc._terms], [])  # direction generale => no user
        voc = filter_task_assigned_users(selected_orgs[1])
        self.assertListEqual([t.title for t in voc._terms], [u"Fred Agent", u"Jean Encodeur"])

    def test_AssignedUsersVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, "collective.task.AssignedUsers")
        self.assertIsInstance(voc_inst, SimplySortedUsers)
        # value is userid and not username
        self.assertListEqual(
            sorted([t.value for t in voc_inst(None)]),
            ["agent", "agent1", "bourgmestre", "chef", "dirg", "encodeur", "lecteur", "scanner", "siteadmin",
             "test_user_1_"],
        )
        self.assertListEqual(
            [t.title for t in voc_inst(None)],
            [
                u"Fred Agent",
                u"Jean Encodeur",
                u"Jef Lecteur",
                u"Maxime DG",
                u"Michel Chef",
                u"Paul BM",
                u"siteadmin",
                u"Scanner",
                u"Stef Agent",
                u"test_user_1_",
            ],
        )
