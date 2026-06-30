# -*- coding: utf-8 -*-
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from imio.dms.mail.interfaces import IPersonnelDashboard
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
            ["all_requests", "to_approve", "to_treat", "in_my_group", "in_copy", "in_esign_sessions",
             "searchfor_created", "searchfor_to_approve", "searchfor_to_be_signed", "searchfor_signed",
             "searchfor_closed"],
        )

    def test_personnel_folder_is_faceted_dashboard(self):
        pf = self.portal["contacts"]["personnel-folder"]
        # personnel-folder is itself the faceted dashboard (not redirected to a subfolder)
        self.assertTrue(IFacetedNavigable.providedBy(pf))
        self.assertTrue(IPersonnelDashboard.providedBy(pf))
        # no content default page must shadow the faceted layout: an empty/leftover
        # default_page makes __browser_default__ return [''] and raises Unauthorized
        self.assertFalse(pf.hasProperty("default_page"))
        self.assertEqual(pf.__browser_default__(pf.REQUEST)[1], ["facetednavigation_view"])
        # only persons may be added (no sub-folders)
        self.assertEqual(list(pf.getLocallyAllowedTypes()), ["person"])

    def test_personnel_dashboard_filter_and_collection(self):
        pf = self.portal["contacts"]["personnel-folder"]
        # the dashboard exposes a left-column 'usages' (signataire/approbateur) facet filter
        indexes = [getattr(c, "index", None) for c in ICriteria(pf).values()]
        self.assertIn("usages", indexes)
        # the default collection lists personnel persons only (held positions are excluded)
        coll = pf["personnel-searches"]["all_personnel"]
        query_indexes = [q["i"] for q in coll.query]
        self.assertIn("portal_type", query_indexes)
        self.assertIn("object_provides", query_indexes)

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
