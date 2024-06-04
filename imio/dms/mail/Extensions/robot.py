# -*- coding: utf-8 -*-
from imio.dms.mail import add_path
from plone import api
from Products.CMFPlone.utils import safe_unicode
from zope.component import getMultiAdapter


def delete_category(self, key, identifier="identifier"):
    portal = self
    element = portal["tree"].get_by(identifier, key)
    if element:
        element.__parent__._delete_element(element)
    return self.REQUEST.response.redirect(self.absolute_url())


def lock(self, unlock=None):
    """
    lock context
    """
    view = getMultiAdapter((self, self.REQUEST), name="plone_lock_operations")
    if unlock:
        view.safe_unlock()
    else:
        view.create_lock()
    return self.REQUEST.response.redirect(self.absolute_url())


def robot_init(self):
    portal = self
    for msg in portal["messages-config"].objectValues():
        if api.content.get_state(obj=msg) == "activated":
            api.content.transition(obj=msg, transition="deactivate")

    # Deactivate auto refresh on outgoingmail
    portal.portal_javascripts.updateScript("++resource++imio.dms.mail/outgoingmail.js", enabled=False)

    return self.REQUEST.response.redirect(self.absolute_url())
    # must always return a redirect in robot...


def video_doc_init(self, pdb=""):
    portal = self
    if pdb:
        import ipdb

        ipdb.set_trace()
    filename = "outlook-ruban.jpg"
    if filename in portal:
        return self.REQUEST.response.redirect(self.absolute_url())
    iprops = portal.portal_properties.imaging_properties
    orig_sizes = iprops.allowed_sizes
    new_sizes = [size for size in orig_sizes if not size.startswith("preview")]
    new_sizes.append("preview 768:768")
    iprops.manage_changeProperties(allowed_sizes=new_sizes)
    filepath = add_path("tests/robot/outlook-ruban-1.jpg")
    with open(filepath, "rb") as fo:
        portal.invokeFactory("Image", id=filename, title=safe_unicode(filename), file=fo.read(), excludeFromNav=True)
    return self.REQUEST.response.redirect(self.absolute_url())
    # must always return a redirect in robot...
