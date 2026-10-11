# -*- coding: utf-8 -*-
"""Test viewlets."""
from collective.iconifiedcategory.interfaces import ICategorizedApproved
from collective.iconifiedcategory.interfaces import ICategorizedSigned
from collective.messagesviewlet.message import PseudoMessage
from imio.dms.mail.browser.viewlets import CKBatchActionsViewlet
from imio.dms.mail.browser.viewlets import ContactContentBackrefsViewlet
from imio.dms.mail.browser.viewlets import ContextInformationViewlet
from imio.dms.mail.browser.viewlets import DMSTaskParentViewlet
from imio.dms.mail.browser.viewlets import ImioFacetedSessionInfoViewlet
from imio.dms.mail.browser.viewlets import ImioFooterViewlet
from imio.dms.mail.browser.viewlets import ImioItemSessionInfoViewlet
from imio.dms.mail.browser.viewlets import IMVersionsViewlet
from imio.dms.mail.browser.viewlets import OMVersionsViewlet
from imio.dms.mail.browser.viewlets import PrettyLinkTitleViewlet
from imio.dms.mail.browser.viewlets import SignRequestVersionsViewlet
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.Extensions.demo import activate_signing
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.esign.utils import add_files_to_session
from imio.esign.utils import create_session
from imio.helpers.content import get_object
from plone import api
from plone.app.layout.globals.interfaces import IViewView
from plone.app.testing import login
from plone.browserlayer.utils import registered_layers
from Products.Five import BrowserView
from zope.component import getMultiAdapter
from zope.interface import alsoProvides
from zope.viewlet.interfaces import IViewlet
from zope.viewlet.interfaces import IViewletManager

import unittest


def get_viewlet(context, name, manager_name, view_name=None):
    """Get a registered viewlet, as rendered on a page (request marked with the installed browser layers)."""
    request = context.REQUEST
    for layer in registered_layers():
        alsoProvides(request, layer)
    view = BrowserView(context, request)
    if view_name:
        view.__name__ = view_name
    alsoProvides(view, IViewView)
    manager = getMultiAdapter((context, request, view), IViewletManager, name=manager_name)
    viewlet = getMultiAdapter((context, request, view, manager), IViewlet, name=name)
    viewlet.update()
    return viewlet


class TestContactContentBackrefsViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.ctct = self.portal["contacts"]
        self.elec = self.ctct["electrabel"]
        self.jean = self.ctct["jeancourant"]
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]

    def test_backrefs(self):
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        # configure to see all refs
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view", True)
        self.assertListEqual(
            [self.portal.unrestrictedTraverse(b.getPath()) for b in viewlet.backrefs()],
            [
                get_object(oid="reponse7", ptype="dmsoutgoingmail"),
                get_object(oid="reponse1", ptype="dmsoutgoingmail"),
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            ],
        )
        # configure to see only permitted refs
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.all_backrefs_view", False)
        self.assertListEqual(viewlet.backrefs(), [])
        # login to get view permission
        login(self.portal, "encodeur")
        self.assertListEqual(
            [b.getObject() for b in viewlet.backrefs()],
            [
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            ],
        )

    def test_render(self):
        login(self.portal, "encodeur")
        viewlet = get_viewlet(self.elec, "collective.contact.core.backrefs", "plone.belowcontentbody")
        self.assertIsInstance(viewlet, ContactContentBackrefsViewlet)
        rendered = viewlet.render()
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertIn(im1.absolute_url(), rendered)
        # not rendered in an overlay
        viewlet.request["ajax_load"] = "1"
        self.assertEqual(viewlet.render(), "")

    def test_find_relations(self):
        login(self.portal, "encodeur")
        viewlet = ContactContentBackrefsViewlet(self.elec, self.elec.REQUEST, None)
        ret = viewlet.find_relations(from_attribute="sender")
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            },
        )
        ret = viewlet.find_relations(from_interfaces_flattened=IImioDmsIncomingMail)
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier7", ptype="dmsincomingmail"),
                get_object(oid="courrier1", ptype="dmsincomingmail"),
            },
        )
        # call on person
        viewlet = ContactContentBackrefsViewlet(self.jean, self.jean.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(
            set([b.getObject() for b in ret]),
            {
                get_object(oid="courrier3", ptype="dmsincomingmail"),
                get_object(oid="courrier9", ptype="dmsincomingmail"),
            },
        )
        # call on held position
        agent = self.jean["agent-electrabel"]
        viewlet = ContactContentBackrefsViewlet(agent, agent.REQUEST, None)
        ret = viewlet.find_relations()
        self.assertSetEqual(set([b.getObject() for b in ret]), {get_object(oid="courrier5", ptype="dmsincomingmail")})

    def test_ContextInformationViewlet(self):
        login(self.portal, "encodeur")
        org_v = ContextInformationViewlet(self.elec, self.elec.REQUEST, None)
        self.assertListEqual(org_v.getAllMessages(), [])
        sorg_v = ContextInformationViewlet(self.elec["travaux"], self.elec.REQUEST, None)
        self.assertTrue(self.elec["travaux"].use_parent_address)
        self.assertListEqual(sorg_v.getAllMessages(), [])
        pers_v = ContextInformationViewlet(self.jean, self.elec.REQUEST, None)
        self.assertEqual(len(pers_v.getAllMessages()), 1)  # no address
        hp_v = ContextInformationViewlet(self.jean["agent-electrabel"], self.elec.REQUEST, None)
        self.assertTrue(self.jean["agent-electrabel"].use_parent_address)
        self.assertListEqual(hp_v.getAllMessages(), [])
        om_v = ContextInformationViewlet(get_object(oid="reponse1", ptype="dmsoutgoingmail"), self.elec.REQUEST, None)
        self.assertListEqual(om_v.getAllMessages(), [])
        # removing street from electrabel org
        self.elec.street = None
        msgs = org_v.getAllMessages()
        self.assertEqual(len(msgs), 1)
        self.assertTrue(isinstance(msgs[0], PseudoMessage))
        self.assertIn("missing address fields: street", msgs[0].text.output)
        self.assertEqual(len(sorg_v.getAllMessages()), 1)  # suborganization has missing street too
        self.assertEqual(len(hp_v.getAllMessages()), 1)  # held position has missing street too
        self.assertEqual(len(om_v.getAllMessages()), 1)  # outgoing mail has missing street too


class TestDMSTaskParentViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_render(self):
        portal = self.layer["portal"]
        change_user(portal)
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        viewlet = get_viewlet(im1["tache1"], "collective.task.task_parent", "plone.abovecontentbody")
        self.assertIsInstance(viewlet, DMSTaskParentViewlet)
        self.assertFalse(viewlet.display_above_element)
        self.assertIn(im1.absolute_url(), viewlet.render())


class TestVersionsViewlets(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_render(self):
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        viewlet = get_viewlet(im1, "dms.files", "dms.abovecontent")
        self.assertIsInstance(viewlet, IMVersionsViewlet)
        rendered = viewlet.render()
        self.assertIn(u"<legend>Versions</legend>", rendered)
        self.assertIn(u'<a class="version-link" href="{}"'.format(im1.objectValues()[0].absolute_url()), rendered)
        self.assertIn(u'<th class="th_header_filesize-column">', rendered)
        om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        viewlet = get_viewlet(om1, "dms.files", "dms.abovecontent")
        self.assertIsInstance(viewlet, OMVersionsViewlet)
        rendered = viewlet.render()
        self.assertIn(u"<th>To be printed</th>", rendered)
        self.assertIn(u'<a class="version-link" href="{}"'.format(om1["1"].absolute_url()), rendered)

    def test__prepare_table_render(self):
        sreq, files = create_sign_request(self.portal, oid="sr-viewlet", nb_files=1)
        viewlet = get_viewlet(sreq, "dms.files", "dms.abovecontent")
        self.assertIsInstance(viewlet, SignRequestVersionsViewlet)
        rendered = viewlet.render()
        self.assertTrue(ICategorizedSigned.providedBy(viewlet.table))
        self.assertTrue(ICategorizedApproved.providedBy(viewlet.table))
        self.assertIn(u'<a class="version-link" href="{}"'.format(files[0].absolute_url()), rendered)


class TestPrettyLinkTitleViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")

    def test_adapted(self):
        viewlet = PrettyLinkTitleViewlet(self.im1, self.im1.REQUEST, None, None)
        plo = viewlet.adapted()
        self.assertTrue(plo.showContentIcon)
        self.assertFalse(plo.showColors)
        self.assertFalse(plo.isViewable)
        self.assertEqual(
            plo.getLink(),
            u"<div class='pretty_link'><span class='pretty_link_icons'><img title='Incoming Mail' "
            u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png' "
            u"style=\"width: 16px; height: 16px;\" /></span><span class='pretty_link_content'>E0001 - Courrier 1 "
            u"</span></div>",
        )

    def test_render(self):
        viewlet = get_viewlet(self.im1, "pretty-link-title", "plone.belowcontenttitle")
        self.assertIsInstance(viewlet, PrettyLinkTitleViewlet)
        rendered = viewlet.render()
        self.assertIn(u'<h1 id="parent-fieldname-title" class="documentFirstHeading keep-it">', rendered)
        self.assertIn(u"<span class='pretty_link_content'>E0001 - Courrier 1 </span>", rendered)
        task = self.im1["tache1"]
        rendered = get_viewlet(task, "pretty-link-title", "plone.belowcontenttitle").render()
        self.assertIn(u"Tâche 1", rendered)


class TestCKBatchActionsViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_available(self):
        portal = self.layer["portal"]
        change_user(portal)
        oem = portal["templates"]["oem"]
        viewlet = get_viewlet(oem, "collective.eeafaceted.batchactions", "plone.belowcontentbody",
                              view_name="ck-templates-listing")
        self.assertIsInstance(viewlet, CKBatchActionsViewlet)
        self.assertTrue(viewlet.available())
        viewlet = get_viewlet(oem, "collective.eeafaceted.batchactions", "plone.belowcontentbody",
                              view_name="view")
        self.assertFalse(viewlet.available())


class TestImioFooterViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_update(self):
        portal = self.layer["portal"]
        api.portal.set_registry_record("imio.dms.mail.product_version", u"4.0.1")
        viewlet = get_viewlet(portal, "plone.footer", "plone.portalfooter")
        self.assertIsInstance(viewlet, ImioFooterViewlet)
        self.assertEqual(viewlet.version, u"4.0.1")
        self.assertEqual(viewlet.dashversion, u"4-0-1")
        rendered = viewlet.render()
        self.assertIn(u'<div id="portal-footer">', rendered)
        self.assertIn(u">4.0.1</a>", rendered)
        self.assertIn(u"version-4-0-1", rendered)
        api.portal.set_registry_record("imio.dms.mail.product_version", u"")
        viewlet = get_viewlet(portal, "plone.footer", "plone.portalfooter")
        self.assertEqual(viewlet.version, "unknown")


class TestGlobalSectionsViewlet(unittest.TestCase):
    """plone.global_sections viewlet with imio.dms.mail sections.pt template."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_render(self):
        portal = self.layer["portal"]
        change_user(portal)
        imf = portal["incoming-mail"]
        imf.REQUEST["URL"] = imf.absolute_url()
        rendered = get_viewlet(imf, "plone.global_sections", "plone.portalheader").render()
        self.assertIn(u'<li id="portaltab-incoming-mail" class="selected">', rendered)
        self.assertIn(u'<a href="http://nohost/plone/incoming-mail" title="">Entrant</a>', rendered)
        self.assertIn(u'<li id="portaltab-plus" class="plain">', rendered)
        # Font Awesome refresh icon and read mode toggle
        self.assertIn(u'<span class="fa fa-sync-alt" id="collections-count-refresh"', rendered)
        self.assertIn(u'<li id="read_mode_icon"', rendered)
        self.assertIn(u'onclick="toggle_dms_document_view(this);"', rendered)
        # the plus tab is the last one
        self.assertGreater(rendered.index(u"portaltab-plus"), rendered.index(u"portaltab-tasks"))
        # no read mode toggle outside documents sections
        ctf = portal["contacts"]
        ctf.REQUEST["URL"] = ctf.absolute_url()
        rendered = get_viewlet(ctf, "plone.global_sections", "plone.portalheader").render()
        self.assertNotIn(u'id="read_mode_icon"', rendered)


class TestImioFacetedSessionInfoViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        activate_signing(self.portal)
        self.signers = [("dirg", "dirg@macommune.be", u"Maxime DG", u"Directeur Général")]
        self.om_sid, _session = create_session(self.signers)
        add_files_to_session(self.signers, [get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"].UID()],
                             session_id=self.om_sid)
        self.omsf = self.portal["outgoing-mail"]["mail-searches"]

    def test_sessions_collection_uid(self):
        viewlet = ImioFacetedSessionInfoViewlet(self.omsf, self.omsf.REQUEST, None, None)
        self.assertEqual(viewlet.sessions_collection_uid, "__not_needed__")

    def test__esign_collection(self):
        # not a dashboard
        viewlet = ImioFacetedSessionInfoViewlet(self.portal["front-page"], self.portal.REQUEST, None, None)
        self.assertIsNone(viewlet._esign_collection)
        # default collection
        rsf = self.portal["requests"]["requests-searches"]
        viewlet = ImioFacetedSessionInfoViewlet(rsf, rsf.REQUEST, None, None)
        self.assertIsNone(viewlet._esign_collection)
        # esign sessions collection
        collection = self.omsf["in_esign_sessions"]
        self.omsf.REQUEST.form["c1[]"] = collection.UID()
        viewlet = ImioFacetedSessionInfoViewlet(self.omsf, self.omsf.REQUEST, None, None)
        self.assertEqual(viewlet._esign_collection, collection)

    def test_available(self):
        viewlet = ImioFacetedSessionInfoViewlet(self.omsf, self.omsf.REQUEST, None, None)
        self.assertFalse(viewlet.available())
        self.assertEqual(viewlet.render(), "")

    def test_render(self):
        self.omsf.REQUEST.form["c1[]"] = self.omsf["in_esign_sessions"].UID()
        viewlet = get_viewlet(self.omsf, "esign-faceted-session-info", "collective.eeafaceted.z3ctable.topabovenav")
        self.assertIsInstance(viewlet, ImioFacetedSessionInfoViewlet)
        self.assertTrue(viewlet.available())
        # sessions listing table
        rendered = viewlet.render()
        self.assertEqual(viewlet.request.get("esign_portal_type"), "dmsoutgoingmail")
        self.assertIn(u"<table", rendered)
        self.assertIn(u"esign_session_id={}".format(self.om_sid), rendered)
        # selected session
        self.omsf.REQUEST.form["esign_session_id[]"] = str(self.om_sid)
        viewlet = get_viewlet(self.omsf, "esign-faceted-session-info", "collective.eeafaceted.z3ctable.topabovenav")
        rendered = viewlet.render()
        self.assertIn(u"http://nohost/plone/@@parapheo", rendered)


class TestImioItemSessionInfoViewlet(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.viewlet = ImioItemSessionInfoViewlet(self.om1, self.om1.REQUEST, None, None)

    def test_get_table_rows(self):
        self.assertListEqual(self.viewlet.get_table_rows(1), ["session_id", "state"])
        self.assertListEqual(self.viewlet.get_table_rows(2), ["external_link", "update_date"])
        self.assertListEqual(self.viewlet.get_table_rows(3), [])

    def test_session_listing_url(self):
        self.assertEqual(self.viewlet.session_listing_url, "http://nohost/plone/@@parapheo")

    def test_collapsible_css_default(self):
        self.assertEqual(self.viewlet.collapsible_css_default(), "collapsible discreet active")

    def test_collapsible_content_css_default(self):
        self.assertEqual(self.viewlet.collapsible_content_css_default(), "collapsible-content discreet")

    def test_render(self):
        viewlet = get_viewlet(self.om1, "esign-item-session-info", "plone.belowcontenttitle")
        self.assertIsInstance(viewlet, ImioItemSessionInfoViewlet)
        self.assertEqual(viewlet.render(), "")
        activate_signing(self.portal)
        signers = [("dirg", "dirg@macommune.be", u"Maxime DG", u"Directeur Général")]
        sid, _session = create_session(signers)
        add_files_to_session(signers, [self.om1["1"].UID()], session_id=sid)
        viewlet = get_viewlet(self.om1, "esign-item-session-info", "plone.belowcontenttitle")
        rendered = viewlet.render()
        self.assertIn(u"collapsible discreet active", rendered)
        self.assertIn(u"http://nohost/plone/@@parapheo", rendered)
