# -*- coding: utf-8 -*-
import unittest2 as unittest
from zope.component import getUtility
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.browser.table import VersionsTitleColumn, AssignedGroupColumn


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
                                 scan_id='IMIO123456789')
        # Cannot use scan_date because toLocalizedTime causes error in test
        brains = self.portal.portal_catalog(portal_type='dmsmainfile', id='testid1')
        self.assertEqual(len(brains), 1)
        col = VersionsTitleColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.getLinkTitle(brains[0]), u'title="scan_id: IMIO123456789\nscan_date: "')

    def test_AssignedGroupColumn(self):
        registry = getUtility(IRegistry)
        group0 = registry[ORGANIZATIONS_REGISTRY][0]
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        task = createContentInContainer(imail, 'task', id='testid1', assigned_group=group0)
        col = AssignedGroupColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.renderCell(task).encode('utf8'), "Département Jeunesse - Cité de l'Enfance")
