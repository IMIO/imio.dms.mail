# -*- coding: utf-8 -*-

from imio.dms.mail import add_path
from plone import api
from Products.CMFPlone.utils import safe_unicode
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


def video_doc_init(self):
    portal = api.portal.get()
    filename = 'outlook-ruban.jpg'
    filepath = add_path('tests/robot/outlook-ruban-1.jpg')
    with open(filepath, 'rb') as fo:
        portal.invokeFactory('Image', id=filename, title=safe_unicode(filename), file=fo.read(), excludeFromNav=True)
