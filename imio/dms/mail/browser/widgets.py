# -*- coding: utf-8 -*-
from collective.z3cform.datagridfield.datagridfield import DataGridField
from collective.z3cform.datagridfield.datagridfield import DataGridFieldObject
from z3c.form import interfaces
from z3c.form.widget import FieldWidget
from zope.component import adapter
from zope.interface import implementer
from zope.schema.interfaces import IField
from z3c.form.interfaces import IFormLayer
from zope.schema.interfaces import IObject


class ExpandableDataGridFieldObject(DataGridFieldObject):
    """DataGridFieldObject row widget that adds an expand/collapse button."""

    def isExpandEnabled(self):
        return True


@adapter(IField, IFormLayer)
@implementer(interfaces.IFieldWidget)
def ExpandableDataGridFieldObjectFactory(field, request):
    """IFieldWidget factory for ExpandableDataGridFieldObject."""
    return FieldWidget(field, ExpandableDataGridFieldObject(request))


class ExpandableDataGridField(DataGridField):
    """DataGridField subclass whose rows include an expand/collapse toggle button."""

    def createObjectWidget(self, idx):
        valueType = self.field.value_type
        if IObject.providedBy(valueType):
            widget = ExpandableDataGridFieldObjectFactory(valueType, self.request)
            widget.setErrors = idx not in ['TT', 'AA']
        else:
            from zope.component import getMultiAdapter
            widget = getMultiAdapter(
                (valueType, self.request),
                interfaces.IFieldWidget,
            )
        return widget


@adapter(IField, IFormLayer)
@implementer(interfaces.IFieldWidget)
def ExpandableDataGridFieldFactory(field, request):
    """IFieldWidget factory for ExpandableDataGridField."""
    return FieldWidget(field, ExpandableDataGridField(request))
