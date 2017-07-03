# -*- coding: utf-8 -*-
"""Subscribers."""
from Acquisition import aq_get
from DateTime import DateTime
from zc.relation.interfaces import ICatalog
from zExceptions import Redirect
from zope.component import getUtility, queryUtility, getAdapter
from zope.container.interfaces import IContainerModifiedEvent
from zope.i18n import translate
from zope.interface import alsoProvides, noLongerProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from plone import api
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.app.uuid.utils import uuidToObject
from plone.registry.interfaces import IRecordModifiedEvent, IRegistry

from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY, FUNCTIONS_REGISTRY
from collective.contact.plonegroup.interfaces import INotPloneGroupContact, IPloneGroupContact
from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig, getOwnOrganizationPath
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.task.interfaces import ITaskContainerMethods
from imio.helpers.cache import invalidate_cachekey_volatile_for

from . import _


# DMSDOCUMENT

def dmsdocument_modified(mail, event):
    """
        Replace the batch creator by the editor.
        Updates contained tasks.
    """
    # owner
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
    # tasks
    if not event.descriptions:
        return
    updates = []
    adapted = getAdapter(mail, ITaskContainerMethods)
    fields = adapted.get_parents_fields()
    for at in event.descriptions:
        for field in fields:
            for dic in fields[field]:
                fieldname = (dic['prefix'] and '%s.%s' % (dic['prefix'], dic['at'])
                             or dic['at'])
                if fieldname in at.attributes:
                    updates.append(field)
                    break
    for field in updates:
        adapted.set_lower_parents_value(field, fields[field])


def dmsdocument_transition(mail, event):
    """
        update indexes after a transition
    """
    mail.reindexObject(['state_group'])


def referenceDocumentRemoved(obj, event):
    """
        Check if there is a relation with another Document.
        Like collective.contact.core.subscribers.referenceRemoved.
        Where referenceObjectRemoved is also used
    """
    request = aq_get(obj, 'REQUEST', None)
    if not request:
        return
    storage = ILinkIntegrityInfo(request)

    catalog = queryUtility(ICatalog)
    intids = queryUtility(IIntIds)
    if catalog is None or intids is None:
        return

    obj_id = intids.queryId(obj)

    # find all relations that point to us
    for rel in catalog.findRelations({'to_id': obj_id, 'from_attribute': 'reply_to'}):
        storage.addBreach(rel.from_object, rel.to_object)
    # find relations we point
    for rel in catalog.findRelations({'from_id': obj_id, 'from_attribute': 'reply_to'}):
        storage.addBreach(rel.to_object, rel.from_object)


# VARIOUS

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
    mail = dmf.aq_parent
    if IDmsDocument.providedBy(mail):
        mail.reindexObject(idxs=['SearchableText'])


def dexterity_transition(obj, event):
    """
        Dexterity content transition
    """
    obj.setModificationDate(DateTime())


# CONFIGURATION

def contact_plonegroup_change(event):
    """
        Update outgoing-mail folder local roles for encodeur
    """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName and
            event.record.interface == IContactPlonegroupConfig):
        registry = getUtility(IRegistry)
        if not registry[FUNCTIONS_REGISTRY] or not registry[ORGANIZATIONS_REGISTRY]:
            return
        portal = api.portal.get()
        # contributor on a contact can edit too
        for folder in (portal['outgoing-mail'], portal['contacts']):
            dic = folder.__ac_local_roles__
            for principal in dic.keys():
                if principal.endswith('_encodeur'):
                    del dic[principal]
            for uid in registry[ORGANIZATIONS_REGISTRY]:
                dic["%s_encodeur" % uid] = ['Contributor']
            folder._p_changed = True
        # we add a directory by organization in templates/om
        base_folder = portal.templates.om
        for uid in registry[ORGANIZATIONS_REGISTRY]:
            if uid not in base_folder:
                obj = uuidToObject(uid)
                full_title = obj.get_full_title(separator=' - ', first_index=1)
                folder = api.content.create(container=base_folder, type='Folder', id=uid, title=full_title)
                roles = ['Reader']
                if registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.org_templates_encoder_can_edit']:
                    roles += ['Contributor', 'Editor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
                alsoProvides(folder, INextPrevNotNavigable)


def ploneGroupContactChanged(organization, event):
    """
        Manage an organization change
    """
    # zope.lifecycleevent.ObjectRemovedEvent : delete
    # zope.lifecycleevent.ObjectModifiedEvent : edit, rename
    # is the container who's modified at creation ?
    # bypass if we are removing the Plone Site
    if IContainerModifiedEvent.providedBy(event) or \
       event.object.portal_type == 'Plone Site':
        return
    # is the current organization a part of own organization
    organization_path = '/'.join(organization.getPhysicalPath())
    if not organization_path.startswith(getOwnOrganizationPath()):  # can be unfound too
        return
    portal = api.portal.getSite()
    pcat = portal.portal_catalog
    brains = pcat(portal_type='organization', path=organization_path)
    om_folder = portal['templates']['om']
    for brain in brains:
        obj = brain.getObject()
        full_title = obj.get_full_title(separator=' - ', first_index=1)
        folder = om_folder.get(brain.UID)
        if folder and folder.title != full_title:
            folder.title = full_title
            folder.reindexObject(idxs=['Title', 'SearchableText'])
            modified(folder)


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


def user_deleted(event):
    """
        Raises exception if user cannot be deleted
    """
    princ = event.principal
    portal = api.portal.get()
    request = portal.REQUEST

    # is protected user
    if princ in ('scanner'):
        api.portal.show_message(message=_("You cannot delete the user name '${user}'.", mapping={'user': princ}),
                                request=request, type='error')
        raise Redirect(request.get('ACTUAL_URL'))

    # check groups
    pg = portal.acl_users.source_groups._principal_groups
    groups = pg.get(princ, [])
    if groups:
        api.portal.show_message(message=_("You cannot delete the user name '${user}', used in following groups.",
                                          mapping={'user': princ}), request=request, type='error')
        titles = []
        for groupid in groups:
            grp = api.group.get(groupname=groupid)
            titles.append('"%s"' % (grp and safe_unicode(grp.getProperty('title')) or groupid))
        api.portal.show_message(message=_('<a href="${url}" target="_blank">Linked groups</a> : ${list}',
                                          mapping={'list': ', '.join(titles), 'url': '%s/@@usergroup-usermembership?'
                                                   'userid=%s' % (portal.absolute_url(), princ)}),
                                request=request, type='error')
        raise Redirect(request.get('ACTUAL_URL'))

    # search in assigned_user index
    for (idx, domain) in (('assigned_user', 'collective.eeafaceted.z3ctable'), ('Creator', 'plone')):
        brains = portal.portal_catalog({idx: princ})
        if brains:
            api.portal.show_message(message=_("You cannot delete the user name '${user}', used in '${idx}' index.",
                                              mapping={'user': princ, 'idx': translate(idx, domain=domain,
                                                                                       context=request)}),
                                    request=request, type='error')
            api.portal.show_message(message=_("Linked objects: ${list}", mapping={'list': ', '.join(['<a href="%s" '
                                    'target="_blank">%s</a>' % (b.getURL(), safe_unicode(b.Title)) for b in brains])}),
                                    request=request, type='error')
            raise Redirect(request.get('ACTUAL_URL'))


def group_deleted(event):
    """
        Raises exception if group cannot be deleted
    """
    group = event.principal
    portal = api.portal.get()
    request = portal.REQUEST

    # is protected group
    if group in ('dir_general', 'encodeurs', 'expedition', 'Administrators', 'Reviewers', 'Site Administrators'):
        api.portal.show_message(message=_("You cannot delete the group '${group}'.", mapping={'group': group}),
                                request=request, type='error')
        raise Redirect(request.get('ACTUAL_URL'))

    parts = group.split('_')
    if len(parts) == 1:
        return

    # search in indexes
    for (idx, domain) in (('assigned_group', 'collective.eeafaceted.z3ctable'),
                          ('treating_groups', 'collective.eeafaceted.z3ctable'),
                          ('recipient_groups', 'collective.eeafaceted.z3ctable')):
        brains = portal.portal_catalog({idx: parts[0]})
        if brains:
            api.portal.show_message(message=_("You cannot delete the group '${group}', used in '${idx}' index.",
                                              mapping={'group': group, 'idx': translate(idx, domain=domain,
                                                                                        context=request)}),
                                    request=request, type='error')
            api.portal.show_message(message=_("Linked objects: ${list}", mapping={'list': ', '.join(['<a href="%s" '
                                    'target="_blank">%s</a>' % (b.getURL(), safe_unicode(b.Title)) for b in brains])}),
                                    request=request, type='error')
            raise Redirect(request.get('ACTUAL_URL'))


# CONTACT

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


def conversion_finished(obj, event):
    # put a flag on the File to know that its conversion is finished
    obj.conversion_finished = True


def file_added(obj, event):
    obj.just_added = True
