# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_organizations
from collective.dms.batchimport.utils import createDocument
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import date
from datetime import datetime
from imio.dms.mail import add_path
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.utils import DummyView
from itertools import cycle
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.CPUtils.Extensions.utils import check_role
from Products.CPUtils.Extensions.utils import log_list
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.intid import IIntIds

import copy
import os
import time


def import_scanned(self, number=2, only='', ptype='dmsincomingmail', redirect='1'):  # i_e ok
    """
        Import some incoming mail for demo site
    """
    if ptype not in ('dmsincomingmail', 'dmsincoming_email'):
        return "ptype parameter must be in ('dmsincomingmail', 'dmsincoming_email') values"
    now = datetime.now()
    portal = getToolByName(self, "portal_url").getPortalObject()
    contacts = portal.contacts
    intids = getUtility(IIntIds)
    docs = {
        'dmsincomingmail': {  # i_e ok
            '59.PDF':
            {
                'c': {'mail_type': 'courrier', 'file_title': '010500000000001.pdf', 'recipient_groups': []},
                'f': {'scan_id': '010500000000001', 'pages_number': 1, 'scan_date': now,
                      'scan_user': 'Opérateur', 'scanner': 'Ricola'}
            },
            '60.PDF':
            {
                'c': {'mail_type': 'courrier', 'file_title': '010500000000002.pdf', 'recipient_groups': []},
                'f': {'scan_id': '010500000000002', 'pages_number': 1, 'scan_date': now,
                      'scan_user': 'Opérateur', 'scanner': 'Ricola'}
            },
        },
        'dmsincoming_email': {
            'email1.pdf':
            {
                'c': {'title': u'Réservation de la salle Le Foyer', 'mail_type': u'email', 'file_title': u'email1.pdf',
                      'assigned_user': 'agent', 'recipient_groups': [], 'original_sender_email': u's.geul@mail.com'},
                'f': {'scan_id': '', 'pages_number': 1, 'scan_date': now, 'scan_user': '', 'scanner': ''}
            },
            'email2.pdf':
            {
                'c': {'title': u'Où se situe votre entité par rapport aux Objectifs de développement durable ?',
                      'mail_type': u'email', 'file_title': u'email2.pdf',
                      'recipient_groups': [], 'original_sender_email': u'm.bou@rw.be'},
                'f': {'scan_id': '', 'pages_number': 1, 'scan_date': now, 'scan_user': '', 'scanner': ''}
            },
        }
    }
    docs_cycle = cycle(docs[ptype])
    folder = portal['incoming-mail']
    count = 1
    limit = int(number)
    while count <= limit:
        doc = docs_cycle.next()
        if only and doc != only:
            time.sleep(0.5)
            continue
        with open(add_path('Extensions/%s' % doc), 'rb') as fo:
            file_object = NamedBlobFile(fo.read(), filename=unicode(doc))

        irn = internalReferenceIncomingMailDefaultValue(DummyView(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[ptype][doc]['c'])
        doc_metadata['internal_reference_no'] = irn
        (document, main_file) = createDocument(
            DummyView(portal, portal.REQUEST),
            folder,
            ptype,
            '',
            file_object,
            owner='scanner',
            metadata=doc_metadata)
        for key, value in docs[ptype][doc]['f'].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=('scan_id', 'internal_reference_number'))
        # transaction.commit()  # commit here to be sure to index preceding when using collective.indexing
        # change has been done in IdmSearchableExtender to avoid using catalog
        document.reindexObject(idxs=('SearchableText', ))
        count += 1
    if redirect:
        return portal.REQUEST.response.redirect(folder.absolute_url())


def import_scanned2(self, number=2):
    """
        Import some outgoing mail for demo site
    """
    now = datetime.now()
    docs = {
        u'011500000000001.pdf':
        {
            'c': {'mail_type': 'courrier', 'file_title': u'011500000000001.pdf', 'outgoing_date': now},
            'f': {'scan_id': '011500000000001', 'pages_number': 1, 'scan_date': now,
                  'scan_user': 'Opérateur', 'scanner': 'Ricola'}
        },
        u'011500000000002.pdf':
        {
            'c': {'mail_type': 'courrier', 'file_title': u'011500000000002.pdf', 'outgoing_date': now},
            'f': {'scan_id': '011500000000002', 'pages_number': 1, 'scan_date': now,
                  'scan_user': 'Opérateur', 'scanner': 'Ricola'}
        },
    }
    docs_cycle = cycle(docs)
    portal = getToolByName(self, "portal_url").getPortalObject()
    folder = portal['outgoing-mail']
    count = 1
    limit = int(number)
    user = api.user.get_current()
    while count <= limit:
        doc = docs_cycle.next()
        with open(add_path('Extensions/%s' % doc), 'rb') as fo:
            file_object = NamedBlobFile(fo.read(), filename=doc)
        count += 1
        irn = internalReferenceOutgoingMailDefaultValue(DummyView(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[doc]['c'])
        doc_metadata['internal_reference_no'] = irn
        (document, main_file) = createDocument(
            DummyView(portal, portal.REQUEST),
            folder,
            'dmsoutgoingmail',
            '',
            file_object,
            mainfile_type='dmsommainfile',
            owner='scanner',
            metadata=doc_metadata)
        for key, value in docs[doc]['f'].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=('scan_id', 'internal_reference_number'))
        document.reindexObject(idxs=('SearchableText'))
        # we adopt roles for robotframework
        # with api.env.adopt_roles(roles=['Batch importer', 'Manager']):
        # previous is not working
        api.user.grant_roles(user=user, roles=['Batch importer'], obj=document)
        api.content.transition(obj=document, transition='set_scanned')
        api.user.revoke_roles(user=user, roles=['Batch importer'], obj=document)

    return portal.REQUEST.response.redirect(folder.absolute_url())


def create_main_file(self, filename='', title='1', mainfile_type='dmsmainfile', redirect='1'):
    """
        Create a main file on context
    """
    if not filename:
        return "You must pass the filename parameter"
    exm = self.REQUEST['PUBLISHED']
    path = os.path.dirname(exm.filepath())
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return "The file path '%s' doesn't exist" % filepath
    with open(filepath, 'rb') as fo:
        file_object = NamedBlobFile(fo.read(), filename=safe_unicode(filename))
        obj = createContentInContainer(self, mainfile_type, title=safe_unicode(title), file=file_object)
    if redirect:
        return obj.REQUEST.response.redirect('%s/view' % obj.absolute_url())


def clean_examples(self):
    """ Clean created examples """
    if not check_zope_admin():
        return "You must be a zope manager to run this script"
    out = []
    portal = api.portal.getSite()
    portal.portal_properties.site_properties.enable_link_integrity_checks = False
    registry = getUtility(IRegistry)

    # Delete om
    brains = api.content.find(portal_type='dmsoutgoingmail')
    for brain in brains:
        log_list(out, "Deleting om '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_number'] = 1

    # Create test om
    params = {'title': u'Courrier test pour création de modèles (ne pas effacer)',
              'internal_reference_no': internalReferenceOutgoingMailDefaultValue(DummyView(portal, portal.REQUEST)),
              'mail_date': date.today(),
              'mail_type': 'courrier',
              }
    portal['outgoing-mail'].invokeFactory('dmsoutgoingmail', id='test_creation_modele', **params)

    # Delete im
    brains = api.content.find(portal_type='dmsincomingmail')
    for brain in brains:
        log_list(out, "Deleting im '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_number'] = 1
    # Delete own personnel
    pf = portal['contacts']['personnel-folder']
    brains = api.content.find(context=pf, portal_type='person')
    for brain in brains:
        log_list(out, "Deleting person '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    # Deactivate own organizations
    ownorg = portal['contacts']['plonegroup-organization']
    brains = api.content.find(context=ownorg, portal_type='organization',
                              id=['plonegroup-organization', 'college-communal', 'conseil-communal'])
    kept_orgs = [brain.UID for brain in brains]
    log_list(out, "Activating only 'college-communal'")
    set_registry_organizations([ownorg['college-communal'].UID()])
    # Delete organization and template folders
    tmpl_folder = portal['templates']['om']
    brains = api.content.find(context=ownorg, portal_type='organization', sort_on='path', sort_order='descending')
    for brain in brains:
        uid = brain.UID
        if uid in kept_orgs:
            continue
        log_list(out, "Deleting organization '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        if uid in tmpl_folder:
            log_list(out, "Deleting template folder '%s'" % '/'.join(tmpl_folder[uid].getPhysicalPath()))
            api.content.delete(obj=tmpl_folder[uid])
    # Delete contacts
    brains = api.content.find(context=portal['contacts'], portal_type='person',
                              id=['jeancourant', 'sergerobinet', 'bernardlermitte'])
    for brain in brains:
        log_list(out, "Deleting person '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    brains = api.content.find(context=portal['contacts'], portal_type='organization', id=['electrabel', 'swde'])
    for brain in brains:
        log_list(out, "Deleting organization '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    brains = api.content.find(context=portal['contacts'], portal_type='contact_list')
    for brain in brains:
        log_list(out, "Deleting contact list '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    # Delete users
    for userid in ['encodeur', 'dirg', 'chef', 'agent', 'agent1', 'lecteur']:
        user = api.user.get(userid=userid)
        for brain in api.content.find(Creator=userid, sort_on='path', sort_order='descending'):
            log_list(out, "Deleting object '%s' created by '%s'" % (brain.getPath(), userid))
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        for group in api.group.get_groups(user=user):
            if group.id == 'AuthenticatedUsers':
                continue
            log_list(out, "Removing user '%s' from group '%s'" % (userid, group.getProperty('title')))
            api.group.remove_user(group=group, user=user)
        log_list(out, "Deleting user '%s'" % userid)
        api.user.delete(user=user)
    # Delete groups
    functions = [dic['fct_id'] for dic in get_registry_functions()]
    groups = api.group.get_groups()
    for group in groups:
        if '_' not in group.id or group.id in ['dir_general']:
            continue
        parts = group.id.split('_')
        if len(parts) == 1:
            continue
        org_uid = parts[0]
        function = '_'.join(parts[1:])
        if org_uid in kept_orgs or function not in functions:
            continue
        log_list(out, "Deleting group '%s'" % group.getProperty('title'))
        api.group.delete(group=group)
    portal.portal_properties.site_properties.enable_link_integrity_checks = True
    return '\n'.join(out)


def activate_group_encoder(self, typ='imail'):
    """ Clean created examples """
    if not check_role(self):
        return "You must be a manager to run this script"
    portal = api.portal.getSite()
    # activate group encoder
    api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}_group_encoder'.format(typ),
                                   True)
    # we add organizations
    orgs = [portal['contacts']['plonegroup-organization']['direction-generale']['secretariat'].UID(),
            portal['contacts']['plonegroup-organization']['evenements'].UID()]
    functions = get_registry_functions()
    for dic in functions:
        if dic['fct_id'] != CREATING_GROUP_SUFFIX:
            continue
        if not dic['fct_orgs']:
            dic['fct_orgs'] = orgs
    set_registry_functions(functions)
    # we add members in groups
    if 'encodeur' not in [u.getId() for u in
                          api.user.get_users(groupname='{}_{}'.format(orgs[0], CREATING_GROUP_SUFFIX))]:
        api.group.add_user(groupname='{}_{}'.format(orgs[0], CREATING_GROUP_SUFFIX), username='encodeur')
        api.group.add_user(groupname='{}_{}'.format(orgs[1], CREATING_GROUP_SUFFIX), username='agent1')

    return portal.REQUEST.response.redirect(portal.absolute_url())
