# -*- coding: utf-8 -*-
from datetime import datetime
from imio.dms.mail.columns import SenderColumn
from imio.dms.mail.columns import TaskActionsColumn
from imio.dms.mail.columns import TaskParentColumn
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from plone import api
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
