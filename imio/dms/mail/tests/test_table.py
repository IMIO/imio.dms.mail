# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from datetime import datetime
from imio.dms.mail.browser.table import AssignedGroupColumn
from imio.dms.mail.browser.table import IMVersionsTitleColumn
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from plone.dexterity.utils import createContentInContainer

import unittest


class TestTable(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_VersionsTitleColumn(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        createContentInContainer(imail, "dmsmainfile", id="testid1", title="title", scan_id="123456789")
        # Cannot use scan_date because toLocalizedTime causes error in test
        brains = self.portal.portal_catalog(portal_type="dmsmainfile", id="testid1")
        self.assertEqual(len(brains), 1)
        col = IMVersionsTitleColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.getLinkTitle(brains[0]), u'title="scan_id: 123456789\nscan_date: \nVersion: "')

    def test_AssignedGroupColumn(self):
        group0 = get_registry_organizations()[0]
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        task = createContentInContainer(imail, "task", id="testid1", assigned_group=group0)
        col = AssignedGroupColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.renderCell(task).encode("utf8"), "Direction générale")
