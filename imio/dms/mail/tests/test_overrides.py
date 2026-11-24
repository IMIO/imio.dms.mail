# -*- coding: utf-8 -*-
"""Test overrides."""

from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object

import json
import unittest


class TestOverrides(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        change_user(self.portal)

    def test_hide_collabora_popups(self):
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        view = omf.restrictedTraverse("@@collabora-wopi")
        # file info: guest, with our user settings
        view.wopi_mode = "file_info"
        info = json.loads(view())
        self.assertEqual(info["BaseFileName"], omf.file.filename)
        self.assertEqual(info["UserExtraInfo"], {"is_guest": True})
        self.assertEqual(
            info["UserSettings"], {"uri": "{}/@@collabora-settings".format(self.portal.absolute_url()), "stamp": "1"}
        )
        # user settings uploads are dropped
        self.request["PATH_INFO"] = "{}/@@collabora-wopi/settings/upload".format(omf.absolute_url_path())
        self.assertEqual(view(), "")
