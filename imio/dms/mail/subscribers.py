# -*- coding: utf-8 -*-
"""Subscribers."""
from Acquisition import aq_get
from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_own_organization_path
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.task.interfaces import ITaskContainerMethods
from DateTime import DateTime
from imio.dms.mail import _
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IPersonnelContact
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone import api
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.app.uuid.utils import uuidToObject
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.interfaces import IRecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from z3c.relationfield.event import updateRelations
from z3c.relationfield.relation import RelationValue
from zc.relation.interfaces import ICatalog
from zExceptions import Redirect
from zope.component import getAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.container.interfaces import IContainerModifiedEvent
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

import logging


logger = logging.getLogger('imio.dms.mail: events')


def replace_contact_list(obj, fieldname):
    """
        Replace ContactList in contact field
    """
    value = getattr(obj, fieldname)
    if not value:
        return False
    newvalue = []
    objs = []
    changed = False
    for relation in value:
        if not relation.isBroken() and relation.to_object:
            to_obj = relation.to_object
            if to_obj.portal_type == 'contact_list':
                changed = True
                intids = getUtility(IIntIds)
                # contact_list.contacts is a ContactList field
                for rel in to_obj.contacts:
                    if not rel.isBroken() and rel.to_object and rel.to_object not in objs:
                        objs.append(rel.to_object)
                        newvalue.append(RelationValue(intids.getId(rel.to_object)))
            elif to_obj not in objs:
                objs.append(to_obj)
                newvalue.append(relation)
    if changed:
        setattr(obj, fieldname, newvalue)
        updateRelations(obj, None)
    return changed

# DMSDOCUMENT


def dmsdocument_added(mail, event):
    """
        Replace ContactList in contact field.
    """
    if mail.portal_type == 'dmsincomingmail':
        if replace_contact_list(mail, 'sender'):
            mail.reindexObject(['sender', ])
    elif mail.portal_type == 'dmsoutgoingmail':
        if replace_contact_list(mail, 'recipients'):
            mail.reindexObject(['recipients', ])


def dmsdocument_modified(mail, event):
    """
        Replace the batch creator by the editor.
        Replace ContactList in contact field.
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
            if 'scanner' in creators:
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

    # contact list
    if mail.portal_type == 'dmsincomingmail':
        replace_contact_list(mail, 'sender')
    elif mail.portal_type == 'dmsoutgoingmail':
        replace_contact_list(mail, 'recipients')

    if not event.descriptions:
        return
    mod_attr = [name for at in event.descriptions for name in at.attributes]

    # tasks: update parents_assigned_groups field on children tasks following treating_groups value
    updates = []
    adapted = getAdapter(mail, ITaskContainerMethods)
    fields = adapted.get_parents_fields()
    for field in fields:
        for dic in fields[field]:
            fieldname = (dic['prefix'] and '%s.%s' % (dic['prefix'], dic['at'])
                         or dic['at'])
            if fieldname in mod_attr:
                updates.append(field)
                break
    for field in updates:
        adapted.set_lower_parents_value(field, fields[field])


def im_edit_finished(mail, event):
    """
    """
    user = api.user.get_current()
    if not user.has_permission('View', mail):
        portal = api.portal.get()
        redirectToUrl = api.portal.get().absolute_url()
        col_path = '%s/incoming-mail/mail-searches/all_mails' % portal.absolute_url_path()
        brains = portal.portal_catalog(path={'query': col_path, 'depth': 0})
        if brains:
            redirectToUrl = '%s/incoming-mail/mail-searches#c1=%s' % (redirectToUrl, brains[0].UID)
        # add a specific portal_message before redirecting the user
        msg = _('redirected_after_edition',
                default="You have been redirected here because you do not have "
                        "access anymore to the element you just edited.")
        portal['plone_utils'].addPortalMessage(msg, 'warning')
        response = mail.REQUEST.response
        response.redirect(redirectToUrl)


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
        Update outgoing-mail folder local roles for encodeur.
        Adding directory by organization in templates/om and contacts/contact-lists-folder
    """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName and
            event.record.interface == IContactPlonegroupConfig):
        registry = getUtility(IRegistry)
        if not registry[FUNCTIONS_REGISTRY] or not registry[ORGANIZATIONS_REGISTRY]:
            return
        # invalidate vocabularies caches
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.CreatingGroupVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary')

        portal = api.portal.get()
        # contributor on a contact can edit too
        for folder in (portal['outgoing-mail'], portal['contacts'],
                       portal['contacts']['contact-lists-folder']['common']):
            dic = folder.__ac_local_roles__
            for principal in dic.keys():
                if principal.endswith('_encodeur'):
                    del dic[principal]
            for uid in registry[ORGANIZATIONS_REGISTRY]:
                dic["%s_encodeur" % uid] = ['Contributor']
            folder._p_changed = True
        # we add a directory by organization in templates/om
        base_folder = portal.templates.om
        base_model = base_folder.get('main', None)
        cl_folder = portal.contacts['contact-lists-folder']
        for uid in registry[ORGANIZATIONS_REGISTRY]:
            obj = uuidToObject(uid)
            full_title = obj.get_full_title(separator=' - ', first_index=1)
            if uid not in base_folder:
                folder = api.content.create(container=base_folder, type='Folder', id=uid, title=full_title)
                alsoProvides(folder, IActionsPanelFolder)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ['Reader']
                if registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.org_templates_encoder_can_edit']:
                    roles += ['Contributor', 'Editor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
                if base_model and base_model.has_been_modified():
                    logger.info("Copying %s in %s" % (base_model, '/'.join(folder.getPhysicalPath())))
                    api.content.copy(source=base_model, target=folder)
            if uid not in cl_folder:
                folder = api.content.create(container=cl_folder, type='Folder', id=uid, title=full_title)
                folder.setLayout('folder_tabular_view')
                alsoProvides(folder, IActionsPanelFolderAll)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ['Reader', 'Contributor', 'Editor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
        # we manage local roles to give needed permissions related to group_encoder
        group_encoder_config = [dic for dic in registry[FUNCTIONS_REGISTRY] if dic['fct_id'] == CREATING_GROUP_SUFFIX]
        if group_encoder_config:
            orgs = group_encoder_config[0]['fct_orgs']
            for folder in (portal['incoming-mail'], portal['contacts'],
                           portal['contacts']['contact-lists-folder']['common']):
                dic = folder.__ac_local_roles__
                for principal in dic.keys():
                    if principal.endswith(CREATING_GROUP_SUFFIX):
                        del dic[principal]
                for uid in orgs:
                    dic["{}_{}".format(uid, CREATING_GROUP_SUFFIX)] = ['Contributor']
                folder._p_changed = True


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
    # invalidate vocabularies caches
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.CreatingGroupVocabulary')
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary')
    # is the current organization a part of own organization
    organization_path = '/'.join(organization.getPhysicalPath())
    if not organization_path.startswith(get_own_organization_path('unfound')):
        return
    portal = api.portal.getSite()
    pcat = portal.portal_catalog
    brains = pcat(portal_type='organization', path=organization_path)
    for brain in brains:
        obj = brain.getObject()
        full_title = obj.get_full_title(separator=' - ', first_index=1)
        for base_folder in (portal['templates']['om'], portal.contacts['contact-lists-folder']):
            folder = base_folder.get(brain.UID)
            if folder and folder.title != full_title:
                folder.title = full_title
                folder.reindexObject(idxs=['Title', 'SearchableText', 'sortable_title'])
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
    for (idx, domain, criterias) in (('assigned_user', 'collective.eeafaceted.z3ctable', {}),
                                     ('Creator', 'plone', {}),
                                     ('mail_type', 'collective.eeafaceted.z3ctable',
                                      {'object_provides': IPersonnelContact.__identifier__})):
        criterias.update({idx: princ})
        brains = portal.portal_catalog(**criterias)
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
    group_suffix = '_'.join(parts[1:])

    # invalidate vocabularies caches
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.CreatingGroupVocabulary')
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary')

    def get_query(portal_type, field, idx, org, suffix):
        fti = getUtility(IDexterityFTI, name=portal_type)
        config = fti.localroles.get(field)
        if not config:
            return {}
        for st in config:
            if suffix in config[st]:
                return {idx: org}
        return {}

    # search in indexes following suffix use in type localroles
    for (idx, field, pts, domain) in (
            ('assigned_group', 'assigned_group', ['task'], 'collective.eeafaceted.z3ctable'),
            ('treating_groups', 'treating_groups', ['dmsincomingmail', 'dmsoutgoingmail'],
             'collective.eeafaceted.z3ctable'),
            ('recipient_groups', 'recipient_groups', ['dmsincomingmail', 'dmsoutgoingmail'],
             'collective.eeafaceted.z3ctable'),
            ('assigned_group', 'creating_group', ['dmsincomingmail', 'dmsoutgoingmail'],
             'collective.eeafaceted.z3ctable')):
        for pt in pts:
            query = get_query(pt, field, idx, parts[0], group_suffix)
            if not query:
                continue
            query.update({'portal_type': pt})
            brains = portal.portal_catalog(**query)
            if brains:
                api.portal.show_message(message=_("You cannot delete the group '${group}', used in '${idx}' index.",
                                                  mapping={'group': group, 'idx': translate(idx, domain=domain,
                                                                                            context=request)}),
                                        request=request, type='error')
                api.portal.show_message(message=_("Linked objects: ${list}", mapping={'list': ', '.join(['<a href="%s" '
                                        'target="_blank">%s</a>' % (b.getURL(), safe_unicode(b.Title))
                                        for b in brains])}),
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
    if '/plonegroup-organization' in contact.absolute_url_path():
        if not IPloneGroupContact.providedBy(contact):
            alsoProvides(contact, IPloneGroupContact)
        if INotPloneGroupContact.providedBy(contact):
            noLongerProvides(contact, INotPloneGroupContact)
        # don't check for IPersonnelContact because we can only add organization in this folder
    elif '/personnel-folder/' in contact.absolute_url_path():
        if not IPersonnelContact.providedBy(contact):
            alsoProvides(contact, IPersonnelContact)
        if INotPloneGroupContact.providedBy(contact):
            noLongerProvides(contact, INotPloneGroupContact)
        # don't check for IPloneGroupContact because we can't add organization in this folder
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')
    else:
        if not INotPloneGroupContact.providedBy(contact):
            alsoProvides(contact, INotPloneGroupContact)
        if IPloneGroupContact.providedBy(contact):
            noLongerProvides(contact, IPloneGroupContact)
        if IPersonnelContact.providedBy(contact):
            noLongerProvides(contact, IPersonnelContact)
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')

    contact.reindexObject(idxs='object_provides')


def contact_modified(obj, event):
    """
        Update the sortable_title index
    """
    # at site removal
#    if IObjectRemovedEvent.providedBy(event):
#        return
    if IPersonnelContact.providedBy(obj):
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMSenderVocabulary')


def personnel_contact_removed(del_obj, event):
    """
        Check if a personnel held_position is used as sender.
    """
    # only interested by held_position user
    if del_obj.portal_type == 'person':
        return
    try:
        portal = api.portal.get()
        pp = portal.portal_properties
        catalog = portal.portal_catalog
    except api.portal.CannotGetPortalError:
        # When deleting site, the portal is no more found...
        return
    if pp.site_properties.enable_link_integrity_checks:
        storage = ILinkIntegrityInfo(aq_get(del_obj, 'REQUEST', None))
        for brain in catalog.unrestrictedSearchResults(portal_type=['dmsoutgoingmail'], sender=[del_obj.UID()]):
            storage.addBreach(brain._unrestrictedGetObject(), del_obj)


def conversion_finished(obj, event):
    # put a flag on the File to know that its conversion is finished
    obj.conversion_finished = True


def file_added(obj, event):
    obj.just_added = True


def member_area_added(obj, event):
    obj.setConstrainTypesMode(1)
    obj.setLocallyAllowedTypes([])
    obj.setImmediatelyAddableTypes([])
    if 'contact-lists' not in obj:
        folder = api.content.create(container=obj, type='Folder', id='contact-lists',
                                    title=translate('Contact lists', domain='imio.dms.mail', context=obj.REQUEST))
        folder.setConstrainTypesMode(1)
        folder.setLocallyAllowedTypes(['contact_list'])
        folder.setImmediatelyAddableTypes(['contact_list'])
        folder.manage_setLocalRoles(obj.getId(), ['Reader', 'Contributor', 'Editor'])
