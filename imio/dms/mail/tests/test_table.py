# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail.browser.table import AssignedGroupColumn
from imio.dms.mail.browser.table import IMVersionsTitleColumn
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer

import unittest


class TestTable(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_VersionsTitleColumn(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        createContentInContainer(imail, 'dmsmainfile', id='testid1', title='title',
                                 scan_id='123456789')
        # Cannot use scan_date because toLocalizedTime causes error in test
        brains = self.portal.portal_catalog(portal_type='dmsmainfile', id='testid1')
        self.assertEqual(len(brains), 1)
        col = IMVersionsTitleColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.getLinkTitle(brains[0]), u'title="scan_id: 123456789\nscan_date: \nVersion: "')

    def test_AssignedGroupColumn(self):
        group0 = get_registry_organizations()[0]
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        task = createContentInContainer(imail, 'task', id='testid1', assigned_group=group0)
        col = AssignedGroupColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.renderCell(task).encode('utf8'), "Direction générale")
