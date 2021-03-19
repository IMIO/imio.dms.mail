# -*- coding: utf-8 -*-
"""Subscribers."""
from Acquisition import aq_get  # noqa
from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_own_organization_path
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.task.interfaces import ITaskContainerMethods
from collective.wfadaptations.api import get_applied_adaptations
from DateTime import DateTime
from ftw.labels.interfaces import ILabeling
from imio.dms.mail import _
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import separate_fullname
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.pm.wsclient.browser.settings import notify_configuration_changed
from persistent.list import PersistentList
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
# from zope.component.interfaces import ComponentLookupError
from zope.annotation import IAnnotations
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

import datetime
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
    if mail.portal_type in ('dmsincomingmail', 'dmsincoming_email'):
        if replace_contact_list(mail, 'sender'):
            mail.reindexObject(['sender', ])
    elif mail.portal_type in ('dmsoutgoingmail', 'dmsoutgoing_email'):
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
    if mail.portal_type in ('dmsincomingmail', 'dmsincoming_email'):
        replace_contact_list(mail, 'sender')
    elif mail.portal_type in ('dmsoutgoingmail', 'dmsoutgoing_email'):
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
        redirect_to_url = api.portal.get().absolute_url()
        col_path = '%s/incoming-mail/mail-searches/all_mails' % portal.absolute_url_path()
        brains = portal.portal_catalog(path={'query': col_path, 'depth': 0})
        if brains:
            redirect_to_url = '%s/incoming-mail/mail-searches#c1=%s' % (redirect_to_url, brains[0].UID)
        # add a specific portal_message before redirecting the user
        msg = _('redirected_after_edition',
                default="You have been redirected here because you do not have "
                        "access anymore to the element you just edited.")
        portal['plone_utils'].addPortalMessage(msg, 'warning')
        response = mail.REQUEST.response
        response.redirect(redirect_to_url)


def dmsdocument_transition(mail, event):
    """
        update indexes after a transition
    """
    mail.reindexObject(['state_group'])


def dmsincomingmail_transition(mail, event):
    """When closing an incoming mail, add the assigned_user if necessary."""
    if event.transition and event.transition.id == 'close' and mail.assigned_user is None:
        username = event.status['actor']
        view = IdmUtilsMethods(mail, mail.REQUEST)
        if view.is_in_user_groups(suffixes=IM_EDITOR_SERVICE_FUNCTIONS, org_uid=mail.treating_groups,
                                  user=api.user.get(username)):
            mail.assigned_user = username
            mail.reindexObject(['assigned_user'])


def reference_document_removed(obj, event):
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

    if event.transition:
        if event.transition.id == 'do_to_assign':
            task.auto_to_do_flag = False
            # Set auto_to_do_flag on task if :
            # assigned_user is set OR
            # level n_plus_1 is not there OR
            # users in level n_plus_1
            if task.assigned_user:
                task.auto_to_do_flag = True
            elif not [dic for dic in get_applied_adaptations()
                      if dic['adaptation'] == 'imio.dms.mail.wfadaptations.TaskServiceValidation']:
                task.auto_to_do_flag = True
            else:
                transitions_levels = get_dms_config(['transitions_levels', 'task'])
                if task.assigned_group and transitions_levels['created'][task.assigned_group][0] != 'do_to_assign':
                    task.auto_to_do_flag = True
        elif event.transition.id == 'back_in_to_assign':
            # Remove auto_to_do_flag on task.
            task.auto_to_do_flag = False


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


def imiodmsfile_added(obj, event):
    """when an om file is added
    """
    # we check if the file is added manually or generated
    if obj.scan_id and obj.id == obj.scan_id:  # generated
        obj.generated = 1


def dexterity_transition(obj, event):
    """
        Dexterity content transition
    """
    obj.setModificationDate(DateTime())


# CONFIGURATION

def contact_plonegroup_change(event):
    """Event handler when contact.plonegroup records are modified.

    * update workflow dms config (new groups).
    * invalidate vocabulary caches.
    * set localroles on contacts for _encodeur groups.
    * add a directory by organization in templates/om, templates/oem and contacts/contact-lists-folder.
    * set local roles on contacts, incoming-mail for group_encoder.
    """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName and
            event.record.interface == IContactPlonegroupConfig):
        registry = getUtility(IRegistry)
        s_orgs = get_registry_organizations()
        s_fcts = get_registry_functions()
        if not s_fcts or not s_orgs:
            return
        # we update dms config
        update_transitions_auc_config('dmsincomingmail')  # i_e ok
        update_transitions_levels_config(['dmsincomingmail', 'dmsoutgoingmail', 'task'])  # i_e ok
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
            for uid in s_orgs:
                dic["%s_encodeur" % uid] = ['Contributor']
            folder._p_changed = True
        # we add a directory by organization in templates/om
        om_folder = portal.templates.om
        oem_folder = portal.templates.oem
        base_model = om_folder.get('main', None)
        cl_folder = portal.contacts['contact-lists-folder']
        for uid in s_orgs:
            obj = uuidToObject(uid)
            full_title = obj.get_full_title(separator=' - ', first_index=1)
            if uid not in om_folder:
                folder = api.content.create(container=om_folder, type='Folder', id=uid, title=full_title)
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
            if uid not in oem_folder:
                folder = api.content.create(container=oem_folder, type='Folder', id=uid, title=full_title)
                alsoProvides(folder, IActionsPanelFolder)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ['Reader']
                if registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.org_email_templates_encoder_can_edit']:
                    roles += ['Contributor', 'Editor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
                # if base_model and base_model.has_been_modified():
                #    logger.info("Copying %s in %s" % (base_model, '/'.join(folder.getPhysicalPath())))
                #    api.content.copy(source=base_model, target=folder)
            if uid not in cl_folder:
                folder = api.content.create(container=cl_folder, type='Folder', id=uid, title=full_title)
                folder.setLayout('folder_tabular_view')
                alsoProvides(folder, IActionsPanelFolderAll)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ['Reader', 'Contributor', 'Editor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
        # we manage local roles to give needed permissions related to group_encoder
        options_config = {portal['incoming-mail']: ['imail_group_encoder'],
                          portal['outgoing-mail']: ['omail_group_encoder'],
                          portal['contacts']: ['imail_group_encoder', 'omail_group_encoder', 'contact_group_encoder'],
                          portal['contacts']['contact-lists-folder']['common']: ['imail_group_encoder',
                                                                                 'omail_group_encoder',
                                                                                 'contact_group_encoder']}
        ge_config = {opt: api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(
            opt), default=False) for opt in ('imail_group_encoder', 'omail_group_encoder', 'contact_group_encoder')}

        group_encoder_config = [dic for dic in s_fcts if dic['fct_id'] == CREATING_GROUP_SUFFIX]  # noqa F812
        if group_encoder_config:
            orgs = group_encoder_config[0]['fct_orgs']
            for folder in options_config:
                if any([ge_config[opt] for opt in options_config[folder]]):
                    dic = folder.__ac_local_roles__
                    for principal in dic.keys():
                        if principal.endswith(CREATING_GROUP_SUFFIX):
                            del dic[principal]
                    for uid in orgs:
                        dic["{}_{}".format(uid, CREATING_GROUP_SUFFIX)] = ['Contributor']
                    folder._p_changed = True


def plonegroup_contact_changed(organization, event):
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
    if princ in ('scanner',):
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

    def get_query(portal_type, field_p, idx_p, org, suffix):
        fti = getUtility(IDexterityFTI, name=portal_type)
        # try:
        #     fti = getUtility(IDexterityFTI, name=portal_type)
        # except ComponentLookupError:
        #     return {}
        config = getattr(fti, 'localroles', {}).get(field, None)
        if not config:
            return {}
        for st in config:
            if suffix in config[st]:
                return {idx: org}
        return {}

    # search in indexes following suffix use in type localroles
    for (idx, field, pts, domain) in (
            ('assigned_group', 'assigned_group', ['task'], 'collective.eeafaceted.z3ctable'),
            ('treating_groups', 'treating_groups',
             ['dmsincomingmail', 'dmsincoming_email', 'dmsoutgoingmail', 'dmsoutgoing_email'],
             'collective.eeafaceted.z3ctable'),
            ('recipient_groups', 'recipient_groups',
             ['dmsincomingmail', 'dmsincoming_email', 'dmsoutgoingmail', 'dmsoutgoing_email'],
             'collective.eeafaceted.z3ctable'),
            ('assigned_group', 'creating_group',
             ['dmsincomingmail', 'dmsincoming_email', 'dmsoutgoingmail', 'dmsoutgoing_email'],
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

    # we update dms config
    if 'n_plus_' in group:
        update_transitions_auc_config('dmsincomingmail', action='delete', group_id=group)  # i_e ok
        update_transitions_levels_config(['dmsincomingmail', 'dmsoutgoingmail', 'task'], action='delete',  # i_e ok
                                         group_id=group)


def group_assignment(event):
    """
        manage the add of a user in a plone group
    """
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.AssignedUsersVocabulary')
    if event.group_id.endswith(CREATING_GROUP_SUFFIX):
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary')
    # we update dms config
    if 'n_plus_' in event.group_id:
        update_transitions_auc_config('dmsincomingmail', action='add', group_id=event.group_id)  # i_e ok
        update_transitions_levels_config(['dmsincomingmail', 'dmsoutgoingmail', 'task'], action='add',  # i_e ok
                                         group_id=event.group_id)
    # we manage the 'lu' label for a new assignment
    # same functions as IncomingMailInCopyGroupUnreadCriterion
    userid = event.principal
    orgs = organizations_with_suffixes([event.group_id], IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
    if orgs:
        days_back = 5
        start = datetime.datetime(1973, 02, 12)
        end = datetime.datetime.now() - datetime.timedelta(days=days_back)
        catalog = api.portal.get_tool('portal_catalog')
        for brain in catalog(portal_type=['dmsincomingmail', 'dmsincoming_email'], recipient_groups=orgs,
                             labels={'not': ['%s:lu' % userid]},
                             created={'query': (start, end), 'range': 'min:max'}):
            # if not brain.recipient_groups:
            #    continue
            obj = brain.getObject()
            labeling = ILabeling(obj)
            user_ids = labeling.storage.setdefault('lu', PersistentList())  # _p_changed is managed
            user_ids.append(userid)  # _p_changed is managed
            obj.reindexObject(idxs=['labels'])
    # we manage the personnel-folder person and held position
    orgs = organizations_with_suffixes([event.group_id], ['encodeur'], group_as_str=True)
    if orgs:
        user = api.user.get(userid)
        start = api.portal.get_registry_record('omail_fullname_used_form', IImioDmsMailConfig, default='firstname')
        firstname, lastname = separate_fullname(user, start=start)
        portal = api.portal.get()
        intids = getUtility(IIntIds)
        pf = portal['contacts']['personnel-folder']
        # exists already
        exist = portal.portal_catalog(mail_type=userid, portal_type='person')
        if userid in pf:
            pers = pf[userid]
        elif exist:
            pers = exist[0].getObject()
        else:
            pers = api.content.create(container=pf, type='person', id=userid, userid=userid, lastname=lastname,
                                      firstname=firstname, use_parent_address=False)
        if api.content.get_state(pers) == 'deactivated':
            api.content.transition(pers, 'activate')
        hps = [b.getObject() for b in api.content.find(context=pers, portal_type='held_position')]
        hps_orgs = dict([(hp.get_organization(), hp) for hp in hps])
        uid = orgs[0]
        org = uuidToObject(uid)
        if not org:
            return
        if uid in pers:
            hp = pers[uid]
        elif org in hps_orgs:
            hp = hps_orgs[org]
        else:
            hp = api.content.create(container=pers, id=uid, type='held_position',
                                    email=safe_unicode(user.getProperty('email')),
                                    position=RelationValue(intids.getId(org)), use_parent_address=True)
        if api.content.get_state(hp) == 'deactivated':
            api.content.transition(hp, 'activate')


def group_unassignment(event):
    """
        manage the remove of a user in a plone group
    """
    invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.AssignedUsersVocabulary')
    if event.group_id.endswith(CREATING_GROUP_SUFFIX):
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary')
    # we update dms config
    if 'n_plus_' in event.group_id:
        update_transitions_auc_config('dmsincomingmail', action='remove', group_id=event.group_id)  # i_e ok
        update_transitions_levels_config(['dmsincomingmail', 'dmsoutgoingmail', 'task'], action='remove',  # i_e ok
                                         group_id=event.group_id)
    # we manage the personnel-folder person and held position
    orgs = organizations_with_suffixes([event.group_id], ['encodeur'], group_as_str=True)
    if orgs:
        userid = event.principal
        portal = api.portal.get()
        pf = portal['contacts']['personnel-folder']
        exist = portal.portal_catalog(mail_type=userid, portal_type='person')
        if userid in pf:
            pers = pf[userid]
        elif exist:
            pers = exist[0].getObject()
        else:
            return
        hps = [b.getObject() for b in api.content.find(context=pers, portal_type='held_position')]
        for hp in hps:
            if hp.get_organization().UID() == orgs[0] and api.content.get_state(hp) == 'active':
                api.content.transition(hp, 'deactivate')


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
        for brain in catalog.unrestrictedSearchResults(portal_type=['dmsoutgoingmail'], sender_index=[del_obj.UID()]):
            storage.addBreach(brain._unrestrictedGetObject(), del_obj)


def cktemplate_moved(obj, event):
    """Managed the annotation for the Service template.

    Linked to creation, move, rename, delete and copy.
    """
    # TODO move it to ckeditortemplates
    if IObjectRemovedEvent.providedBy(event):
        return
    path = '/'.join(obj.getPhysicalPath()[:-1])
    # skip rename or inplace copy
    if event.oldParent == event.newParent or \
            (event.oldParent and path == '/'.join(event.oldParent.getPhysicalPath())):
        return
    if '/templates/oem' not in path:
        return  # oem has been renamed
    index = path.index('/templates/oem') + 14
    subpath = path[index + 1:]
    parts = subpath and subpath.split('/') or []
    value = u''
    if parts:
        pcat = obj.portal_catalog
        brains = pcat(path='{}/{}'.format(path[:index], parts[0]), sort_on='path', )
        titles = {br.getPath(): br.Title for br in brains}
        values = []
        current_path = path[:index]
        for part in parts:
            current_path += '/{}'.format(part)
            values.append(titles[current_path].decode('utf8'))
        value = u' - '.join(values)
    annot = IAnnotations(obj)
    annot['dmsmail.cke_tpl_tit'] = value


def conversion_finished(obj, event):
    # put a flag on the File to know that its conversion is finished
    obj.conversion_finished = True


def wsclient_configuration_changed(event):
    """ call original subscriber and do more stuff """
    if IRecordModifiedEvent.providedBy(event):
        # generated_actions changed, we need to update generated actions in portal_actions
        if event.record.fieldName == 'generated_actions':
            notify_configuration_changed(event)
            portal = api.portal.get()
            ids = []
            object_buttons = portal.portal_actions.object_buttons
            portlet_actions = portal.portal_actions.object_portlet
            for object_button in object_buttons.objectValues():
                if object_button.id.startswith('plonemeeting_wsclient_action_'):
                    ids.append(object_button.id)
                    if object_button.id in portlet_actions:
                        api.content.delete(portlet_actions[object_button.id])
                    api.content.copy(object_button, portlet_actions)
            existing_pos = portlet_actions.getObjectPosition('im-listing')
            for i, aid in enumerate(ids):
                portlet_actions.moveObjectToPosition(aid, existing_pos + i)


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
