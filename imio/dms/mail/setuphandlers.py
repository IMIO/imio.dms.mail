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

import datetime
import logging
import os
from itertools import cycle
from Products.CMFPlone.utils import base_hasattr
from zope.component import queryUtility, getMultiAdapter, getUtility
from zope.component.hooks import getSite
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobFile
#from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry
from collective.contact.facetednav.interfaces import IActionsEnabled
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY, ORGANIZATIONS_REGISTRY
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue, receptionDateDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue, mailDateDefaultValue
from dexterity.localroles.utils import add_fti_configuration
from eea.facetednavigation.settings.interfaces import IDisableSmartFacets
from eea.facetednavigation.settings.interfaces import IHidePloneLeftColumn
from eea.facetednavigation.settings.interfaces import IHidePloneRightColumn
from imio.helpers.security import get_environment, generate_password
from imio.dashboard.utils import enableFacetedDashboardFor, _updateDefaultCollectionFor
from imio.dms.mail.interfaces import IDirectoryFacetedNavigable
from imio.dms.mail.subscribers import mark_organization
from imio.dms.mail.utils import list_wf_states


logger = logging.getLogger('imio.dms.mail: setuphandlers')


def _(msgid, domain='imio.dms.mail'):
    translation_domain = queryUtility(ITranslationDomain, domain)
    return translation_domain.translate(msgid, context=getSite().REQUEST, target_language='fr')


def mark_organizations(portal):
    """Mark each contact content as internal or external."""
    for brain in portal.portal_catalog.searchResults(
            object_provides=['collective.contact.widget.interfaces.IContactContent']):
        mark_organization(brain.getObject(), None)


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

    def create_collections_folder(folder):
        if not base_hasattr(folder, 'collections'):
            folder.invokeFactory("Folder", id='collections', title=u"Collections: ne pas effacer")

        col_folder = folder['collections']
        col_folder.setConstrainTypesMode(1)
        col_folder.setLocallyAllowedTypes(['DashboardCollection'])
        col_folder.setImmediatelyAddableTypes(['DashboardCollection'])
        return col_folder

    # we create the basic folders
    if not base_hasattr(site, 'incoming-mail'):
        folderid = site.invokeFactory("Folder", id='incoming-mail', title=_(u"Incoming mail"))
        im_folder = getattr(site, folderid)

        # configure faceted navigation
        configure_incoming_mail_folder(im_folder)

        col_folder = create_collections_folder(im_folder)
        #blacklistPortletCategory(context, im_folder, CONTEXT_CATEGORY, u"plone.leftcolumn")
        createIMCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')
        # select default collection
        _updateDefaultCollectionFor(im_folder, col_folder['all_mails'].UID())
        im_folder.setConstrainTypesMode(1)
        im_folder.setLocallyAllowedTypes(['dmsincomingmail'])
        im_folder.setImmediatelyAddableTypes(['dmsincomingmail'])
        site.portal_workflow.doActionFor(im_folder, "show_internally")
        logger.info('incoming-mail folder created')

    if not base_hasattr(site, 'outgoing-mail'):
        folderid = site.invokeFactory("Folder", id='outgoing-mail', title=_(u"Outgoing mail"))
        om_folder = getattr(site, folderid)
        col_folder = create_collections_folder(om_folder)
        #blacklistPortletCategory(context, om_folder, CONTEXT_CATEGORY, u"plone.leftcolumn")
        om_folder.setConstrainTypesMode(1)
        om_folder.setLocallyAllowedTypes(['dmsoutgoingmail'])
        om_folder.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        logger.info('outgoing-mail folder created')

    # enable portal diff on incoming mail
    api.portal.get_tool('portal_diff').setDiffForPortalType(
        'dmsincomingmail', {'any': "Compound Diff for Dexterity types"})

    # reimport collective.contact.widget's registry step (disable jQueryUI's autocomplete)
    site.portal_setup.runImportStepFromProfile(
        'profile-collective.contact.widget:default',
        'plone.app.registry')

    configure_actions_panel(site)


def blacklistPortletCategory(context, object, category, utilityname):
    """
        block portlets on object for the corresponding category
    """
    from plone.portlets.interfaces import IPortletManager, ILocalPortletAssignmentManager
    # Get the proper portlet manager
    manager = queryUtility(IPortletManager, name=utilityname)
    # Get the current blacklist for the location
    blacklist = getMultiAdapter((object, manager), ILocalPortletAssignmentManager)
    # Turn off the manager
    blacklist.setBlacklistStatus(category, True)


def createStateCollections(folder, content_type):
    """
        create a collection for each contextual workflow state
    """
    conditions = {'dmsincomingmail': {
        'created': "python: object.restrictedTraverse('idm-utils').created_col_cond()",
        'proposed_to_manager': "python: object.restrictedTraverse('idm-utils').proposed_to_manager_col_cond()",
        'proposed_to_service_chief': "python: object.restrictedTraverse('idm-utils').proposed_to_serv_chief_col_cond()",
    }
    }
    for state in list_wf_states(folder, content_type):
        col_id = "searchfor_%s" % state
        if not base_hasattr(folder, col_id):
            folder.invokeFactory("DashboardCollection", id=col_id, title=_(col_id),
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [content_type]},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [state]}],
                                 customViewFields=(u'pretty_link', u'review_state', u'treating_groups',
                                                   u'assigned_user', u'CreationDate', u'actions'),
                                 tal_condition=conditions[content_type].get(state),
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'created', sort_reversed=True, b_size=30)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.portal_workflow.doActionFor(col, "show_internally")


def createIMCollections(folder):
    """
        create some topic for incoming mails
    """
    collections = [
        {'id': 'all_mails', 'tit': _('all_incoming_mails'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'to_validate', 'tit': _('im_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-highest-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsincomingmail')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'to_treat', 'tit': _('im_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['proposed_to_agent']}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'im_treating', 'tit': _('im_im_treating'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['in_treatment']}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'have_treated', 'tit': _('im_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['closed']}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'in_my_group', 'tit': _('im_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
        {'id': 'in_copy', 'tit': _('im_in_copy'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-copy-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                     u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, },
    ]

    for dic in collections:
        if base_hasattr(folder, dic['id']):
            continue

        folder.invokeFactory("DashboardCollection",
                             dic['id'],
                             title=dic['tit'],
                             query=dic['query'],
                             tal_condition=dic['cond'],
                             roles_bypassing_talcondition=dic['bypass'],
                             customViewFields=dic['flds'],
                             sort_on=dic['sort'],
                             sort_reversed=dic['rev'],
                             b_size=30)
        collection = folder[dic['id']]
        folder.portal_workflow.doActionFor(collection, "show_internally")
        if 'subj' in dic:
            collection.setSubject(dic['subj'])
            collection.reindexObject(['Subject'])
        collection.setLayout('tabular_view')


def adaptDefaultPortal(context):
    """
       Adapt some properties of the portal
    """
    site = context.getSite()

    #deactivate tabs auto generation in navtree_properties
    #site.portal_properties.site_properties.disable_folder_sections = True
    #remove default created objects like events, news, ...
    for id in ('events', 'news', 'Members'):
        try:
            site.manage_delObjects(ids=[id, ])
            logger.info('%s folder deleted' % id)
        except AttributeError:
            continue

    #change the content of the front-page
    try:
        frontpage = getattr(site, 'front-page')
        if not base_hasattr(site, 'incoming-mail'):
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')
            #remove the presentation mode
            frontpage.setPresentation(False)
            site.portal_workflow.doActionFor(frontpage, "show_internally")
            frontpage.reindexObject()
            logger.info('front page adapted')
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


def changeSearchedTypes(site):
    """
        Change searched types
    """
    to_show = ['dmsmainfile']
    to_hide = ['Collection', 'Document', 'Event', 'File', 'Folder', 'Image', 'Link', 'News Item', 'Topic', 'directory',
               'dmsdocument']
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
        Configure the rolefields on types
    """
    roles_config = {'localroleconfig': {
        'created': {'encodeurs': ['Contributor', 'Editor', 'IM Field Writer']},
        'proposed_to_manager': {'dir_general': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer'],
                                'encodeurs': ['Reader', 'IM Field Writer']},
        'proposed_to_service_chief': {'dir_general': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer'],
                                      'encodeurs': ['Reader']},
        'proposed_to_agent': {'dir_general': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer'],
                              'encodeurs': ['Reader']},
        'in_treatment': {'dir_general': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer'],
                         'encodeurs': ['Reader']},
        'closed': {'dir_general': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer'],
                   'encodeurs': ['Reader']},
    }, 'treating_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': ['Contributor', 'Editor', 'Reviewer']},
        'proposed_to_agent': {'validateur': ['Contributor', 'Editor', 'Reviewer'],
                              'editeur': ['Contributor', 'Editor', 'Reviewer'],
                              'lecteur': ['Reader']},
        'in_treatment': {'validateur': ['Contributor', 'Editor', 'Reviewer'],
                         'editeur': ['Contributor', 'Editor', 'Reviewer'],
                         'lecteur': ['Reader']},
        'closed': {'validateur': ['Reviewer'],
                   'editeur': ['Reviewer'],
                   'lecteur': ['Reader']},
    }, 'recipient_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': ['Reader']},
        'proposed_to_agent': {'validateur': ['Reader'],
                              'editeur': ['Reader'],
                              'lecteur': ['Reader']},
        'in_treatment': {'validateur': ['Reader'],
                         'editeur': ['Reader'],
                         'lecteur': ['Reader']},
        'closed': {'validateur': ['Reader'],
                   'editeur': ['Reader'],
                   'lecteur': ['Reader']},
    },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration('dmsincomingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)


def configure_task_rolefields(context):
    """
        Configure the rolefields on task
    """
    roles_config = {
        'localroleconfig': {
        },
        'assigned_group': {
            'to_assign': {
                'validateur': ['Editor', 'Reviewer'],
            },
            'to_do': {
                'editeur': ['Editor'],
                'validateur': ['Editor', 'Reviewer'],
            },
            'in_progress': {
                'editeur': ['Editor'],
                'validateur': ['Editor', 'Reviewer'],
            },
            'realized': {
                'editeur': ['Editor'],
                'validateur': ['Editor', 'Reviewer'],
            },
            'closed': {
                'validateur': ['Editor', 'Reviewer'],
            },
        },
        'assigned_user': {
        },
    }
    for keyname in roles_config:
        # we overwrite existing configuration from task installation !
        msg = add_fti_configuration('task', roles_config[keyname], keyname=keyname, force=True)
        if msg:
            logger.warn(msg)


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
            [{'code': u'in', 'portal_type': u'dmsincomingmail'}]


def configureImioDmsMail(context):
    """
        Add french test imio dms mail configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info('Configure imio dms mail')
    registry = getUtility(IRegistry)

    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'] = [
            {'mt_value': u'courrier', 'mt_title': u'Courrier', 'mt_active': True},
            {'mt_value': u'recommande', 'mt_title': u'Recommandé', 'mt_active': True},
            {'mt_value': u'email', 'mt_title': u'E-mail', 'mt_active': True},
            {'mt_value': u'fax', 'mt_title': u'Fax', 'mt_active': True},
            {'mt_value': u'retour-recommande', 'mt_title': u'Retour recommandé', 'mt_active': True},
            {'mt_value': u'facture', 'mt_title': u'Facture', 'mt_active': True},
        ]
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
    registry = getUtility(IRegistry)
    site = context.getSite()
    if not registry.get(FUNCTIONS_REGISTRY):
        registry[FUNCTIONS_REGISTRY] = [
            {'fct_title': u'Encodeur', 'fct_id': u'encodeur'},
            {'fct_title': u'Lecteur', 'fct_id': u'lecteur'},
            {'fct_title': u'Éditeur', 'fct_id': u'editeur'},
            {'fct_title': u'Validateur', 'fct_id': u'validateur'},
        ]
    if not registry.get(ORGANIZATIONS_REGISTRY):
        contacts = site['contacts']
        own_orga = contacts['plonegroup-organization']
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        services0 = own_orga[departments[0].id].listFolderContents(contentFilter={'portal_type': 'organization'})
        services2 = own_orga[departments[2].id].listFolderContents(contentFilter={'portal_type': 'organization'})
        registry[ORGANIZATIONS_REGISTRY] = [
            services0[0].UID(),
            services0[1].UID(),
            departments[1].UID(),
            services2[0].UID(),
        ]
        # Add users to created groups
        site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_validateur" % services0[0].UID())
        site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_editeur" % services0[0].UID())
        site.acl_users.source_groups.addPrincipalToGroup('lecteur', "%s_lecteur" % services0[0].UID())


def addTestDirectory(context):
    """
        Add french test data: directory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding test directory')
    if base_hasattr(site, 'contacts'):
        logger.warn('Nothing done: directory contacts already exists. You must first delete it to reimport!')
        return

    # Directory creation
    position_types = [{'name': u'Président', 'token': 'president'},
                      {'name': u'Directeur général', 'token': 'directeur-gen'},
                      {'name': u'Directeur financier', 'token': 'directeur-fin'},
                      {'name': u'Secrétaire', 'token': 'secretaire'},
                      {'name': u'Employé', 'token': 'employe'},
                      ]

    organization_types = [{'name': u'Commune', 'token': 'commune'},
                          {'name': u'CPAS', 'token': 'cpas'},
                          {'name': u'SA', 'token': 'sa'},
                          ]

    organization_levels = [{'name': u'Département', 'token': 'department'},
                           {'name': u'Service', 'token': 'service'},
                           ]

    params = {'title': "Contacts",
              'position_types': position_types,
              'organization_types': organization_types,
              'organization_levels': organization_levels,
              }
    site.invokeFactory('directory', 'contacts', **params)
    contacts = site['contacts']
    site.portal_workflow.doActionFor(contacts, "show_internally")
    #blacklistPortletCategory(context, contacts, CONTEXT_CATEGORY, u"plone.leftcolumn")

    # create plonegroup-organization
    addOwnOrganization(context)

    # Add not encoded person (in directory)
    contacts.invokeFactory('person', 'notencoded', lastname=u'Non encodé')

    # Organisations creation (in directory)
    params = {'title': u"Electrabel",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de la l'électron",
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'electrabel', **params)
    electrabel = contacts['electrabel']

    params = {'title': u"SWDE",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'eau vive",
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'swde', **params)
    swde = contacts['swde']

    # Positions creation (in organisations)
    params = {'title': u"Agent",
              'position_type': u'employe',
              }
    electrabel.invokeFactory('position', 'agent', **params)

    params = {'title': u"Agent",
              'position_type': u'employe',
              }
    swde.invokeFactory('position', 'agent', **params)

    # Persons creation (in directory)
    params = {'lastname': u'Courant',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1981, 11, 22),
              'email': u'jean.courant@electrabel.be',
              'phone': u'012/345.678',
              }
    contacts.invokeFactory('person', 'jeancourant', **params)
    jeancourant = contacts['jeancourant']

    params = {'lastname': u'Robinet',
              'firstname': u'Serge',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1981, 11, 22),
              'email': u'serge.robinet@swde.be',
              'phone': u'012/345.678',
              }
    contacts.invokeFactory('person', 'sergerobinet', **params)
    sergerobinet = contacts['sergerobinet']

    params = {'lastname': u'Lermitte',
              'firstname': u'Bernard',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1981, 11, 22),
              'email': u'bernard.lermitte@swde.be',
              'phone': u'012/345.678',
              }
    contacts.invokeFactory('person', 'bernardlermitte', **params)
    bernardlermitte = contacts['bernardlermitte']

    # Held positions creation (in persons)
    intids = getUtility(IIntIds)

    # link to a defined position
    aswde = swde['agent']
    params = {'start_date': datetime.date(2001, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(aswde)),
              }
    sergerobinet.invokeFactory('held_position', 'agent-swde', **params)
    bernardlermitte.invokeFactory('held_position', 'agent-swde', **params)

    # link to an organisation
    aelec = electrabel['agent']
    params = {'start_date': datetime.date(2005, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(aelec)),
              }
    jeancourant.invokeFactory('held_position', 'agent-electrabel', **params)

    # we configure faceted navigations for contacts
    alsoProvides(contacts, IDirectoryFacetedNavigable)
    setupFacetedContacts(site)

    # set marker interfaces on organizations
    mark_organizations(site)


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

    class dummy(object):
        def __init__(self, context, request):
            self.context = context
            self.request = request

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
    # incoming mails
    ifld = site['incoming-mail']
    data = dummy(site, site.REQUEST)
    for i in range(1, 10):
        if not 'courrier%d' % i in ifld:
            params = {'title': 'Courrier %d' % i,
                      'mail_type': 'courrier',
                      'internal_reference_no': internalReferenceIncomingMailDefaultValue(data),
                      'reception_date': receptionDateDefaultValue(data),
                      'sender': RelationValue(senders_cycle.next()),
                      'recipient_groups': [],
                      'description': 'Ceci est la description du courrier %d' % i,
                      }
            ifld.invokeFactory('dmsincomingmail', id='courrier%d' % i, **params)
            mail = ifld['courrier%d' % i]
            filename = files_cycle.next()
            with open("%s/%s" % (filespath, filename), 'rb') as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, 'dmsmainfile', title='', file=file_object)

    senders_cycle = cycle(senders)
    # outgoing mails
    ofld = site['outgoing-mail']
    for i in range(1, 10):
        if not 'reponse%d' % i in ofld:
            params = {'title': 'Réponse %d' % i,
                      'internal_reference_no': internalReferenceOutgoingMailDefaultValue(data),
                      'mail_date': mailDateDefaultValue(data),
                      #temporary in comment because it doesn't pass in test and case probably errors when deleting site
                      #'in_reply_to': [RelationValue(intids.getId(inmail))],
                      'recipients': [RelationValue(senders_cycle.next())],
                      }
            ofld.invokeFactory('dmsoutgoingmail', id='reponse%d' % i, **params)


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
        ('lecteur', u'Jef Lecteur'): [],
    }
    password = 'Dmsmail69!'
    if get_environment() == 'prod':
#        password = site.portal_registration.generatePassword()
        password = generate_password()
    logger.info("Generated password='%s'" % password)

    for uid, fullname in users.keys():
        try:
            member = site.portal_registration.addMember(id=uid, password=password,
                                                        roles=['Member'] + users[(uid, fullname)])
            member.setMemberProperties({'fullname': fullname, 'email': 'test@macommune.be'})
        except ValueError, exc:
            if str(exc).startswith('The login name you selected is already in use'):
                continue
            logger("Error creating user '%s': %s" % (uid, exc))

    if api.group.get('encodeurs') is None:
        api.group.create('encodeurs', '1 Encodeurs courrier')
        site['incoming-mail'].manage_addLocalRoles('encodeurs', ['Contributor', 'Reader'])
        site['contacts'].manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
#        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname='encodeurs', username='scanner')
        api.group.add_user(groupname='encodeurs', username='encodeur')
    if api.group.get('dir_general') is None:
        api.group.create('dir_general', '1 Directeur général')
        api.group.add_user(groupname='dir_general', username='dirg')


def addOwnOrganization(context):
    """
        Add french test data: own organization
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
              }
    contacts.invokeFactory('organization', 'plonegroup-organization', **params)
    own_orga = contacts['plonegroup-organization']

    # Departments and services creation
    sublevels = [
        (u'Département Jeunesse', [u'Cité de l\'Enfance', u'AMO Ancrages', u'MCAE Cité P\'tit',
                                    u'MCAE Bébé Lune', u'Crèche de Mons ', u'Crèche de Jemappes',
                                    u'Crèche Nid Douillet', u'SAEC']),
        (u'Département Égalité des chances', []),
        (u'Département GRH', [u'Personnel', u'Traitements']),
        (u'Département du Patrimoine', [u'Technique', u'Technique administratif', u'Patrimoine']),
        (u'Département du DG', [u'Cabinet du DG', u'Cellule Marchés Publics', u'IPP', u'FRCE']),
        (u'Département du Président', [u'Cabinet du Président']),
        (u'Département des Aînés', [u'BMB', u'MRS Havré', u'Acasa']),
        (u'Département Social', [u'Aide générale', u'Service personnes âgées', u'Service social administratif', u'SIP',
                                  u'Guidance / Médiation', u'VIF', u'Logement', u'EFT', u'Service juridique']),
        (u'Département informatique', []),
        (u'Département des Finances', [u'Gestion Financière', u'Cellule Financière', u'Directeur financier',
                                        u'Homes Extérieurs', u'Avances et Récupérations', u'Assurances']),
    ]
    idnormalizer = queryUtility(IIDNormalizer)
    for (department, services) in sublevels:
        id = own_orga.invokeFactory('organization', idnormalizer.normalize(department),
                                    **{'title': department, 'organization_type': u'department'})
        dep = own_orga[id]
        for service in services:
            dep.invokeFactory('organization', idnormalizer.normalize(service),
                              **{'title': service, 'organization_type': u'service'})


def configureDocumentViewer(context):
    """
        Set the settings of document viewer product
    """
    from collective.documentviewer.settings import GlobalSettings
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
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


def reimport_faceted_config(portal):
    """Reimport faceted navigation config."""
    portal['contacts'].unrestrictedTraverse('@@faceted_exportimport').import_xml(
        import_file=open(os.path.dirname(__file__) + '/faceted_conf/contacts-faceted.xml'))


def setupFacetedContacts(portal):
    """Setup facetednav for contacts."""
    alsoProvides(portal.contacts, IDirectoryFacetedNavigable)
    alsoProvides(portal.contacts, IActionsEnabled)
    alsoProvides(portal.contacts, IDisableSmartFacets)
    # hide portlets columns in contacts
    alsoProvides(portal.contacts, IHidePloneLeftColumn)
    alsoProvides(portal.contacts, IHidePloneRightColumn)
    reimport_faceted_config(portal)


def configure_actions_panel(portal):
    """
        Configure actions panel registry
    """
    logger.info('Configure actions panel registry')
    registry = getUtility(IRegistry)

    if not registry.get('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'):
        registry['imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'] = \
            ['dmsincomingmail.back_to_creation|', 'dmsincomingmail.back_to_manager|',
             'dmsincomingmail.back_to_service_chief|', 'dmsincomingmail.back_to_treatment|',
             'dmsincomingmail.back_to_agent|']


def configure_incoming_mail_folder(im_folder):
    """Configure faceted navigation for incoming-mail folder."""
    enableFacetedDashboardFor(im_folder, os.path.dirname(__file__) + '/faceted_conf/im-faceted.xml')
