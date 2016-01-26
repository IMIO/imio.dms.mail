# -*- coding: utf-8 -*-
"""Subscribers."""
from Products.CMFCore.utils import getToolByName
from imio.dms.mail.dmsmail import IImioDmsIncomingMail


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


def new_incomingmail(imail, event):
    """
        Block local roles
    """
    imail.__ac_local_roles_block__ = True
    imail.reindexObjectSecurity()


def dmsmainfile_modified(dmf, event):
    """
        Update the SearchableText mail index
    """
    imail = dmf.aq_parent
    if IImioDmsIncomingMail.providedBy(imail):
        imail.reindexObject(idxs=['SearchableText'])
