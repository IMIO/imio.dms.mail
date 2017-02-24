# -*- coding: utf-8 -*-
"""Subscribers."""
from Acquisition import aq_get
from zc.relation.interfaces import ICatalog
from zExceptions import Redirect
from zope.component import getUtility, queryUtility
from zope.i18n import translate
from zope.interface import alsoProvides, noLongerProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from plone import api
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.registry.interfaces import IRecordModifiedEvent, IRegistry

from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY, FUNCTIONS_REGISTRY
from collective.contact.plonegroup.interfaces import INotPloneGroupContact, IPloneGroupContact
from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from imio.helpers.cache import invalidate_cachekey_volatile_for

from . import _


# DMSDOCUMENT

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
        omf = portal['outgoing-mail']
        dic = omf.__ac_local_roles__
        for principal in dic.keys():
            if principal.endswith('_encodeur'):
                del dic[principal]
        for uid in registry[ORGANIZATIONS_REGISTRY]:
            dic["%s_encodeur" % uid] = ['Contributor']
        omf._p_changed = True


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


def principal_deleted(event):
    """
        Raises exception if user is deleted
    """
    princ = event.principal
    portal = api.portal.get()
    request = portal.REQUEST
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
