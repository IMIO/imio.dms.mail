# -*- coding: utf-8 -*-
from imio.dms.mail import logger
from z3c.form import interfaces
from z3c.form.widget import SequenceWidget


SequenceWidget.__old_dms__extract = SequenceWidget.extract


def extract(self, default=interfaces.NO_VALUE):
    """See z3c.form.interfaces.IWidget.
    Patched to handle unicode tokens from the request (Python 2 str/unicode
    mismatch with vocabulary term tokens), so that getTermByToken does not
    raise LookupError and return NO_VALUE when it should return the submitted
    value. Without this patch, multi-select/checkbox fields show old stored
    values instead of the user's submitted values when a form re-renders after
    a validation error."""
    if (self.name not in self.request and
            self.name + '-empty-marker' in self.request):
        return []
    value = self.request.get(self.name, default)
    if value != default:
        if not isinstance(value, (tuple, list)):
            value = (value,)
        for token in value:
            # do not encode to utf-8 for MasterSelectWidget
            # as it uses unicode values and encoding would break its validation
            if isinstance(token, unicode) and \
                    not self.__class__.__name__ == 'MasterSelectWidget':
                token = token.encode('utf-8')
            if token == self.noValueToken:
                continue
            try:
                self.terms.getTermByToken(token)
            except LookupError:
                return default
    return value


SequenceWidget.extract = extract
logger.info("Monkey patching z3c.form.widget.SequenceWidget (extract)")
