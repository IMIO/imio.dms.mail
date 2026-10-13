# -*- coding: utf-8 -*-
"""Test views."""
from collective.contact.duplicated.interfaces import ICollectiveContactDuplicatedLayer
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from collective.eeafaceted.collectionwidget.utils import getCollectionLinkCriterion
from collective.iconifiedcategory.interfaces import ICollectiveIconifiedCategoryLayer
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.batchactions import BATCH_APPROVAL_LIMIT_RECORD
from imio.dms.mail.browser.batchactions import BATCH_APPROVAL_SIGNERS_RECORD
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.esign.config import set_esign_registry_file_url
from imio.fpaudit import LOG_DIR
from imio.fpaudit.utils import get_lines_of
from imio.fpaudit.utils import get_log_option
from imio.helpers.content import get_object
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.statusmessages import STATUSMESSAGEKEY
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield.relation import RelationValue
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds

import os
import unittest


class BatchActions(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pc = api.portal.get_tool("portal_catalog")
        self.imf = self.portal["incoming-mail"]
        self.msf = self.imf["mail-searches"]
        self.imdb = self.imf["mail-searches"]["all_mails"]
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.im2 = get_object(oid="courrier2", ptype="dmsincomingmail")
        self.im3 = get_object(oid="courrier3", ptype="dmsincomingmail")
        self.im4 = get_object(oid="courrier4", ptype="dmsincomingmail")
        self.tsf = self.portal["tasks"]["task-searches"]
        self.ta1 = self.im1["tache1"]
        self.ta2 = self.im1["tache2"]
        self.ta3 = self.im1["tache3"]
        self.pgof = self.portal["contacts"]["plonegroup-organization"]

    def test_TransitionBatchActionForm(self):
        self.assertEqual("created", api.content.get_state(self.im1))
        view = self.msf.unrestrictedTraverse("@@transition-batch-action")
        view.request.form["form.widgets.uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        # override z3c.form.field.FieldWidgets.extract
        view.widgets.extract = lambda *a, **kw: ({"transition": u"propose_to_manager", "comment": u""}, [])
        view.handleApply(view, "apply")
        self.assertEqual("proposed_to_manager", api.content.get_state(self.im1))
        self.assertEqual("proposed_to_manager", api.content.get_state(self.im2))

    def test_TreatingGroupBatchActionForm(self):
        self.assertEqual(self.im1.treating_groups, self.pgof["direction-generale"].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof["direction-generale"]["secretariat"].UID())
        api.group.add_user(groupname="{}_editeur".format(self.pgof["direction-financiere"].UID()), username="chef")
        self.im2.assigned_user = "agent"
        self.im2.reindexObject()
        # assigned user blocking
        view = self.msf.unrestrictedTraverse("@@treatinggroup-batch-action")
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"treating_group": self.pgof["direction-financiere"].UID()}, [])
        view.handleApply(view, "apply")
        self.assertEqual(self.im1.treating_groups, self.pgof["direction-generale"].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof["direction-generale"]["secretariat"].UID())
        # assigned_user not blocking
        self.im2.assigned_user = "chef"
        self.im2.reindexObject()
        view = self.msf.unrestrictedTraverse("@@treatinggroup-batch-action")
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"treating_group": self.pgof["direction-financiere"].UID()}, [])
        view.handleApply(view, "apply")
        self.assertEqual(self.im1.treating_groups, self.pgof["direction-financiere"].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof["direction-financiere"].UID())

    def test_RecipientGroupBatchActionForm(self):
        self.im1.recipient_groups = [
            self.pgof["direction-generale"].UID(),
            self.pgof["direction-financiere"]["budgets"].UID(),
        ]
        self.im2.recipient_groups = [
            self.pgof["direction-generale"].UID(),
            self.pgof["direction-generale"]["secretariat"].UID(),
        ]
        view = self.msf.unrestrictedTraverse("@@recipientgroup-batch-action")
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        # test remove action
        view.widgets.extract = lambda *a, **kw: (
            {"action_choice": "remove", "removed_values": [self.pgof["direction-generale"].UID()]},
            [],
        )
        view.handleApply(view, "apply")
        self.assertListEqual(self.im1.recipient_groups, [self.pgof["direction-financiere"]["budgets"].UID()])
        self.assertListEqual(self.im2.recipient_groups, [self.pgof["direction-generale"]["secretariat"].UID()])
        # test add action
        view.widgets.extract = lambda *a, **kw: (
            {"action_choice": "add", "added_values": [self.pgof["direction-financiere"].UID()]},
            [],
        )
        view.handleApply(view, "apply")
        self.assertSetEqual(
            set(self.im1.recipient_groups),
            {self.pgof["direction-financiere"]["budgets"].UID(), self.pgof["direction-financiere"].UID()},
        )
        self.assertSetEqual(
            set(self.im2.recipient_groups),
            {self.pgof["direction-generale"]["secretariat"].UID(), self.pgof["direction-financiere"].UID()},
        )
        # test replace action (only applied when all removed values are found on the object)
        view.widgets.extract = lambda *a, **kw: (
            {
                "action_choice": "replace",
                "removed_values": [
                    self.pgof["direction-financiere"].UID(),
                    self.pgof["direction-financiere"]["budgets"].UID(),
                ],
                "added_values": [
                    self.pgof["direction-generale"].UID(),
                    self.pgof["direction-generale"]["secretariat"].UID(),
                ],
            },
            [],
        )
        view.handleApply(view, "apply")
        self.assertSetEqual(
            set(self.im1.recipient_groups),
            {self.pgof["direction-generale"].UID(), self.pgof["direction-generale"]["secretariat"].UID()},
        )
        # not changed because all values to remove are not found
        self.assertSetEqual(
            set(self.im2.recipient_groups),
            {self.pgof["direction-generale"]["secretariat"].UID(), self.pgof["direction-financiere"].UID()},
        )
        # test overwrite action
        view.widgets.extract = lambda *a, **kw: (
            {
                "action_choice": "overwrite",
                "added_values": [
                    self.pgof["direction-generale"].UID(),
                    self.pgof["direction-generale"]["secretariat"].UID(),
                ],
            },
            [],
        )
        view.handleApply(view, "apply")
        self.assertSetEqual(
            set(self.im1.recipient_groups),
            {self.pgof["direction-generale"].UID(), self.pgof["direction-generale"]["secretariat"].UID()},
        )
        self.assertSetEqual(
            set(self.im2.recipient_groups),
            {self.pgof["direction-generale"].UID(), self.pgof["direction-generale"]["secretariat"].UID()},
        )

    def test_AssignedUserBatchActionForm(self):
        self.assertIsNone(self.im1.assigned_user)
        self.assertIsNone(self.im2.assigned_user)
        view = self.msf.unrestrictedTraverse("@@assigneduser-batch-action")
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"assigned_user": "agent"}, [])
        view.handleApply(view, "apply")
        self.assertEqual(self.im1.assigned_user, "agent")
        self.assertEqual(self.im2.assigned_user, "agent")
        view = self.msf.unrestrictedTraverse("@@assigneduser-batch-action")
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"assigned_user": "__none__"}, [])
        view.handleApply(view, "apply")
        self.assertIsNone(self.im1.assigned_user)
        self.assertIsNone(self.im2.assigned_user)

    def test_TransitionBatchActionFormOnTasks(self):
        self.assertEqual("created", api.content.get_state(self.ta1))
        self.assertEqual("created", api.content.get_state(self.ta2))
        view = self.tsf.unrestrictedTraverse("@@transition-batch-action")
        view.request.form["form.widgets.uids"] = ",".join([self.ta1.UID(), self.ta2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"transition": u"do_to_assign", "comment": u""}, [])
        view.handleApply(view, "apply")
        # to_do due to automatic transition
        self.assertEqual("to_do", api.content.get_state(self.ta1))
        self.assertEqual("to_do", api.content.get_state(self.ta2))

    def test_AssignedGroupBatchActionForm(self):
        self.assertEqual(self.ta1.assigned_group, self.pgof["direction-generale"].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof["direction-financiere"].UID())
        view = self.tsf.unrestrictedTraverse("@@assignedgroup-batch-action")
        view.request["uids"] = ",".join([self.ta1.UID(), self.ta3.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: (
            {"assigned_group": self.pgof["direction-financiere"]["budgets"].UID()},
            [],
        )
        view.handleApply(view, "apply")
        self.assertEqual(self.ta1.assigned_group, self.pgof["direction-financiere"]["budgets"].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof["direction-financiere"]["budgets"].UID())
        # assigned user blocking
        self.ta1.assigned_user = "agent"
        self.ta1.reindexObject()
        view = self.tsf.unrestrictedTraverse("@@assignedgroup-batch-action")
        view.request["uids"] = ",".join([self.ta1.UID(), self.ta3.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"assigned_group": self.pgof["direction-generale"].UID()}, [])
        view.handleApply(view, "apply")
        # Not changed !
        self.assertEqual(self.ta1.assigned_group, self.pgof["direction-financiere"]["budgets"].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof["direction-financiere"]["budgets"].UID())

    def test_DuplicatedBatchActionForm_on_personnel_dashboard(self):
        pf = self.portal["contacts"]["personnel-folder"]
        psf = pf["personnel-searches"]
        p1 = api.content.create(container=pf, type="person", id="dup1", lastname=u"Dupont")
        p2 = api.content.create(container=pf, type="person", id="dup2", lastname=u"Dupond")
        view = psf.unrestrictedTraverse("@@duplicated-batch-action")
        alsoProvides(view.request, ICollectiveContactDuplicatedLayer)
        view.request["uids"] = ",".join([p1.UID(), p2.UID()])
        result = view()
        self.assertIn(p1.UID(), result)
        self.assertIn(p2.UID(), result)

    def test_TaskAssignedUserBatchActionForm(self):
        self.assertIsNone(self.ta1.assigned_user)
        self.assertIsNone(self.ta2.assigned_user)
        view = self.msf.unrestrictedTraverse("@@assigneduser-batch-action")
        view.request["uids"] = ",".join([self.ta1.UID(), self.ta2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({"assigned_user": "chef"}, [])
        view.handleApply(view, "apply")
        self.assertEqual(self.ta1.assigned_user, "chef")
        self.assertEqual(self.ta2.assigned_user, "chef")


class TestApproveBatchActionForm(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.change_user("siteadmin")
        alsoProvides(self.request, ICollectiveIconifiedCategoryLayer)
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        self.om_searches = self.portal["outgoing-mail"]["mail-searches"]
        self.req_searches = self.portal["requests"]["requests-searches"]
        set_esign_registry_file_url("https://downloads.files.com")
        pf = self.portal["contacts"]["personnel-folder"]
        self.bourgmestre = pf["bourgmestre"]["bourgmestre"]
        self.dirg = pf["dirg"]["directeur-general"]
        self.chef = pf["chef"]
        # the bourgmestre signs, chef approves for him
        self.omail1 = self._create_mail("om1", [(self.bourgmestre, self.chef.UID())], "012999900000601")
        # the directeur general approves first for himself, then chef for the bourgmestre
        self.omail2 = self._create_mail(
            "om2", [(self.dirg, u"_themself_"), (self.bourgmestre, self.chef.UID())], "012999900000602"
        )

    def _create_mail(self, oid, signers, scan_id):
        """Create an e-signed outgoing mail with one file to approve. signers: (held position, approving)."""
        intids = getUtility(IIntIds)
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            oid,
            title=u"Courrier sortant {}".format(oid),
            internal_reference_no=internalReferenceOutgoingMailDefaultValue(DummyView(self.portal, self.request)),
            mail_type="courrier",
            treating_groups=self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            recipients=[RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            assigned_user="agent",
            sender=self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            send_modes=u"post",
            signers=[
                {"number": i, "signer": hp.UID(), "approvings": [approving], "editor": False}
                for i, (hp, approving) in enumerate(signers, start=1)
            ],
            esign=True,
        )
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(
                omail,
                "dmsommainfile",
                id="file1",
                scan_id=scan_id,
                file=NamedBlobFile(fo.read(), filename=filename),
                content_category=calculate_category_id(ct),
            )
        return omail

    def _select_collection(self, searches, col_id):
        """Select a dashboard collection as the faceted request does."""
        self.request.form["{}[]".format(getCollectionLinkCriterion(searches).__name__)] = searches[col_id].UID()
        IAnnotations(self.request).pop("collectionwidget-utils-getCurrentCollection-{}".format(searches.UID()), None)

    def _actions(self, searches):
        return [action["name"] for action in BatchActionsViewlet(searches, self.request, None, None)
                .get_batch_actions()]

    def test_available(self):
        self._select_collection(self.om_searches, "to_approve")
        # no signer enabled: hidden for everyone
        self.assertNotIn("approve-batch-action", self._actions(self.om_searches))
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID()])
        self.assertIn("approve-batch-action", self._actions(self.om_searches))
        self._select_collection(self.om_searches, "all_mails")
        self.assertNotIn("approve-batch-action", self._actions(self.om_searches))
        # requests dashboard
        self._select_collection(self.req_searches, "to_approve")
        self.assertIn("approve-batch-action", self._actions(self.req_searches))
        self._select_collection(self.req_searches, "all_requests")
        self.assertNotIn("approve-batch-action", self._actions(self.req_searches))
        # the form opened with the selected uids is not checked against the collection
        self.request["uids"] = self.omail1.UID()
        self.assertTrue(self.req_searches.restrictedTraverse("@@approve-batch-action").available())

    def _propose_to_chef(self):
        """om1, for the bourgmestre, and a new mail, for the directeur general, both waiting for chef."""
        omail3 = self._create_mail("om3", [(self.dirg, self.chef.UID())], "012999900000603")
        for omail in (self.omail1, omail3):
            api.content.transition(omail, "propose_to_approve")
        self.change_user("chef")
        return omail3

    def _form(self, *omails):
        """The overlay form opened on omails."""
        self.request.form["form.widgets.uids"] = ",".join([omail.UID() for omail in omails])
        form = self.om_searches.restrictedTraverse("@@approve-batch-action")
        form.update()
        return form

    def test__update(self):
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID(), self.dirg.UID()])
        omail3 = self._propose_to_chef()
        api.portal.set_registry_record(BATCH_APPROVAL_LIMIT_RECORD, 1)
        self.assertNotIn("apply", self._form(self.omail1, omail3).actions)
        # the directeur general is not enabled: one mail to approve, within the limit
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID()])
        self.assertIn("apply", self._form(self.omail1, omail3).actions)
        # nothing to approve
        self.assertNotIn("apply", self._form(omail3).actions)
        # 0 means no limit
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID(), self.dirg.UID()])
        api.portal.set_registry_record(BATCH_APPROVAL_LIMIT_RECORD, 0)
        self.assertIn("apply", self._form(self.omail1, omail3).actions)

    def test__excluded_mails(self):
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID()])
        omail3 = self._propose_to_chef()
        self.assertEqual(self._form(self.omail1, omail3)._excluded_mails(), [omail3])
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID(), self.dirg.UID()])
        self.assertEqual(self._form(self.omail1, omail3)._excluded_mails(), [])

    def test_description(self):
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID(), self.dirg.UID()])
        omail3 = self._propose_to_chef()
        api.portal.set_registry_record(BATCH_APPROVAL_LIMIT_RECORD, 1)
        descr = self._form(self.omail1, omail3).description
        base = descr.split(u"<div")[0]  # the number of selected elements
        self.assertEqual(
            descr,
            base + u'<div class="portalMessage error"><p>You can approve at most 1 element(s) at once: select fewer '
                   u'elements.</p></div>',
        )
        skipped = (
            u'<div class="portalMessage warning"><p>These mails will be skipped due to site settings:</p>'
            u'<ul><li><a href="{}" target="_blank">{}</a></li></ul></div>'.format(
                omail3.absolute_url(), omail3.Title().decode("utf8")
            )
        )
        # the directeur general is not enabled: one mail to approve, within the limit
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID()])
        self.assertEqual(self._form(self.omail1, omail3).description, base + skipped)
        api.portal.set_registry_record(BATCH_APPROVAL_LIMIT_RECORD, 0)
        self.assertEqual(
            self._form(self.omail1, omail3).description,
            base + u'<div class="portalMessage warning"><p>Approving too many files at once may take a long time'
                   u'</p></div>' + skipped,
        )
        # nothing to approve
        descr = self._form(omail3).description
        self.assertEqual(
            descr,
            descr.split(u"<div")[0] + u'<div class="portalMessage error"><p>None of the selected mails can be batch '
                                      u'approved due to site settings.</p></div>',
        )

    def _approve_as_current_user(self, *omails):
        """Apply the batch approval on omails from the overlay, return the messages the browser gets."""
        self.request.form["ajax_load"] = "1"
        self.request.form["form.widgets.uids"] = ",".join([omail.UID() for omail in omails])
        form = self.om_searches.restrictedTraverse("@@approve-batch-action")
        form.update()
        form.handleApply(form, "apply")
        # an expired cookie would never reach the browser
        self.assertNotIn("max_age", self.request.response.cookies[STATUSMESSAGEKEY])
        return [msg.message for msg in IStatusMessage(self.request).show()]

    def test__apply(self):
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID()])
        for omail in (self.omail1, self.omail2):
            api.content.transition(omail, "propose_to_approve")
        # chef approves om1 for the bourgmestre; om2, waiting for the directeur general, is not in his dashboard
        # but is skipped anyway
        self.change_user("chef")
        msgs = self._approve_as_current_user(self.omail1, self.omail2)
        self.assertEqual(
            msgs, [u"1 file(s) approved on 1 element(s). 1 element(s) skipped due to site settings."]
        )
        self.assertEqual(api.content.get_state(self.omail1), "to_be_signed")
        self.assertTrue(self.omail1.approval().is_file_approved(self.omail1["file1"].UID()))
        self.assertTrue(self.omail1["file1"].approved)
        self.assertEqual(len(self.omail1.approval().annot["session_ids"]), 1)
        self.assertEqual(api.content.get_state(self.omail2), "to_approve")
        self.assertEqual(self.omail2.approval().current_nb, 0)
        # the directeur general, enabled, approves for himself, then it is chef's turn for the bourgmestre
        self.change_user("dirg")
        api.portal.set_registry_record(BATCH_APPROVAL_SIGNERS_RECORD, [self.bourgmestre.UID(), self.dirg.UID()])
        msgs = self._approve_as_current_user(self.omail2)
        self.assertEqual(msgs, [u"1 file(s) approved on 1 element(s)."])
        self.assertEqual(api.content.get_state(self.omail2), "to_approve")
        self.assertEqual(self.omail2.approval().current_nb, 1)
        self.change_user("chef")
        self._approve_as_current_user(self.omail2)
        self.assertEqual(api.content.get_state(self.omail2), "to_be_signed")
        # the signing session cannot be created: the approval of the mail is cancelled
        self.change_user("siteadmin")
        omail3 = self._create_mail(
            "om3", [(self.bourgmestre, self.chef.UID())], "0129999"
        )
        api.content.transition(omail3, "propose_to_approve")
        self.change_user("chef")
        msgs = self._approve_as_current_user(omail3)
        self.assertEqual(msgs[0], u"0 file(s) approved on 0 element(s).")
        self.assertIn(u"Approval cancelled for: {} (".format(omail3.Title().decode("utf8")), msgs[1])
        self.assertIn(omail3["file1"].absolute_url(), msgs[1])  # the wrong scan id message
        self.assertEqual(api.content.get_state(omail3), "to_approve")
        self.assertEqual(omail3.approval().current_nb, 0)
        self.assertFalse(omail3.approval().is_file_approved(omail3["file1"].UID(), nb=0))
        self.assertFalse(omail3["file1"].approved)
        audit_log = os.path.join(LOG_DIR, get_log_option("esign", "audit_log"))
        last_line = next(get_lines_of(audit_log, actions=("batch_approval_rolled_back",)))
        self.assertIn(u"mail={} approver=chef reason=".format(omail3.UID()), last_line)
