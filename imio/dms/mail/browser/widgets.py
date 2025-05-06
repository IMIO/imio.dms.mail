from z3c.form import interfaces
from z3c.form.browser.textarea import TextAreaWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer

import zope.interface
import zope.schema.interfaces


class IDataTransferTextAreaWidget(interfaces.ITextAreaWidget):
    """Interface for the data transfer text widget."""


@implementer(IDataTransferTextAreaWidget)
class DataTransferTextAreaWidget(TextAreaWidget):
    pass


@implementer(IFieldWidget)
def DataTransferTextAreaFieldWidget(field, request):
    """Factory for creating HeaderFileWidget which is bound to one field"""
    return FieldWidget(field, DataTransferTextAreaWidget(request))
