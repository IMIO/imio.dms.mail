# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.interfaces import IPersonnelDashboard
from imio.dms.mail.setuphandlers import add_transforms
from imio.dms.mail.setuphandlers import HiddenProfiles
from imio.dms.mail.setuphandlers import list_templates
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import login
from plone.app.testing import SITE_OWNER_NAME
from Products.CMFPlone.utils import safe_unicode
from zope.annotation.interfaces import IAnnotations

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
        self.assertTrue(ICountableTab.providedBy(req_folder))
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

    def test_add_transforms(self):
        ptr = self.portal.portal_transforms
        for name in ("pdf_to_text", "pdf_to_html", "odt_to_text"):
            self.assertIn(name, ptr.objectIds())
        ptr.manage_delObjects(["odt_to_text"])
        add_transforms(self.portal)
        self.assertIn("odt_to_text", ptr.objectIds())
        # an odt document is converted to text (header, footer and images excluded)
        with open("{}/batchimport/toprocess/requests/3-degradation-voirie.odt".format(PRODUCT_DIR), "rb") as fo:
            data = ptr.convertTo("text/plain", fo.read(), mimetype="application/vnd.oasis.opendocument.text")
        self.assertTrue(
            safe_unicode(data.getData()).startswith(u"IMIO012999800000012\nAgent traitant : Michel Chef\n")
        )

    def test_set_portlet(self):
        portlet = IAnnotations(self.portal)["plone.portlets.contextassignments"]["plone.leftcolumn"][
            "portlet_actions"
        ]
        portlet.ptitle = u"Actions"
        portlet.show_icons = True
        set_portlet(self.portal)
        # the left actions portlet shows the object_portlet actions without icons
        self.assertEqual(portlet.ptitle, u"Liens divers")
        self.assertEqual(portlet.category, u"object_portlet")
        self.assertFalse(portlet.show_icons)
        self.assertIsNone(portlet.default_icon)

    def test_clean_examples_step(self):
        pc = self.portal.portal_catalog
        login(self.layer["app"], SITE_OWNER_NAME)  # clean_examples needs the zope admin
        # not run outside the examples-minimal profile
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:default", "imiodmsmail-clean-examples", run_dependencies=False
        )
        self.assertEqual(len(pc(portal_type="dmsincomingmail")), 9)
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:examples-minimal", "imiodmsmail-clean-examples", run_dependencies=False
        )
        # demo mails, users and services are removed
        self.assertEqual(len(pc(portal_type=["dmsincomingmail", "dmsincoming_email"])), 0)
        self.assertListEqual([brain.id for brain in pc(portal_type="dmsoutgoingmail")], ["test_creation_modele"])
        for userid in ("encodeur", "dirg", "chef", "agent", "agent1", "lecteur", "bourgmestre"):
            self.assertIsNone(api.user.get(userid=userid), userid)
        own_org = self.portal["contacts"]["plonegroup-organization"]
        self.assertListEqual(get_registry_organizations(), [own_org["college-communal"].UID()])
        self.assertListEqual(own_org.objectIds(), ["college-communal"])
        for oid in ("electrabel", "swde", "jeancourant"):
            self.assertNotIn(oid, self.portal["contacts"])

    def test_HiddenProfiles(self):
        self.assertListEqual(HiddenProfiles().getNonInstallableProfiles(), ["imio.dms.mail:singles"])

    def ttest_addTemplates(self):
        self.assertIn("templates", self.portal)
        self.assertEqual(len(self.portal["templates"].listFolderContents()), 2)
