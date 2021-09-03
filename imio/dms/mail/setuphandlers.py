# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2013 by CommunesPlone, Imio
#
# GNU General Public License (GPL)
#

__author__ = """Gauthier BASTIEN <gbastien@imio.be>, Stephan GEULETTE
<stephan.geulette@imio.be>"""
__docformat__ = 'plaintext'

from collections import OrderedDict
from collective.ckeditortemplates.setuphandlers import FOLDER as default_cke_templ_folder
from collective.classification.folder.utils import evaluate_internal_reference
from collective.classification.tree.utils import create_category
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_groups_mgt
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_groups_mgt
from collective.contact.plonegroup.config import set_registry_organizations
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.dms.mailcontent.dmsmail import mailDateDefaultValue
from collective.dms.mailcontent.dmsmail import receptionDateDefaultValue
from collective.documentgenerator.interfaces import IBelowContentBodyBatchActionsMarker
from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from collective.querynextprev.interfaces import INextPrevNotNavigable
from dexterity.localroles.utils import add_fti_configuration
from ftw.labels.interfaces import ILabelJar
from ftw.labels.interfaces import ILabelRoot
# from imio.dms.mail import CREATING_FIELD_ROLE
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IClassificationFoldersDashboard
from imio.dms.mail.interfaces import IContactListsDashboardBatchActions
from imio.dms.mail.interfaces import IHeldPositionsDashboardBatchActions
from imio.dms.mail.interfaces import IIMDashboardBatchActions
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.interfaces import IOMCKTemplatesFolder
from imio.dms.mail.interfaces import IOMDashboardBatchActions
from imio.dms.mail.interfaces import IOMTemplatesFolder
from imio.dms.mail.interfaces import IOrganizationsDashboardBatchActions
from imio.dms.mail.interfaces import IPersonsDashboardBatchActions
from imio.dms.mail.interfaces import ITaskDashboardBatchActions
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import set_dms_config
from imio.helpers.content import create
from imio.helpers.content import create_NamedBlob
from imio.helpers.content import richtextval
from imio.helpers.content import transitions
from imio.helpers.security import generate_password
from imio.helpers.security import get_environment
from itertools import cycle
from plone import api
from plone.app.controlpanel.markup import MarkupControlPanelAdapter
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobFile
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry
# from Products.CMFPlone import PloneMessageFactory as pmf
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import configure_ckeditor
from utils import list_wf_states
from z3c.relationfield.relation import RelationValue
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds

import copy
import datetime
import logging
import os
import pkg_resources


logger = logging.getLogger('imio.dms.mail: setuphandlers')
GEDURL = os.getenv('PUBLIC_URL', '')


def _(msgid, domain='imio.dms.mail'):
    translation_domain = queryUtility(ITranslationDomain, domain)
    sp = api.portal.get().portal_properties.site_properties
    return translation_domain.translate(msgid, target_language=sp.getProperty('default_language', 'fr'))


def add_db_col_folder(folder, id, title, displayed=''):
    if base_hasattr(folder, id):
        return folder[id]

    folder.invokeFactory('Folder', id=id, title=title, rights=displayed)
    col_folder = folder[id]
    col_folder.setConstrainTypesMode(1)
    col_folder.setLocallyAllowedTypes(['DashboardCollection'])
    col_folder.setImmediatelyAddableTypes(['DashboardCollection'])
    transitions(col_folder, transitions=['show_internally'])
    alsoProvides(col_folder, ICollectionCategories)
    return col_folder


def order_1st_level(site):
    """Order 1st level folders."""
    ordered = ['incoming-mail', 'outgoing-mail', 'folders', 'tasks', 'contacts', 'templates', 'tree']
    for i, oid in enumerate(ordered):
        site.moveObjectToPosition(oid, i)


def setup_classification(site):
    # Layer is required to ensure that faceted is correctly configured
    alsoProvides(site.REQUEST, IImioDmsMailLayer)

    if not base_hasattr(site, 'folders'):
        site.invokeFactory("ClassificationFolders", id='folders', title=_(u'folders_tab'))
        folders = site["folders"]
        alsoProvides(folders, ILabelRoot)
        adapted = ILabelJar(folders)
        adapted.add("Suivi", "yellow", True)  # label_id = suivi
        transitions(folders, transitions=['show_internally'])

    if not base_hasattr(site, 'tree'):
        site.invokeFactory("ClassificationContainer", id='tree', title=_(u'classification_tree_tab'))
        blacklistPortletCategory(site, site['tree'])
        # transitions(site['tree'], transitions=['show_internally'])

    roles_config = {
        'service_in_charge': {
            'internally_published': {'editeur': {'roles': ['Editor']},
                                     'lecteur': {'roles': ['Reader']}},
            'private': {'editeur': {'roles': ['Editor']},
                        'lecteur': {'roles': ['Reader']}},
        }, 'services_in_copy': {
            'internally_published': {'lecteur': {'roles': ['Reader']}},
            'private': {'lecteur': {'roles': ['Reader']}},
        },
    }

    for keyname in roles_config:
        msg = add_fti_configuration('ClassificationFolder', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        msg = add_fti_configuration('ClassificationSubfolder', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)

    fti = getUtility(IDexterityFTI, name=site["folders"].portal_type)
    original_allowed = copy.deepcopy(fti.allowed_content_types)
    fti.allowed_content_types += ("Folder", )

    # Setup dashboard collections
    collection_folder = add_db_col_folder(
        site["folders"],
        "folder-searches",
        _("Folders searches"),
        _("Folders"),
    )
    alsoProvides(collection_folder, INextPrevNotNavigable)
    alsoProvides(collection_folder, IClassificationFoldersDashboard)
    create_classification_folders_collections(collection_folder)

    fti.allowed_content_types = original_allowed
    configure_faceted_folder(
        collection_folder,
        xml="classificationfolders-searches.xml",
        default_UID=collection_folder["all_folders"].UID(),
    )
    site["folders"].setDefaultPage("folder-searches")

    logger.info("Classification configured")


def postInstall(context):
    """Called as at the end of the setup process. """
    # the right place for your custom code

    if not context.readDataFile("imiodmsmail_marker.txt"):
        return
    site = context.getSite()

    # we adapt default portal
    adaptDefaultPortal(context)

    # we change searched types
    changeSearchedTypes(site)

    # we configure rolefields
    configure_rolefields(context)
    configure_iem_rolefields(context)
    configure_om_rolefields(context)

    if (base_hasattr(site.portal_types.task, 'localroles') and
            site.portal_types.task.localroles.get('assigned_group', '') and
            site.portal_types.task.localroles['assigned_group'].get('created') and
            '' in site.portal_types.task.localroles['assigned_group']['created']):
        configure_task_rolefields(context, force=True)
    else:
        configure_task_rolefields(context, force=False)

    configure_task_config(context)
    update_task_workflow(site)

    # we create the basic folders
    if not base_hasattr(site, 'incoming-mail'):
        folderid = site.invokeFactory("Folder", id='incoming-mail', title=_(u'incoming_mail_tab'))
        im_folder = getattr(site, folderid)
        alsoProvides(im_folder, INextPrevNotNavigable)
        alsoProvides(im_folder, ILabelRoot)
        alsoProvides(im_folder, ICountableTab)
        adapted = ILabelJar(im_folder)
        adapted.add('Lu', 'green', True)  # label_id = lu
        adapted.add('Suivi', 'yellow', True)  # label_id = suivi

        # add mail-searches
        col_folder = add_db_col_folder(im_folder, 'mail-searches', _("Incoming mail searches"),
                                       _('Incoming mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IIMDashboardBatchActions)

        createIMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')  # i_e ok
        configure_faceted_folder(col_folder, xml='im-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        # configure incoming-mail faceted
        configure_faceted_folder(im_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())

        im_folder.setConstrainTypesMode(1)
        im_folder.setLocallyAllowedTypes(['dmsincomingmail', 'dmsincoming_email'])
        im_folder.setImmediatelyAddableTypes(['dmsincomingmail', 'dmsincoming_email'])
        transitions(im_folder, transitions=['show_internally'])
        logger.info('incoming-mail folder created')

    if not base_hasattr(site, 'outgoing-mail'):
        folderid = site.invokeFactory("Folder", id='outgoing-mail', title=_(u'outgoing_mail_tab'))
        om_folder = getattr(site, folderid)
        alsoProvides(om_folder, INextPrevNotNavigable)
        alsoProvides(om_folder, ILabelRoot)
        alsoProvides(om_folder, ICountableTab)

        # add mail-searches
        col_folder = add_db_col_folder(om_folder, 'mail-searches', _("Outgoing mail searches"),
                                       _('Outgoing mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOMDashboardBatchActions)
        createOMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsoutgoingmail')
        configure_faceted_folder(col_folder, xml='om-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        # configure outgoing-mail faceted
        configure_faceted_folder(om_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())

        om_folder.setConstrainTypesMode(1)
        # om_folder.setLocallyAllowedTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        om_folder.setLocallyAllowedTypes(['dmsoutgoingmail'])
        # om_folder.setImmediatelyAddableTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        om_folder.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        transitions(om_folder, transitions=['show_internally'])
        logger.info('outgoing-mail folder created')

    if not base_hasattr(site, 'tasks'):
        folderid = site.invokeFactory("Folder", id='tasks', title=_(u"tasks_tab"))
        tsk_folder = getattr(site, folderid)
        alsoProvides(tsk_folder, INextPrevNotNavigable)
        alsoProvides(tsk_folder, ILabelRoot)
        alsoProvides(tsk_folder, ICountableTab)
        # add task-searches
        col_folder = add_db_col_folder(tsk_folder, 'task-searches', _("Tasks searches"),
                                       _("Tasks"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, ITaskDashboardBatchActions)
        createTaskCollections(col_folder)
        createStateCollections(col_folder, 'task')
        configure_faceted_folder(col_folder, xml='im-task-searches.xml',
                                 default_UID=col_folder['all_tasks'].UID())
        # configure outgoing-mail faceted
        configure_faceted_folder(tsk_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_tasks'].UID())

        tsk_folder.setConstrainTypesMode(1)
        tsk_folder.setLocallyAllowedTypes(['task'])
        tsk_folder.setImmediatelyAddableTypes(['task'])
        transitions(tsk_folder, transitions=['show_internally'])
        logger.info('tasks folder created')

    # Directory creation
    if not base_hasattr(site, 'contacts'):
        position_types = [{'name': u'Président', 'token': u'president'},
                          {'name': u'Directeur général', 'token': u'directeur-gen'},
                          {'name': u'Directeur financier', 'token': u'directeur-fin'},
                          {'name': u'Secrétaire', 'token': u'secretaire'},
                          {'name': u'Employé', 'token': u'employe'},
                          ]
        organization_types = [{'name': u'Non défini', 'token': u'non-defini'},
                              {'name': u'SA', 'token': u'sa'},
                              {'name': u'Commune', 'token': u'commune'},
                              {'name': u'CPAS', 'token': u'cpas'},
                              {'name': u'Intercommunale', 'token': u'intercommunale'},
                              {'name': u'Zone de police', 'token': u'zp'},
                              {'name': u'Zone de secours', 'token': u'zs'},
                              ]
        organization_levels = [{'name': u'Non défini', 'token': u'non-defini'},
                               {'name': u'Département', 'token': u'department'},
                               {'name': u'Service', 'token': u'service'},
                               ]
        params = {'title': _(u'contacts_tab'),
                  'position_types': position_types,
                  'organization_types': organization_types,
                  'organization_levels': organization_levels,
                  }
        site.invokeFactory('directory', 'contacts', **params)
        contacts = site['contacts']
        site.portal_types.directory.filter_content_types = False
        # add organizations searches
        col_folder = add_db_col_folder(contacts, 'orgs-searches', _("Organizations searches"), _("Organizations"))
        contacts.moveObjectToPosition('orgs-searches', 0)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOrganizationsDashboardBatchActions)
        createOrganizationsCollections(col_folder)
        # createStateCollections(col_folder, 'organization')
        configure_faceted_folder(col_folder, xml='organizations-searches.xml',
                                 default_UID=col_folder['all_orgs'].UID())
        # configure contacts faceted
        configure_faceted_folder(contacts, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_orgs'].UID())
        # add held positions searches
        col_folder = add_db_col_folder(contacts, 'hps-searches', _("Held positions searches"), _("Held positions"))
        contacts.moveObjectToPosition('hps-searches', 1)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IHeldPositionsDashboardBatchActions)
        createHeldPositionsCollections(col_folder)
        # createStateCollections(col_folder, 'held_position')
        configure_faceted_folder(col_folder, xml='held-positions-searches.xml',
                                 default_UID=col_folder['all_hps'].UID())
        # add persons searches
        col_folder = add_db_col_folder(contacts, 'persons-searches', _("Persons searches"), _("Persons"))
        contacts.moveObjectToPosition('persons-searches', 2)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IPersonsDashboardBatchActions)
        createPersonsCollections(col_folder)
        # createStateCollections(col_folder, 'person')
        configure_faceted_folder(col_folder, xml='persons-searches.xml',
                                 default_UID=col_folder['all_persons'].UID())
        # add contact list searches
        col_folder = add_db_col_folder(contacts, 'cls-searches', _("Contact list searches"), _("Contact lists"))
        contacts.moveObjectToPosition('cls-searches', 3)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IContactListsDashboardBatchActions)
        createContactListsCollections(col_folder)
        # createStateCollections(col_folder, 'contact_list')
        configure_faceted_folder(col_folder, xml='contact-lists-searches.xml',
                                 default_UID=col_folder['all_cls'].UID())

        site.portal_types.directory.filter_content_types = True
        transitions(contacts, transitions=['show_internally'])
        logger.info('contacts folder created')

    setup_classification(site)

    # enable portal diff on mails
    pdiff = api.portal.get_tool('portal_diff')
    pdiff.setDiffForPortalType('dmsincomingmail', {'any': "Compound Diff for Dexterity types"})  # i_e ok
    pdiff.setDiffForPortalType('dmsincoming_email', {'any': "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType('dmsoutgoingmail', {'any': "Compound Diff for Dexterity types"})
    # pdiff.setDiffForPortalType('dmsoutgoing_email', {'any': "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType('task', {'any': "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType('dmsommainfile', {'any': "Compound Diff for Dexterity types"})

    # reimport collective.contact.widget's registry step (disable jQueryUI's autocomplete)
    site.portal_setup.runImportStepFromProfile(
        'profile-collective.contact.widget:default',
        'plone.app.registry')

    configure_actions_panel(site)

    configure_ckeditor(site, custom='ged', filtering='disabled')

    add_templates(site)
    add_oem_templates(site)

    add_transforms(site)

    set_portlet(site)

    order_1st_level(site)

    # add usefull methods
    try:
        from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
        manage_addExternalMethod(site, 'sge_clean_examples', '', 'imio.dms.mail.demo', 'clean_examples')
        manage_addExternalMethod(site, 'sge_import_contacts', '', 'imports', 'import_contacts')
        manage_addExternalMethod(site, 'sge_import_scanned', '', 'imio.dms.mail.demo', 'import_scanned')
        manage_addExternalMethod(site, 'sge_import_scanned2', '', 'imio.dms.mail.demo', 'import_scanned2')
    except:
        pass

    site.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                               'imiodmsmail-add-icons-to-contact-workflow', run_dependencies=False)
    site.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                               'imiodmsmail-configure-wsclient', run_dependencies=False)
    site.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                               'imiodmsmail-contact-import-pipeline', run_dependencies=False)

    # remove collective.ckeditortemplates folder
    if default_cke_templ_folder in site:
        api.content.delete(obj=site[default_cke_templ_folder])

    # hide plone.portalheader message viewlet
    site.portal_setup.runImportStepFromProfile('profile-plonetheme.imioapps:default', 'viewlets')


def blacklistPortletCategory(obj, category=CONTEXT_CATEGORY, utilityname=u"plone.leftcolumn", value=True):
    """
        block portlets on object for the corresponding category
    """
    from plone.portlets.interfaces import IPortletManager, ILocalPortletAssignmentManager
    # Get the proper portlet manager
    manager = queryUtility(IPortletManager, name=utilityname)
    # Get the current blacklist for the location
    blacklist = getMultiAdapter((obj, manager), ILocalPortletAssignmentManager)
    # Turn off the manager
    blacklist.setBlacklistStatus(category, value)


def createStateCollections(folder, content_type):
    """
        create a collection for each contextual workflow state
    """
    conditions = {
        'dmsincomingmail': {  # i_e ok
            'created': "python: object.restrictedTraverse('idm-utils').created_col_cond()",
            'proposed_to_manager': "python: object.restrictedTraverse('idm-utils').proposed_to_manager_col_cond()",
        },
        'dmsoutgoingmail': {
            'scanned': "python: object.restrictedTraverse('odm-utils').scanned_col_cond()",
        },
    }
    view_fields = {
        'dmsincomingmail': {  # i_e ok
            '*': (u'select_row', u'pretty_link', u'treating_groups', u'assigned_user', u'due_date', u'mail_type',
                  u'sender', u'reception_date', u'classification_folders', u'actions'),
        },
        'task': {
            '*': (u'select_row', u'pretty_link', u'task_parent', u'assigned_group', u'assigned_user', u'due_date',
                  u'CreationDate', u'actions'),
        },
        'dmsoutgoingmail': {
            '*': (u'select_row', u'pretty_link', u'treating_groups', u'sender', u'recipients', u'send_modes',
                  u'mail_type', u'assigned_user', u'CreationDate', u'classification_folders', u'actions'),
            'sent': (u'select_row', u'pretty_link', u'treating_groups', u'sender', u'recipients', u'send_modes',
                     u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date',
                     u'classification_folders', u'actions')
        },
        'organization': {
            '*': (u'select_row', u'pretty_link', u'CreationDate', u'actions'),
        },
        'held_position': {
            '*': (u'select_row', u'pretty_link', u'CreationDate', u'actions'),
        },
        'person': {
            '*': (u'select_row', u'pretty_link', u'CreationDate', u'actions'),
        },
        'contact_list': {
            '*': (u'select_row', u'pretty_link', u'CreationDate', u'actions'),
        },
    }
    showNumberOfItems = {
        'dmsincomingmail': ('created',),  # i_e ok
        'dmsoutgoingmail': ('scanned',),
    }
    sort_on = {
        'dmsincomingmail': {  # i_e ok
            '*': u"organization_type",
        },
        'task': {'*': u"created"},
        'dmsoutgoingmail': {
            'scanned': u"organization_type",
        },
    }

    portal_types = {
        'dmsincomingmail': ['dmsincomingmail', 'dmsincoming_email']
    }

    for stateo in list_wf_states(folder, content_type):
        state = stateo.id
        col_id = "searchfor_%s" % state
        if not base_hasattr(folder, col_id):
            folder.invokeFactory("DashboardCollection", id=col_id, title=_(col_id), enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': portal_types.get(content_type, content_type)},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [state]}],
                                 customViewFields=(state in view_fields[content_type] and
                                                   view_fields[content_type][state] or view_fields[content_type]['*']),
                                 tal_condition=conditions.get(content_type, {}).get(state),
                                 showNumberOfItems=(state in showNumberOfItems.get(content_type, [])),
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=sort_on.get(content_type, {}).get(state, sort_on.get(
                                     content_type, {}).get('*', u'sortable_title')),
                                 sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')


def createDashboardCollections(folder, collections):
    """
        create some dashboard collections in searches folder
    """
    for i, dic in enumerate(collections):
        if not dic.get('id'):
            continue
        if not base_hasattr(folder, dic['id']):
            folder.invokeFactory("DashboardCollection",
                                 dic['id'],
                                 enabled=dic.get('enabled', True),
                                 title=dic['tit'],
                                 query=dic['query'],
                                 tal_condition=dic['cond'],
                                 roles_bypassing_talcondition=dic['bypass'],
                                 customViewFields=dic['flds'],
                                 showNumberOfItems=dic['count'],
                                 sort_on=dic['sort'],
                                 sort_reversed=dic['rev'],
                                 b_size=30,
                                 limit=0)
            collection = folder[dic['id']]
            if 'subj' in dic:
                collection.setSubject(dic['subj'])
                collection.reindexObject(['Subject'])
            collection.setLayout('tabular_view')
        if folder.getObjectPosition(dic['id']) != i:
            folder.moveObjectToPosition(dic['id'], i)


def createIMailCollections(folder):
    """
        create some incoming mails dashboard collections
    """
    collections = [
        {'id': 'all_mails', 'tit': _('all_incoming_mails'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': False},
        {'id': 'to_validate', 'tit': _('im_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsincomingmail')",  # i_e ok
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': True},
        {'id': 'to_treat', 'tit': _('im_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['proposed_to_agent']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': True},
        {'id': 'im_treating', 'tit': _('im_im_treating'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['in_treatment']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': True},
        {'id': 'have_treated', 'tit': _('im_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['closed']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': False},
        {'id': 'to_treat_in_my_group', 'tit': _('im_to_treat_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['proposed_to_agent']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': True},
        {'id': 'in_my_group', 'tit': _('im_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': False},
        {'id': 'in_copy_unread', 'tit': _('im_in_copy_unread'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-copy-group-unread'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': True},
        {'id': 'in_copy', 'tit': _('im_in_copy'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-copy-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': False},
        {'id': 'followed', 'tit': _('im_followed'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsincomingmail', 'dmsincoming_email']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-followed'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'reception_date', u'classification_folders', u'actions'),
            'sort': u'organization_type', 'rev': True, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createTaskCollections(folder):
    """
        create some tasks dashboard collections
    """
    collections = [
        {'id': 'all_tasks', 'tit': _('all_im_tasks'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_assign', 'tit': _('tasks_to_assign'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['to_assign']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True, 'enabled': False},
        {'id': 'to_treat', 'tit': _('task_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['to_do']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'im_treating', 'tit': _('task_im_treating'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['in_progress']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'have_treated', 'tit': _('task_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['closed', 'realized']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_treat_in_my_group', 'tit': _('task_to_treat_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['to_do']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-in-assigned-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'in_my_group', 'tit': _('tasks_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-in-assigned-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'have_created', 'tit': _('tasks_have_created'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'Creator', 'o': 'plone.app.querystring.operation.string.currentUser'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_proposing_group', 'tit': _('tasks_in_proposing_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-in-proposing-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_close', 'tit': _('tasks_to_close'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['realized']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True, 'enabled': False},
    ]
    createDashboardCollections(folder, collections)


def createOMailCollections(folder):
    """
        create some outgoing mails dashboard collections
    """
    collections = [
        {'id': 'all_mails', 'tit': _('all_outgoing_mails'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             # 'v': ['dmsoutgoingmail', 'dmsoutgoing_email']}], the same for all under
             'v': ['dmsoutgoingmail']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'send_modes', u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date',
                     u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_validate', 'tit': _('om_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsoutgoingmail')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'send_modes', u'mail_type', u'assigned_user', u'CreationDate',
                     u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': True, 'enabled': False},
        {'id': 'to_treat', 'tit': _('om_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['created']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'send_modes', u'mail_type', u'CreationDate', u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'om_treating', 'tit': _('om_im_treating'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v':
                ['to_be_signed']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'send_modes', u'mail_type', u'sender', u'CreationDate', u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'om_to_email', 'tit': _('om_to_email'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v':
                ['to_be_signed']},
            {'i': 'enabled', 'o': 'plone.app.querystring.operation.boolean.isTrue'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'send_modes', u'mail_type', u'sender', u'CreationDate', u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'have_treated', 'tit': _('om_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['sent']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'send_modes', u'mail_type', u'sender', u'CreationDate', u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_my_group', 'tit': _('om_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'send_modes', u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date',
                     u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_copy', 'tit': _('om_in_copy'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
             'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-in-copy-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'send_modes', u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date',
                     u'classification_folders', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createOrganizationsCollections(folder):
    """ create some dashboard collections """
    collections = [
        {'id': 'all_orgs', 'tit': _('all_orgs'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['organization']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'CreationDate', u'actions'),
            'sort': u'sortable_title', 'rev': False, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createHeldPositionsCollections(folder):
    """ create some dashboard collections """
    collections = [
        {'id': 'all_hps', 'tit': _('all_hps'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['held_position']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'CreationDate', u'actions'),
            'sort': u'sortable_title', 'rev': False, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createPersonsCollections(folder):
    """ create some dashboard collections """
    collections = [
        {'id': 'all_persons', 'tit': _('all_persons'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['person']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'CreationDate', u'actions'),
            'sort': u'sortable_title', 'rev': False, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createContactListsCollections(folder):
    """ create some dashboard collections """
    collections = [
        {'id': 'all_cls', 'tit': _('all_cls'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['contact_list']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'relative_path', u'review_state', u'CreationDate', u'actions'),
            'sort': u'sortable_title', 'rev': False, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def create_classification_folders_collections(folder):
    """Create classification folders default collections"""
    collections = [
        {
            "id": "all_folders",
            "tit": _("all_folders"),
            "subj": (u"search", ),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
            ],
            'cond': u"",
            'bypass': [],
            "flds": (
                u"pretty_link",
                u"internal_reference_no",
                u"classification_tree_identifiers",
                u"classification_treating_group",
                u"ModificationDate",
                u'review_state',
                u'actions',
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("in_my_group"),
            "subj": (u"search", ),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    'i': 'CompoundCriterion',
                    'o': 'plone.app.querystring.operation.compound.is',
                    'v': 'classificationfolder-in-treating-group',
                },
            ],
            'cond': u"",
            'bypass': [],
            "flds": (
                u"pretty_link",
                u"internal_reference_no",
                u"classification_tree_identifiers",
                u"classification_treating_group",
                u"ModificationDate",
                u'review_state',
                u'actions',
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("in_copy"),
            "subj": (u"todo", ),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    'i': 'CompoundCriterion',
                    'o': 'plone.app.querystring.operation.compound.is',
                    'v': 'classificationfolder-in-copy-group',
                },
            ],
            'cond': u"",
            'bypass': [],
            "flds": (
                u"pretty_link",
                u"internal_reference_no",
                u"classification_tree_identifiers",
                u"classification_treating_group",
                u"ModificationDate",
                u'review_state',
                u'actions',
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "followed",
            "tit": _("followed"),
            "subj": (u"search", ),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    'i': 'CompoundCriterion',
                    'o': 'plone.app.querystring.operation.compound.is',
                    'v': 'dmsincomingmail-followed',
                },
            ],
            'cond': u"",
            'bypass': [],
            "flds": (
                u"pretty_link",
                u"internal_reference_no",
                u"classification_tree_identifiers",
                u"classification_treating_group",
                u"ModificationDate",
                u'review_state',
                u'actions',
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def adaptDefaultPortal(context):
    """
       Adapt some properties of the portal
    """
    site = context.getSite()

    #deactivate tabs auto generation in navtree_properties
    #site.portal_properties.site_properties.disable_folder_sections = True
    #remove default created objects like events, news, ...
    for obj, ids in {site: ('events', 'news'), site.portal_actions.user: ('contact-contactlist-mylists', )}.items():
        for id in ids:
            try:
                obj.manage_delObjects(ids=[id])
                logger.info("'%s' deleted in '%s'" % (id, obj))
            except AttributeError:
                continue

    #set member area type
    site.portal_membership.setMemberAreaType('member_area')
    site.portal_membership.memberareaCreationFlag = 0
    site.Members.setExcludeFromNav(True)
    site.Members.setConstrainTypesMode(1)
    site.Members.setLocallyAllowedTypes([])
    site.Members.setImmediatelyAddableTypes([])

    #change the content of the front-page
    try:
        frontpage = getattr(site, 'front-page')
        if not base_hasattr(site, 'incoming-mail'):
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')
            #remove the presentation mode
            frontpage.setPresentation(False)
            transitions(frontpage, transitions=['show_internally'])
            frontpage.reindexObject()
            logger.info('front page adapted')
        # set front-page folder as not next/prev navigable
        if not INextPrevNotNavigable.providedBy(frontpage):
            alsoProvides(frontpage, INextPrevNotNavigable)

    except AttributeError:
        #the 'front-page' object does not exist...
        pass

    #reactivate old Topic
    site.portal_types.Topic.manage_changeProperties(global_allow=True)
    for action in site.portal_controlpanel.listActions():
        if action.id == 'portal_atct':
            action.visible = True

    #change default_page_types property
    if 'Folder' not in site.portal_properties.site_properties.default_page_types:
        new_list = list(site.portal_properties.site_properties.default_page_types)
        new_list.append('Folder')
        site.portal_properties.site_properties.manage_changeProperties(default_page_types=new_list)

    #permissions
    #Removing owner to 'hide' sharing tab
    site.manage_permission('Sharing page: Delegate roles', ('Manager', 'Site Administrator'),
                           acquire=0)
    #Hiding layout menu
    site.manage_permission('Modify view template', ('Manager', 'Site Administrator'),
                           acquire=0)
    #Hiding folder contents
    site.manage_permission('List folder contents', ('Manager', 'Site Administrator'),
                           acquire=0)
    #List undo
    site.manage_permission('List undoable changes', ('Manager', 'Site Administrator'),
                           acquire=0)
    #History: can revert to previous versions
    site.manage_permission('CMFEditions: Revert to previous versions', ('Manager', 'Site Administrator'),
                           acquire=0)

    #History: add history after contact merging.
    # Member needed if the treating_group is changed to another where current user doesn't have rights
    site.manage_permission('CMFEditions: Access previous versions', ('Manager', 'Site Administrator', 'Contributor',
                           'Editor', 'Member', 'Owner', 'Reviewer'), acquire=0)
    site.manage_permission('CMFEditions: Save new version', ('Manager', 'Site Administrator', 'Contributor',
                           'Editor', 'Member', 'Owner', 'Reviewer'), acquire=0)

    # Default roles for own permissions
    site.manage_permission('imio.dms.mail: Write mail base fields', ('Manager', 'Site Administrator'),
                           acquire=0)
    site.manage_permission('imio.dms.mail: Write treating group field', ('Manager', 'Site Administrator'),
                           acquire=0)
    # site.manage_permission('imio.dms.mail: Write creating group field', ('Manager', 'Site Administrator'),
    #                       acquire=0)

    # Set markup allowed types: for RichText field, don't display anymore types listbox
    adapter = MarkupControlPanelAdapter(site)
    adapter.set_allowed_types(['text/html'])

    # Activate browser message
    msg = site['messages-config']['browser-warning']
    api.content.transition(obj=msg, to_state='activated')

    #we need external edition so make sure it is activated
    # site.portal_properties.site_properties.manage_changeProperties(ext_editor=True)  # sans effet
    site.portal_memberdata.manage_changeProperties(ext_editor=True)  # par défaut pour les nouveaux utilisateurs

    #for collective.externaleditor
    registry = getUtility(IRegistry)
    registry['externaleditor.ext_editor'] = True
    if 'Image' in registry['externaleditor.externaleditor_enabled_types']:
        registry['externaleditor.externaleditor_enabled_types'] = ['PODTemplate', 'ConfigurablePODTemplate',
                                                                   'DashboardPODTemplate', 'SubTemplate',
                                                                   'StyleTemplate', 'dmsommainfile',
                                                                   'MailingLoopTemplate']

    # Default roles for ftw labels
    site.manage_permission('ftw.labels: Manage Labels Jar', ('Manager', 'Site Administrator'),
                           acquire=0)
    site.manage_permission('ftw.labels: Change Labels', ('Manager', 'Site Administrator'),
                           acquire=0)
    site.manage_permission('ftw.labels: Change Personal Labels', ('Manager', 'Site Administrator', 'Member'),
                           acquire=0)
    site.manage_permission('Portlets: Manage own portlets', ('Manager', 'Site Administrator'),
                           acquire=0)

    # registry
    api.portal.set_registry_record(name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.'
                                        'allowed', value=False)
    api.portal.set_registry_record(name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.'
                                        'search_rss_enabled', value=False)
    api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                   'contact_source_metadata_content',
                                   u'{gft} ⏺ {number}, {street}, {zip_code}, {city} ⏺ {email}')
    # chars ⏺, ↈ  , ▐ , ⬤ (see ubuntu character table. Use ctrl+shift+u+code)
    api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                   'display_below_content_title_on_views', True)
    # imio.dms.mail configuration annotation
    # if changed, must be updated in testing.py !
    set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'from'],  # i_e ok
                   [('created', 'back_to_creation'), ('proposed_to_manager', 'back_to_manager')])
    set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],  # i_e ok
                   [('closed', 'close'), ('proposed_to_agent', 'propose_to_agent')])
    set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'from'], [('created', 'back_to_creation')])
    set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'],
                   [('sent', 'mark_as_sent'), ('to_be_signed', 'propose_to_be_signed')])
    # review levels configuration, used in utils and adapters
    set_dms_config(['review_levels', 'dmsincomingmail'],  # i_e ok
                   OrderedDict([('dir_general', {'st': ['proposed_to_manager']})]))
    set_dms_config(['review_levels', 'task'], OrderedDict())
    set_dms_config(['review_levels', 'dmsoutgoingmail'], OrderedDict())
    # review_states configuration, is the same as review_levels with some key, value inverted
    set_dms_config(['review_states', 'dmsincomingmail'],  # i_e ok
                   OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),]))
    set_dms_config(['review_states', 'task'], OrderedDict())
    set_dms_config(['review_states', 'dmsoutgoingmail'], OrderedDict())


def changeSearchedTypes(site):
    """
        Change searched types
    """
    to_show = ['dmsmainfile', 'dmsommainfile']
    to_hide = ['Collection', 'ConfigurablePODTemplate', 'DashboardCollection', 'DashboardPODTemplate',
               'Discussion Item', 'Document', 'Event', 'File', 'Folder', 'Image', 'Link', 'MessagesConfig',
               'News Item', 'PodTemplate', 'StyleTemplate', 'SubTemplate', 'Topic', 'directory',
               'dmsdocument', 'held_position', 'organization', 'person', 'position', 'task']
    not_searched = list(site.portal_properties.site_properties.types_not_searched)
    for typ in to_show:
        if typ in not_searched:
            not_searched.remove(typ)
    for typ in to_hide:
        if typ not in not_searched:
            not_searched.append(typ)
    site.portal_properties.site_properties.manage_changeProperties(types_not_searched=not_searched)


def configure_rolefields(context):
    """
        Configure the rolefields for dmsincomingmail
    """

    roles_config = {'static_config': {
        'created': {'encodeurs': {'roles': ['Contributor', 'Editor', 'DmsFile Contributor', 'Base Field Writer',
                                            'Treating Group Writer']}},
        'proposed_to_manager': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Base Field Writer',
                                                          'Treating Group Writer']},
                                'encodeurs': {'roles': ['Base Field Writer', 'Reader']},
                                'lecteurs_globaux_ce': {'roles': ['Reader']}},
        'proposed_to_agent': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                              'encodeurs': {'roles': ['Reader']},
                              'lecteurs_globaux_ce': {'roles': ['Reader']}},
        'in_treatment': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                         'encodeurs': {'roles': ['Reader']},
                         'lecteurs_globaux_ce': {'roles': ['Reader']}},
        'closed': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                   'encodeurs': {'roles': ['Reader']},
                   'lecteurs_globaux_ce': {'roles': ['Reader']}},
    }, 'treating_groups': {
        # 'created': {},
        # 'proposed_to_manager': {},
        'proposed_to_agent': {'editeur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                              'lecteur': {'roles': ['Reader']}},
        'in_treatment': {'editeur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                         'lecteur': {'roles': ['Reader']}},
        'closed': {'editeur': {'roles': ['Reviewer']},
                   'lecteur': {'roles': ['Reader']}},
    }, 'recipient_groups': {
        # 'created': {},
        # 'proposed_to_manager': {},
        'proposed_to_agent': {'editeur': {'roles': ['Reader']},
                              'lecteur': {'roles': ['Reader']}},
        'in_treatment': {'editeur': {'roles': ['Reader']},
                         'lecteur': {'roles': ['Reader']}},
        'closed': {'editeur': {'roles': ['Reader']},
                   'lecteur': {'roles': ['Reader']}},
    },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration('dmsincomingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        msg = add_fti_configuration('dmsincoming_email', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)


def configure_iem_rolefields(context):
    """
        Configure the rolefields for dmsincoming_email
    """
    fti = getUtility(IDexterityFTI, name='dmsincoming_email')
    lr = getattr(fti, 'localroles')
    lrs = lr['static_config']
    if 'Base Field Writer' not in lrs['proposed_to_agent']['encodeurs']['roles']:
        lrs['proposed_to_agent']['encodeurs']['roles'] = ['Contributor', 'Editor', 'Base Field Writer',
                                                          'Treating Group Writer']
    lrt = lr['treating_groups']
    if 'Base Field Writer' not in lrt['proposed_to_agent']['editeur']['roles']:
        lrt['proposed_to_agent']['editeur']['roles'] = ['Contributor', 'Editor', 'Reviewer', 'Base Field Writer',
                                                        'Treating Group Writer']
    lr._p_changed = True


def configure_om_rolefields(context):
    """
        Configure the rolefields for dmsoutgoingmail
    """
    roles_config = {'static_config': {
        'to_be_signed': {'expedition': {'roles': ['Editor', 'Reviewer']},
                         'encodeurs': {'roles': ['Reader']},
                         'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor']},
                         'lecteurs_globaux_cs': {'roles': ['Reader']}},
        'sent': {'expedition': {'roles': ['Reader', 'Reviewer']},
                 'encodeurs': {'roles': ['Reader']},
                 'dir_general': {'roles': ['Reader', 'Reviewer']},
                 'lecteurs_globaux_cs': {'roles': ['Reader']}},
        'scanned': {'expedition': {'roles': ['Contributor', 'Editor', 'Reader', 'Reviewer', 'DmsFile Contributor',
                                             'Base Field Writer', 'Treating Group Writer']},
                    'encodeurs': {'roles': ['Reader']}},
    }, 'treating_groups': {
        'created': {'encodeur': {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor',
                                           'Base Field Writer', 'Treating Group Writer']}},
        'to_be_signed': {'editeur': {'roles': ['Reader']},
                         'encodeur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                         'lecteur': {'roles': ['Reader']}},
        'sent': {'editeur': {'roles': ['Reader']},
                 'encodeur': {'roles': ['Reader', 'Reviewer']},
                 'lecteur': {'roles': ['Reader']}},
    }, 'recipient_groups': {
        'to_be_signed': {'editeur': {'roles': ['Reader']},
                         'encodeur': {'roles': ['Reader']},
                         'lecteur': {'roles': ['Reader']}},
        'sent': {'editeur': {'roles': ['Reader']},
                 'encodeur': {'roles': ['Reader']},
                 'lecteur': {'roles': ['Reader']}},
    },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration('dmsoutgoingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        # msg = add_fti_configuration('dmsoutgoing_email', roles_config[keyname], keyname=keyname)
        # if msg:
        #     logger.warn(msg)


def configure_task_rolefields(context, force=False):
    """
        Configure the rolefields on task
    """
    roles_config = {
        'static_config': {
            'to_assign': {
                'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                'encodeurs': {'roles': ['Reader']},
            },
            'to_do': {
                'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                'encodeurs': {'roles': ['Reader']},
            },
            'in_progress': {
                'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                'encodeurs': {'roles': ['Reader']},
            },
            'realized': {
                'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                'encodeurs': {'roles': ['Reader']},
            },
            'closed': {
                'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                'encodeurs': {'roles': ['Reader']},
            },
        },
        'assigned_group': {
            'to_assign': {},
            'to_do': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'in_progress': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'realized': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'closed': {
                'editeur': {'roles': ['Reader'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
        },
        'assigned_user': {
        },
        'enquirer': {
        },
        'parents_assigned_groups': {
            'to_assign': {},
            'to_do': {
                'editeur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'in_progress': {
                'editeur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'realized': {
                'editeur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'closed': {
                'editeur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
        },
        'parents_enquirers': {
        },
    }
    for keyname in roles_config:
        # we overwrite existing configuration from task installation !
        msg = add_fti_configuration('task', roles_config[keyname], keyname=keyname, force=force)
        if msg:
            logger.warn(msg)


def configure_task_config(context):
    """
        Configure collective task
    """
    PARENTS_FIELDS_CONFIG = [
        {'fieldname': u'parents_assigned_groups', 'attribute': u'assigned_group', 'attribute_prefix': u'ITask',
         'provided_interface': u'collective.task.interfaces.ITaskContent'},
        {'fieldname': u'parents_enquirers', 'attribute': u'enquirer', 'attribute_prefix': u'ITask',
         'provided_interface': u'collective.task.interfaces.ITaskContent'},
        {'fieldname': u'parents_assigned_groups', 'attribute': u'treating_groups', 'attribute_prefix': None,
         'provided_interface': u'collective.dms.basecontent.dmsdocument.IDmsDocument'},
    ]
    registry = getUtility(IRegistry)
    logger.info("Configure registry")
    registry['collective.task.parents_fields'] = PARENTS_FIELDS_CONFIG


def configureBatchImport(context):
    """
        Add batch import configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info('Configure batch import')
    registry = getUtility(IRegistry)
    import imio.dms.mail as imiodmsmail
    productpath = imiodmsmail.__path__[0]

    if not registry.get('collective.dms.batchimport.batchimport.ISettings.fs_root_directory'):
        registry['collective.dms.batchimport.batchimport.ISettings.fs_root_directory'] = \
            os.path.join(productpath, u'batchimport/toprocess')
    if not registry.get('collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory'):
        registry['collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory'] = \
            os.path.join(productpath, u'batchimport/toprocess')
    if not registry.get('collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping'):
        registry['collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping'] = \
            [{'code': u'in', 'portal_type': u'dmsincomingmail'}]  # i_e ok


def configureImioDmsMail(context):
    """
        Add french test imio dms mail configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info('Configure imio dms mail')
    registry = getUtility(IRegistry)

    # IM
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'] = [
            {'value': u'courrier', 'dtitle': u'Courrier', 'active': True},
            {'value': u'recommande', 'dtitle': u'Recommandé', 'active': True},
            {'value': u'email', 'dtitle': u'E-mail', 'active': True},
            {'value': u'certificat', 'dtitle': u'Certificat médical', 'active': True},
            {'value': u'fax', 'dtitle': u'Fax', 'active': True},
            {'value': u'retour-recommande', 'dtitle': u'Retour recommandé', 'active': True},
            {'value': u'facture', 'dtitle': u'Facture', 'active': True},
        ]
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states'] = ['proposed_to_agent']
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields'):
        fields = [
            'IDublinCore.title', 'IDublinCore.description', 'orig_sender_email', 'sender', 'treating_groups',
            'ITask.assigned_user', 'recipient_groups', 'reception_date', 'ITask.due_date', 'mail_type', 'reply_to',
            'ITask.task_description', 'external_reference_no', 'original_mail_date',
            'IClassificationFolder.classification_categories', 'IClassificationFolder.classification_folders',
            'internal_reference_no'
        ]
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields'] = [
            {"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""}
            for v in fields
        ]

    # OM
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'] = [
            {'value': u'courrier', 'dtitle': u'Courrier', 'active': True},
            {'value': u'recommande', 'dtitle': u'Recommandé', 'active': True},
        ]
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'] = True
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_response_prefix'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_response_prefix'] = _(u'Response: ')
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes'] = [
            {'value': u'post', 'dtitle': u'Lettre', 'active': True},
            {'value': u'post_registered', 'dtitle': u'Lettre recommandée', 'active': True},
            {'value': u'email', 'dtitle': u'Email', 'active': True},
        ]
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields'):
        fields = [
            'IDublinCore.title', 'IDublinCore.description', 'orig_sender_email', 'recipients', 'treating_groups',
            'ITask.assigned_user', 'sender', 'recipient_groups', 'send_modes', 'mail_type', 'mail_date', 'reply_to',
            'ITask.task_description', 'ITask.due_date', 'outgoing_date', 'external_reference_no',
            'IClassificationFolder.classification_categories', 'IClassificationFolder.classification_folders',
            'internal_reference_no', 'email_status', 'email_subject', 'email_sender', 'email_recipient', 'email_cc',
            'email_attachments', 'email_body']
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields'] = [
            {"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""}
            for v in fields
        ]


    # IEM
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature'):
        from string import Template
        template = Template(
u"""
<meta charset="UTF-8">
<tal:global define="ctct_det python: dghv.get_ctct_det(sender['hp']);
                    label python: sender['hp'].label;
                    services python: dghv.separate_full_title(sender['org_full_title']);">
<p style="font-weight: bold;" tal:condition="nothing">!! Attention: ne pas modifier ceci directement mais passer par "Source" !!</p>
<br />
<p><span style="font-size:large;font-family:Quicksand,Arial" 
tal:content="python:u'{} {}'.format(sender['person'].firstname, sender['person'].lastname)">Prénom Nom</span></p>

<div style="float:left;">
<div style="font-size:small; float:left;clear:both;width:350px">
<span tal:condition="label" tal:content="label">Fonction</span><br />
<span tal:content="python:services[0]">Département</span><br />
<span tal:condition="python:services[1]" tal:content="python:services[1]">Service</span><br />

<a style="display: inline-block; padding-top: 1em;" href="mailto" target="_blank" 
tal:attributes="href python:'mailto:{}'.format(ctct_det['email'])" tal:content="python:ctct_det['email']">email</a>
<br /><span tal:content="python: dghv.display_phone(phone=ctct_det['phone'], check=False, pattern='/.')">Téléphone</span><br />

<span style="display: inline-block; padding-top: 0.5em;" 
tal:content="python:u'{}, {}'.format(ctct_det['address']['street'], ctct_det['address']['number'])">Rue, numéro</span><br />
<span tal:content="python:u'{} {}'.format(ctct_det['address']['zip_code'], ctct_det['address']['city'])">CP Localité</span><br />
<!--a href="https://www.google.be/maps/" target="_blank">Plan</a-->
</div></div>

<div style="float:left;display: inline-grid;"><a href="$url" target="_blank"><img alt="" src="$url/++resource++imio.dms.mail/belleville.png" /></a><br />
<span style="font-size:small;text-align: center;">Administration communale de Belleville</span><br />
</div>

<p>&nbsp;</p>

<div style="font-size: x-small;color:#424242;clear:both"><br />
Limite de responsabilité: les informations contenues dans ce courrier électronique (annexes incluses) sont confidentielles et réservées à l'usage exclusif des destinataires repris ci-dessus. Si vous n'êtes pas le destinataire, soyez informé par la présente que vous ne pouvez ni divulguer, ni reproduire, ni faire usage de ces informations pour vous-même ou toute tierce personne. Si vous avez reçu ce courrier électronique par erreur, vous êtes prié d'en avertir immédiatement l'expéditeur et d'effacer le message e-mail de votre ordinateur.
</div>
</tal:global>""")  # noqa
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature'] = template.substitute(
            url=GEDURL)

    # general
    api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.users_hidden_in_dashboard_filter',
                                   ['scanner'])

    # mailcontent
    # Hide internal reference for om. Increment number automatically
    registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_edit_irn'] = u'hide'
    registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_increment_number'] = True

    if registry.get('collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_talexpression') == \
            u"python:'in/'+number":
        registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_talexpression'] = \
            u"python:'E%04d'%int(number)"
    if registry.get('collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_talexpression') == \
            u"python:'out/'+number":
        registry['collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_talexpression'] = \
            u"python:'S%04d'%int(number)"


def configureContactPloneGroup(context):
    """
        Add french test contact plonegroup configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info('Configure contact plonegroup')
    site = context.getSite()
    if not get_registry_functions():
        set_registry_functions([
            {'fct_title': u'Créateur CS', 'fct_id': u'encodeur', 'fct_orgs': [], 'fct_management': False,
             'enabled': True},
            {'fct_title': u'Lecteur', 'fct_id': u'lecteur', 'fct_orgs': [], 'fct_management': False, 'enabled': True},
            {'fct_title': u'Éditeur', 'fct_id': u'editeur', 'fct_orgs': [], 'fct_management': False, 'enabled': True},
        ])
    if not get_registry_groups_mgt():
        set_registry_groups_mgt(['dir_general', 'encodeurs', 'expedition'])
    if not get_registry_organizations():
        contacts = site['contacts']
        own_orga = contacts['plonegroup-organization']
        # full list of orgs defined in addOwnOrganization ~1600
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        dep0 = departments[0]
        dep1 = departments[1]
        dep2 = departments[2]
        services0 = dep0.listFolderContents(contentFilter={'portal_type': 'organization'})
        services1 = dep1.listFolderContents(contentFilter={'portal_type': 'organization'})
        services2 = dep2.listFolderContents(contentFilter={'portal_type': 'organization'})
        orgas = [dep0, services0[0], services0[1], services0[3], dep1, services1[0], services1[1],
                 dep2, services2[0], services2[1], departments[5]]
        # selected orgs
        # u'Direction générale', (u'Secrétariat', u'GRH', u'Communication')
        # u'Direction financière', (u'Budgets', u'Comptabilité')
        # u'Direction technique', (u'Bâtiments', u'Voiries')
        # u'Événements'
        set_registry_organizations([org.UID() for org in orgas])
        # Add users to activated groups
        for org in orgas:
            uid = org.UID()
            site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_encodeur" % uid)
            if org.organization_type == 'service':
                site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_editeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_encodeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup('lecteur', "%s_lecteur" % uid)
        site.acl_users.source_groups.addPrincipalToGroup('agent1', "%s_editeur" % departments[5].UID())
        site.acl_users.source_groups.addPrincipalToGroup('agent1', "%s_encodeur" % departments[5].UID())


def addTestDirectory(context):
    """
        Add french test data: directory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding test directory')
    contacts = site['contacts']
    if base_hasattr(contacts, 'plonegroup-organization'):
        logger.warn('Nothing done: directory contacts already exists. You must first delete it to reimport!')
        return

    # create plonegroup-organization
    addOwnOrganization(context)

    # Add not encoded person (in directory)
    contacts.invokeFactory('person', 'notencoded', lastname=u'Non encodé', use_parent_address=False)

    # Organisations creation (in directory)
    params = {'title': u"Electrabel",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'électron",
              'number': u'1',
              'email': u'contak@electrabel.eb',
              'use_parent_address': False
              }
    contacts.invokeFactory('organization', 'electrabel', **params)
    electrabel = contacts['electrabel']

    electrabel.invokeFactory('organization', 'travaux', title=u'Travaux 1', organization_type=u'service')

    params = {'title': u"SWDE",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'eau vive",
              'number': u'1',
              'email': u'contak@swde.eb',
              'use_parent_address': False
              }
    contacts.invokeFactory('organization', 'swde', **params)
    swde = contacts['swde']

    # Persons creation (in directory)
    params = {'lastname': u'Courant',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'use_parent_address': False
              }
    contacts.invokeFactory('person', 'jeancourant', **params)
    jeancourant = contacts['jeancourant']

    params = {'lastname': u'Robinet',
              'firstname': u'Serge',
              'gender': u'M',
              'person_title': u'Monsieur',
              'use_parent_address': False
              }
    contacts.invokeFactory('person', 'sergerobinet', **params)
    sergerobinet = contacts['sergerobinet']

    params = {'lastname': u'Lermitte',
              'firstname': u'Bernard',
              'gender': u'M',
              'person_title': u'Monsieur',
              'use_parent_address': False
              }
    contacts.invokeFactory('person', 'bernardlermitte', **params)
    bernardlermitte = contacts['bernardlermitte']

    # Held positions creation (in persons)
    intids = getUtility(IIntIds)

    # link to a defined organisation
    params = {'start_date': datetime.date(2001, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(swde)),
              'label': u'Agent',
              'email': u'serge.robinet@swde.eb',
              'phone': u'012345678',
              'use_parent_address': True
              }
    sergerobinet.invokeFactory('held_position', 'agent-swde', **params)
    params['email'] = u'bernard.lermitte@swde.eb'
    bernardlermitte.invokeFactory('held_position', 'agent-swde', **params)

    params = {'start_date': datetime.date(2005, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(electrabel)),
              'label': u'Agent',
              'email': u'jean.courant@electrabel.eb',
              'phone': u'012345678',
              'use_parent_address': True
              }
    jeancourant.invokeFactory('held_position', 'agent-electrabel', **params)


def add_test_folders(context):
    """Add french test data: tree categories"""
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info('Adding test categories')
    site = context.getSite()
    cats = [{'identifier': u'-1', 'title': u'Tâche des organes. (*)', 'parent': None},
            {'identifier': u'-1.7', 'title': u'Tâches de police.', 'parent': u'-1'},
            {'identifier': u'-1.75', 'title': u'Ordre public. (*)', 'parent': u'-1.7'},
            {'identifier': u'-1.753', 'title': u'Contrôle des armes et munitions.', 'parent': u'-1.75'},
            {'identifier': u'-1.754', 'title': u'Police de la voie publique (voies et cours d''eau).',
             'parent': u'-1.75'},
            {'identifier': u'-1.754.2', 'title': u'Usage de la voie publique. (*)', 'parent': u'-1.754'},
            {'identifier': u'-1.754.21', 'title': u'Stationnement et amarrage. (*)', 'parent': u'-1.754.2'},
            {'identifier': u'-1.758', 'title': u'Police des édifices et lieux de réunions publiques.',
             'parent': u'-1.75'},
            {'identifier': u'-1.758.1', 'title': u'Contrôle des fêtes, représentations, expositions, etc. (*)',
             'parent': u'-1.758'},
            {'identifier': u'-1.758.2', 'title': u'Contrôle des foires, marchés et kermesses. (*)',
             'parent': u'-1.758'},
            {'identifier': u'-1.758.3', 'title': u'Contrôle des cabarets, cafés et débits de boissons.',
             'parent': u'-1.758'},
            {'identifier': u'-1.758.5', 'title': u'Contrôle des lieux des réunions religieuses.  (*)',
             'parent': u'-1.758'},
            ]
    objs = {None: site['tree']}
    for cat in cats:
        parent = cat.pop('parent')
        if cat['identifier'] in [bb.identifier for bb in objs.get(parent).values()]:
            return
        obj = create_category(objs.get(parent), cat)
        objs[cat['identifier']] = obj

    logger.info('Adding test folders')
    orgs = get_registry_organizations()
    data = [
        {'title': u'Ordre public - Règlement général de police', 'classification_categories': [objs['-1.75'].UID()],
         'archived': False,
         'subs': [{'title': u'Anciens règlements', 'archived': True},
                  {'title': u'Adaptation pour les caméras de surveillance de l\'espace public', 'archived': False},
                  {'title': u'Demandes de renseignements', 'archived': False}]},
        {'title': u'Règlement général de police : Sanctions administratives / Service de médiation',
         'classification_categories': [objs['-1.75'].UID()], 'archived': False,
         'subs': [{'title': u'Sanctions administratives / Amendes administratives : Agents sanctionnateurs',
                   'archived': True},
                  {'title': u'Sanctions administratives communales : Législation', 'archived': False},
                  {'title': u'Service de médiation : Bilans / Rapports annuels', 'archived': False}]},
        {'title': u'Contrôle des armes et munitions', 'classification_categories': [objs['-1.753'].UID()],
         'archived': False,
         'subs': [{'title': u'Collectionneur d\'armes : Mr Fred Chasseur', 'archived': True},
                  {'title': u'Stands de tir : Certificats d\'agrément / Contrôles quinquennals', 'archived': False},
                  {'title': u'Loi sur les armes à feu : redevances fédérales - Année 2020 à', 'archived': False}]},
        {'title': u'Usage de la voie publique : Stationnement et amarrage',
         'classification_categories': [objs['-1.754.21'].UID()], 'archived': False,
         'subs': [{'title': u'Cas particuliers : Demandes en autorisation - 2008 à 2020', 'archived': True},
                  {'title': u'Cas particuliers : Demandes en autorisation – 2021', 'archived': False}]},
        {'title': u'Usage de la voie publique : Stationnement et amarrage - Friteries',
         'classification_categories': [objs['-1.754.21'].UID()], 'archived': False,
         'subs': [{'title': u'Attestations d\'assurance', 'archived': True},
                  {'title': u'Autorisation d\'exploiter : Belleville, Rue de la Fleur', 'archived': False}]},
        {'title': u'Police des édifices et lieux de réunions publiques : Contrôle des fêtes, bals,...',
         'classification_categories': [objs['-1.758.1'].UID()], 'archived': False,
         'subs': [{'title': u'Demandes en autorisation - 2009 à 2020', 'archived': True},
                  {'title': u'Demandes en autorisation – 2021', 'archived': False},
                  {'title': u'Fancy-fair (Ecoles libres ou non communales) : Demandes en autorisation - 2021',
                   'archived': False}]},
    ]
    folders = site['folders']
    for cf_dic in data:
        cf_dic['internal_reference_no'] = evaluate_internal_reference(folders, folders.REQUEST, 'folder_number',
                                                                      'folder_talexpression')
        cf_dic['treating_groups'] = orgs[1]
        cf_dic['recipient_groups'] = []
        subs = cf_dic.pop('subs')
        cf_obj = createContentInContainer(folders, 'ClassificationFolder', **cf_dic)
        cf_obj._increment_internal_reference()
        for i, csf_dic in enumerate(subs, start=1):
            csf_dic['internal_reference_no'] = u'{}-{:02d}'.format(cf_obj.internal_reference_no, i)
            csf_dic['treating_groups'] = cf_obj.treating_groups
            csf_dic['recipient_groups'] = []
            if 'classification_categories' not in csf_dic:
                csf_dic['classification_categories'] = list(cf_obj.classification_categories)
            csf_obj = createContentInContainer(cf_obj, 'ClassificationSubfolder', **csf_dic)
            if not csf_dic['archived']:
                transitions(csf_obj, transitions=['deactivate'])


def addTestMails(context):
    """
        Add french test data: mails
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding test mails')
    import imio.dms.mail as imiodmsmail
    filespath = "%s/batchimport/toprocess/incoming-mail" % imiodmsmail.__path__[0]
    files = [unicode(name) for name in os.listdir(filespath)
             if os.path.splitext(name)[1][1:] in ('pdf', 'doc', 'jpg')]
    files_cycle = cycle(files)

    intids = getUtility(IIntIds)

    contacts = site['contacts']
    senders = [
        intids.getId(contacts['electrabel']),  # sender is the organisation
        intids.getId(contacts['swde']),  # sender is the organisation
        intids.getId(contacts['jeancourant']),  # sender is a person
        intids.getId(contacts['sergerobinet']),  # sender is a person
        intids.getId(contacts['jeancourant']['agent-electrabel']),  # sender is a person with a position
        intids.getId(contacts['sergerobinet']['agent-swde']),  # sender is a person with a position
    ]
    senders_cycle = cycle(senders)

    selected_orgs = [org for i, org in enumerate(get_registry_organizations()) if i in (0, 1, 2, 4, 5, 6)]
    orgas_cycle = cycle(selected_orgs)

    # incoming mails
    ifld = site['incoming-mail']
    data = DummyView(site, site.REQUEST)
    for i in range(1, 10):
        if not 'courrier%d' % i in ifld:
            scan_date = receptionDateDefaultValue(data)
            params = {'title': 'Courrier %d' % i,
                      'mail_type': 'courrier',
                      'internal_reference_no': internalReferenceIncomingMailDefaultValue(data),
                      'reception_date': scan_date,
                      'sender': [RelationValue(senders_cycle.next())],
                      'treating_groups': orgas_cycle.next(),
                      'recipient_groups': [],
                      'description': 'Ceci est la description du courrier %d' % i,
                      }
            ifld.invokeFactory('dmsincomingmail', id='courrier%d' % i, **params)  # i_e ok
            mail = ifld['courrier%d' % i]
            filename = files_cycle.next()
            with open("%s/%s" % (filespath, filename), 'rb') as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, 'dmsmainfile', title='', file=file_object,
                                         scan_id='0509999000000%02d' % i, scan_date=scan_date)

    # tasks
    mail = ifld['courrier1']
    mail.invokeFactory('task', id='tache1', title=u'Tâche 1', assigned_group=mail.treating_groups,
                       enquirer=mail.treating_groups)
    mail.invokeFactory('task', id='tache2', title=u'Tâche 2', assigned_group=mail.treating_groups,
                       enquirer=mail.treating_groups)
    mail.invokeFactory('task', id='tache3', title=u'Tâche autre service', assigned_group=orgas_cycle.next(),
                       enquirer=mail.treating_groups)
    task3 = mail['tache3']
    task3.invokeFactory('task', id='tache3-1', title=u'Sous-tâche 1', assigned_group=task3.assigned_group,
                        enquirer=task3.assigned_group)
    task3.invokeFactory('task', id='tache3-2', title=u'Sous-tâche 2', assigned_group=task3.assigned_group,
                        enquirer=task3.assigned_group)

    filespath = "%s/batchimport/toprocess/outgoing-mail" % imiodmsmail.__path__[0]
    files = [safe_unicode(name) for name in os.listdir(filespath)
             if os.path.splitext(name)[1][1:] in ('odt')]
    files.sort()
    files_cycle = cycle(files)
    pf = contacts['personnel-folder']
    orgas_cycle = cycle(selected_orgs)
    recipients_cycle = cycle(senders)
    users_cycle = cycle(['chef', 'agent', 'agent'])
    senders_cycle = cycle([pf['chef']['responsable-grh'].UID(), pf['agent']['agent-grh'].UID(),
                           pf['agent']['agent-secretariat'].UID()])

    # outgoing mails
    ofld = site['outgoing-mail']
    for i in range(1, 10):
        if not 'reponse%d' % i in ofld:
            params = {'title': 'Réponse %d' % i,
                      'internal_reference_no': internalReferenceOutgoingMailDefaultValue(data),
                      'mail_date': mailDateDefaultValue(data),
                      'treating_groups': orgas_cycle.next(),
                      'mail_type': 'courrier',
                      'sender': senders_cycle.next(),
                      'assigned_user': users_cycle.next(),
                      # temporary in comment because it doesn't pass in test and case probably errors when deleting site
                      #'in_reply_to': [RelationValue(intids.getId(inmail))],
                      'recipients': [RelationValue(recipients_cycle.next())],
                      'send_modes': ['post'],
                      }
            ofld.invokeFactory('dmsoutgoingmail', id='reponse%d' % i, **params)
            mail = ofld['reponse%d' % i]
            filename = files_cycle.next()
            with open(u"%s/%s" % (filespath, filename), 'rb') as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, 'dmsommainfile', id='1', title='', file=file_object)


def addTestUsersAndGroups(context):
    """
        Add french test data: users and groups
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()

    # creating users
    users = {
        ('scanner', u'Scanner'): ['Batch importer'],
        ('encodeur', u'Jean Encodeur'): [],
        ('dirg', u'Maxime DG'): [],
        ('chef', u'Michel Chef'): [],
        ('agent', u'Fred Agent'): [],
        ('agent1', u'Stef Agent'): [],
        ('lecteur', u'Jef Lecteur'): [],
    }
    password = 'Dmsmail69!'
    if get_environment() == 'prod':
        # password = site.portal_registration.generatePassword()
        password = generate_password()
    logger.info("Generated password='%s'" % password)

    for uid, fullname in users.keys():
        try:
            member = site.portal_registration.addMember(id=uid, password=password,
                                                        roles=['Member'] + users[(uid, fullname)])
            member.setMemberProperties({'fullname': fullname, 'email': '{}@macommune.be'.format(uid)})
        except ValueError, exc:
            if str(exc).startswith('The login name you selected is already in use'):
                continue
            logger("Error creating user '%s': %s" % (uid, exc))

    if api.group.get('encodeurs') is None:
        api.group.create('encodeurs', '1 Encodeurs courrier entrant')
        site['incoming-mail'].manage_addLocalRoles('encodeurs', ['Contributor', 'Reader'])
        site['contacts'].manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
        site['contacts']['contact-lists-folder'].manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
#        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname='encodeurs', username='scanner')
        api.group.add_user(groupname='encodeurs', username='encodeur')
    if api.group.get('dir_general') is None:
        api.group.create('dir_general', '1 Directeur général')
        api.group.add_user(groupname='dir_general', username='dirg')
        site['outgoing-mail'].manage_addLocalRoles('dir_general', ['Contributor'])
        site['contacts'].manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])
        site['contacts']['contact-lists-folder'].manage_addLocalRoles('dir_general',
                                                                      ['Contributor', 'Editor', 'Reader'])
    if api.group.get('expedition') is None:
        api.group.create('expedition', '1 Expédition courrier sortant')
        site['outgoing-mail'].manage_addLocalRoles('expedition', ['Contributor'])
        site['contacts'].manage_addLocalRoles('expedition', ['Contributor', 'Editor', 'Reader'])
        site['contacts']['contact-lists-folder'].manage_addLocalRoles('expedition', ['Contributor', 'Editor', 'Reader'])
        api.group.add_user(groupname='expedition', username='scanner')
        api.group.add_user(groupname='expedition', username='encodeur')
    if api.group.get('lecteurs_globaux_ce') is None:
        api.group.create('lecteurs_globaux_ce', '2 Lecteurs Globaux CE')
    if api.group.get('lecteurs_globaux_cs') is None:
        api.group.create('lecteurs_globaux_cs', '2 Lecteurs Globaux CS')


def addOwnOrganization(context):
    """
        Add french test data: plonegroup organization
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    contacts = site['contacts']

    if base_hasattr(contacts, 'plonegroup-organization'):
        logger.warn('Nothing done: plonegroup-organization already exists. You must first delete it to reimport!')
        return

    # Organisations creation (in directory)
    params = {'title': u"Mon organisation",
              'organization_type': u'commune',
              'zip_code': u'0010',
              'city': u'Ma ville',
              'street': u'Rue de la commune',
              'number': u'1',
              'use_parent_address': False,
              }
    contacts.invokeFactory('organization', 'plonegroup-organization', **params)
    contacts.moveObjectToPosition('plonegroup-organization', 5)

    own_orga = contacts['plonegroup-organization']
    blacklistPortletCategory(own_orga)

    # Departments and services creation
    sublevels = [
        (u'Direction générale', (u'Secrétariat', u'GRH', u'Informatique', u'Communication')),
        (u'Direction financière', (u'Budgets', u'Comptabilité', u'Taxes', u'Marchés publics')),
        (u'Direction technique', (u'Bâtiments', u'Voiries', u'Urbanisme')),
        (u'Département population', (u'Population', u'État-civil')),
        (u'Département culturel', (u'Enseignement', u'Culture-loisirs')),
        (u'Événements', []),
        (u'Collège communal', []),
        (u'Conseil communal', []),
    ]
    idnormalizer = queryUtility(IIDNormalizer)
    for (department, services) in sublevels:
        id = own_orga.invokeFactory('organization', idnormalizer.normalize(department),
                                    **{'title': department,
                                       'organization_type': (len(services) and u'department' or u'service')})
        dep = own_orga[id]
        for service in services:
            dep.invokeFactory('organization', idnormalizer.normalize(service),
                              **{'title': service, 'organization_type': u'service'})


def addOwnPersonnel(context):
    """
        Add french test data: personnel folder
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    contacts = site['contacts']

    if base_hasattr(contacts, 'personnel-folder'):
        if contacts['personnel-folder'].portal_type != 'Folder':
            raise Exception('Object personnel-folder already exists')
        logger.warn('Nothing done: personnel-folder already exists. You must first delete it to reimport!')
        return

    site.portal_types.directory.filter_content_types = False
    contacts.invokeFactory('Folder', 'personnel-folder', title=u'Mon personnel')
    contacts.moveObjectToPosition('personnel-folder', 4)
    pf = contacts['personnel-folder']
    blacklistPortletCategory(pf)
    site.portal_types.directory.filter_content_types = True
    api.content.transition(obj=pf, transition='show_internally')
    alsoProvides(pf, IActionsPanelFolder)
    pf.manage_permission('imio.dms.mail: Write userid field', ('Manager', 'Site Administrator'),
                         acquire=0)
    # Set restrictions
    pf.setConstrainTypesMode(1)
    pf.setLocallyAllowedTypes(['person'])
    pf.setImmediatelyAddableTypes(['person'])

    intids = getUtility(IIntIds)
    own_orga = contacts['plonegroup-organization']
    inb = api.portal.get_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                         'incomingmail_number')
    # Test if we are already in production
    if inb > 20:
        return
    # selected orgs
    # u'Direction générale', (u'Secrétariat', u'GRH', u'Communication')
    # u'Direction financière', (u'Budgets', u'Comptabilité')
    # u'Direction technique', (u'Bâtiments', u'Voiries')
    # u'Événements'
    # Assignments defined in configureContactPloneGroup
    orgs = {
        'chef': {
            'o': [own_orga['direction-generale'], own_orga['direction-generale']['secretariat'],
                  own_orga['direction-generale']['grh'], own_orga['direction-generale']['communication'],
                  own_orga['direction-financiere'], own_orga['direction-financiere']['budgets'],
                  own_orga['direction-financiere']['comptabilite'], own_orga['direction-technique'],
                  own_orga['direction-technique']['batiments'], own_orga['direction-technique']['voiries'],
                  own_orga['evenements']],
            'e': u'michel.chef@macommune.be', 'p': u'012345679', 'l': u'Responsable {}'},
        'agent': {
            'o': [own_orga['direction-generale']['secretariat'], own_orga['direction-generale']['grh'],
                  own_orga['direction-generale']['communication'], own_orga['direction-financiere']['budgets'],
                  own_orga['direction-financiere']['comptabilite'], own_orga['direction-technique']['batiments'],
                  own_orga['direction-technique']['voiries']],
            'e': u'fred.agent@macommune.be', 'p': u'012345670', 'l': u'Agent {}'},
        'agent1': {
            'o': [own_orga['evenements']], 'l': u'Agent {}'}
    }

    def hp_dic_list(key):
        return [{'position': RelationValue(intids.getId(o)), 'email': orgs[key].get('e'),
                 'phone': orgs[key].get('p'), 'use_parent_address': True,
                 'label': orgs[key]['l'].format(o.title)} for o in orgs[key]['o']]

    persons = {
        'dirg': {'pers': {'lastname': u'DG', 'firstname': u'Maxime', 'gender': u'M', 'person_title': u'Monsieur',
                 'zip_code': u'5000', 'city': u'Namur', 'street': u"Rue de l'électron",
                 'number': u'1', 'use_parent_address': False},
                 'fcts': [{'position': RelationValue(intids.getId(own_orga['direction-generale'])),
                           'label': u'Directeur général', 'email': u'maxime.dirg@macommune.be', 'phone': u'012345678',
                           'use_parent_address': True},
                          {'position': RelationValue(intids.getId(own_orga['direction-generale']['grh'])),
                           'label': u'Directeur du personnel', 'start_date': datetime.date(2012, 9, 1),
                           'end_date': datetime.date(2016, 6, 14), 'use_parent_address': True,
                           'email': u'maxime.dirg@macommune.be', 'phone': u'012345678'}]},
        'chef': {'pers': {'lastname': u'Chef', 'firstname': u'Michel', 'gender': u'M', 'person_title': u'Monsieur',
                 'zip_code': u'4000', 'city': u'Liège', 'street': u"Rue du cimetière",
                 'number': u'2', 'use_parent_address': False},
                 'fcts': hp_dic_list('chef')},
        'agent': {'pers': {'lastname': u'Agent', 'firstname': u'Fred', 'gender': u'M', 'person_title': u'Monsieur',
                  'zip_code': u'7000', 'city': u'Mons', 'street': u"Rue de la place",
                  'number': u'3', 'use_parent_address': False},
                  'fcts': hp_dic_list('agent')},
        'agent1': {'pers': {'lastname': u'Agent', 'firstname': u'Stef', 'gender': u'M', 'person_title': u'Monsieur',
                   'zip_code': u'5000', 'city': u'Namur', 'street': u"Rue du désespoir",
                   'number': u'1', 'use_parent_address': False},
                   'fcts': hp_dic_list('agent1')},
    }

    normalizer = getUtility(IIDNormalizer)
    for person in persons:
        pers = api.content.create(container=pf, type='person', id=person, userid=person, **persons[person]['pers'])
        for fct_dic in persons[person]['fcts']:
            api.content.create(container=pers, id=normalizer.normalize(fct_dic['label']), type='held_position',
                               **fct_dic)


def addContactListsFolder(context):
    """
        Add contacts list folder in directory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    contacts = site['contacts']

    if base_hasattr(contacts, 'contact-lists-folder'):
        if contacts['contact-lists-folder'].portal_type != 'Folder':
            raise Exception('Object contact-lists-folder already exists')
        logger.warn('Nothing done: contact-lists-folder already exists. You must first delete it to reimport!')
        return

    site.portal_types.directory.filter_content_types = False
    contacts.invokeFactory('Folder', 'contact-lists-folder', title=u'Listes de contact')
    contacts.moveObjectToPosition('contact-lists-folder', 5)
    clf = contacts['contact-lists-folder']
    clf.setLayout('folder_tabular_view')
    site.portal_types.directory.filter_content_types = True
    api.content.transition(obj=clf, transition='show_internally')
    alsoProvides(clf, IActionsPanelFolder)
    alsoProvides(clf, INextPrevNotNavigable)
    # Set restrictions
    clf.setConstrainTypesMode(1)
    clf.setLocallyAllowedTypes(['Folder', 'contact_list'])
    clf.setImmediatelyAddableTypes(['Folder', 'contact_list'])
    clf.__ac_local_roles_block__ = True
    # set common
    clf.invokeFactory("Folder", id='common', title=u"Listes communes")
    clf['common'].setLayout('folder_tabular_view')
    transitions(clf['common'], transitions=['show_internally'])
    alsoProvides(clf['common'], IActionsPanelFolder)
    alsoProvides(clf['common'], INextPrevNotNavigable)
    intids = getUtility(IIntIds)
    if 'sergerobinet' in contacts and 'bernardlermitte' in contacts:
        api.content.create(container=clf['common'], type='contact_list', id='list-agents-swde',
                           title=u'Liste des agents SWDE',
                           contacts=[RelationValue(intids.getId(contacts['sergerobinet']['agent-swde'])),
                                     RelationValue(intids.getId(contacts['bernardlermitte']['agent-swde']))])


def configureDocumentViewer(context):
    """
        Set the settings of document viewer product
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    from collective.documentviewer.settings import GlobalSettings
    site = context.getSite()
    gsettings = GlobalSettings(site)
    gsettings.storage_location = os.path.join(os.getcwd(), 'var', 'dv_files')
    gsettings.storage_type = 'Blob'
    gsettings.pdf_image_format = 'jpg'
    if 'excel' not in gsettings.auto_layout_file_types:
        gsettings.auto_layout_file_types = list(gsettings.auto_layout_file_types) + ['excel', 'image']
    gsettings.show_search = True


def refreshCatalog(context):
    """
        Reindex catalog
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    site.portal_catalog.refreshCatalog()


def setupFacetedContacts(portal):
    """Setup facetednav for contacts. Was used in old migration"""


def configure_actions_panel(portal):
    """
        Configure actions panel registry
    """
    logger.info('Configure actions panel registry')
    registry = getUtility(IRegistry)

    if not registry.get('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'):
        registry['imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'] = \
            ['dmsincomingmail.back_to_creation|', 'dmsincomingmail.back_to_manager|',
             'dmsincomingmail.back_to_treatment|', 'dmsincomingmail.back_to_agent|',
             'dmsincoming_email.back_to_creation|', 'dmsincoming_email.back_to_manager|',
             'dmsincoming_email.back_to_treatment|', 'dmsincoming_email.back_to_agent|',
             'task.back_in_created|', 'task.back_in_to_assign|',
             'task.back_in_to_do|', 'task.back_in_progress|', 'task.back_in_realized|',
             'dmsoutgoingmail.back_to_agent|', 'dmsoutgoingmail.back_to_creation|',
             'dmsoutgoingmail.back_to_be_signed|', 'dmsoutgoingmail.back_to_scanned|']


def configure_faceted_folder(folder, xml=None, default_UID=None):
    """Configure faceted navigation on folder."""
    enableFacetedDashboardFor(folder, xml and os.path.dirname(__file__) + '/faceted_conf/%s' % xml or None)
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


def get_dashboard_collections(folder, uids=False):
    """ Return dashboard collections """
    brains = folder.portal_catalog(portal_type='DashboardCollection', path='/'.join(folder.getPhysicalPath()))
    if uids:
        return [b.UID for b in brains]
    return brains


def list_templates():
    """ Templates list used in add_templates method but also in update method """
    dpath = pkg_resources.resource_filename('imio.dms.mail', 'profiles/default/templates')
    # (cid, plone_path, os_path)
    return [
        (10, 'templates/d-im-listing', os.path.join(dpath, 'd-im-listing.odt')),
        (20, 'templates/all-contacts-export', os.path.join(dpath, 'contacts-export.ods')),
        (90, 'templates/om/style', os.path.join(dpath, 'om-styles.odt')),
        (100, 'templates/om/header', os.path.join(dpath, 'om-header.odt')),
        (105, 'templates/om/footer', os.path.join(dpath, 'om-footer.odt')),
        (110, 'templates/om/intro', os.path.join(dpath, 'om-intro.odt')),
        (120, 'templates/om/ending', os.path.join(dpath, 'om-ending.odt')),
        (150, 'templates/om/mailing', os.path.join(dpath, 'om-mailing.odt')),
        (200, 'templates/om/d-print', os.path.join(dpath, 'd-print.odt')),
        (205, 'templates/om/main', os.path.join(dpath, 'om-main.odt')),
#        (210, 'templates/om/common/receipt', os.path.join(dpath, 'om-receipt.odt')),
    ]


def add_templates(site):
    """Create pod templates."""
    from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES
    template_types = POD_TEMPLATE_TYPES.keys() + ['Folder', 'DashboardPODTemplate']
    for path, title, interfaces in [('templates', _(u'templates_tab'), []),
                                    ('templates/om', _(u'Outgoing mail'), [IOMTemplatesFolder]),
                                    ('templates/om/common', _(u'Common templates'), [])]:
        parts = path.split('/')
        id = parts[-1]
        parent = site.unrestrictedTraverse('/'.join(parts[:-1]))
        if not base_hasattr(parent, id):
            folderid = parent.invokeFactory("Folder", id=id, title=title)
            tplt_fld = getattr(parent, folderid)
            tplt_fld.setLocallyAllowedTypes(template_types)
            tplt_fld.setImmediatelyAddableTypes(template_types)
            tplt_fld.setConstrainTypesMode(1)
            tplt_fld.setExcludeFromNav(False)
            api.content.transition(obj=tplt_fld, transition='show_internally')
            alsoProvides(tplt_fld, IActionsPanelFolderAll)
            alsoProvides(tplt_fld, INextPrevNotNavigable)
            for itf in interfaces:
                alsoProvides(tplt_fld, itf)
            logger.info("'%s' folder created" % path)

    # adding view for Folder type
    # ptype = site.portal_types.Folder
    # if 'dg-templates-listing' not in ptype.view_methods:
    #     views = list(ptype.view_methods)
    #     views.append('dg-templates-listing')
    #     ptype.view_methods = tuple(views)
    site.templates.om.layout = 'dg-templates-listing'
    alsoProvides(site.templates.om, IBelowContentBodyBatchActionsMarker)

    def combine_data(data, test=None):
        templates_list = list_templates()
        ret = []
        for cid, ppath, ospath in templates_list:
            if not test or test(cid):
                dic = data[cid]
                dic['cid'] = cid
                parts = ppath.split('/')
                dic['id'] = parts[-1]
                dic['cont'] = '/'.join(parts[0:-1])
                if 'attrs' not in dic:
                    dic['attrs'] = {}
                dic['attrs']['odt_file'] = create_NamedBlob(ospath)
                ret.append(dic)
        return ret

    data = {
        10: {'title': _(u'Mail listing template'), 'type': 'DashboardPODTemplate', 'trans': ['show_internally'],
             'attrs': {'pod_formats': ['odt'], 'rename_page_styles': False,
                       'dashboard_collections': [b.UID for b in
                                                 get_dashboard_collections(site['incoming-mail']['mail-searches'])
                                                 if b.id == 'all_mails'],
                       # cond: check c10 reception date (display link), check output_format (generation view)
                       'tal_condition': "python:request.get('c10[]', False) or request.get('output_format', False)"}},
        20: {'title': _(u'All contacts export'), 'type': 'DashboardPODTemplate', 'trans': ['show_internally'],
             'attrs': {'pod_formats': ['ods'], 'rename_page_styles': False,
                       'dashboard_collections': [b.UID for b in
                                                 get_dashboard_collections(site['contacts']['orgs-searches'])
                                                 if b.id == 'all_orgs'],
                       'tal_condition': "python: False",
                       'roles_bypassing_talcondition': ['Manager', 'Site Administrator']}},
        90: {'title': _(u'Style template'), 'type': 'StyleTemplate', 'trans': ['show_internally']},
    }

    templates = combine_data(data, test=lambda x: x < 100)
    cids = create(templates, pos=False)
    exists = 'main' in site['templates']['om']

    data = {
        100: {'title': _(u'Header template'), 'type': 'SubTemplate', 'trans': ['show_internally'],
              'attrs': {'style_template': [cids[90].UID()]}},
        105: {'title': _(u'Footer template'), 'type': 'SubTemplate', 'trans': ['show_internally'],
              'attrs': {'style_template': [cids[90].UID()]}},
        110: {'title': _(u'Intro template'), 'type': 'SubTemplate', 'trans': ['show_internally'],
              'attrs': {'style_template': [cids[90].UID()]}},
        120: {'title': _(u'Ending template'), 'type': 'SubTemplate', 'trans': ['show_internally'],
              'attrs': {'style_template': [cids[90].UID()]}},
        150: {'title': _(u'Mailing template'), 'type': 'MailingLoopTemplate', 'trans': ['show_internally'],
              'attrs': {'style_template': [cids[90].UID()], 'rename_page_styles': True}},
    }

    templates = combine_data(data, test=lambda x: x >= 100 and x < 200)
    cids = create(templates, pos=False, cids=cids)

    data = {
        200: {'title': _(u'Print template'), 'type': 'DashboardPODTemplate', 'trans': ['show_internally'],
              'attrs': {'pod_formats': ['odt'],
                        'tal_condition': "python: context.restrictedTraverse('odm-utils').is_odt_activated()",
                        'dashboard_collections': get_dashboard_collections(site['outgoing-mail']['mail-searches'],
                                                                           uids=True),
                        'style_template': [cids[90].UID()], 'rename_page_styles': True}},
        205: {'title': _(u'Base template'), 'type': 'ConfigurablePODTemplate', 'trans': ['show_internally'],
              'attrs': {'pod_formats': ['odt'], 'pod_portal_types': ['dmsoutgoingmail'], 'merge_templates':
                        [{'pod_context_name': u'doc_entete', 'do_rendering': False, 'template': cids[100].UID()},
                         {'pod_context_name': u'doc_intro', 'do_rendering': False, 'template': cids[110].UID()},
                         {'pod_context_name': u'doc_fin', 'do_rendering': False, 'template': cids[120].UID()},
                         {'pod_context_name': u'doc_pied_page', 'do_rendering': False, 'template': cids[105].UID()}],
                        'style_template': [cids[90].UID()], 'mailing_loop_template': cids[150].UID(),
                        'rename_page_styles': False}},
#                       'context_variables': [{'name': u'do_mailing', 'value': u'1'}]}},
        210: {'title': _(u'Receipt template'), 'type': 'ConfigurablePODTemplate', 'trans': ['show_internally'],
              'attrs': {'pod_formats': ['odt'], 'pod_portal_types': ['dmsoutgoingmail'], 'merge_templates':
                        [{'pod_context_name': u'doc_entete', 'do_rendering': False, 'template': cids[100].UID()},
                         {'pod_context_name': u'doc_intro', 'do_rendering': False, 'template': cids[110].UID()},
                         {'pod_context_name': u'doc_fin', 'do_rendering': False, 'template': cids[120].UID()},
                         {'pod_context_name': u'doc_pied_page', 'do_rendering': False, 'template': cids[105].UID()}],
                        'style_template': [cids[90].UID()], 'mailing_loop_template': cids[150].UID(),
                        'context_variables': [{'name': u'PD', 'value': u'True'},
                                              {'name': u'PC', 'value': u'True'},
                                              {'name': u'PVS', 'value': u'False'}],
                        'rename_page_styles': False}},
    }

    templates = combine_data(data, test=lambda x: x >= 200)
    cids = create(templates, pos=False, cids=cids)

    if not exists:
        site['templates']['om'].moveObjectToPosition('d-print', 1)
        site['templates']['om'].moveObjectToPosition('main', 10)
        site['templates']['om'].moveObjectToPosition('common', 11)


def add_transforms(site):
    """
        Add some transforms
    """
    pt = site.portal_transforms
    for name, module in (('pdf_to_text', 'Products.PortalTransforms.transforms.pdf_to_text'),
                         ('pdf_to_html', 'Products.PortalTransforms.transforms.pdf_to_html'),
                         ('odt_to_text', 'imio.dms.mail.transforms')):
        if name not in pt.objectIds():
            pt.manage_addTransform(name, module)
            logger.info("Added '%s' transform" % name)


def add_oem_templates(site):
    """Create email templates."""
    folder_id = 'oem'
    if folder_id not in site.templates:
        site.templates.invokeFactory("Folder", id=folder_id, title=_('Outgoing email'))
        tplt_fld = site.templates[folder_id]
        tplt_fld.setLocallyAllowedTypes(['Folder', 'cktemplate'])
        tplt_fld.setImmediatelyAddableTypes(['Folder', 'cktemplate'])
        tplt_fld.setConstrainTypesMode(1)
        tplt_fld.setExcludeFromNav(False)
        api.content.transition(obj=tplt_fld, transition='show_internally')
        alsoProvides(tplt_fld, IActionsPanelFolderAll)
        alsoProvides(tplt_fld, INextPrevNotNavigable)
        for itf in []:
            alsoProvides(tplt_fld, itf)
        logger.info("'templates/{}' folder created".format(folder_id))
    site.templates.moveObjectToPosition(folder_id, 1)
    site.templates.oem.layout = 'ck-templates-listing'
    alsoProvides(site.templates.oem, IOMCKTemplatesFolder)

    templates = [
        {'cid': 10, 'cont': 'templates/oem', 'type': 'cktemplate', 'id': 'emain', 'title': _(u'Email general template'),
         'trans': ['show_internally'],
         'attrs': {'content': richtextval(u'<p>Bonjour,</p><p>en réponse à votre email, vous trouverez ci-dessous les '
                                          u'infos demandées.</p><p>Cordialement</p><p>&nbsp;</p><p>Administration '
                                          u'communale</p><p>...</p>')}},
    ]
    create(templates, pos=False)


def set_portlet(portal):
    ann = IAnnotations(portal)
    portlet = ann['plone.portlets.contextassignments']['plone.leftcolumn']['portlet_actions']
    portlet.ptitle = u'Liens divers'
    portlet.category = u'object_portlet'
    portlet.show_icons = False
    portlet.default_icon = None
    portlet._p_changed = True


def update_task_workflow(portal):
    """ remove back_in_to_assign transition in task workflow """
    wf = portal.portal_workflow['task_workflow']
    if 'back_in_created2' not in wf.transitions:
        wf.transitions.addTransition('back_in_created2')
        wf.transitions['back_in_created2'].setProperties(
            title='back_in_created',
            new_state_id='created', trigger_type=1, script_name='',
            actbox_name='back_in_created2', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++collective.task/back_in_created.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Request review'})
    # modify to_do transitions
    state = wf.states['to_do']
    transitions = list(state.transitions)  # noqa
    if 'back_in_to_assign' in transitions:
        transitions.remove('back_in_to_assign')
        transitions.append('back_in_created2')
        state.transitions = tuple(transitions)
