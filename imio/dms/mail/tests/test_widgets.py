# -*- coding: utf-8 -*-
"""Test expandable datagrid widgets."""
from collective.z3cform.datagridfield.interfaces import IDataGridFieldLayer
from collective.z3cform.datagridfield.row import DictRow
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.browser.widgets import ExpandableDataGridField
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldFactory
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldObject
from imio.dms.mail.browser.widgets import ExpandableDataGridFieldObjectFactory
from imio.dms.mail.content.behaviors import ISigningBehavior
from imio.dms.mail.content.behaviors import ISignRequestSigningBehavior
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from zope.interface import alsoProvides
from zope.schema import getFieldsInOrder

import unittest


class TestWithInheritedFields(unittest.TestCase):
    """collective.z3cform.datagridfield 4 converts only the fields defined on the row schema itself."""

    def test_row_schemas(self):
        rows = [
            fld.value_type.schema
            for name, fld in getFieldsInOrder(IImioDmsMailConfig)
            if isinstance(getattr(fld, "value_type", None), DictRow)
        ]
        rows += [
            ISigningBehavior["signers"].value_type.schema,
            ISignRequestSigningBehavior["signers"].value_type.schema,
        ]
        for schema in rows:
            self.assertListEqual(sorted(schema.names()), sorted(schema.names(all=True)), schema)
        # column order kept
        schema = IImioDmsMailConfig["request_signer_rules"].value_type.schema
        self.assertListEqual(
            [name for name, fld in getFieldsInOrder(schema)][:4], ["number", "signer", "esign", "approvings"]
        )


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
        """The settings form renders rules rows with an expand button (Bootstrap icons)."""
        alsoProvides(self.request, IDataGridFieldLayer)
        self.request["REQUEST_METHOD"] = "GET"
        rendered = self.portal.unrestrictedTraverse("@@imiodmsmail-settings")()
        self.assertIn('<table class="table table-striped datagridwidget-expandable"', rendered)
        self.assertIn('<button class="btn btn-outline-dark btn-sm expand-row-btn"', rendered)
        self.assertIn('title="Augmenter/réduire la hauteur de ligne"', rendered)
        self.assertIn("bi-arrows-angle-expand", rendered)
        self.assertIn("dgf--row-add", rendered)
