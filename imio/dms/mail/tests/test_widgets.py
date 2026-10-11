# -*- coding: utf-8 -*-
"""Test expandable datagrid widgets."""
from collective.z3cform.datagridfield.interfaces import IDataGridFieldLayer
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.browser.widgets import ExpandableDataGridField
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldFactory
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldObject
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldObjectFactory
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from zope.interface import alsoProvides

import unittest


class TestExpandableDataGridFieldObject(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_isExpandEnabled(self):
        widget = ExpandableDataGridFieldObjectFactory(
            IImioDmsMailConfig["omail_signer_rules"].value_type, self.layer["request"]
        )
        self.assertIsInstance(widget, ExpandableDataGridFieldObject)
        self.assertTrue(widget.isExpandEnabled())


class TestExpandableDataGridField(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        change_user(self.portal)

    def test_createObjectWidget(self):
        widget = ExpandableDataGridFieldFactory(IImioDmsMailConfig["omail_signer_rules"], self.request)
        self.assertIsInstance(widget, ExpandableDataGridField)
        row = widget.createObjectWidget(0)
        self.assertIsInstance(row, ExpandableDataGridFieldObject)
        self.assertTrue(row.setErrors)
        self.assertFalse(widget.createObjectWidget("TT").setErrors)
        self.assertFalse(widget.createObjectWidget("AA").setErrors)

    def test_render(self):
        """The settings form renders rules rows with an expand button (Font Awesome icon)."""
        alsoProvides(self.request, IDataGridFieldLayer)
        self.request["REQUEST_METHOD"] = "GET"
        rendered = self.portal.unrestrictedTraverse("@@imiodmsmail-settings")()
        self.assertIn(u'<a href="" class="expand-row-btn" title="Expand/Collapse row">', rendered)
        self.assertIn(u'<i class="fa fa-expand"></i>', rendered)
        self.assertIn(u'onclick="dataGridField2Functions.addRowAfter(this); return false"', rendered)
