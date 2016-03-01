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
import pkg_resources
from itertools import cycle
from zope.component import queryUtility, getMultiAdapter, getUtility
from zope.component.hooks import getSite
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue

from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.app.controlpanel.markup import MarkupControlPanelAdapter
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobFile
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry

from Products.CPUtils.Extensions.utils import configure_ckeditor
from collective.contact.facetednav.interfaces import IActionsEnabled
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY, ORGANIZATIONS_REGISTRY
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue, receptionDateDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue, mailDateDefaultValue
from collective.documentgenerator.config import POD_TEMPLATE_TYPES
from collective.querynextprev.interfaces import INextPrevNotNavigable
from dexterity.localroles.utils import add_fti_configuration
from eea.facetednavigation.settings.interfaces import IDisableSmartFacets
from eea.facetednavigation.settings.interfaces import IHidePloneLeftColumn
from eea.facetednavigation.settings.interfaces import IHidePloneRightColumn
from imio.helpers.security import get_environment, generate_password
from imio.dashboard.utils import enableFacetedDashboardFor, _updateDefaultCollectionFor
from imio.dms.mail.interfaces import IIMDashboard, IIMTaskDashboard

from interfaces import IDirectoryFacetedNavigable
from utils import list_wf_states

logger = logging.getLogger('imio.dms.mail: setuphandlers')


def _(msgid, domain='imio.dms.mail'):
    translation_domain = queryUtility(ITranslationDomain, domain)
    return translation_domain.translate(msgid, context=getSite().REQUEST, target_language='fr')


def add_db_col_folder(folder, id, title, displayed=''):
    if base_hasattr(folder, id):
        return folder[id]

    folder.invokeFactory('Folder', id=id, title=title, rights=displayed)
    col_folder = folder[id]
    col_folder.setConstrainTypesMode(1)
    col_folder.setLocallyAllowedTypes(['DashboardCollection'])
    col_folder.setImmediatelyAddableTypes(['DashboardCollection'])
    folder.portal_workflow.doActionFor(col_folder, "show_internally")
    return col_folder


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
    if (base_hasattr(site.portal_types.task, 'localroles') and
            site.portal_types.task.localroles.get('assigned_group', '') and
            site.portal_types.task.localroles['assigned_group'].get('created') and
            '' in site.portal_types.task.localroles['assigned_group']['created']):
        configure_task_rolefields(context, force=True)
    else:
        configure_task_rolefields(context, force=False)

    # we create the basic folders
    if not base_hasattr(site, 'incoming-mail'):
        folderid = site.invokeFactory("Folder", id='incoming-mail', title=_(u"Incoming mail"))
        im_folder = getattr(site, folderid)
        alsoProvides(im_folder, INextPrevNotNavigable)

        # add mail-searches
        col_folder = add_db_col_folder(im_folder, 'mail-searches', _("Incoming mail searches"),
                                       _('Incoming mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IIMDashboard)

        # blacklistPortletCategory(context, im_folder)
        createIMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')
        configure_faceted_folder(col_folder, xml='im-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        # configure incoming-mail faceted
        configure_faceted_folder(im_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())

        # add task-searches
        col_folder = add_db_col_folder(im_folder, 'task-searches', _("Tasks searches"),
                                       _("I.M. tasks"))
        alsoProvides(col_folder, IIMTaskDashboard)
        createIMTaskCollections(col_folder)
        createStateCollections(col_folder, 'task')
        configure_faceted_folder(col_folder, xml='im-task-searches.xml',
                                 default_UID=col_folder['all_tasks'].UID())

        im_folder.setConstrainTypesMode(1)
        im_folder.setLocallyAllowedTypes(['dmsincomingmail'])
        im_folder.setImmediatelyAddableTypes(['dmsincomingmail'])
        site.portal_workflow.doActionFor(im_folder, "show_internally")
        logger.info('incoming-mail folder created')

    if not base_hasattr(site, 'outgoing-mail'):
        folderid = site.invokeFactory("Folder", id='outgoing-mail', title=_(u"Outgoing mail"))
        om_folder = getattr(site, folderid)
        # col_folder = add_db_col_folder(om_folder)
        # blacklistPortletCategory(context, om_folder)
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

    configure_ckeditor(site, custom='ged')

    add_test_models(site)


def blacklistPortletCategory(context, obj, category=CONTEXT_CATEGORY, utilityname=u"plone.leftcolumn", value=True):
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
        'dmsincomingmail': {
        'created': "python: object.restrictedTraverse('idm-utils').created_col_cond()",
        'proposed_to_manager': "python: object.restrictedTraverse('idm-utils').proposed_to_manager_col_cond()",
        'proposed_to_service_chief': "python: object.restrictedTraverse('idm-utils').proposed_to_serv_chief_col_cond()",
        },
        'task': {}
    }
    view_fields = {
        'dmsincomingmail': (u'select_row', u'pretty_link', u'review_state', u'treating_groups',
                            u'assigned_user', u'due_date', u'mail_type', u'sender', u'CreationDate', u'actions'),
        'task': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group', u'assigned_user',
                 u'due_date', u'CreationDate', u'actions'),
    }
    showNumberOfItems = {
        'dmsincomingmail': ('created',),
    }
    for state in list_wf_states(folder, content_type):
        col_id = "searchfor_%s" % state
        if not base_hasattr(folder, col_id):
            folder.invokeFactory("DashboardCollection", id=col_id, title=_(col_id),
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [content_type]},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [state]}],
                                 customViewFields=view_fields[content_type],
                                 tal_condition=conditions[content_type].get(state),
                                 showNumberOfItems=(state in showNumberOfItems.get(content_type, [])),
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'created', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.portal_workflow.doActionFor(col, "show_internally")


def createDashboardCollections(folder, collections):
    """
        create some dashboard collections in searches folder
    """
    for i, dic in enumerate(collections):
        if not base_hasattr(folder, dic['id']):
            folder.invokeFactory("DashboardCollection",
                                 dic['id'],
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
            folder.portal_workflow.doActionFor(collection, "show_internally")
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
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_validate', 'tit': _('im_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-highest-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsincomingmail')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'to_treat', 'tit': _('im_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['proposed_to_agent']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'im_treating', 'tit': _('im_im_treating'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['in_treatment']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'have_treated', 'tit': _('im_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['closed']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_my_group', 'tit': _('im_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_copy', 'tit': _('im_in_copy'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-copy-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
    ]
    createDashboardCollections(folder, collections)


def createIMTaskCollections(folder):
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
        {'id': 'to_validate', 'tit': _('tasks_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-highest-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
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
        {'id': 'in_my_group', 'tit': _('tasks_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['task']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'task-in-assigned-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'task_parent', u'review_state', u'assigned_group',
                     u'assigned_user', u'due_date', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
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
    #History: can revert to previous versions
    site.manage_permission('CMFEditions: Revert to previous versions', ('Manager', 'Site Administrator'),
                           acquire=0)

    # Set markup allowed types: for RichText field, don't display anymore types listbox
    adapter = MarkupControlPanelAdapter(site)
    adapter.set_allowed_types(['text/html'])


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
    roles_config = {'static_config': {
        'created': {'encodeurs': {'roles': ['Contributor', 'Editor', 'IM Field Writer', 'IM Treating Group Writer']}},
        'proposed_to_manager': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer',
                                                'IM Treating Group Writer']},
                                'encodeurs': {'roles': ['Reader']}},
        'proposed_to_service_chief': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer',
                                                      'IM Treating Group Writer']},
                                      'encodeurs': {'roles': ['Reader']}},
        'proposed_to_agent': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer',
                                              'IM Treating Group Writer']},
                              'encodeurs': {'roles': ['Reader']}},
        'in_treatment': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer',
                                         'IM Treating Group Writer']},
                         'encodeurs': {'roles': ['Reader']}},
        'closed': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer',
                                             'IM Treating Group Writer']},
                   'encodeurs': {'roles': ['Reader']}},
    }, 'treating_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer',
                                                               'IM Treating Group Writer']}},
        'proposed_to_agent': {'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                              'editeur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                              'lecteur': {'roles': ['Reader']}},
        'in_treatment': {'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                         'editeur': {'roles': ['Contributor', 'Editor', 'Reviewer']},
                         'lecteur': {'roles': ['Reader']}},
        'closed': {'validateur': {'roles': ['Reviewer']},
                   'editeur': {'roles': ['Reviewer']},
                   'lecteur': {'roles': ['Reader']}},
    }, 'recipient_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': {'roles': ['Reader']}},
        'proposed_to_agent': {'validateur': {'roles': ['Reader']},
                              'editeur': {'roles': ['Reader']},
                              'lecteur': {'roles': ['Reader']}},
        'in_treatment': {'validateur': {'roles': ['Reader']},
                         'editeur': {'roles': ['Reader']},
                         'lecteur': {'roles': ['Reader']}},
        'closed': {'validateur': {'roles': ['Reader']},
                   'editeur': {'roles': ['Reader']},
                   'lecteur': {'roles': ['Reader']}},
    },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration('dmsincomingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)


def configure_task_rolefields(context, force=False):
    """
        Configure the rolefields on task
    """
    roles_config = {
        'static_config': {
        },
        'assigned_group': {
            'to_assign': {
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
            'to_do': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
            'in_progress': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
            'realized': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
            'closed': {
                'editeur': {'roles': ['Reader'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
        },
        'assigned_user': {
        },
    }
    for keyname in roles_config:
        # we overwrite existing configuration from task installation !
        msg = add_fti_configuration('task', roles_config[keyname], keyname=keyname, force=force)
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
        (u'Direction générale', (u'Secrétariat', u'GRH', u'Informatique', u'Communication')),
        (u'Direction financière', (u'Budgets', u'Comptabilité', u'Taxes', u'Marchés publics')),
        (u'Direction technique', (u'Bâtiments', u'Voiries', u'Urbanisme')),
        (u'Département population', (u'Population', u'État-civil')),
        (u'Département culturel', (u'Enseignement', u'Culture-loisirs')),
        (u'Collège communal', [])
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        dep0 = departments[0]
        dep1 = departments[1]
        services0 = dep0.listFolderContents(contentFilter={'portal_type': 'organization'})
        services1 = dep1.listFolderContents(contentFilter={'portal_type': 'organization'})
        orgas = [dep0, services0[0], services0[1], dep1, services1[0], services1[1]]
        registry[ORGANIZATIONS_REGISTRY] = [org.UID() for org in orgas]

        # Add users to created groups
        for org in orgas:
            uid = org.UID()
            site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_validateur" % uid)
            if org.organization_type == 'service':
                site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_editeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup('lecteur', "%s_lecteur" % uid)


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

    organization_types = [{'name': u'Non défini', 'token': 'non-defini'},
                          {'name': u'Commune', 'token': 'commune'},
                          {'name': u'CPAS', 'token': 'cpas'},
                          {'name': u'SA', 'token': 'sa'},
                          ]

    organization_levels = [{'name': u'Non défini', 'token': 'non-defini'},
                           {'name': u'Département', 'token': 'department'},
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
    blacklistPortletCategory(context, contacts)

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

    registry = getUtility(IRegistry)
    orgas_cycle = cycle(registry[ORGANIZATIONS_REGISTRY])

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
                      'treating_groups': orgas_cycle.next(),
                      'recipient_groups': [],
                      'description': 'Ceci est la description du courrier %d' % i,
                      }
            ifld.invokeFactory('dmsincomingmail', id='courrier%d' % i, **params)
            mail = ifld['courrier%d' % i]
            filename = files_cycle.next()
            with open("%s/%s" % (filespath, filename), 'rb') as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, 'dmsmainfile', title='', file=file_object)

    # tasks
    mail = ifld['courrier1']
    mail.invokeFactory('task', id='tache1', title=u'Tâche 1', assigned_group=mail.treating_groups)
    mail.invokeFactory('task', id='tache2', title=u'Tâche 2', assigned_group=mail.treating_groups)
    mail.invokeFactory('task', id='tache3', title=u'Tâche autre service', assigned_group=orgas_cycle.next())
    task3 = mail['tache3']
    task3.invokeFactory('task', id='tache3-1', title=u'Sous-tâche 1', assigned_group=task3.assigned_group)
    task3.invokeFactory('task', id='tache3-2', title=u'Sous-tâche 2', assigned_group=task3.assigned_group)

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
        site['contacts'].manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])


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
              }
    contacts.invokeFactory('organization', 'plonegroup-organization', **params)
    own_orga = contacts['plonegroup-organization']

    # Departments and services creation
    sublevels = [
        (u'Direction générale', (u'Secrétariat', u'GRH', u'Informatique', u'Communication')),
        (u'Direction financière', (u'Budgets', u'Comptabilité', u'Taxes', u'Marchés publics')),
        (u'Direction technique', (u'Bâtiments', u'Voiries', u'Urbanisme')),
        (u'Département population', (u'Population', u'État-civil')),
        (u'Département culturel', (u'Enseignement', u'Culture-loisirs')),
        (u'Collège communal', [])
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
    gsettings.pdf_image_format = 'png'
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


def reimport_faceted_config(folder, xml, default_UID=None):
    """Reimport faceted navigation config."""
    folder.unrestrictedTraverse('@@faceted_exportimport').import_xml(
        import_file=open(os.path.dirname(__file__) + '/faceted_conf/%s' % xml))
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


def setupFacetedContacts(portal):
    """Setup facetednav for contacts."""
    alsoProvides(portal.contacts, IDirectoryFacetedNavigable)
    alsoProvides(portal.contacts, IActionsEnabled)
    alsoProvides(portal.contacts, IDisableSmartFacets)
    # hide portlets columns in contacts
    alsoProvides(portal.contacts, IHidePloneLeftColumn)
    alsoProvides(portal.contacts, IHidePloneRightColumn)
    reimport_faceted_config(portal['contacts'], 'contacts-faceted.xml')


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
             'dmsincomingmail.back_to_agent|', 'task.back_in_created|', 'task.back_in_to_assign|',
             'task.back_in_to_do|', 'task.back_in_progress|', 'task.back_in_realized|', ]


def configure_faceted_folder(folder, xml=None, default_UID=None):
    """Configure faceted navigation for incoming-mail folder."""
    enableFacetedDashboardFor(folder, xml and os.path.dirname(__file__) + '/faceted_conf/%s' % xml or None)
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


def add_test_models(site):
    """Create test models."""
    if not base_hasattr(site, 'models'):
        folderid = site.invokeFactory(
            "Folder", id='models', title=_(u"Models"))
        models_folder = getattr(site, folderid)
        template_types = POD_TEMPLATE_TYPES.keys()
        models_folder.setLocallyAllowedTypes(template_types)
        models_folder.setImmediatelyAddableTypes(template_types)
        # alsoProvides(im_folder, INextPrevNotNavigable)
        logger.info('models folder created')
        if not 'modele1' in models_folder:
            api.content.create(
                type='PODTemplate',
                id='modele1',
                title='Modèle 1',
                enabled=False,
                container=models_folder,
                )

        template_path = pkg_resources.resource_filename(
            'collective.documentgenerator',
            'profiles/demo/templates/modele_general.odt')
        if not 'modele2' in models_folder:
            with open(template_path) as template_file:
                api.content.create(
                    type='PODTemplate',
                    id='modele2',
                    title=u'Modèle 2',
                    odt_file=NamedBlobFile(
                        data=template_file.read(),
                        contentType='applications/odt',
                        filename=u'modele_general.odt',
                    ),
                    container=models_folder,
                )

