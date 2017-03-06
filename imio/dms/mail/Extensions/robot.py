# -*- coding: utf-8 -*-

from zope.component import getMultiAdapter


def lock(self, unlock=None):
    """
        lock context
    """
    view = getMultiAdapter((self, self.REQUEST), name='plone_lock_operations')
    if unlock:
        view.safe_unlock()
    else:
        view.create_lock()
    return self.REQUEST.response.redirect(self.absolute_url())
