# -*- coding: utf-8 -*-

from zope.component import getMultiAdapter
from plone import api


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


def deactivate_message(self):
    portal = api.portal.get()
    for msg in portal['messages-config'].objectValues():
        if api.content.get_state(obj=msg) == 'activated':
            api.content.transition(obj=msg, transition='deactivate')
    return self.REQUEST.response.redirect(self.absolute_url())
