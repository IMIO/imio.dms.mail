# -*- coding: utf-8 -*-
"""Test overrides."""

from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone import api
from zExceptions import Redirect

import json
import unittest


COLLABORATIVE_EDIT = "imio.dms.mail.browser.settings.IImioDmsMailConfig.collabora_collaborative_edit"


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

    def wopi(self, obj, operation="", lock_id=""):
        """Call the WOPI file endpoint like Collabora. Return the status, the body and the X-WOPI-Lock header."""
        response = self.request.response
        response.setStatus(200)
        self.request.environ["HTTP_X_WOPI_OVERRIDE"] = operation
        self.request.environ["HTTP_X_WOPI_LOCK"] = lock_id
        view = obj.restrictedTraverse("@@collabora-wopi")
        view.wopi_mode = "file_info"
        body = view()
        return response.getStatus(), body, response.getHeader("X-WOPI-Lock")

    def test_lock_collabora_edition(self):
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        # siteadmin opens the file in Collabora, which locks it
        info = json.loads(self.wopi(omf)[1])
        self.assertTrue(info["SupportsLocks"])
        self.assertTrue(info["UserCanWrite"])
        self.assertEqual(self.wopi(omf, "LOCK", "cool-lock1"), (200, "", ""))
        self.assertTrue(omf.wl_isLocked())
        self.assertTrue(json.loads(self.wopi(omf)[1])["UserCanWrite"])
        self.assertEqual(self.wopi(omf, "GET_LOCK")[2], "cool-lock1")
        self.assertEqual(self.wopi(omf, "REFRESH_LOCK", "cool-lock1"), (200, "", "cool-lock1"))
        # the service head opens it read-only, and can neither lock it nor edit its metadata
        change_user(self.portal, "chef")
        self.assertTrue(api.user.has_permission("Modify portal content", obj=omf))
        self.assertFalse(json.loads(self.wopi(omf)[1])["UserCanWrite"])
        self.assertEqual(self.wopi(omf, "LOCK", "cool-lock2"), (409, "", "cool-lock1"))
        self.assertRaises(Redirect, omf.restrictedTraverse("@@edit"))
        # collaborative editing: they join the edition, still not the metadata
        api.portal.set_registry_record(COLLABORATIVE_EDIT, True)
        self.assertTrue(json.loads(self.wopi(omf)[1])["UserCanWrite"])
        self.assertRaises(Redirect, omf.restrictedTraverse("@@edit"))
        # Collabora unlocks at the end of the edition
        self.assertEqual(self.wopi(omf, "UNLOCK", "cool-lock2")[0], 409)
        self.assertEqual(self.wopi(omf, "UNLOCK", "cool-lock1"), (200, "", "cool-lock1"))
        self.assertFalse(omf.wl_isLocked())
        self.assertEqual(self.wopi(omf, "REFRESH_LOCK", "cool-lock1"), (409, "", ""))
