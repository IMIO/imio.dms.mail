# -*- coding: utf-8 -*-
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from imio.dms.mail.interfaces import IPersonnelDashboard
from imio.dms.mail.setuphandlers import list_templates
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

    def test_add_templates_order(self):
        self.assertEqual([o.getId() for o in self.portal["templates"].objectValues()],
                         ['om', 'oem', 'd-im-listing', 'd-im-listing-tab', 'd-im-listing-tab-details',
                          'all-contacts-export', 'export-users-groups', 'audit-contacts'])
        for tup in list_templates():
            parts = tup[1].split("/")
            folder = self.portal.unrestrictedTraverse("/".join(parts[:-1]))
            self.assertEqual(folder.getObjectPosition(parts[-1]), tup[3], parts[-1])
        # subfolders are not moved: om stays first in templates, common first in om
        self.assertEqual(self.portal["templates"]["om"].getObjectPosition("common"), 10)

    def test_requests_dashboard(self):
        self.assertTrue(hasattr(self.portal, "requests"))
        req_folder = self.portal["requests"]
        self.assertIn("requests-searches", req_folder)
        col_folder = req_folder["requests-searches"]
        self.assertEqual(
            [c.getId() for c in col_folder.listFolderContents()],
            ["all_requests", "to_approve", "to_treat", "in_my_group", "in_copy", "in_esign_sessions",
             "searchfor_created", "searchfor_to_approve", "searchfor_to_be_signed", "searchfor_signed",
             "searchfor_closed"],
        )

    def test_personnel_folder_is_faceted_dashboard(self):
        pf = self.portal["contacts"]["personnel-folder"]
        # personnel-folder is the faceted dashboard
        self.assertTrue(IFacetedNavigable.providedBy(pf))
        self.assertTrue(IPersonnelDashboard.providedBy(pf))
        self.assertFalse(pf.hasProperty("default_page"))
        self.assertEqual(pf.__browser_default__(pf.REQUEST)[1], ["facetednavigation_view"])
        self.assertEqual(list(pf.getLocallyAllowedTypes()), ["person"])

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

    def test_setup_iconified_categories(self):
        brains = self.portal.portal_catalog.unrestrictedSearchResults(
            portal_type=["ContentCategory", "ContentSubcategory"])
        self.assertTrue(brains)
        for brain in brains:
            self.assertFalse(brain._unrestrictedGetObject().predefined_title)

    def ttest_addTemplates(self):
        self.assertIn("templates", self.portal)
        self.assertEqual(len(self.portal["templates"].listFolderContents()), 2)
