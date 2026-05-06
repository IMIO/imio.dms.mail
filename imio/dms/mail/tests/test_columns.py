# -*- coding: utf-8 -*-
from datetime import datetime
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.browser.table import OMVersionsTable
from imio.dms.mail.columns import SenderColumn
from imio.dms.mail.columns import SessionIdColumn
from imio.dms.mail.columns import TaskActionsColumn
from imio.dms.mail.columns import TaskParentColumn
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.esign.utils import add_files_to_session
from imio.esign.utils import create_session
from imio.helpers.content import get_object
from persistent.list import PersistentList
from plone import api
from plone.app.testing import login
from plone.app.testing import TEST_USER_ID
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestColumns(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.intids = getUtility(IIntIds)
        self.mail_table = self.portal["incoming-mail"]["mail-searches"].unrestrictedTraverse("@@faceted-table-view")
        self.task_table = self.portal["incoming-mail"]["mail-searches"].unrestrictedTraverse("@@faceted-table-view")
        self.imf = self.portal["incoming-mail"]
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.im5 = get_object(oid="courrier5", ptype="dmsincomingmail")
        self.ta1 = self.im1["tache1"]
        self.ta31 = self.im1["tache3"]["tache3-1"]
        self.maxDiff = None

    def test_SenderColumn(self):
        column = SenderColumn(self.portal, self.portal.REQUEST, self.mail_table)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(
            column.renderCell(brain),
            u"<a href='http://nohost/plone/contacts/jeancourant/agent-electrabel' target='_blank' "
            "class='pretty_link link-tooltip'><span class='pretty_link_icons'><img title='Held position' "
            "src='http://nohost/plone/held_position_icon.png' /></span><span class='pretty_link_content'"
            ">Monsieur Jean Courant, Agent (Electrabel)</span></a>",
        )
        # multiple senders
        self.im5.sender.append(RelationValue(self.intids.getId(self.portal["contacts"]["sergerobinet"])))
        self.im5.reindexObject(idxs=["sender_index"])
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        rendered = column.renderCell(brain)
        self.assertIn('<ul class="contacts_col"><li>', rendered)
        self.assertEqual(rendered.count("<a href"), 2)
        # no sender
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            **{"title": u"My title", "description": u"Description"}
        )
        brain = self.portal.portal_catalog(UID=imail.UID())[0]
        self.assertEqual(column.renderCell(brain), "-")
        # sender not found: we delete it
        self.im5.sender = self.im5.sender[0:1]
        self.im5.reindexObject(idxs=["sender_index"])
        api.content.delete(obj=self.portal["contacts"]["jeancourant"]["agent-electrabel"], check_linkintegrity=False)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(column.renderCell(brain), "-")

    def test_TaskParentColumn(self):
        column = TaskParentColumn(self.portal, self.portal.REQUEST, self.task_table)
        brain = self.portal.portal_catalog(UID=self.ta1.UID())[0]
        mail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(
            column.renderCell(brain),
            u"<a class='pretty_link' title='E0001 - Courrier 1' "
            u"href='{}' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
            u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png' style="
            u"\"width: 16px; height: 16px;\" /></span><span class='pretty_link_content state-created'>"
            u"E0001 - Courrier 1</span></a>".format(mail.absolute_url()),
        )
        brain = self.portal.portal_catalog(UID=self.ta31.UID())[0]
        self.assertEqual(
            column.renderCell(brain),
            u"<a class='pretty_link' title='E0001 - Courrier 1' "
            u"href='{}' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
            u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png' style="
            u"\"width: 16px; height: 16px;\" /></span><span class='pretty_link_content state-created'>"
            u"E0001 - Courrier 1</span></a>".format(mail.absolute_url()),
        )

    def test_TaskActionsColumn(self):
        column = TaskActionsColumn(self.portal, self.portal.REQUEST, None)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username=TEST_USER_ID)
        rendered = column.renderCell(self.ta1)
        self.assertIn("do_to_assign", rendered)
        self.assertIn('title="Edit"', rendered)
        self.assertIn('title="Delete"', rendered)
        self.assertIn('"overlay-history"', rendered)
        column.view_name = ""
        self.assertRaises(KeyError, column.renderCell, self.ta1)


class TestSessionIdColumn(unittest.TestCase):
    """Tests for SessionIdColumn."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-esigning", run_dependencies=False
        )
        change_user(self.portal)

        # 1 omail, 3 files: file_a in 2 sessions, file_b in 1 session, file_c in no session
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        file_a = omail["1"]
        file_b = get_object(oid="reponse2", ptype="dmsoutgoingmail")["1"]
        file_c = get_object(oid="reponse3", ptype="dmsoutgoingmail")["1"]

        signers = [("agent", "agent@macommune.be", u"Test Agent", u"Agent")]
        self.sid0, _session = create_session(signers)
        add_files_to_session(signers, [file_a.UID(), file_b.UID()], session_id=self.sid0)
        self.sid1, _session = create_session(signers)
        add_files_to_session(signers, [file_a.UID()], session_id=self.sid1)

        approval = OMApprovalAdapter(omail)
        approval.annot["session_ids"] = PersistentList([self.sid0, self.sid1])

        pc = api.portal.get_tool("portal_catalog")
        self.brain_a = pc(UID=file_a.UID())[0]  # in sid0 and sid1
        self.brain_b = pc(UID=file_b.UID())[0]  # in sid0 only
        self.brain_c = pc(UID=file_c.UID())[0]  # in no session
        self.table = OMVersionsTable(omail, self.portal.REQUEST, None)
        self.column = SessionIdColumn(self.portal, self.portal.REQUEST, None)
        self.column.table = self.table

    def test_renderCell(self):
        """Empty for <=1 sessions; empty when file not in any session; single badge; comma-separated badges."""
        approval = self.table._approval

        # Guard: <=1 session_ids -> empty regardless of which file
        approval.annot["session_ids"] = PersistentList([])
        self.assertEqual(self.column.renderCell(self.brain_a), u"")
        approval.annot["session_ids"] = PersistentList([self.sid0])
        self.assertEqual(self.column.renderCell(self.brain_a), u"")
        approval.annot["session_ids"] = PersistentList([self.sid0, self.sid1])  # back to setUp

        # File not in any session -> empty
        self.assertEqual(self.column.renderCell(self.brain_c), u"")

        # File in exactly one of the two sessions -> one badge, no comma
        rendered = self.column.renderCell(self.brain_b)
        collection_uid = self.portal["outgoing-mail"]["mail-searches"]["in_esign_sessions"].UID()
        self.assertEqual(
            rendered,
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=0 "
            u'title="Paraphéo session ID: 0" class="pdf-session-badge">0</a>'.format(collection_uid),
        )

        # File in both sessions -> two badges, comma-separated, sorted by session id
        rendered = self.column.renderCell(self.brain_a)
        self.assertEqual(
            rendered,
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=0 "
            u'title="Paraphéo session ID: 0" class="pdf-session-badge">0</a>, '
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=1 "
            u'title="Paraphéo session ID: 1" class="pdf-session-badge">1</a>'.format(collection_uid, collection_uid),
        )
