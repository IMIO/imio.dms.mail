# -*- coding: utf-8 -*-
import unittest

from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer

from ..columns import SenderColumn, TaskParentColumn, TaskActionsColumn
from ..testing import DMSMAIL_INTEGRATION_TESTING


class TestColumns(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.mail_table = self.portal['incoming-mail']['mail-searches'].unrestrictedTraverse('@@faceted-table-view')
        self.task_table = self.portal['incoming-mail']['mail-searches'].unrestrictedTraverse('@@faceted-table-view')
        self.imf = self.portal['incoming-mail']
        self.im1 = self.imf['courrier1']
        self.im5 = self.imf['courrier5']
        self.ta1 = self.im1['tache1']
        self.ta31 = self.im1['tache3']['tache3-1']

    def test_SenderColumn(self):
        column = SenderColumn(self.portal, self.portal.REQUEST, self.mail_table)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(column.renderCell(brain),
                         u"<a href='http://nohost/plone/contacts/jeancourant/agent-electrabel' target='_blank'>"
                         "<span class='pretty_link_icons'><img title='Held position' src='http://nohost/plone/"
                         "held_position_icon.png' /></span><span class='pretty_link_content'>Monsieur Jean Courant "
                         "(Electrabel - Agent)</span></a>")
        # no sender
        imail = createContentInContainer(self.imf, 'dmsincomingmail', id='my-id', title='My title',
                                         description='Description')
        brain = self.portal.portal_catalog(UID=imail.UID())[0]
        self.assertEqual(column.renderCell(brain), '-')
        # sender not found: we delete it
        api.content.delete(obj=self.portal['contacts']['jeancourant']['agent-electrabel'], check_linkintegrity=False)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(column.renderCell(brain), '-')

    def test_TaskParentColumn(self):
        column = TaskParentColumn(self.portal, self.portal.REQUEST, self.task_table)
        brain = self.portal.portal_catalog(UID=self.ta1.UID())[0]
        self.assertEqual(column.renderCell(brain),
                         u"<a class='pretty_link state-created' title='' href='http://nohost/plone/incoming-mail/"
                         "courrier1' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
                         "src='http://nohost/plone/++resource++dmsincomingmail_icon.png' /></span><span class='"
                         "pretty_link_content'>E0001 - Courrier 1</span></a>")
        brain = self.portal.portal_catalog(UID=self.ta31.UID())[0]
        self.assertEqual(column.renderCell(brain),
                         u"<a class='pretty_link state-created' title='' href='http://nohost/plone/incoming-mail/"
                         "courrier1' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
                         "src='http://nohost/plone/++resource++dmsincomingmail_icon.png' /></span><span class='"
                         "pretty_link_content'>E0001 - Courrier 1</span></a>")

    def test_TaskActionsColumn(self):
        column = TaskActionsColumn(self.portal, self.portal.REQUEST, None)
        rendered = column.renderCell(self.ta1)
        self.assertIn('do_to_assign', rendered)
        self.assertIn('title="Edit"', rendered)
        self.assertIn('title="Delete"', rendered)
        self.assertIn('"overlay-history"', rendered)
        column.view_name = ''
        self.assertRaises(KeyError, column.renderCell, self.ta1)
