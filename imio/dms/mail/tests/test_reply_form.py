# -*- coding: utf-8 -*-
"""Test reply forms."""
from datetime import datetime
from imio.dms.mail import PERIODS
from imio.dms.mail.browser.reply_form import MultipleReplyForm
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from plone import api
from z3c.form.interfaces import HIDDEN_MODE
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.i18n import translate
from zope.intid.interfaces import IIntIds

import unittest


PREFIX_KEY = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_response_prefix"


class TestReplyForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.imail1 = get_object(oid="courrier1", ptype="dmsincomingmail")

    def test_updateFields(self):
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.updateFields()
        form = self.portal.REQUEST.form
        expected_linked_mails = ("/".join(self.imail1.getPhysicalPath()),)
        self.assertEqual(form["form.widgets.reply_to"], expected_linked_mails)
        self.assertEqual(translate(view.label), u"Reply to E0001 - Courrier 1")
        expected_recipients = ("/plone/contacts/electrabel",)
        self.assertEqual(form["form.widgets.recipients"], expected_recipients)
        # email fields are not in the reply form of a mail
        self.assertIn("orig_sender_email", view.fields)

    def test_updateWidgets(self):
        """GET prefill of the reply form."""
        change_user(self.portal, "agent")
        api.portal.set_registry_record(PREFIX_KEY, u"Re: ")
        self.request["REQUEST_METHOD"] = "GET"
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.update()
        self.assertEqual(view.widgets["IDublinCore.title"].value, u"Re: Courrier 1")
        self.assertEqual(view.widgets["ITask.assigned_user"].value, ["agent"])
        self.assertEqual(view.widgets["send_modes"].value, [u"post"])
        self.assertEqual(view.widgets["treating_groups"].value, self.imail1.treating_groups)
        self.assertEqual(view.widgets["reply_to"].value, ("/".join(self.imail1.getPhysicalPath()),))
        # no original sender email on a paper mail: field hidden
        self.assertEqual(view.widgets["orig_sender_email"].mode, HIDDEN_MODE)
        # the rendered form contains the prefilled title
        rendered = view.render()
        self.assertIn(u'value="Re: Courrier 1"', rendered)
        # the prefix is not added twice
        self.imail1.title = u"Re: Courrier 1"
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.update()
        self.assertEqual(view.widgets["IDublinCore.title"].value, u"Re: Courrier 1")
        # masterselect anonymous call: the prefill is skipped
        self.imail1.title = u"Courrier 1"
        self.request["masterID"] = "form-widgets-treating_groups"
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.update()
        self.assertEqual(view.widgets["IDublinCore.title"].value, u"Courrier 1")

    def test_get_send_modes(self):
        change_user(self.portal)
        self.request["REQUEST_METHOD"] = "GET"
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.update()
        self.assertListEqual(view.get_send_modes(), [u"post"])
        iemail = sub_create(
            self.portal["incoming-mail"],
            "dmsincoming_email",
            datetime.now(),
            "my-email",
            **{"title": u"My email", "treating_groups": self.imail1.treating_groups,
               "sender": [RelationValue(getUtility(IIntIds).getId(self.portal["contacts"]["electrabel"]))],
               "orig_sender_email": u'"Dexter Morgan" <dexter.morgan@mpd.am>'}
        )
        view = iemail.unrestrictedTraverse("@@reply")
        view.update()
        self.assertListEqual(view.get_send_modes(), [u"email"])
        # original sender email is prefilled for an email
        self.assertEqual(view.widgets["orig_sender_email"].value, u'"Dexter Morgan" <dexter.morgan@mpd.am>')
        self.assertNotEqual(view.widgets["orig_sender_email"].mode, HIDDEN_MODE)

    def test_add(self):
        change_user(self.portal)
        omail1 = api.content.create(
            container=self.portal["outgoing-mail"], type="dmsoutgoingmail", id="newo1", title="TEST"
        )
        view = self.imail1.unrestrictedTraverse("@@reply")
        view.add(omail1)
        self.assertIn("newo1", self.portal["outgoing-mail"][datetime.now().strftime(PERIODS["week"])])


class TestMultipleReplyForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.msf = self.portal["incoming-mail"]["mail-searches"]
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.im2 = get_object(oid="courrier2", ptype="dmsincomingmail")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        change_user(self.portal)

    def _view(self):
        self.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        self.request["REQUEST_METHOD"] = "GET"
        return self.msf.unrestrictedTraverse("@@multiple-reply")

    def test_init(self):
        view = self._view()
        self.assertIsInstance(view, MultipleReplyForm)
        self.assertEqual(view.uids, ",".join([self.im1.UID(), self.im2.UID()]))
        self.assertListEqual([b.UID for b in view.brains], [self.im1.UID(), self.im2.UID()])

    def test_label(self):
        view = self._view()
        self.assertEqual(translate(view.label, context=self.request), u"Reply to 2 incoming mails")

    def test_updateFields(self):
        view = self._view()
        view.updateFields()
        form = self.request.form
        # Plone 4: reply_to and recipients are prefilled with paths
        self.assertEqual(
            form["form.widgets.reply_to"],
            ("/".join(self.im1.getPhysicalPath()), "/".join(self.im2.getPhysicalPath())),
        )
        self.assertListEqual(
            sorted(form["form.widgets.recipients"]), ["/plone/contacts/electrabel", "/plone/contacts/swde"]
        )
        # existing form values are kept
        form["form.widgets.reply_to"] = ("/plone/foo",)
        view.updateFields()
        self.assertEqual(form["form.widgets.reply_to"], ("/plone/foo",))
        # masterselect second call without uids: no prefill
        del form["form.widgets.reply_to"]
        self.request["uids"] = ""
        view = self.msf.unrestrictedTraverse("@@multiple-reply")
        view.updateFields()
        self.assertNotIn("form.widgets.reply_to", form)

    def test_updateWidgets(self):
        api.portal.set_registry_record(PREFIX_KEY, u"Re: ")
        self.im1.recipient_groups = [self.pgof["direction-generale"]["grh"].UID()]
        self.im1.reindexObject()
        self.im2.recipient_groups = [self.pgof["direction-financiere"].UID()]
        self.im2.reindexObject()
        view = self._view()
        view.update()
        self.assertEqual(view.widgets["IDublinCore.title"].value, u"Re: Courrier 1")
        self.assertEqual(view.widgets["treating_groups"].value, self.im1.treating_groups)
        self.assertEqual(
            view.widgets["reply_to"].value,
            ("/".join(self.im1.getPhysicalPath()), "/".join(self.im2.getPhysicalPath())),
        )
        self.assertSetEqual(
            set(view.widgets["recipient_groups"].value),
            {self.pgof["direction-generale"]["grh"].UID(), self.pgof["direction-financiere"].UID()},
        )
        rendered = view.render()
        self.assertIn(u'value="Re: Courrier 1"', rendered)
