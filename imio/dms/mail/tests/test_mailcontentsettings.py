# -*- coding: utf-8 -*-
"""Test dmsmailcontent-settings override."""
from imio.dms.mail.browser.mailcontentsettings import DMSMAILCONFIG_PREFIX
from imio.dms.mail.browser.mailcontentsettings import SettingsEditForm
from imio.dms.mail.browser.mailcontentsettings import SettingsView
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from zope.interface import alsoProvides

import unittest


class TestSettingsEditForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)

    def test_schema_prefix(self):
        """Signing request fields are stored with the mailcontent records."""
        self.assertEqual(SettingsEditForm.schema_prefix, DMSMAILCONFIG_PREFIX)
        self.request["REQUEST_METHOD"] = "GET"
        api.portal.set_registry_record("{}.signrequest_number".format(DMSMAILCONFIG_PREFIX), 7)
        form = SettingsEditForm(self.portal, self.request)
        form.update()
        widgets = {}
        for group in form.groups:
            widgets.update(dict(group.widgets.items()))
        self.assertEqual(widgets["signrequest_number"].value, u"7")
        self.assertEqual(widgets["signrequest_talexpression"].value, u"python:'D%04d'%int(number)")
        self.assertIn("incomingmail_number", widgets)


class TestSettingsView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)

    def test_call(self):
        alsoProvides(self.request, IImioDmsMailLayer)
        self.request["REQUEST_METHOD"] = "GET"
        view = self.portal.unrestrictedTraverse("@@dmsmailcontent-settings")
        self.assertIsInstance(view, SettingsView)
        rendered = view()
        self.assertIn(u'id="form-widgets-signrequest_number"', rendered)
        self.assertIn(u'id="form-widgets-incomingmail_number"', rendered)
        # inherited method used to compute internal references
        self.assertEqual(
            view.evaluateTalExpression(u"python:'D%04d'%int(number)", self.portal, self.request, self.portal, 3),
            "D0003",
        )
