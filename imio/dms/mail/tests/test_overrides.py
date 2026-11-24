# -*- coding: utf-8 -*-
"""Test overrides."""

from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from io import BytesIO
from plone import api
from zExceptions import Redirect
from zope.annotation.interfaces import IAnnotations

import json
import os
import unittest


COLLABORATIVE_EDIT = "imio.dms.mail.browser.settings.IImioDmsMailConfig.collabora_collaborative_edit"
COLLABORA_AUTOSAVE = "imio.dms.mail.browser.settings.IImioDmsMailConfig.collabora_autosave"


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
        IAnnotations(self.request).pop("plone.memoize", None)  # each WOPI call is a new request
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
        # a reader, given the mail through sharing, cannot lock it
        api.user.grant_roles(username="lecteur", obj=omf.aq_parent, roles=["Reader"])
        change_user(self.portal, "lecteur")
        self.assertTrue(api.user.has_permission("View", obj=omf))
        self.assertFalse(api.user.has_permission("Modify portal content", obj=omf))
        self.assertEqual(self.wopi(omf, "LOCK", "cool-lock0")[0], 403)
        self.assertFalse(omf.wl_isLocked())
        change_user(self.portal)
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
        # only the lock holder's session saves
        data = omf.file.data
        self.request.method = "POST"
        self.request.environ["HTTP_X_COOL_WOPI_ISMODIFIEDBYUSER"] = "true"
        self.request.environ["HTTP_X_COOL_WOPI_EXTENDEDDATA"] = "SaveAndClose=true"
        for lock_id, status in (("cool-lock2", 409), ("cool-lock1", 200)):
            self.request.response.setStatus(200)
            self.request.environ["HTTP_X_WOPI_LOCK"] = lock_id
            self.request._file = BytesIO(data + b"saved")
            view = omf.restrictedTraverse("@@collabora-wopi")
            view.wopi_mode = "contents"
            view()
            self.assertEqual(self.request.response.getStatus(), status)
        self.assertEqual(omf.file.data, data + b"saved")
        self.request.method = "GET"
        # Collabora unlocks at the end of the edition
        self.assertEqual(self.wopi(omf, "UNLOCK", "cool-lock2")[0], 409)
        self.assertEqual(self.wopi(omf, "UNLOCK", "cool-lock1"), (200, "", "cool-lock1"))
        self.assertFalse(omf.wl_isLocked())
        self.assertEqual(self.wopi(omf, "REFRESH_LOCK", "cool-lock1"), (409, "", ""))

    def test_save_on_request(self):
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        data = omf.file.data
        with open(os.path.join(PRODUCT_DIR, "Extensions", "Refection trottoir.odt"), "rb") as fh:
            edited = fh.read()
        view = omf.restrictedTraverse("@@collabora-wopi")
        view.wopi_mode = "file_info"
        self.assertTrue(json.loads(view())["HideSaveOption"])
        # Collabora saves by itself (when idle, while editing, when leaving): dropped
        self.request.method = "POST"
        self.request.environ["HTTP_X_COOL_WOPI_ISMODIFIEDBYUSER"] = "true"
        self.request._file = BytesIO(edited)
        view.wopi_mode = "contents"
        self.assertEqual(json.loads(view())["BaseFileName"], omf.file.filename)
        self.assertEqual(omf.file.data, data)
        # the save of "Save & Close" is kept, the preview completed before it is outdated
        omf.conversion_finished = "stale"
        self.request.environ["HTTP_X_COOL_WOPI_EXTENDEDDATA"] = "SaveAndClose=true"
        self.request._file = BytesIO(edited)
        view()
        self.assertEqual(omf.file.data, edited)
        self.assertNotEqual(getattr(omf, "conversion_finished", None), "stale")
        # Collabora autosave: every save is kept, with Collabora's own save button
        api.portal.set_registry_record(COLLABORA_AUTOSAVE, True)
        del self.request.environ["HTTP_X_COOL_WOPI_EXTENDEDDATA"]
        self.request._file = BytesIO(data)
        view()
        self.assertEqual(omf.file.data, data)
        view.wopi_mode = "file_info"
        self.assertNotIn("HideSaveOption", json.loads(view()))
