# -*- coding: utf-8 -*-
from imio.dms.mail import add_path
from plone import api
from plone.namedfile.file import NamedBlobImage
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
    api.portal.set_registry_record("plone.bundles/imio-dms-mail-outgoingmail.enabled", False)

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
    orig_sizes = api.portal.get_registry_record("plone.allowed_sizes")
    new_sizes = [size for size in orig_sizes if not size.startswith("preview")]
    new_sizes.append(u"preview 768:768")
    api.portal.set_registry_record("plone.allowed_sizes", new_sizes)
    filepath = add_path("tests/robot/outlook-ruban-1.jpg")
    with open(filepath, "rb") as fo:
        api.content.create(
            container=portal,
            type="Image",
            id=filename,
            title=safe_unicode(filename),
            image=NamedBlobImage(fo.read(), filename=safe_unicode(filename)),
            exclude_from_nav=True,
        )
    return self.REQUEST.response.redirect(self.absolute_url())
    # must always return a redirect in robot...
