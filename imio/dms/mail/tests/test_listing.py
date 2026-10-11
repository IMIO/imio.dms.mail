# -*- coding: utf-8 -*-
"""Test im-listing view."""
from datetime import datetime
from datetime import timedelta
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object

import unittest


class TestListingView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.view = self.portal.unrestrictedTraverse("@@im-listing")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]

    def test_findIncomingMails(self):
        results = self.view.findIncomingMails()
        # mails are grouped by treating group, titled with the group full title
        dg = self.pgof["direction-generale"]
        self.assertEqual(results[dg.UID()]["title"], u"Direction générale")
        self.assertEqual(results[dg["secretariat"].UID()]["title"], u"Direction générale - Secrétariat")
        self.assertNotIn("1_no_group", results)
        # mails are sorted by internal reference number
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        im7 = get_object(oid="courrier7", ptype="dmsincomingmail")
        self.assertListEqual(results[dg.UID()]["mails"], [im1, im7])
        self.assertEqual(sum([len(dic["mails"]) for dic in results.values()]), 9)
        # mail type filter (a byte string in Plone 4)
        self.assertEqual(len(self.view.findIncomingMails(mail_type="courrier")), len(results))
        self.assertDictEqual(self.view.findIncomingMails(mail_type="unknown"), {})
        # start date filter
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        self.assertDictEqual(self.view.findIncomingMails(start_date=tomorrow), {})
        # mail without treating group
        sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id",
            **{"title": u"No group", "mail_type": u"courrier", "reception_date": datetime.now(),
               "internal_reference_no": u"E9999"}
        )
        results = self.view.findIncomingMails()
        self.assertEqual(results["1_no_group"]["title"], "listing_no_group")
        self.assertListEqual([m.id for m in results["1_no_group"]["mails"]], ["my-id"])

    def test_call(self):
        """Render the printable listing."""
        rendered = self.view()
        self.assertIn(u"Direction générale - Secrétariat", rendered)
        self.assertIn(u"<td>E0001 - Courrier 1</td>", rendered)
        self.assertIn(u"Electrabel", rendered)
        self.assertIn(u'src="http://nohost/plone/print_icon.png"', rendered)
        # nothing to list
        self.view.request.form["start_date"] = "29991231"
        self.view.request["start_date"] = "29991231"
        rendered = self.view()
        self.assertNotIn(u"Courrier 1", rendered)
