# -*- coding: utf-8 -*-
"""Test views."""

from collective.MockMailHost.MockMailHost import MockMailHost
from datetime import datetime
from imio.dms.mail import PERIODS
from imio.dms.mail.browser.views import parse_query
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from imio.helpers.content import richtextval
from imio.helpers.emailer import get_mail_host
from imio.helpers.test_helpers import ImioTestHelpers
from mock import patch
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.i18n import translate
from zope.intid.interfaces import IIntIds

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
            "imio.dms.mail.browser.settings.IImioDmsMailConfig." "omail_email_signature"
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

class TestDuplicate(unittest.TestCase, ImioTestHelpers):
    """
    Test the duplication of outgoing mails.
    """

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.pc = api.portal.get_tool('portal_catalog')
        self.change_user("siteadmin")
        self.intids = getUtility(IIntIds)

        self.omail2 = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id2",
            title="My title",
            description="Description",
            send_modes=["post"],
            classification_folders=[self.portal.folders['ordre-public-reglement-general-de-police'].UID()],
            classification_categories=self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories,
        )

        self.omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            send_modes=["post"],
            classification_folders=[self.portal.folders['ordre-public-reglement-general-de-police'].UID()],
            classification_categories=self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories,
            reply_to=[RelationValue(self.intids.getId(self.omail2))],
        )
        self.dmsommainfile = createContentInContainer(self.omail, "dmsommainfile", title=u"D001", file=NamedBlobFile(filename=u"scanned.pdf"))
        self.dmsappendixfile = createContentInContainer(
            self.omail, "dmsappendixfile", title=u"A001", file=NamedBlobFile(filename=u"appendix.odt")
        )
        self.form = self.omail.restrictedTraverse("@@duplicate")

    @patch("imio.dms.mail.browser.views.DuplicateForm.extractData")
    def test_duplicate(self, extractData):
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': True,
            'keep_linked_mails': True,
            'keep_dms_files': True,
            'keep_annexes': True,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")

        brains = self.pc(portal_type="dmsoutgoingmail", id="copy_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertEqual(duplicated_mail.title, u"My title")
        self.assertEqual(duplicated_mail.description, u"Description")
        self.assertEqual(duplicated_mail.send_modes, ["post"])
        self.assertGreater(duplicated_mail.creation_date, self.omail.creation_date)
        self.assertNotEqual(duplicated_mail.internal_reference_no, self.omail.internal_reference_no)
        self.assertIsNone(duplicated_mail.mail_date)
        self.assertIsNone(duplicated_mail.due_date)
        self.assertIsNone(duplicated_mail.outgoing_date)

        # Test keep_category
        self.assertEqual(duplicated_mail.classification_categories, self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories)
        # Test keep_folder
        self.assertEqual(duplicated_mail.classification_folders, [self.portal.folders['ordre-public-reglement-general-de-police'].UID()])
        # Test keep_linked_mails
        self.assertEqual(len(duplicated_mail.reply_to), 2)
        self.assertEqual(self.omail2, duplicated_mail.reply_to[0].to_object)
        # Test keep_dms_files
        self.assertIn("d001", duplicated_mail)
        # Test keep_annexes
        self.assertIn("a001", duplicated_mail)
        # Test link_to_original
        self.assertEqual(self.omail, duplicated_mail.reply_to[1].to_object)

        # Test not keeping categories
        extractData.return_value = {
            'keep_category': False,
            'keep_folder': True,
            'keep_linked_mails': True,
            'keep_dms_files': True,
            'keep_annexes': True,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy2_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertIsNone(duplicated_mail.classification_categories)

        # Test not keeping folders
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': False,
            'keep_linked_mails': True,
            'keep_dms_files': True,
            'keep_annexes': True,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy3_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertIsNone(duplicated_mail.classification_folders)

        # Test not keeping linked mails
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': True,
            'keep_linked_mails': False,
            'keep_dms_files': True,
            'keep_annexes': True,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy4_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertEqual(len(duplicated_mail.reply_to), 1)
        self.assertNotEqual(self.omail2, duplicated_mail.reply_to[0].to_object)

        # Test not keeping dms files
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': True,
            'keep_linked_mails': True,
            'keep_dms_files': False,
            'keep_annexes': True,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy5_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertNotIn("d001", duplicated_mail)

        # Test not keeping annexes
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': True,
            'keep_linked_mails': True,
            'keep_dms_files': True,
            'keep_annexes': False,
            'link_to_original': True,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy6_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertNotIn("a001", duplicated_mail)

        # Test not linking to original
        extractData.return_value = {
            'keep_category': True,
            'keep_folder': True,
            'keep_linked_mails': True,
            'keep_dms_files': True,
            'keep_annexes': True,
            'link_to_original': False,
        }, None
        self.form.handleApply(self.form, "duplicate")
        brains = self.pc(portal_type="dmsoutgoingmail", id="copy7_of_my-id")
        self.assertEqual(len(brains), 1)
        duplicated_mail = brains[0].getObject()
        self.assertEqual(len(duplicated_mail.reply_to), 1)
        self.assertNotEqual(self.omail, duplicated_mail.reply_to[0].to_object)
