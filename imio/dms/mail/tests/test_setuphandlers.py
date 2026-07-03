# -*- coding: utf-8 -*-
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING

import unittest


class TestSetuphandlers(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_postInstall(self):
        self.assertTrue(hasattr(self.portal, "incoming-mail"))
        self.assertTrue(hasattr(self.portal, "outgoing-mail"))

    def test_requests_dashboard(self):
        self.assertTrue(hasattr(self.portal, "requests"))
        req_folder = self.portal["requests"]
        self.assertIn("requests-searches", req_folder)
        col_folder = req_folder["requests-searches"]
        self.assertEqual(
            [c.getId() for c in col_folder.listFolderContents()],
            ["all_requests", "to_approve", "to_treat", "in_my_group", "in_copy", "searchfor_created",
             "searchfor_to_approve", "searchfor_to_be_signed", "searchfor_signed", "searchfor_closed"],
        )

    def test_adaptDefaultPortal(self):
        # ltool = self.portal.portal_languages
        # defaultLanguage = 'fr'
        # supportedLanguages = ['en','fr']
        # ltool.manage_setLanguageSettings(defaultLanguage, supportedLanguages, setUseCombinedLanguageCodes=False)
        # ltool.setLanguageBindings()
        self.assertFalse(hasattr(self.portal, "news"))
        self.assertFalse(hasattr(self.portal, "events"))
        # check front-page modification
        self.assertIn("Gestion du courrier", self.portal["front-page"].Title())
        # check old Topic activation
        self.assertTrue("Collection (old-style)" in [pt.title for pt in self.portal.allowedContentTypes()])

    def ttest_addTemplates(self):
        self.assertIn("templates", self.portal)
        self.assertEqual(len(self.portal["templates"].listFolderContents()), 2)
