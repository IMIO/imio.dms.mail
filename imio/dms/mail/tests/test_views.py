# -*- coding: utf-8 -*-
"""Test views."""

from AccessControl import Unauthorized
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.utils import calculate_category_id
from collective.MockMailHost.MockMailHost import MockMailHost
from datetime import datetime
from HTMLParser import HTMLParser
from imio.dms.mail import PERIODS
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.views import parse_query
from imio.dms.mail.browser.views import SigningAnnotationInfoView
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.esign.config import set_registry_file_url
from imio.esign.utils import get_session_annotation
from imio.helpers.content import get_object
from imio.helpers.content import richtextval
from imio.helpers.emailer import get_mail_host
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.app.testing import login
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import safe_unicode
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.i18n import translate
from zope.intid import IIntIds

import json
import unittest


class TestReplyForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_updateFields(self):
        imail1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        view = imail1.unrestrictedTraverse("@@reply")
        view.updateFields()
        form = self.portal.REQUEST.form
        expected_linked_mails = ("/".join(imail1.getPhysicalPath()),)
        self.assertEqual(form["form.widgets.reply_to"], expected_linked_mails)
        self.assertEqual(translate(view.label), u"Reply to E0001 - Courrier 1")
        expected_recipients = ("/plone/contacts/electrabel",)
        self.assertEqual(form["form.widgets.recipients"], expected_recipients)

    def test_add(self):
        change_user(self.portal)
        imail1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        omail1 = api.content.create(
            container=self.portal["outgoing-mail"], type="dmsoutgoingmail", id="newo1", title="TEST"
        )
        view = imail1.unrestrictedTraverse("@@reply")
        view.add(omail1)
        self.assertIn("newo1", self.portal["outgoing-mail"][datetime.now().strftime(PERIODS["week"])])


class TestPloneView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_showEditableBorder(self):
        view = get_object(oid="courrier1", ptype="dmsincomingmail").unrestrictedTraverse("@@plone")
        self.assertEqual(view.showEditableBorder(), False)
        view = self.portal["front-page"].unrestrictedTraverse("@@plone")
        self.assertEqual(view.showEditableBorder(), True)


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
        self.assertEqual(api.content.get_state(omail1), "sent")
        self.assertIsNotNone(omail1.email_status)


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


class TestSigningAnnotationInfoView(unittest.TestCase, ImioTestHelpers):
    """Test SigningAnnotationInfoView"""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.view = SigningAnnotationInfoView(self.om1, self.portal.REQUEST)
        self.pf = self.portal["contacts"]["personnel-folder"]
        self.pgof = self.portal["contacts"]["plonegroup-organization"]

    def _setup_esign_omail(self):
        """Create a new outgoing mail with esign enabled and two files."""
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-esigning", run_dependencies=False
        )
        set_registry_file_url("https://downloads.files.com")
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
        for i in range(2):
            with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                files.append(
                    createContentInContainer(
                        omail,
                        "dmsommainfile",
                        id="file%s" % i,
                        scan_id="012999900000601",
                        file=file_object,
                        content_category=calculate_category_id(ct),
                    )
                )
        return omail, files, IOMApproval(omail)

    def _approve_all_files(self, omail, files, approval):
        """Approve all files through the full two-signer approval process."""
        pw = self.portal.portal_workflow
        pw.doActionFor(omail, "propose_to_approve")
        approval.approve_file(files[0], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "bourgmestre", transition="propose_to_be_signed")
        approval.approve_file(files[0], "bourgmestre", transition="propose_to_be_signed")

    def test_call(self):
        with self.assertRaises(Unauthorized):
            self.view()
        login(self.portal.aq_parent, "admin")
        self.assertIsInstance(self.view(), basestring)

    def test_render_value(self):
        # Dict
        self.assertEqual(self.view._render_value({}), u"{}")
        self.assertEqual(
            self.view._render_value({"key": "val"}),
            u"{\n  &#x27;key&#x27;: &#x27;val&#x27;,\n}",
        )

        # Indentation: nested value increases indent level
        self.assertEqual(
            self.view._render_value({"key": ["a"]}),
            u"{\n  &#x27;key&#x27;: [\n    &#x27;a&#x27;,\n  ],\n}",
        )

        # List
        self.assertEqual(self.view._render_value([]), u"[]")
        self.assertEqual(
            self.view._render_value(["a", "b"]),
            u"[\n  &#x27;a&#x27;,\n  &#x27;b&#x27;,\n]",
        )

        # Tuple
        self.assertEqual(self.view._render_value(()), u"[]")

        # String
        self.assertEqual(self.view._render_value(u"hello"), u"u&#x27;hello&#x27;")

        # UID not found
        fake_uid = u"a" * 32
        self.assertEqual(
            self.view._render_value(fake_uid),
            u"<span title='not found'>aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</span>",
        )

        # UID found
        self.assertEqual(
            self.view._render_value(self.om1.UID()),
            u"<a href='http://nohost/plone/outgoing-mail/202608/reponse1' title='/plone/outgoing-mail/202608/reponse1'>R\xe9ponse 1</a>",
        )

    def test_uid_to_link(self):
        uid = self.om1.UID()
        result = self.view._uid_to_link(uid)
        self.assertIn(u"<a href=", result)
        self.assertIn(self.om1.absolute_url(), result)

        result = self.view._uid_to_link(u"a" * 32)
        self.assertIn(u"<span", result)
        self.assertIn(u"not found", result)

    def test_approval_and_esign_sessions(self):
        """Test approval_annot_html and esign_session_html after a true approval process."""
        omail, files, approval = self._setup_esign_omail()
        self._approve_all_files(omail, files, approval)

        view = SigningAnnotationInfoView(omail, self.portal.REQUEST)

        # approval annot html
        self.assertEqual(
            HTMLParser().unescape(view.approval_annot_html),
            u"""{{
  'approval': [
    [
      {{
        'approved_by': 'dirg',
        'approved_on': {},
        'status': 'a',
      }},
      {{
        'approved_by': 'dirg',
        'approved_on': {},
        'status': 'a',
      }},
    ],
    [
      {{
        'approved_by': 'bourgmestre',
        'approved_on': {},
        'status': 'a',
      }},
      {{
        'approved_by': 'bourgmestre',
        'approved_on': {},
        'status': 'a',
      }},
    ],
  ],
  'approvers': [
    [
      'dirg',
    ],
    [
      'bourgmestre',
    ],
  ],
  'current_nb': -1,
  'editors': [
    True,
    False,
  ],
  'files': [
    <a href='http://nohost/plone/outgoing-mail/202608/om-esign/file0' title='/plone/outgoing-mail/202608/om-esign/file0'>Réponse salle.odt</a>,
    <a href='http://nohost/plone/outgoing-mail/202608/om-esign/file1' title='/plone/outgoing-mail/202608/om-esign/file1'>Réponse salle.odt</a>,
  ],
  'pdf_files': [
    [
      <a href='http://nohost/plone/outgoing-mail/202608/om-esign/reponse-salle.pdf' title='/plone/outgoing-mail/202608/om-esign/reponse-salle.pdf'>Réponse salle.pdf</a>,
    ],
    [
      <a href='http://nohost/plone/outgoing-mail/202608/om-esign/reponse-salle-1.pdf' title='/plone/outgoing-mail/202608/om-esign/reponse-salle-1.pdf'>Réponse salle.pdf</a>,
    ],
  ],
  'session_ids': [
    0,
  ],
  'signers': [
    [
      'dirg',
      u'Maxime DG',
      u'Directeur G\\xe9n\\xe9ral',
    ],
    [
      'bourgmestre',
      u'Paul BM',
      u'Bourgmestre',
    ],
  ],
}}""".format(
                repr(approval.annot["approval"][0][0]["approved_on"]),
                repr(approval.annot["approval"][0][1]["approved_on"]),
                repr(approval.annot["approval"][1][0]["approved_on"]),
                repr(approval.annot["approval"][1][1]["approved_on"]),
            ),
        )

        # esign essions property
        esign_sessions = view.esign_sessions
        self.assertEqual(len(esign_sessions), 1)
        esign_session = esign_sessions[0]
        self.assertIsInstance(esign_session, tuple)
        self.assertEqual(esign_session[0], 0)

        # esign session html
        self.assertEqual(
            HTMLParser().unescape(view.esign_session_html(esign_session[1])),
            u"""{{
  'acroform': True,
  'client_id': '0129999',
  'discriminators': [],
  'files': [
    {{
      'context_uid': <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign' title='/plone/outgoing-mail/{folder_name}/om-esign'>Courrier test esign</a>,
      'filename': u'R\\xe9ponse salle__{pdf1_uid}.pdf',
      'scan_id': '012999900000601',
      'status': '',
      'title': u'R\\xe9ponse salle.pdf',
      'uid': <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/reponse-salle.pdf' title='/plone/outgoing-mail/{folder_name}/om-esign/reponse-salle.pdf'>Réponse salle.pdf</a>,
    }},
    {{
      'context_uid': <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign' title='/plone/outgoing-mail/{folder_name}/om-esign'>Courrier test esign</a>,
      'filename': u'R\\xe9ponse salle__{pdf2_uid}.pdf',
      'scan_id': '012999900000601',
      'status': '',
      'title': u'R\\xe9ponse salle.pdf',
      'uid': <a href='http://nohost/plone/outgoing-mail/{folder_name}/om-esign/reponse-salle-1.pdf' title='/plone/outgoing-mail/{folder_name}/om-esign/reponse-salle-1.pdf'>Réponse salle.pdf</a>,
    }},
  ],
  'last_update': {last_update},
  'returns': [],
  'seal': False,
  'sign_id': '012999900000',
  'sign_url': None,
  'signers': [
    {{
      'email': 'dirg@macommune.be',
      'fullname': u'Maxime DG',
      'position': u'Directeur G\\xe9n\\xe9ral',
      'status': '',
      'userid': 'dirg',
    }},
    {{
      'email': 'bourgmestre@macommune.be',
      'fullname': u'Paul BM',
      'position': u'Bourgmestre',
      'status': '',
      'userid': 'bourgmestre',
    }},
  ],
  'size': 54660,
  'state': 'draft',
  'title': u'[ia.docs] Session 012999900000',
  'watchers': [],
}}""".format(
                pdf1_uid=api.content.get(omail.absolute_url_path() + "/reponse-salle.pdf").UID(),
                pdf2_uid=api.content.get(omail.absolute_url_path() + "/reponse-salle-1.pdf").UID(),
                folder_name=omail.__parent__.__name__,
                last_update=repr(get_session_annotation()["sessions"][0]["last_update"]),
            ),
        )
