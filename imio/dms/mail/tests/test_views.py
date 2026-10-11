# -*- coding: utf-8 -*-
"""Test views."""

from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.utils import calculate_category_id
from collective.MockMailHost.MockMailHost import MockMailHost
from datetime import datetime
from HTMLParser import HTMLParser
from imio.dms.mail import _
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.browser.views import ApprovalTableView
from imio.dms.mail.browser.views import CreateFromTemplateForm
from imio.dms.mail.browser.views import ImioCatalogNavigationTabs
from imio.dms.mail.browser.views import ImioExternalSessionCreateView
from imio.dms.mail.browser.views import ImioRecreateSessionView
from imio.dms.mail.browser.views import ImioRemoveItemFromSessionView
from imio.dms.mail.browser.views import ImioSessionsListingView
from imio.dms.mail.browser.views import parse_query
from imio.dms.mail.browser.views import SessionAnnotationInfoView
from imio.dms.mail.Extensions.demo import activate_signing
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.interfaces import ISignRequestApproval
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.esign.config import set_esign_registry_enabled
from imio.esign.config import set_esign_registry_file_url
from imio.esign.utils import add_files_to_session
from imio.esign.utils import create_session
from imio.esign.utils import get_session_annotation
from imio.helpers.content import get_object
from imio.helpers.content import richtextval
from imio.helpers.emailer import get_mail_host
from imio.helpers.test_helpers import ImioTestHelpers
from persistent.list import PersistentList
from plone import api
from plone.app.testing import login
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import safe_unicode
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield import RelationValue
from zExceptions import Unauthorized
from zope.component import getUtility
from zope.intid import IIntIds

import json
import unittest


class TestCreateFromTemplateForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)
        self.omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.view = self.omail.unrestrictedTraverse("@@create-from-template")

    def test_label(self):
        self.assertIsInstance(self.view, CreateFromTemplateForm)
        self.assertEqual(self.view.label(), u"S0001 - Réponse 1: create from template")

    def test_get_action_name(self):
        self.assertEqual(self.view.get_action_name(), u"Choose this template")

    def test_get_query(self):
        self.assertDictEqual(
            self.view.get_query(),
            {
                "path": {"query": "/plone/templates/om", "depth": -1},
                "portal_type": ("Folder", "ConfigurablePODTemplate"),
                "enabled": True,
            },
        )
        # only enabled templates in non empty folders are proposed
        data = json.loads(self.view.get_data())
        self.assertListEqual(
            [(node["title"], node["folder"]) for node in data],
            [(u"Modèle de base", False), (u"Modèles communs", True), (u"Direction générale - Secrétariat", True)],
        )
        main = self.portal["templates"]["om"]["main"]
        main.enabled = False
        main.reindexObject()
        data = json.loads(self.view.get_data())
        self.assertNotIn(main.UID(), [node["key"] for node in data])

    def test_redirect_url(self):
        self.assertEqual(
            self.view.redirect_url("abc"),
            "{}/persistent-document-generation?template_uid=abc&output_format=odt".format(self.omail.absolute_url()),
        )

    def test_call(self):
        # GET: the fancytree form
        self.request["REQUEST_METHOD"] = "GET"
        rendered = self.view()
        self.assertIn(u"<h1>S0001 - Réponse 1: create from template</h1>", rendered)
        self.assertIn(u'<form id="tree-form" method="post"', rendered)
        self.assertIn(u'<div id="tree" data-nodes="[{&quot;folder&quot;: false', rendered)
        self.assertIn(u'<input name="uid" type="hidden" value="" />', rendered)
        self.assertIn(u'<input type="submit" value="Choose this template" />', rendered)
        # POST: redirect to the generation view
        main = self.portal["templates"]["om"]["main"]
        self.request.method = "POST"
        self.request.form["uid"] = main.UID()
        self.request["uid"] = main.UID()
        self.assertEqual(self.view(), "")
        self.assertEqual(
            self.request.response.getHeader("Location"),
            "{}/persistent-document-generation?template_uid={}&output_format=odt".format(
                self.omail.absolute_url(), main.UID()
            ),
        )


class TestContactSuggest(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.ctct = self.portal["contacts"]
        self.elec = self.ctct["electrabel"]
        self.pf = self.ctct["personnel-folder"]
        self.pgo = self.portal["contacts"]["plonegroup-organization"]

    def test_parse_query(self):
        self.assertEqual(parse_query("dir*"), {"SearchableText": "dir*"})
        self.assertEqual(parse_query("director(organization)"), {"SearchableText": "director* AND organization*"})

    def test_call_ContactSuggest(self):
        imail1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        view = imail1.unrestrictedTraverse("@@contact-autocomplete-suggest")
        # no term
        self.assertEqual(view(), "[]")
        # term electra
        view.request["term"] = "electra"
        ret = json.loads(view())
        self.assertEqual(ret.pop(0), {"text": "Electrabel", "id": self.elec.UID()})
        self.assertEqual(ret.pop(0), {"text": "Electrabel / Travaux 1", "id": self.elec["travaux"].UID()})
        self.assertEqual(
            ret.pop(0),
            {
                "text": "Monsieur Jean Courant, Agent (Electrabel)",
                "id": self.ctct["jeancourant"]["agent-electrabel"].UID(),
            },
        )
        self.assertEqual(ret.pop(0), {"text": "Monsieur Jean Courant", "id": self.ctct["jeancourant"].UID()})
        self.assertEqual(ret.pop(0), {"text": "Electrabel [TOUT]", "id": "l:%s" % self.elec.UID()})
        self.assertEqual(
            ret.pop(0), {"text": "Electrabel / Travaux 1 [TOUT]", "id": "l:%s" % self.elec["travaux"].UID()}
        )
        self.assertEqual(view.request.response.getHeader("Content-type"), "application/json")
        # a term emptied by the cleaning: empty SearchableText, every contact is found (Plone 4 catalog)
        view.request["term"] = "()"
        ret = json.loads(view())
        self.assertListEqual(
            [dic["text"] for dic in ret[:3]], [u"Electrabel", u"Electrabel / Travaux 1", u"Mon organisation"]
        )
        self.assertGreater(len(ret), 20)

    def test_call_SenderSuggest(self):
        omail1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        view = omail1.unrestrictedTraverse("@@sender-autocomplete-suggest")
        # no term
        self.assertEqual(view(), "[]")
        # search held position
        view.request["term"] = "agent evenements"
        ret = json.loads(view())
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Monsieur Fred Agent, Agent Événements (Mon organisation / Événements)",
                "id": self.pf["agent"]["agent-evenements"].UID(),
            },
        )
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Monsieur Stef Agent, Agent Événements (Mon organisation / Événements)",
                "id": self.pf["agent1"]["agent-evenements"].UID(),
            },
        )
        # search organization
        view.request["term"] = "direction générale grh"
        ret = json.loads(view())
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Mon organisation / Direction générale / GRH",
                u"id": self.pgo["direction-generale"]["grh"].UID(),
            },
        )
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Monsieur Fred Agent, Agent GRH (Mon organisation / Direction générale / GRH)",
                "id": self.pf["agent"]["agent-grh"].UID(),
            },
        )
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Monsieur Michel Chef, Responsable GRH (Mon organisation / Direction générale / GRH)",
                "id": self.pf["chef"]["responsable-grh"].UID(),
            },
        )
        self.assertEqual(
            ret.pop(0),
            {
                "text": u"Mon organisation / Direction générale / GRH [TOUT]",
                u"id": "l:%s" % self.pgo["direction-generale"]["grh"].UID(),
            },
        )
        # a term emptied by the cleaning: empty SearchableText, every internal contact is found (Plone 4 catalog)
        view.request["term"] = "*"
        ret = json.loads(view())
        self.assertListEqual(
            [dic["text"] for dic in ret[:2]], [u"Mon organisation", u"Mon organisation / Collège communal"]
        )
        self.assertNotIn(u"Electrabel", [dic["text"] for dic in ret])


class TestServerSentEvents(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_call(self):
        omail1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omf = omail1["1"]
        sse_vw = omail1.restrictedTraverse("server_sent_events")
        eee_vw = omf.restrictedTraverse("@@externalEditorEnabled")

        # a dmsommainfile has been added manually and we go back on the dmsoutgoingmail
        self.assertEqual(omf.conversion_finished, True)
        self.assertFalse(hasattr(omf, "generated"))
        self.assertEqual(sse_vw(), u"")  # no refresh
        response = sse_vw.request.response
        self.assertEqual(response.getHeader("Content-Type"), "text/event-stream")
        self.assertEqual(response.getHeader("Cache-Control"), "no-cache")

        # a dmsommainfile has been generated
        omf.generated = 1
        omf.conversion_finished = True
        self.assertEqual(sse_vw(), u"")  # no refresh
        self.assertEqual(omf.generated, 2)  # waiting external edition
        # we lock like zopeedit
        omf.restrictedTraverse("lock-unlock")()
        self.assertTrue(eee_vw.isObjectLocked())
        self.assertEqual(sse_vw(), u"")  # no refresh
        self.assertEqual(omf.generated, 3)  # was always waiting but will end
        self.assertEqual(sse_vw(), u"")  # no refresh
        self.assertEqual(omf.generated, 3)  # no more waiting but locked
        # we unlock
        omf.restrictedTraverse("lock-unlock")(unlock=1)
        self.assertFalse(eee_vw.isObjectLocked())
        res = sse_vw()
        # u'data: {"path": "/plone/outgoing-mail/reponse1/1", "id": "1", "refresh": true}\n\n'
        self.assertIn('"id": "1", "refresh": true', res)  # we refresh

        # a dmsommainfile is edited with zopeedit
        self.assertFalse(hasattr(omf, "generated"))
        self.assertFalse(hasattr(omf, "conversion_finished"))
        self.assertEqual(sse_vw(), u"")  # no refresh
        # we lock like zopeedit
        omf.restrictedTraverse("lock-unlock")()
        self.assertTrue(eee_vw.isObjectLocked())
        self.assertEqual(sse_vw(), u"")  # no refresh
        # we save the file in the editor but dont close it
        omf.conversion_finished = True
        self.assertEqual(sse_vw(), u"")  # no refresh
        self.assertEqual(omf.generated, 3)  # set as no more waiting
        # we unlock
        omf.restrictedTraverse("lock-unlock")(unlock=1)
        self.assertFalse(eee_vw.isObjectLocked())
        res = sse_vw()
        # u'data: {"path": "/plone/outgoing-mail/reponse1/1", "id": "1", "refresh": true}\n\n'
        self.assertIn('"id": "1", "refresh": true', res)  # we refresh


class TestUpdateItem(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_call(self):
        imail1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertIsNone(imail1.assigned_user)
        view = imail1.unrestrictedTraverse("@@update_item")
        # called without form value
        view()
        self.assertIsNone(imail1.assigned_user)
        # called with form value
        form = self.portal.REQUEST.form
        form["assigned_user"] = "chef"
        view()
        self.assertEqual(imail1.assigned_user, "chef")
        # catalog is updated
        pc = self.portal.portal_catalog
        self.assertEqual(len(pc.unrestrictedSearchResults(UID=imail1.UID(), assigned_user="chef")), 1)
        # Plone 4: the write is done on a GET request, without CSRF token (called by callViewAndReload)
        self.portal.REQUEST["REQUEST_METHOD"] = "GET"
        self.portal.REQUEST["assigned_user"] = "agent"
        imail1.unrestrictedTraverse("@@update_item")()
        self.assertEqual(imail1.assigned_user, "agent")


class TestSendEmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_call(self):
        omail1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail1.send_modes = [u"email"]
        omail1.email_subject = u"Email subject"
        omail1.email_sender = u"sender@mio.be"
        omail1.email_recipient = u"contakt@mio.be"
        omail1.email_body = richtextval(u"My email content.")
        view = omail1.unrestrictedTraverse("@@send_email")
        # Status before call
        self.assertEqual(api.content.get_state(omail1), "created")
        self.assertIsNone(omail1.email_status)
        MockMailHost.secureSend = MockMailHost.send
        mail_host = get_mail_host()
        mail_host.reset()
        # view call
        view()
        # self.assertIn("Subject: =?utf-8?q?Email_subject?=\n", mail_host.messages[0])
        self.assertIn("Subject: Email subject\n", mail_host.messages[0])
        self.assertIn("My email content.", mail_host.messages[0])
        self.assertIn("From: sender@mio.be", mail_host.messages[0])
        self.assertEqual(api.content.get_state(omail1), "sent")
        self.assertIsNotNone(omail1.email_status)
        messages = IStatusMessage(self.portal.REQUEST).show()
        self.assertIn(u"Your email has been sent.", [msg.message for msg in messages])
        # second sending (GET, without CSRF token), with reply-to option and without closing
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_replyto_email_send", True
        )
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_close_on_email_send", False
        )
        self.portal.manage_changeProperties(email_from_address="noreply@macommune.be")
        first_status = omail1.email_status
        self.portal.REQUEST["REQUEST_METHOD"] = "GET"
        mail_host.reset()
        omail1.unrestrictedTraverse("@@send_email")()
        self.assertIn("reply-to: sender@mio.be", mail_host.messages[0])
        self.assertIn("From: noreply@macommune.be", mail_host.messages[0])
        self.assertTrue(omail1.email_status.startswith(first_status + u" "))
        self.assertEqual(omail1.email_status.count(u"Email envoyé le"), 2)


class TestRenderEmailSignature(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pgo = self.portal.contacts["plonegroup-organization"]
        self.pgo.use_parent_address = False
        self.pgo.street = u"Rue Léon Morel"
        self.pgo.number = u"1"
        self.pgo.zip_code = u"5032"
        self.pgo.city = u"Isnes"
        self.pgo.email = u"contakt@mio.be"

    def test_call(self):
        model = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature"
        )
        self.assertIn("http://localhost:8081/", model)  # $url well replaced by PUBLIC_URL
        omail1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = omail1.unrestrictedTraverse("@@render_email_signature")
        self.assertIn("sender", view.namespace)
        self.assertEqual(view.namespace["sender"]["org_full_title"], u"Direction générale - GRH")
        self.assertEqual(view.namespace["sender"]["person"].title, u"Monsieur Michel Chef")
        # ctct_det = view.namespace['dghv'].get_ctct_det(view.namespace['sender']['hp'])
        rendered = view().output
        self.assertIn(u">Michel Chef<", rendered)
        self.assertIn(u">Responsable GRH<", rendered)
        self.assertIn(u">Direction générale<", rendered)
        self.assertIn(u">GRH<", rendered)
        self.assertIn(u">chef@macommune.be<", rendered)
        self.assertIn(u">012/34.56.79<", rendered)
        self.assertIn(u">Rue Léon Morel, 1<", rendered)
        self.assertIn(u">5032 Isnes<", rendered)


class TestSessionAnnotationInfoView(unittest.TestCase, ImioTestHelpers):
    """Test SessionAnnotationInfoView"""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.view = SessionAnnotationInfoView(self.om1, self.portal.REQUEST)
        self.pf = self.portal["contacts"]["personnel-folder"]
        self.pgof = self.portal["contacts"]["plonegroup-organization"]

    def _setup_esign_omail(self):
        """Create a new outgoing mail with esign enabled and two files."""
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        intids = getUtility(IIntIds)
        params = {
            "title": u"Courrier test esign",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "courrier",
            "treating_groups": self.pgof["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
            "signers": [
                {
                    "number": 1,
                    "signer": self.pf["dirg"]["directeur-general"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": True,
                },
                {
                    "number": 2,
                    "signer": self.pf["bourgmestre"]["bourgmestre"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": False,
                },
            ],
            "esign": True,
        }
        omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om-esign", **params)
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        files = []
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            files.append(
                createContentInContainer(
                    omail,
                    "dmsommainfile",
                    id="file0",
                    scan_id="012999900000601",
                    file=file_object,
                    content_category=calculate_category_id(ct),
                )
            )
        view = omail.restrictedTraverse("persistent-document-generation")
        view.pod_template = self.portal["templates"]["om"]["main"]
        view.output_format = "odt"
        files.append(view.generate_persistent_doc(view.pod_template, view.output_format))
        return omail, files, IOMApproval(omail)

    def _approve_all_files(self, omail, files, approval):
        """Approve all files through the full two-signer approval process."""
        pw = self.portal.portal_workflow
        pw.doActionFor(omail, "propose_to_approve")
        approval.approve_file(files[0], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "bourgmestre", transition="propose_to_be_signed")
        approval.approve_file(files[0], "bourgmestre", transition="propose_to_be_signed")

    def test_annot_html(self):
        """Test approval_annot_html and esign_session_html."""
        def fmt_dt(dte):
            """Format a datetime like the view does."""
            return u"datetime({})".format(dte.strftime("%d/%m/%Y %H:%M:%S"))

        omail, files, approval = self._setup_esign_omail()
        self._approve_all_files(omail, files, approval)

        view = SessionAnnotationInfoView(omail, self.portal.REQUEST)

        # approval annot html
        self.assertEqual(
            HTMLParser().unescape(view.approval_annot_html),
            u"""{{
  "approval": [
    [
      {{
        "approved_by": "dirg",
        "approved_on": {},
        "status": "a",
      }},
      {{
        "approved_by": "dirg",
        "approved_on": {},
        "status": "a",
      }},
    ],
    [
      {{
        "approved_by": "bourgmestre",
        "approved_on": {},
        "status": "a",
      }},
      {{
        "approved_by": "bourgmestre",
        "approved_on": {},
        "status": "a",
      }},
    ],
  ],
  "approvers": [
    [
      "dirg",
    ],
    [
      "bourgmestre",
    ],
  ],
  "current_nb": -1,
  "editors": [
    True,
    False,
  ],
  "files": [
    <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/file0/view' title='/plone/outgoing-mail/{folder_name}/om-esign/file0'>Réponse salle.odt</a> ({uid1}),
    <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/012999900000602/view' title='/plone/outgoing-mail/{folder_name}/om-esign/012999900000602'>Modèle de base</a> ({uid2}),
  ],
  "pdf_files": [
    [
      <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/file0/view' title='/plone/outgoing-mail/{folder_name}/om-esign/file0'>Réponse salle.odt</a> ({puid1}),
    ],
    [
      <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/modele-de-base-s0010-courrier-test-esign.pdf/view' title='/plone/outgoing-mail/{folder_name}/om-esign/modele-de-base-s0010-courrier-test-esign.pdf'>Modele de base S0010 Courrier test esign.pdf</a> ({puid2}),
    ],
  ],
  "session_ids": [
    0,
  ],
  "signers": [
    [
      "dirg",
      "Maxime DG",
      "Directeur Général",
    ],
    [
      "bourgmestre",
      "Paul BM",
      "Bourgmestre",
    ],
  ],
}}""".format(  # noqa E501
                fmt_dt(approval.annot["approval"][0][0]["approved_on"]),
                fmt_dt(approval.annot["approval"][0][1]["approved_on"]),
                fmt_dt(approval.annot["approval"][1][0]["approved_on"]),
                fmt_dt(approval.annot["approval"][1][1]["approved_on"]),
                folder_name=omail.__parent__.__name__,
                uid1=approval.files_uids[0],
                uid2=approval.files_uids[1],
                puid1=approval.pdf_files_uids[0][0],
                puid2=approval.pdf_files_uids[1][0],
            ),
        )

        # esign essions property
        esign_sessions = view.esign_sessions
        self.assertEqual(len(esign_sessions), 1)
        esign_session = esign_sessions[0]
        self.assertIsInstance(esign_session, tuple)
        self.assertEqual(esign_session[0], 0)

        # esign session html
        # self.maxDiff = None
        self.assertEqual(
            HTMLParser().unescape(view.esign_session_html(esign_session[1])),
            u"""{{
  "acroform": True,
  "client_id": "0129999",
  "discriminators": [
    "dmsoutgoingmail",
  ],
  "files": [
    {{
      "context_uid": <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/view' title='/plone/outgoing-mail/{folder_name}/om-esign'>Courrier test esign</a> ({c_uid}),
      "filename": "Réponse salle__{pdf1_uid}.pdf",
      "scan_id": "012999900000601",
      "status": "",
      "title": "Réponse salle.odt",
      "uid": <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/file0/view' title='/plone/outgoing-mail/{folder_name}/om-esign/file0'>Réponse salle.odt</a> ({pdf1_uid}),
    }},
    {{
      "context_uid": <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/view' title='/plone/outgoing-mail/{folder_name}/om-esign'>Courrier test esign</a> ({c_uid}),
      "filename": "Modele de base S0010 Courrier test esign__{pdf2_uid}.pdf",
      "scan_id": "012999900000602",
      "status": "",
      "title": "Modele de base S0010 Courrier test esign.pdf",
      "uid": <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/modele-de-base-s0010-courrier-test-esign.pdf/view' title='/plone/outgoing-mail/{folder_name}/om-esign/modele-de-base-s0010-courrier-test-esign.pdf'>Modele de base S0010 Courrier test esign.pdf</a> ({pdf2_uid}),
    }},
  ],
  "last_update": {last_update},
  "returns": [],
  "seal": False,
  "sign_id": "012999900000",
  "sign_url": None,
  "signers": [
    {{
      "email": "dirg@macommune.be",
      "fullname": "Maxime DG",
      "position": "Directeur Général",
      "status": "",
      "userid": "dirg",
    }},
    {{
      "email": "bourgmestre@macommune.be",
      "fullname": "Paul BM",
      "position": "Bourgmestre",
      "status": "",
      "userid": "bourgmestre",
    }},
  ],
  "size": {size},
  "state": "draft",
  "title": "[iA.Docs] Courrier sortant - 012999900000",
  "watchers": [],
}}""".format(  # noqa E501
                c_uid=omail.UID(),
                pdf1_uid=api.content.get(omail.absolute_url_path() + "/file0").UID(),
                pdf2_uid=api.content.get(omail.absolute_url_path()
                                         + "/modele-de-base-s0010-courrier-test-esign.pdf").UID(),
                folder_name=omail.__parent__.__name__,
                last_update=fmt_dt(get_session_annotation()["sessions"][0]["last_update"]),
                size=api.content.get(omail.absolute_url_path() + "/file0").file.size
                + api.content.get(omail.absolute_url_path()
                                  + "/modele-de-base-s0010-courrier-test-esign.pdf").file.size,
            ),
        )

    def _setup_esign_sign_request(self):
        """Create an esign sign_request with one file (the view is also registered for sign_request)."""
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-sign-request", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        return create_sign_request(self.portal, oid="sr-esign", nb_files=1, esign=True)

    def test_sign_request_annot_html(self):
        request, files = self._setup_esign_sign_request()
        pw = self.portal.portal_workflow
        pw.doActionFor(request, "propose_to_approve")
        approval = ISignRequestApproval(request)
        for userid in ("dirg", "bourgmestre"):
            approval.approve_file(files[0], userid, transition="propose_to_be_signed")

        view = SessionAnnotationInfoView(request, self.portal.REQUEST)
        # approval annotation rendered as HTML
        html = view.approval_annot_html
        self.assertIn("approved_by", html)
        self.assertIn("dirg", html)
        # esign session created for the request
        self.assertEqual(len(view.esign_sessions), 1)


class TestObjectRenameTitleView(unittest.TestCase):
    """Test ObjectRenameTitleView (replaces the legacy CMF skin form)."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_call(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omf = omail["1"]
        original_title = omf.Title()
        request = self.portal.REQUEST
        token = omf.restrictedTraverse("@@authenticator").token()

        # GET: form renders with current title pre-filled
        request.form.clear()
        request["HTTP_REFERER"] = omail.absolute_url() + "?foo=bar"
        view = omf.restrictedTraverse("@@object_rename_title")
        rendered = view()
        self.assertIn(u'name="new_title"', rendered)
        self.assertIn(original_title, rendered)
        self.assertEqual(view.orig_template, omail.absolute_url())
        self.assertEqual(omf.Title(), original_title)

        # POST with empty title: re-renders with error, title unchanged
        request.form.clear()
        request.form.update({
            "form.submitted": "1",
            "_authenticator": token,
            "new_title": u"   ",
            "orig_template": omail.absolute_url(),
            "form.button.RenameAll": "Rename All",
        })
        view = omf.restrictedTraverse("@@object_rename_title")
        rendered = view()
        self.assertTrue(view.error)
        self.assertIn(u"field error", rendered)
        self.assertEqual(omf.Title(), original_title)

        # POST with new title: persists, reindexes, redirects
        new_title = u"Nouveau titre éàü"
        request.form.clear()
        request.form.update({
            "form.submitted": "1",
            "_authenticator": token,
            "new_title": new_title,
            "orig_template": omail.absolute_url(),
            "form.button.RenameAll": "Rename All",
        })
        view = omf.restrictedTraverse("@@object_rename_title")
        view()
        self.assertEqual(omf.Title(), new_title)
        self.assertEqual(request.response.getHeader("Location"), omail.absolute_url())
        brain = api.content.find(UID=omf.UID())[0]
        self.assertEqual(safe_unicode(brain.Title), new_title)


class TestImioRecreateSessionView(unittest.TestCase):
    """Tests for the dms.mail override ImioRecreateSessionView."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pf = self.portal["contacts"]["personnel-folder"]
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        self.portal.REQUEST.form.clear()

    def _make_omail_with_session(self):
        """Create an outgoing mail, directly build an esign session for one of its files, and
        put the session in the refused state.  Also registers the session_id in the approval
        annotation, mirroring what add_mail_files_to_session does during a real workflow."""
        intids = getUtility(IIntIds)
        params = {
            "title": u"Courrier recreate test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "courrier",
            "treating_groups": self.pgof["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
            "signers": [
                {
                    "number": 1,
                    "signer": self.pf["dirg"]["directeur-general"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": True,
                },
            ],
            "esign": True,
        }
        omail = sub_create(
            self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om-recreate", **params
        )
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_obj = createContentInContainer(
                omail,
                "dmsommainfile",
                id="file0",
                scan_id="012999900000603",
                file=NamedBlobFile(fo.read(), filename=filename),
                content_category=calculate_category_id(ct),
            )

        signers = [("dirg", "dirg@macommune.be", u"Maxime DG", u"Directeur Général")]
        old_id, _session = add_files_to_session(
            signers, [file_obj.UID()], title=_("[iA.Docs] Session {sign_id}")
        )[-1]
        # Flip to refused
        annot = get_session_annotation()
        annot["sessions"][old_id]["state"] = "refused"
        # Mirror what the approval adapter does: register session_id
        approval = OMApprovalAdapter(omail)
        if "session_ids" not in approval.annot:
            approval.annot["session_ids"] = PersistentList()
        approval.annot["session_ids"].append(old_id)
        return omail, old_id

    def test_call(self):
        """Recreation appends new session id to approval.session_ids and reindexes the mail;
        a failed recreation (bad session id) leaves session_ids unchanged."""
        omail, old_id = self._make_omail_with_session()
        approval = OMApprovalAdapter(omail)
        pc = api.portal.get_tool("portal_catalog")

        # --- Failed recreation: bad session id — session_ids unchanged ---
        before = list(approval.session_ids)
        self.portal.REQUEST.form["esign_session_id"] = "9999"
        view = ImioRecreateSessionView(self.portal, self.portal.REQUEST)
        view()
        self.assertIsNone(view._new_session_id)
        self.assertEqual(list(approval.session_ids), before)

        # --- Successful recreation: new id appended, mail reindexed ---
        self.portal.REQUEST.form["esign_session_id"] = str(old_id)
        view = ImioRecreateSessionView(self.portal, self.portal.REQUEST)
        view()
        new_id = view._new_session_id
        self.assertIsNotNone(new_id)
        self.assertNotEqual(new_id, old_id)
        self.assertIn(old_id, approval.session_ids)
        self.assertIn(new_id, approval.session_ids)
        brains = pc(UID=omail.UID())
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, omail.UID())
        annot = get_session_annotation()
        # the old session is consumed by the recreation, the new one gets a title with the new sign_id
        self.assertNotIn(old_id, annot["sessions"])
        self.assertEqual(annot["sessions"][new_id]["title"], u"[iA.Docs] Courrier sortant - 012999900001")


class TestPlusPortaltabContent(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_get_tabs(self):
        view = self.portal.unrestrictedTraverse("@@plus-portaltab-content")
        self.assertListEqual(
            view.get_tabs(),
            [
                ("Contacts", "http://nohost/plone/contacts"),
                ("Modèles", "http://nohost/plone/templates"),
                ("Classement", "http://nohost/plone/tree"),
                ("Types d'annexes", "http://nohost/plone/annexes_types"),
            ],
        )
        rendered = view()
        self.assertIn(u'<div id="subportaltab-plus">', rendered)
        self.assertIn(u'<a href="http://nohost/plone/annexes_types">Types d\'annexes</a>', rendered)


class TestDmsMailRestClientView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_detailed_description(self):
        portal = self.layer["portal"]
        change_user(portal)
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        view = imail.unrestrictedTraverse("@@IncomingmailRestWSClient")
        self.assertEqual(
            view.detailed_description(),
            u'<p>Fiche courrier liée: <a href="{}/view" target="_blank">E0001 - Courrier 1</a></p>'.format(
                imail.absolute_url()
            ),
        )


class TestImioSessionsListingView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)
        self.signers = [("dirg", "dirg@macommune.be", u"Maxime DG", u"Directeur Général")]

    def test_session_portal_type(self):
        view = ImioSessionsListingView(self.portal, self.request)
        self.assertEqual(view.session_portal_type({"discriminators": ("sign_request",)}), "sign_request")
        self.assertEqual(view.session_portal_type({"discriminators": ()}), "dmsoutgoingmail")
        self.assertEqual(view.session_portal_type({}), "dmsoutgoingmail")

    def test_get_dashboard_link(self):
        activate_signing(self.portal)
        om_sid, _session = create_session(self.signers)
        sr_sid, _session = create_session(self.signers, discriminators=("sign_request",))
        view = ImioSessionsListingView(self.portal, self.request)
        om_col = self.portal["outgoing-mail"]["mail-searches"]["in_esign_sessions"]
        self.assertEqual(
            view.get_dashboard_link({"id": om_sid}),
            "http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id={}".format(
                om_col.UID(), om_sid
            ),
        )
        sr_col = self.portal["requests"]["requests-searches"]["in_esign_sessions"]
        self.assertEqual(
            view.get_dashboard_link({"id": sr_sid}),
            "http://nohost/plone/requests/requests-searches#c3=20&b_start=0&c1={}&esign_session_id={}".format(
                sr_col.UID(), sr_sid
            ),
        )

    def test_get_sessions(self):
        activate_signing(self.portal)
        om_sid, _session = create_session(self.signers)
        sr_sid, _session = create_session(self.signers, discriminators=("sign_request",))
        view = ImioSessionsListingView(self.portal, self.request)
        self.assertListEqual([sess["id"] for sess in view.get_sessions()], [sr_sid, om_sid])
        self.request.set("esign_portal_type", "sign_request")
        self.assertListEqual([sess["id"] for sess in view.get_sessions()], [sr_sid])
        self.request.set("esign_portal_type", "dmsoutgoingmail")
        self.assertListEqual([sess["id"] for sess in view.get_sessions()], [om_sid])

    def test_available(self):
        with api.env.adopt_roles(["Manager"]):
            if api.group.get("esign_watchers") is None:
                api.group.create("esign_watchers")
            api.group.add_user(groupname="esign_watchers", username="agent")
        view = ImioSessionsListingView(self.portal, self.request)
        # esign disabled
        self.assertFalse(view.available())
        self.assertRaises(Unauthorized, self.portal.unrestrictedTraverse("@@parapheo"))
        activate_signing(self.portal)
        # session manager
        self.assertTrue(view.available())
        self.assertIn(u"<", self.portal.unrestrictedTraverse("@@parapheo")())
        # approver
        change_user(self.portal, "dirg")
        self.assertTrue(view.available())
        # other user
        change_user(self.portal, "agent1")
        self.assertFalse(view.available())
        # esign watcher
        change_user(self.portal, "agent")
        self.assertTrue(view.available())
        set_esign_registry_enabled(False)
        self.assertFalse(view.available())


class TestImioExternalSessionCreateView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)

    def test_may_create_external_sessions(self):
        with api.env.adopt_roles(["Manager"]):
            if api.group.get("esign_watchers") is None:
                api.group.create("esign_watchers")
            api.group.add_user(groupname="esign_watchers", username="agent")
        view = ImioExternalSessionCreateView(self.portal, self.request)
        self.assertFalse(view.may_create_external_sessions())
        self.assertRaises(Unauthorized, self.portal.unrestrictedTraverse("@@external-esign-session-create"))
        activate_signing(self.portal)
        self.assertTrue(view.may_create_external_sessions())
        # no session id: back to the sessions listing with an error
        self.assertEqual(view(), "http://nohost/plone/@@parapheo")
        self.assertIn(u"No session ID provided!", [msg.message for msg in IStatusMessage(self.request).show()])
        change_user(self.portal, "dirg")
        self.assertTrue(view.may_create_external_sessions())
        change_user(self.portal, "agent1")
        self.assertFalse(view.may_create_external_sessions())
        change_user(self.portal, "agent")
        self.assertTrue(view.may_create_external_sessions())


class TestImioRemoveItemFromSessionView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-sign-request", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        self.sreq, self.files = create_sign_request(self.portal, oid="sr-remove", nb_files=1, esign=True)
        api.content.transition(obj=self.sreq, transition="propose_to_approve")
        self.approval = ISignRequestApproval(self.sreq)
        for userid in ("dirg", "bourgmestre"):
            self.approval.approve_file(self.files[0], userid, transition="propose_to_be_signed")
        self.pdf = api.content.get(UID=self.approval.pdf_files_uids[0][0])

    def test_available(self):
        view = self.pdf.restrictedTraverse("@@remove-item-from-esign-session")
        self.assertIsInstance(view, ImioRemoveItemFromSessionView)
        self.assertTrue(view.available())
        # a file outside the approval
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        self.assertFalse(ImioRemoveItemFromSessionView(omf, self.request).available())
        # a file of an incoming mail
        imf = get_object(oid="courrier1", ptype="dmsincomingmail").objectValues()[0]
        self.assertFalse(ImioRemoveItemFromSessionView(imf, self.request).available())

    def test_actions(self):
        pdf_uid = self.pdf.UID()
        self.assertIn(pdf_uid, get_session_annotation()["uids"])
        view = ImioRemoveItemFromSessionView(self.pdf, self.request)
        view.actions()
        self.assertNotIn(pdf_uid, get_session_annotation()["uids"])
        self.assertNotIn(pdf_uid, [uid for lst in self.approval.pdf_files_uids for uid in lst])

    def test_index(self):
        pdf_uid = self.pdf.UID()
        self.request["HTTP_REFERER"] = self.sreq.absolute_url()
        view = ImioRemoveItemFromSessionView(self.pdf, self.request)
        view.index()
        self.assertNotIn(pdf_uid, get_session_annotation()["uids"])
        self.assertEqual(self.request.response.getHeader("Location"), self.sreq.absolute_url())
        self.assertIn(u"Élément retiré de la session !",
                      [msg.message for msg in IStatusMessage(self.request).show()])
        # not available anymore: nothing done
        self.request.response.setHeader("Location", "")
        self.assertIsNone(view.index())
        self.assertEqual(self.request.response.getHeader("Location"), "")


class TestApprovalTableView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)

    def test_available(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertFalse(ApprovalTableView(omail, self.request).available())
        self.assertEqual(omail.unrestrictedTraverse("@@approvals")(), "")
        sreq, files = create_sign_request(self.portal, oid="sr-approvals", nb_files=1)
        view = ApprovalTableView(sreq, self.request)
        self.assertTrue(view.available())
        api.content.transition(obj=sreq, transition="propose_to_approve")
        self.assertTrue(view.available())
        for userid in ("dirg", "bourgmestre"):
            ISignRequestApproval(sreq).approve_file(files[0], userid, transition="propose_to_be_signed")
        self.assertEqual(api.content.get_state(sreq), "to_be_signed")
        self.assertFalse(view.available())

    def test_call(self):
        sreq, files = create_sign_request(self.portal, oid="sr-approvals", nb_files=1)
        self.request["REQUEST_METHOD"] = "GET"
        rendered = sreq.unrestrictedTraverse("@@approvals")()
        self.assertIn(u'action="{}/@@approvals"'.format(sreq.absolute_url()), rendered)
        self.assertIn(u'<input type="checkbox" name="approvals.{}.dirg"  />'.format(files[0].UID()), rendered)
        self.assertIn(u'name="form.button.Save"', rendered)
        # Plone 4: no CSRF token in the form
        action = u'action="{}/@@approvals"'.format(sreq.absolute_url())
        form_html = rendered[rendered.index(action):rendered.index(u'name="form.button.Cancel"')]
        self.assertNotIn(u"_authenticator", form_html)
        # cancel
        self.request.form["form.button.Cancel"] = "Cancel"
        sreq.unrestrictedTraverse("@@approvals")()
        self.assertEqual(self.request.response.getHeader("Location"), sreq.absolute_url())


class TestImioCatalogNavigationTabs(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_topLevelTabs(self):
        view = ImioCatalogNavigationTabs(self.portal, self.portal.REQUEST)
        tabs = view.topLevelTabs()
        # the "plus" tab is always the last one, after the portal_tabs actions
        self.assertListEqual(
            [tab["id"] for tab in tabs], ["incoming-mail", "outgoing-mail", "folders", "tasks", "index_html", "plus"]
        )
        self.assertEqual(tabs[0]["url"], "http://nohost/plone/incoming-mail")
        self.assertEqual(tabs[0]["name"], "Entrant")
        self.assertEqual(tabs[-1]["url"], "http://nohost/plone/plus")
