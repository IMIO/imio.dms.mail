# -*- coding: utf-8 -*-
"""Subscribers."""
from zope.interface import alsoProvides, noLongerProvides
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from Products.CMFCore.utils import getToolByName

from imio.dms.mail.interfaces import IInternalContact, IExternalContact


def replace_scanner(imail, event):
    """
        Replace the batch creator by the editor
    """
    if imail.owner_info().get('id') == 'scanner':
        pms = getToolByName(imail, 'portal_membership')
        user = pms.getAuthenticatedMember()
        userid = user.getId()
        # pass if the container is modified when creating a sub element
        if userid == 'scanner':
            return
        pcat = getToolByName(imail, 'portal_catalog')
        path = '/'.join(imail.getPhysicalPath())
        brains = pcat(path=path)
        for brain in brains:
            obj = brain.getObject()
            creators = list(obj.creators)
            # change creator metadata
            creators.remove('scanner')
            if userid not in creators:
                creators.insert(0, userid)
            obj.setCreators(creators)
            # change owner
            obj.changeOwnership(user)
            # change Owner role
            owners = obj.users_with_local_role('Owner')
            if 'scanner' in owners:
                obj.manage_delLocalRoles(['scanner'])
            if userid not in owners:
                roles = list(obj.get_local_roles_for_userid(userid))
                roles.append('Owner')
                obj.manage_setLocalRoles(userid, roles)
            obj.reindexObject()
        imail.reindexObjectSecurity()


def mark_organization(contact, event):
    """ Set a marker interface on contact content. """
    if IObjectRemovedEvent.providedBy(event):
        return
    if '/contacts/plonegroup-organization' in contact.absolute_url_path():
        if not IInternalContact.providedBy(contact):
            alsoProvides(contact, IInternalContact)
        if IExternalContact.providedBy(contact):
            noLongerProvides(contact, IExternalContact)
    else:
        if not IExternalContact.providedBy(contact):
            alsoProvides(contact, IExternalContact)
        if IInternalContact.providedBy(contact):
            noLongerProvides(contact, IInternalContact)

    contact.reindexObject(idxs='object_provides')
