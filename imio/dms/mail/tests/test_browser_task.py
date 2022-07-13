# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail.browser.task import filter_task_assigned_users
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers

import unittest


class TestBrowserTask(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.change_user('siteadmin')

    def test_filter_task_assigned_users(self):
        self.assertEqual(len(filter_task_assigned_users(None)), 0)
        selected_orgs = get_registry_organizations()
        voc = filter_task_assigned_users(selected_orgs[0])
        self.assertListEqual([t.title for t in voc._terms], [])  # direction generale => no user
        voc = filter_task_assigned_users(selected_orgs[1])
        self.assertListEqual([t.title for t in voc._terms], [u'Fred Agent'])
