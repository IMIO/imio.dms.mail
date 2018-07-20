# -*- coding: utf-8 -*-

from plone import api
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


def robot_init(self):
    portal = api.portal.get()
    for msg in portal['messages-config'].objectValues():
        if api.content.get_state(obj=msg) == 'activated':
            api.content.transition(obj=msg, transition='deactivate')

    # Deactivate auto refresh on outgoingmail
    portal.portal_javascripts.updateScript('++resource++imio.dms.mail/outgoingmail.js', enabled=False)

    return self.REQUEST.response.redirect(self.absolute_url())
