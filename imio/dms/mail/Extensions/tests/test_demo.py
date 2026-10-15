# -*- coding: utf-8 -*-
from imio.dms.mail.Extensions.demo import import_scanned
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING

import unittest


class TestDemo(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def mails(self, scan_id):
        """Incoming mails whose main file has this scan id"""
        brains = self.portal.portal_catalog.unrestrictedSearchResults(portal_type="dmsmainfile", scan_id=scan_id)
        return [brain._unrestrictedGetObject().aq_parent for brain in brains]

    def test_import_scanned(self):
        # first call: letters 1 and 2, left to encode like a real scan
        import_scanned(self.portal, redirect="")
        mail = self.mails("090555500030000")[0]
        self.assertFalse(mail.title)
        self.assertIsNone(mail.original_mail_date)
        self.assertFalse(mail.sender)
        self.assertEqual(len(self.mails("090555500030001")), 1)
        self.assertEqual(len(self.mails("090555500030002")), 0)
        # next call continues with letters 3 and 4
        import_scanned(self.portal, redirect="")
        self.assertEqual(len(self.mails("090555500030003")), 1)
        # letters 5 to 9, then 1 again
        import_scanned(self.portal, number=6, redirect="")
        self.assertEqual(len(self.mails("090555500030008")), 1)
        self.assertEqual(len(self.mails("090555500030000")), 2)
        self.assertEqual(len(self.mails("090555500030001")), 1)
        # only bypasses the rotation
        import_scanned(self.portal, number=1, only="demo-7.pdf", redirect="")
        self.assertEqual(len(self.mails("090555500030006")), 2)
