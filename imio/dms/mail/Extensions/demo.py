# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.dms.batchimport.utils import createDocument
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import datetime
from imio.dms.mail import add_path
from itertools import cycle
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.CPUtils.Extensions.utils import log_list

import copy
import os


def import_scanned(self, number=2):
    """
        Import some incoming mail for demo site
    """
    now = datetime.now()
    docs = {
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
    }
    docs_cycle = cycle(docs)

    class Dummy(object):
        def __init__(self, context, request):
            self.context = context
            self.request = request

    portal = getToolByName(self, "portal_url").getPortalObject()
    folder = portal['incoming-mail']
    count = 1
    limit = int(number)
    while(count <= limit):
        doc = docs_cycle.next()
        with open(add_path('Extensions/%s' % doc), 'rb') as fo:
            file_object = NamedBlobFile(fo.read(), filename=unicode(doc))

        irn = internalReferenceIncomingMailDefaultValue(Dummy(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[doc]['c'])
        doc_metadata['internal_reference_no'] = irn
        (document, main_file) = createDocument(
            Dummy(portal, portal.REQUEST),
            folder,
            'dmsincomingmail',
            '',
            file_object,
            owner='scanner',
            metadata=doc_metadata)
        for key, value in docs[doc]['f'].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=('scan_id', 'internal_reference_number'))
        document.reindexObject(idxs=('SearchableText'))
        count += 1
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

    class Dummy(object):
        def __init__(self, context, request):
            self.context = context
            self.request = request

    portal = getToolByName(self, "portal_url").getPortalObject()
    folder = portal['outgoing-mail']
    count = 1
    limit = int(number)
    user = api.user.get_current()
    while(count <= limit):
        doc = docs_cycle.next()
        with open(add_path('Extensions/%s' % doc), 'rb') as fo:
            file_object = NamedBlobFile(fo.read(), filename=doc)
        count += 1
        irn = internalReferenceOutgoingMailDefaultValue(Dummy(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[doc]['c'])
        doc_metadata['internal_reference_no'] = irn
        (document, main_file) = createDocument(
            Dummy(portal, portal.REQUEST),
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
        #with api.env.adopt_roles(roles=['Batch importer', 'Manager']):
        # previous is not working
        api.user.grant_roles(user=user, roles=['Batch importer'], obj=document)
        api.content.transition(obj=document, transition='set_scanned')
        api.user.revoke_roles(user=user, roles=['Batch importer'], obj=document)

    return portal.REQUEST.response.redirect(folder.absolute_url())


def create_main_file(self, filename='', title='1', mainfile_type='dmsmainfile'):
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
    return obj.REQUEST.response.redirect('%s/view' % obj.absolute_url())


def clean_examples(self):
    """ Clean created examples """
    if not check_zope_admin():
        return "You must be a zope manager to run this script"
    out = []
    portal = api.portal.getSite()
    portal.portal_properties.site_properties.enable_link_integrity_checks = False

    # Delete om
    brains = api.content.find(portal_type='dmsoutgoingmail')
    for brain in brains:
        log_list(out, "Deleting om '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
    # Delete im
    brains = api.content.find(portal_type='dmsincomingmail')
    for brain in brains:
        log_list(out, "Deleting im '%s'" % brain.getPath())
        api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
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
    api.portal.set_registry_record(name=ORGANIZATIONS_REGISTRY, value=[ownorg['college-communal'].UID()])
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
    functions = [dic['fct_id'] for dic in api.portal.get_registry_record(FUNCTIONS_REGISTRY)]
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
