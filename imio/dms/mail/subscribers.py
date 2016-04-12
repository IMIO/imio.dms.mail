# -*- coding: utf-8 -*-
"""Subscribers."""
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from plone import api
from Products.CMFCore.utils import getToolByName
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.registry.interfaces import IRecordModifiedEvent

from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from imio.helpers.cache import invalidate_cachekey_volatile_for
from dmsmail import IImioDmsIncomingMail


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


def incomingmail_transition(imail, event):
    """
        update indexes after a transition
    """
    imail.reindexObject(['state_group'])


def task_transition(task, event):
    """
        update indexes after a transition
    """
    task.reindexObject(['state_group'])


def dmsmainfile_modified(dmf, event):
    """
        Update the SearchableText mail index
    """
    reindex = False
    if event.descriptions:
        for desc in event.descriptions:
            if desc.interface == IScanFields and 'IScanFields.scan_id' in desc.attributes:
                reindex = True
                break
    if not reindex:
        return
    imail = dmf.aq_parent
    if IImioDmsIncomingMail.providedBy(imail):
        imail.reindexObject(idxs=['SearchableText'])


def user_related_modification(event):
    """
        Manage user modification
          * ignored Products.PluggableAuthService.interfaces.events.IPrincipalCreatedEvent
          * ignored Products.PluggableAuthService.interfaces.events.IPrincipalDeletedEvent
    """
    # we pass if the config change is not related to users
    if IConfigurationChangedEvent.providedBy(event) and not isinstance(event.context, UserDataConfiglet):
        return
    # we pass if the registry change is not related to plonegroup
    if IRecordModifiedEvent.providedBy(event) and event.record.interface != IContactPlonegroupConfig:
        return
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.AssignedUsersVocabulary')


def organization_modified(obj, event):
    """
        Update the sortable_title index
    """
    # at site removal
    if IObjectRemovedEvent.providedBy(event):
        return
    # zope.container.contained.ContainerModifiedEvent: descriptions is () when it's called after children creation
    if hasattr(event, 'descriptions') and not event.descriptions:
        return
    # zope.lifecycleevent.ObjectAddedEvent: oldParent is None when creation
    if hasattr(event, 'oldParent') and not event.oldParent:
        return
    pc = api.portal.get_tool('portal_catalog')
    for brain in pc(portal_type='organization', path='/'.join(obj.getPhysicalPath()), sort_on='path')[1:]:
        brain.getObject().reindexObject(idxs=['sortable_title'])
