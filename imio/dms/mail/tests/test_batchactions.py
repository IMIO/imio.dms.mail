# -*- coding: utf-8 -*-
"""Test views."""
from collective.contact.duplicated.interfaces import ICollectiveContactDuplicatedLayer
from DateTime import DateTime
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone import api
from zope.interface import alsoProvides

import datetime
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
        self.omsf = self.portal["outgoing-mail"]["mail-searches"]
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.om2 = get_object(oid="reponse2", ptype="dmsoutgoingmail")
        self.elec = self.portal["contacts"]["electrabel"]
        self.swde = self.portal["contacts"]["swde"]

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

    def test_ReplyBatchActionForm(self):
        view = self.msf.unrestrictedTraverse("@@reply-batch-action")
        self.assertFalse(view.overlay)  # the form is a full page, not an overlay
        view.request["URL"] = "{}/reply-batch-action".format(self.msf.absolute_url())
        view.request["uids"] = ",".join([self.im1.UID(), self.im2.UID()])
        rendered = view()
        # the multiple-reply form is rendered in place
        self.assertEqual(view.request["URL"], "{}/multiple-reply".format(self.msf.absolute_url()))
        self.assertIn(u"Reply to 2 incoming mails", rendered)
        self.assertIn(u'name="form.widgets.IDublinCore.title"', rendered)
        self.assertEqual(
            view.request.form["form.widgets.reply_to"],
            ("/".join(self.im1.getPhysicalPath()), "/".join(self.im2.getPhysicalPath())),
        )

    def test_IMSenderBatchActionForm(self):
        self.assertListEqual([rel.to_object for rel in self.im1.sender], [self.elec])
        self.assertListEqual([rel.to_object for rel in self.im2.sender], [self.swde])
        uids = ",".join([self.im1.UID(), self.im2.UID()])
        view = self.msf.unrestrictedTraverse("@@im-sender-batch-action")
        view.request["uids"] = uids
        view.update()
        self.assertTrue(view.do_apply)
        # add
        view.widgets.extract = lambda *a, **kw: ({"action_choice": u"add", "added_values": [self.swde]}, [])
        view.handleApply(view, "apply")
        self.assertSetEqual(set([rel.to_object for rel in self.im1.sender]), {self.elec, self.swde})
        self.assertListEqual([rel.to_object for rel in self.im2.sender], [self.swde])
        self.assertSetEqual(
            set([b.UID for b in self.pc(sender_index=self.swde.UID())]) & {self.im1.UID(), self.im2.UID()},
            {self.im1.UID(), self.im2.UID()},
        )
        # remove
        view.widgets.extract = lambda *a, **kw: ({"action_choice": u"remove", "removed_values": [self.elec]}, [])
        view.handleApply(view, "apply")
        self.assertListEqual([rel.to_object for rel in self.im1.sender], [self.swde])
        self.assertNotIn(self.im1.UID(), [b.UID for b in self.pc(sender_index=self.elec.UID())])

    def test_OutgoingDateBatchActionForm(self):
        view = self.omsf.unrestrictedTraverse("@@outgoingdate-batch-action")
        view.request["uids"] = ",".join([self.om1.UID(), self.om2.UID()])
        view.update()
        self.assertTrue(view.do_apply)
        new_date = datetime.datetime(2025, 3, 4, 10, 30)
        view.widgets.extract = lambda *a, **kw: ({"outgoing_date": new_date}, [])
        view.handleApply(view, "apply")
        self.assertEqual(self.om1.outgoing_date, new_date)
        self.assertEqual(self.om2.outgoing_date, new_date)
        # in_out_date index is updated
        brains = self.pc(
            UID=[self.om1.UID(), self.om2.UID()],
            in_out_date={"query": [DateTime("2025/03/04 00:00"), DateTime("2025/03/05 00:00")], "range": "min:max"},
        )
        self.assertEqual(len(brains), 2)

    def test_SendModesBatchActionForm(self):
        uids = ",".join([self.om1.UID(), self.om2.UID()])
        self.assertListEqual(self.om1.send_modes, [u"post"])
        view = self.omsf.unrestrictedTraverse("@@send-modes-batch-action")
        view.request["uids"] = uids
        view.update()
        self.assertTrue(view.do_apply)  # Manage portal on dashboard
        view.widgets.extract = lambda *a, **kw: ({"action_choice": u"add", "added_values": [u"email"]}, [])
        view.handleApply(view, "apply")
        # vocabulary order is kept
        self.assertListEqual(list(self.om1.send_modes), [u"post", u"email"])
        self.assertListEqual(list(self.om2.send_modes), [u"post", u"email"])
        self.assertEqual(len(self.pc(UID=[self.om1.UID(), self.om2.UID()], Subject=u"email")), 2)
        # the result cannot be empty
        view.widgets.extract = lambda *a, **kw: (
            {"action_choice": u"remove", "removed_values": [u"post", u"email"]},
            [],
        )
        view.handleApply(view, "apply")
        self.assertListEqual(list(self.om1.send_modes), [u"post", u"email"])
        # an agent cannot apply it
        change_user(self.portal, "agent")
        view = self.omsf.unrestrictedTraverse("@@send-modes-batch-action")
        view.request["uids"] = uids
        view.update()
        self.assertFalse(view.do_apply)

    def test_RecipientsBatchActionForm(self):
        self.assertListEqual([rel.to_object for rel in self.om1.recipients], [self.elec])
        view = self.omsf.unrestrictedTraverse("@@recipients-batch-action")
        view.request["uids"] = ",".join([self.om1.UID(), self.om2.UID()])
        view.update()
        self.assertTrue(view.do_apply)
        view.widgets.extract = lambda *a, **kw: (
            {"action_choice": u"replace", "removed_values": [self.elec], "added_values": [self.swde]},
            [],
        )
        view.handleApply(view, "apply")
        self.assertListEqual([rel.to_object for rel in self.om1.recipients], [self.swde])
        self.assertListEqual([rel.to_object for rel in self.om2.recipients], [self.swde])
        self.assertIn(self.om1.UID(), [b.UID for b in self.pc(recipients_index=self.swde.UID())])
        view.widgets.extract = lambda *a, **kw: ({"action_choice": u"overwrite", "added_values": [self.elec]}, [])
        view.handleApply(view, "apply")
        self.assertListEqual([rel.to_object for rel in self.om1.recipients], [self.elec])
        self.assertListEqual([rel.to_object for rel in self.om2.recipients], [self.elec])

    def test_CopyToBatchActionForm(self):
        tplf = self.portal["templates"]["om"]
        main = tplf["main"]
        folder_uid = self.pgof["direction-generale"]["secretariat"].UID()
        target = tplf[folder_uid]
        before = target.objectIds()
        view = tplf.unrestrictedTraverse("@@copy-to-batch-action")
        view.request["uids"] = main.UID()
        view.update()
        # only sub folders are proposed
        self.assertSetEqual(
            set([t.value for t in view.voc]),
            set([obj.UID() for obj in tplf.objectValues() if obj.portal_type == "Folder"]),
        )
        self.assertIn(target.UID(), [t.value for t in view.voc])
        self.assertTrue(view.do_apply)
        self.assertEqual(view.widgets["folders"].multiple, "multiple")
        view.widgets.extract = lambda *a, **kw: ({"folders": [target.UID()]}, [])
        view.handleApply(view, "apply")
        added = [oid for oid in target.objectIds() if oid not in before]
        self.assertEqual(len(added), 1)
        self.assertEqual(target[added[0]].title, main.title)
        # an encoder can copy in its organizations folders (Contributor given to <org>_encodeur)
        change_user(self.portal, "agent")
        agent_orgs = [g.getId()[:-9] for g in api.group.get_groups(username="agent") if g.getId().endswith("_encodeur")]
        view = tplf.unrestrictedTraverse("@@copy-to-batch-action")
        view.request["uids"] = main.UID()
        view.update()
        self.assertSetEqual(set([t.value for t in view.voc]), set([tplf[uid].UID() for uid in agent_orgs]))
        self.assertTrue(view.do_apply)
        # a user without add permission has no folder
        change_user(self.portal, "lecteur")
        view = tplf.unrestrictedTraverse("@@copy-to-batch-action")
        view.request["uids"] = main.UID()
        view.update()
        self.assertEqual(len(view.voc), 0)
        self.assertFalse(view.do_apply)
