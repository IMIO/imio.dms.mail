# -*- coding: utf-8 -*-
"""Subscribers."""
from zope.component import getUtility
from zope.interface import alsoProvides, noLongerProvides
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from plone import api
from Products.CMFCore.utils import getToolByName
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.registry.interfaces import IRecordModifiedEvent, IRegistry

from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY, FUNCTIONS_REGISTRY
from collective.contact.plonegroup.interfaces import INotPloneGroupContact, IPloneGroupContact
from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from imio.helpers.cache import invalidate_cachekey_volatile_for


from dmsmail import IImioDmsIncomingMail


def replace_scanner(mail, event):
    """
        Replace the batch creator by the editor
    """
    if mail.owner_info().get('id') == 'scanner':
        user = api.user.get_current()
        userid = user.getId()
        # pass if the container is modified when creating a sub element
        if userid == 'scanner':
            return
        pcat = getToolByName(mail, 'portal_catalog')
        path = '/'.join(mail.getPhysicalPath())
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
        mail.reindexObjectSecurity()


def dmsdocument_transition(mail, event):
    """
        update indexes after a transition
    """
    mail.reindexObject(['state_group'])


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
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName and
            event.record.interface != IContactPlonegroupConfig):
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


def mark_contact(contact, event):
    """ Set a marker interface on contact content. """
    if IObjectRemovedEvent.providedBy(event):
        # at site removal
        if event.object.portal_type == 'Plone Site':
            return
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')
        return
    if '/personnel-folder/' in contact.absolute_url_path() or '/plonegroup-organization' in contact.absolute_url_path():
        if not IPloneGroupContact.providedBy(contact):
            alsoProvides(contact, IPloneGroupContact)
        if INotPloneGroupContact.providedBy(contact):
            noLongerProvides(contact, INotPloneGroupContact)
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')
    else:
        if not INotPloneGroupContact.providedBy(contact):
            alsoProvides(contact, INotPloneGroupContact)
        if IPloneGroupContact.providedBy(contact):
            noLongerProvides(contact, IPloneGroupContact)

    contact.reindexObject(idxs='object_provides')


def contact_modified(obj, event):
    """
        Update the sortable_title index
    """
    # at site removal
#    if IObjectRemovedEvent.providedBy(event):
#        return
    if IPloneGroupContact.providedBy(obj):
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')


def contact_plonegroup_change(event):
    """
        Update outgoing-mail folder local roles for encodeur
    """
    if IRecordModifiedEvent.providedBy(event) and event.record.interface == IContactPlonegroupConfig:
        registry = getUtility(IRegistry)
        if not registry[FUNCTIONS_REGISTRY] or not registry[ORGANIZATIONS_REGISTRY]:
            return
        portal = api.portal.get()
        omf = portal['outgoing-mail']
        dic = omf.__ac_local_roles__
        for principal in dic.keys():
            if principal.endswith('_encodeur'):
                del dic[principal]
        for uid in registry[ORGANIZATIONS_REGISTRY]:
            dic["%s_encodeur" % uid] = ['Contributor']
        omf._p_changed = True
