# -*- coding: utf-8 -*-
"""Test browser overrides."""
from imio.dms.mail.browser.overrides import ClassificationJSONCollectionsCount
from imio.dms.mail.browser.overrides import ContentActionsViewlet
from imio.dms.mail.browser.overrides import DocsCKTemplateListingView
from imio.dms.mail.browser.overrides import DocsGroupsOverviewControlPanel
from imio.dms.mail.browser.overrides import DocsUsersOverviewControlPanel
from imio.dms.mail.browser.overrides import DocumentBylineViewlet
from imio.dms.mail.browser.overrides import FacetedCollectionPortletRenderer
from imio.dms.mail.browser.overrides import IMRenderCategoryView
from imio.dms.mail.browser.overrides import LockInfoViewlet
from imio.dms.mail.browser.overrides import LockingOperations
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone import api
from plone.app.testing import login
from plone.browserlayer.utils import registered_layers
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from webdav.LockItem import LockItem
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.interface import alsoProvides
from zope.security.management import endInteraction
from zope.security.management import newInteraction

import json
import unittest


class TestIMRenderCategoryView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def render(self, path):
        view = self.portal.unrestrictedTraverse(path).unrestrictedTraverse("@@render_collection_widget_category")
        self.assertIsInstance(view, IMRenderCategoryView)
        return view(widget=None)

    def test_contact_infos(self):
        view = IMRenderCategoryView(self.portal["contacts"]["orgs-searches"], self.portal.REQUEST)
        infos = view.contact_infos()
        self.assertListEqual(sorted(infos.keys()), ["cls-searches", "hps-searches", "orgs-searches",
                                                    "persons-searches"])
        # skin images (Plone 6: to be replaced)
        self.assertListEqual(
            [infos[key]["img"] for key in ("orgs-searches", "hps-searches", "persons-searches", "cls-searches")],
            ["organization_icon.png", "create_contact.png", "person_icon.png", "directory_icon.png"],
        )

    def test__get_category_template(self):
        # incoming mail dashboard: add icons for mail and email
        rendered = self.render("incoming-mail/mail-searches")
        self.assertIn(u'href="http://nohost/plone/incoming-mail/++add++dmsincomingmail?no_redirect=1"', rendered)
        self.assertIn(u'href="http://nohost/plone/incoming-mail/++add++dmsincoming_email?no_redirect=1"', rendered)
        self.assertIn(u'src="http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png"', rendered)
        # outgoing mail dashboard
        rendered = self.render("outgoing-mail/mail-searches")
        self.assertIn(u'href="http://nohost/plone/outgoing-mail/++add++dmsoutgoingmail?no_redirect=1"', rendered)
        # signing requests dashboard
        rendered = self.render("requests/requests-searches")
        self.assertIn(u'href="http://nohost/plone/requests/++add++sign_request?no_redirect=1"', rendered)
        # classification folders dashboard
        rendered = self.render("folders/folder-searches")
        self.assertIn(u'href="http://nohost/plone/folders/++add++ClassificationFolder?no_redirect=1"', rendered)
        self.assertIn(u'href="http://nohost/plone/folders/@@import?no_redirect=1"', rendered)
        # contacts dashboards: skin images and overlays
        rendered = self.render("contacts/orgs-searches")
        self.assertIn(u'href="http://nohost/plone/contacts/++add++organization"', rendered)
        self.assertIn(u'class="overlay"', rendered)
        self.assertIn(u'src="http://nohost/plone/organization_icon.png"', rendered)
        rendered = self.render("contacts/hps-searches")
        self.assertIn(u'href="http://nohost/plone/contacts/@@add-contact"', rendered)
        self.assertIn(u'src="http://nohost/plone/create_contact.png"', rendered)
        rendered = self.render("contacts/persons-searches")
        self.assertIn(u'src="http://nohost/plone/person_icon.png"', rendered)
        rendered = self.render("contacts/cls-searches")
        self.assertIn(u'href="http://nohost/plone/contacts/contact-lists-folder"', rendered)
        self.assertIn(u'src="http://nohost/plone/directory_icon.png"', rendered)
        self.assertNotIn(u'class="overlay"', rendered)
        # other dashboard: only the category title
        rendered = self.render("tasks/task-searches")
        self.assertNotIn(u"portlet_add_icons", rendered)
        self.assertIn(u'<div class="title">', rendered)
        # a reader has no add icon
        change_user(self.portal, "lecteur")
        IAnnotations(self.portal.REQUEST).pop("plone.memoize")  # plone_portal_state member is memoized
        rendered = self.render("incoming-mail/mail-searches")
        self.assertNotIn(u"++add++dmsincomingmail", rendered)


class TestDocumentBylineViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")

    def test_show(self):
        viewlet = DocumentBylineViewlet(self.im1, self.portal.REQUEST, None, None)
        self.assertTrue(viewlet.show())
        viewlet = DocumentBylineViewlet(self.portal["incoming-mail"]["mail-searches"], self.portal.REQUEST, None,
                                        None)
        self.assertFalse(viewlet.show())

    def test_creator(self):
        viewlet = DocumentBylineViewlet(self.im1, self.portal.REQUEST, None, None)
        self.assertIsNone(viewlet.creator())
        viewlet = DocumentBylineViewlet(self.om1, self.portal.REQUEST, None, None)
        self.assertEqual(viewlet.creator(), self.om1.Creator())


class TestLockInfoViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_lock_is_stealable(self):
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        # webdav lock, as set by zopeedit (not a plone.locking stealable lock)
        lock = LockItem(api.user.get_current().getUser())
        omf.wl_setLock(lock.getLockToken(), lock)
        viewlet = LockInfoViewlet(omf, self.portal.REQUEST, None, None)
        # external editor enabled type: always stealable
        self.assertTrue(viewlet.lock_is_stealable())
        api.portal.set_registry_record("externaleditor.externaleditor_enabled_types", [])
        viewlet = LockInfoViewlet(omf, self.portal.REQUEST, None, None)
        self.assertFalse(viewlet.lock_is_stealable())


class TestLockingOperations(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_force_unlock(self):
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        omf.restrictedTraverse("lock-unlock")()
        self.assertTrue(omf.wl_isLocked())
        view = omf.restrictedTraverse("@@plone_lock_operations")
        self.assertIsInstance(view, LockingOperations)
        view.force_unlock()
        self.assertFalse(omf.wl_isLocked())
        self.assertEqual(self.portal.REQUEST.response.getHeader("Location"), "{}/view".format(omf.absolute_url()))


class TestPloneView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_showEditableBorder(self):
        view = get_object(oid="courrier1", ptype="dmsincomingmail").unrestrictedTraverse("@@plone")
        self.assertEqual(view.showEditableBorder(), False)
        view = self.portal["front-page"].unrestrictedTraverse("@@plone")
        self.assertEqual(view.showEditableBorder(), True)


class TestPhysicalNavigationBreadcrumbs(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        for layer in registered_layers():
            alsoProvides(self.request, layer)
        change_user(self.portal)

    def test_breadcrumbs(self):
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        crumbs = getMultiAdapter((im1["tache1"], self.request), name="breadcrumbs_view").breadcrumbs()
        # the hidden period folder isn't displayed but the urls are right
        self.assertListEqual(
            [(safe_unicode(dic["Title"]), dic["absolute_url"]) for dic in crumbs],
            [
                (u"Entrant", u"http://nohost/plone/incoming-mail"),
                (u"E0001 - Courrier 1", im1.absolute_url()),
                (u"Tâche 1", im1["tache1"].absolute_url()),
            ],
        )


class TestContentActionsViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def viewlet(self, context):
        view = BrowserView(context, self.portal.REQUEST)
        viewlet = ContentActionsViewlet(context, self.portal.REQUEST, view, None)
        viewlet.update()
        return viewlet

    def test_render(self):
        self.assertEqual(self.viewlet(self.portal).render(), "")
        self.assertEqual(self.viewlet(self.portal["front-page"]).render(), "")
        sreq, files = create_sign_request(self.portal, oid="sr-ca", nb_files=1)
        self.assertEqual(self.viewlet(files[0]).render(), "")
        # rendered elsewhere (as in a published request, with a security interaction)
        newInteraction()
        try:
            rendered = self.viewlet(self.portal["contacts"]).render()
        finally:
            endInteraction()
        self.assertIn(u'id="contentActionMenus"', rendered)


class TestIDMUtilsMethods(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_outgoingmail_folder(self):
        portal = self.layer["portal"]
        view = portal.unrestrictedTraverse("@@cdmc-utils")
        self.assertEqual(view.outgoingmail_folder(), portal["outgoing-mail"])


class TestBaseOverviewControlPanel(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST

    def test_portal_roles(self):
        users = DocsUsersOverviewControlPanel(self.portal, self.request)
        self.assertListEqual(users.portal_roles, ["Batch importer", "Manager", "Member", "Site Administrator"])
        groups = DocsGroupsOverviewControlPanel(self.portal, self.request)
        self.assertListEqual(groups.portal_roles, ["Manager", "Member", "Site Administrator"])

    def test_doSearch(self):
        # site administrator: roles cannot be assigned, users cannot be deleted
        change_user(self.portal)
        view = DocsUsersOverviewControlPanel(self.portal, self.request)
        results = view.doSearch("agent")
        self.assertListEqual(sorted([res["userid"] for res in results]), ["agent", "agent1"])
        for res in results:
            self.assertFalse(res["can_delete"])
            self.assertFalse(any([dic["canAssign"] for dic in res["roles"].values()]))
        view = DocsGroupsOverviewControlPanel(self.portal, self.request)
        results = view.doSearch("Administrators")
        self.assertIn("Administrators", [res["groupid"] for res in results])
        for res in results:
            self.assertFalse(any([dic["canAssign"] for dic in res["roles"].values()]))
        # zope admin: unchanged
        login(self.layer["app"], "admin")
        view = DocsUsersOverviewControlPanel(self.portal, self.request)
        results = view.doSearch("agent")
        self.assertTrue(all([res["roles"]["Member"]["canAssign"] for res in results]))


class TestDocsCKTemplateListingView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.view = DocsCKTemplateListingView(self.portal, self.portal.REQUEST)
        self.tpl = self.portal["templates"]["oem"]["emain"]

    def test_get_templates(self):
        templates = self.view.get_templates()
        self.assertIn((self.tpl, "/".join(self.tpl.getPhysicalPath())), templates)

    def test_render_template(self):
        self.tpl.title = u'Mon "modèle"'
        rendered = self.view.render_template(self.tpl, "")
        self.assertTrue(rendered.startswith(u'{title: "Mon &quot;modèle&quot;", description: "", html: "'))
        IAnnotations(self.tpl)["dmsmail.cke_tpl_tit"] = u"Service"
        rendered = self.view.render_template(self.tpl, "")
        self.assertTrue(rendered.startswith(u'{title: "Service > Mon &quot;modèle&quot;"'))
        # whole javascript
        js = self.view()
        self.assertTrue(js.startswith("CKEDITOR.addTemplates('default',"))
        self.assertIn(u'title: "Service > Mon &quot;modèle&quot;"', js)


class TestFacetedCollectionPortletRenderer(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test__criteriaHolder(self):
        msf = self.portal["incoming-mail"]["mail-searches"]
        renderer = FacetedCollectionPortletRenderer(msf, self.portal.REQUEST, None, None, None)
        self.assertEqual(renderer._criteriaHolder, msf)
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        renderer = FacetedCollectionPortletRenderer(im1, self.portal.REQUEST, None, None, None)
        self.assertEqual(renderer._criteriaHolder, self.portal["incoming-mail"])
        renderer = FacetedCollectionPortletRenderer(self.portal["front-page"], self.portal.REQUEST, None, None,
                                                    None)
        self.assertIsNone(renderer._criteriaHolder)


class TestClassificationJSONCollectionsCount(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_get_context(self):
        view = ClassificationJSONCollectionsCount(self.portal["folders"], self.portal.REQUEST)
        self.assertEqual(view.get_context(self.portal["folders"]), self.portal["folders"])
        self.assertEqual(view.get_context(self.portal["front-page"]), self.portal)
        res = json.loads(view())
        self.assertIn("countByCollection", res)
