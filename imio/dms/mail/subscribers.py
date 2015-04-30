# -*- coding: utf-8 -*-
"""Subscribers."""
from zope.interface import alsoProvides, noLongerProvides

from Products.CMFCore.utils import getToolByName
from plone import api

from imio.dms.mail.interfaces import IInternalOrganization, IExternalOrganization


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


def mark_organization(organization, event):
    """Set a marker interface on organization."""
    try:
        contacts = api.portal.get().contacts
    except api.portal.CannotGetPortalError:
        """ This happens when you delete a site """
        return
    plonegroup_org = contacts['plonegroup-organization']
    if plonegroup_org in organization.get_organizations_chain():
        if not IInternalOrganization.providedBy(organization):
            alsoProvides(organization, IInternalOrganization)

        if IExternalOrganization.providedBy(organization):
            noLongerProvides(organization, IExternalOrganization)
    else:
        if not IExternalOrganization.providedBy(organization):
            alsoProvides(organization, IExternalOrganization)

        if IInternalOrganization.providedBy(organization):
            noLongerProvides(organization, IInternalOrganization)

    organization.reindexObject(idxs='object_provides')
