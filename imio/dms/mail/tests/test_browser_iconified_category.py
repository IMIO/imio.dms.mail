# -*- coding: utf-8 -*-
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail.browser.iconified_category import ApprovedColumn
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.test_helpers import ImioTestHelpers
from plone.dexterity.utils import createContentInContainer

import unittest


class TestBrowserIconifiedCategory(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        self.omail = sub_create(
            self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om", title=u"Test",
            content_category=calculate_category_id(ct)
        )
        self.file1 = createContentInContainer(self.omail, "dmsommainfile", id="file1", scan_id="012999900000600")

    def test_approved_column(self):
        """Test column rendering"""
        brains = self.portal.portal_catalog(portal_type="dmsommainfile", id="file1")
        self.assertEqual(len(brains), 1)
        col = ApprovedColumn(self.portal, self.portal.REQUEST, None)
