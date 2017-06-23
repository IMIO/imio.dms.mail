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
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue

from Products.CMFPlone.utils import base_hasattr, safe_unicode
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
from collective.documentgenerator.utils import update_templates
#from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.querynextprev.interfaces import INextPrevNotNavigable
from dexterity.localroles.utils import add_fti_configuration
from eea.facetednavigation.settings.interfaces import IDisableSmartFacets
from eea.facetednavigation.settings.interfaces import IHidePloneLeftColumn
from eea.facetednavigation.settings.interfaces import IHidePloneRightColumn
from imio.helpers.content import create, add_file
from imio.helpers.security import get_environment, generate_password
from imio.dashboard.utils import enableFacetedDashboardFor, _updateDefaultCollectionFor
from imio.dms.mail.interfaces import IIMDashboard, ITaskDashboard, IOMDashboard

from interfaces import IDirectoryFacetedNavigable, IActionsPanelFolder
from utils import list_wf_states

logger = logging.getLogger('imio.dms.mail: setuphandlers')


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
    folder.portal_workflow.doActionFor(col_folder, "show_internally")
    #alsoProvides(col_folder, ICollectionCategories)
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
    configure_om_rolefields(context)

    if (base_hasattr(site.portal_types.task, 'localroles') and
            site.portal_types.task.localroles.get('assigned_group', '') and
            site.portal_types.task.localroles['assigned_group'].get('created') and
            '' in site.portal_types.task.localroles['assigned_group']['created']):
        configure_task_rolefields(context, force=True)
    else:
        configure_task_rolefields(context, force=False)

    configure_task_config(context)

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

        im_folder.setConstrainTypesMode(1)
        im_folder.setLocallyAllowedTypes(['dmsincomingmail'])
        im_folder.setImmediatelyAddableTypes(['dmsincomingmail'])
        site.portal_workflow.doActionFor(im_folder, "show_internally")
        logger.info('incoming-mail folder created')

    if not base_hasattr(site, 'outgoing-mail'):
        folderid = site.invokeFactory("Folder", id='outgoing-mail', title=_(u"Outgoing mail"))
        om_folder = getattr(site, folderid)
        alsoProvides(om_folder, INextPrevNotNavigable)

        # add mail-searches
        col_folder = add_db_col_folder(om_folder, 'mail-searches', _("Outgoing mail searches"),
                                       _('Outgoing mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOMDashboard)
        createOMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsoutgoingmail')
        configure_faceted_folder(col_folder, xml='om-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        # configure outgoing-mail faceted
        configure_faceted_folder(om_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())

        om_folder.setConstrainTypesMode(1)
        om_folder.setLocallyAllowedTypes(['dmsoutgoingmail'])
        om_folder.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        site.portal_workflow.doActionFor(om_folder, "show_internally")
        logger.info('outgoing-mail folder created')

    if not base_hasattr(site, 'tasks'):
        folderid = site.invokeFactory("Folder", id='tasks', title=_(u"Tasks"))
        tsk_folder = getattr(site, folderid)
        # add task-searches
        col_folder = add_db_col_folder(tsk_folder, 'task-searches', _("Tasks searches"),
                                       _("Tasks"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, ITaskDashboard)
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
        site.portal_workflow.doActionFor(tsk_folder, "show_internally")
        logger.info('tasks folder created')

    # enable portal diff on incoming mail
    api.portal.get_tool('portal_diff').setDiffForPortalType(
        'dmsincomingmail', {'any': "Compound Diff for Dexterity types"})

    # reimport collective.contact.widget's registry step (disable jQueryUI's autocomplete)
    site.portal_setup.runImportStepFromProfile(
        'profile-collective.contact.widget:default',
        'plone.app.registry')

    configure_actions_panel(site)

    configure_ckeditor(site, custom='ged')

    add_templates(site)


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
            'proposed_to_service_chief': "python: object.restrictedTraverse('idm-utils')."
                                         "proposed_to_serv_chief_col_cond()",
        },
        'task': {},
        'dmsoutgoingmail': {
            'scanned': "python: object.restrictedTraverse('odm-utils').scanned_col_cond()",
        }
    }
    view_fields = {
        'dmsincomingmail': {
            '*': (u'select_row', u'pretty_link', u'treating_groups', u'assigned_user', u'due_date', u'mail_type',
                  u'sender', u'CreationDate', u'actions'),
        },
        'task': {
            '*': (u'select_row', u'pretty_link', u'task_parent', u'assigned_group', u'assigned_user', u'due_date',
                  u'CreationDate', u'actions'),
        },
        'dmsoutgoingmail': {
            '*': (u'select_row', u'pretty_link', u'treating_groups', u'sender', u'recipients', u'mail_type',
                  u'assigned_user', u'CreationDate', u'actions'),
            'sent': (u'select_row', u'pretty_link', u'treating_groups', u'sender', u'recipients', u'mail_type',
                     u'assigned_user', u'CreationDate', u'outgoing_date', u'actions')
        }
    }
    showNumberOfItems = {
        'dmsincomingmail': ('created',),
        'dmsoutgoingmail': ('scanned',),
    }
    for stateo in list_wf_states(folder, content_type):
        state = stateo.id
        col_id = "searchfor_%s" % state
        if not base_hasattr(folder, col_id):
            folder.invokeFactory("DashboardCollection", id=col_id, title=_(col_id),
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [content_type]},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [state]}],
                                 customViewFields=(state in view_fields[content_type] and
                                                   view_fields[content_type][state] or view_fields[content_type]['*']),
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
             'v': 'dmsincomingmail-validation'}],
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
        {'id': 'to_treat_in_my_group', 'tit': _('im_to_treat_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['proposed_to_agent']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsincomingmail-in-treating-group'}],
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
            'sort': u'created', 'rev': True, 'count': True},
    ]
    createDashboardCollections(folder, collections)


def createOMailCollections(folder):
    """
        create some outgoing mails dashboard collections
    """
    collections = [
        {'id': 'all_mails', 'tit': _('all_outgoing_mails'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'to_validate', 'tit': _('om_to_validate'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-validation'}],
            'cond': u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsoutgoingmail')",
            'bypass': ['Manager', 'Site Administrator'],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'mail_type', u'assigned_user', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'to_treat', 'tit': _('om_to_treat'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['created']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'mail_type', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': True},
        {'id': 'om_treating', 'tit': _('om_im_treating'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v':
                ['proposed_to_service_chief', 'to_be_signed']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'have_treated', 'tit': _('om_have_treated'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['sent']}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user', u'due_date',
                     u'mail_type', u'sender', u'CreationDate', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_my_group', 'tit': _('om_in_my_group'), 'subj': (u'search', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-in-treating-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date', u'actions'),
            'sort': u'created', 'rev': True, 'count': False},
        {'id': 'in_copy', 'tit': _('om_in_copy'), 'subj': (u'todo', ), 'query': [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
             'v': 'dmsoutgoingmail-in-copy-group'}],
            'cond': u"", 'bypass': [],
            'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'sender', u'recipients',
                     u'mail_type', u'assigned_user', u'CreationDate', u'outgoing_date', u'actions'),
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

    #History: add history after contact merging
    #site.manage_permission('CMFEditions: Access previous versions', ('Manager', 'Site Administrator', 'Contributor',
    #                       'Editor', 'Base Field Writer', 'Owner', 'Reviewer'), acquire=0)
    #site.manage_permission('CMFEditions: Save new version', ('Manager', 'Site Administrator', 'Contributor',
    #                       'Editor', 'Base Field Writer', 'Owner', 'Reviewer'), acquire=0)

    # Default roles for own permissions
    site.manage_permission('imio.dms.mail: Write mail base fields', ('Manager', 'Site Administrator'),
                           acquire=0)
    site.manage_permission('imio.dms.mail: Write treating group field', ('Manager', 'Site Administrator'),
                           acquire=0)
    site.manage_permission('imio.dms.mail: Write userid field', ('Manager', 'Site Administrator'),
                           acquire=0)

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
                                                                   'StyleTemplate', 'dmsommainfile']


def changeSearchedTypes(site):
    """
        Change searched types
    """
    to_show = ['dmsmainfile', 'dmsommainfile']
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
        'created': {'encodeurs': {'roles': ['Contributor', 'Editor', 'DmsFile Contributor', 'Base Field Writer',
                                            'Treating Group Writer']}},
        'proposed_to_manager': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Base Field Writer',
                                                'Treating Group Writer']},
                                'encodeurs': {'roles': ['Base Field Writer', 'Reader']}},
        'proposed_to_service_chief': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer',
                                                      'Base Field Writer', 'Treating Group Writer']},
                                      'encodeurs': {'roles': ['Reader']}},
        'proposed_to_agent': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                              'encodeurs': {'roles': ['Reader']}},
        'in_treatment': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                         'encodeurs': {'roles': ['Reader']}},
        'closed': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']},
                   'encodeurs': {'roles': ['Reader']}},
    }, 'treating_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer',
                                                               'Treating Group Writer']}},
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


def configure_om_rolefields(context):
    """
        Configure the rolefields on types
    """
    roles_config = {'static_config': {
        'to_be_signed': {'expedition': {'roles': ['Editor', 'Reviewer']},
                         'encodeurs': {'roles': ['Reader']},
                         'dir_general': {'roles': ['Reader']}},
        'sent': {'expedition': {'roles': ['Reader', 'Reviewer']},
                 'encodeurs': {'roles': ['Reader']},
                 'dir_general': {'roles': ['Reader']}},
        'scanned': {'expedition': {'roles': ['Contributor', 'Editor', 'Reader', 'Reviewer', 'DmsFile Contributor',
                                             'Base Field Writer', 'Treating Group Writer']},
                    'encodeurs': {'roles': ['Reader']}},
    }, 'treating_groups': {
        'created': {'encodeur': {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor',
                                           'Base Field Writer', 'Treating Group Writer']}},
        'proposed_to_service_chief': {'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer',
                                                     'DmsFile Contributor', 'Base Field Writer',
                                                     'Treating Group Writer']},
                                      'encodeur': {'roles': ['Reader']}},
        'to_be_signed': {'validateur': {'roles': ['Reader']},
                         'editeur': {'roles': ['Reader']},
                         'encodeur': {'roles': ['Reader']},
                         'lecteur': {'roles': ['Reader']}},
        'sent': {'validateur': {'roles': ['Reader']},
                 'editeur': {'roles': ['Reader']},
                 'encodeur': {'roles': ['Reader']},
                 'lecteur': {'roles': ['Reader']}},
    }, 'recipient_groups': {
        'proposed_to_service_chief': {'validateur': {'roles': ['Reader']}},
        'to_be_signed': {'validateur': {'roles': ['Reader']},
                         'editeur': {'roles': ['Reader']},
                         'encodeur': {'roles': ['Reader']},
                         'lecteur': {'roles': ['Reader']}},
        'sent': {'validateur': {'roles': ['Reader']},
                 'editeur': {'roles': ['Reader']},
                 'encodeur': {'roles': ['Reader']},
                 'lecteur': {'roles': ['Reader']}},
    },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration('dmsoutgoingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)


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
            'to_assign': {
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
            },
            'to_do': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'in_progress': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'realized': {
                'editeur': {'roles': ['Contributor', 'Editor'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Contributor', 'Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
            'closed': {
                'editeur': {'roles': ['Reader'],
                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'validateur': {'roles': ['Editor', 'Reviewer'],
                               'rel': "{'collective.task.related_taskcontainer':['Reader']}"},
                'lecteur': {'roles': ['Reader']},
            },
        },
        'assigned_user': {
        },
        'enquirer': {
        },
        'parents_assigned_groups': {
            'to_assign': {
                'validateur': {'roles': ['Reader']},
            },
            'to_do': {
                'editeur': {'roles': ['Reader']},
                'validateur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'in_progress': {
                'editeur': {'roles': ['Reader']},
                'validateur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'realized': {
                'editeur': {'roles': ['Reader']},
                'validateur': {'roles': ['Reader']},
                'lecteur': {'roles': ['Reader']},
            },
            'closed': {
                'editeur': {'roles': ['Reader']},
                'validateur': {'roles': ['Reader']},
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
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states'] = [
            'proposed_to_service_chief', 'proposed_to_agent']
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'] = [
            {'mt_value': u'courrier', 'mt_title': u'Courrier', 'mt_active': True},
            {'mt_value': u'recommande', 'mt_title': u'Recommandé', 'mt_active': True},
        ]
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states'] = [
            'proposed_to_service_chief']
    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'] = True

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
                site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_encodeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_encodeur" % uid)
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
                          {'name': u'SA', 'token': 'sa'},
                          {'name': u'Commune', 'token': 'commune'},
                          {'name': u'CPAS', 'token': 'cpas'},
                          {'name': u'Intercommunale', 'token': 'intercommunale'},
                          {'name': u'Zone de police', 'token': 'zp'},
                          {'name': u'Zone de secours', 'token': 'zs'},
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
              'street': u"Rue de l'électron",
              'number': u'1',
              'use_parent_address': False
              }
    contacts.invokeFactory('organization', 'electrabel', **params)
    electrabel = contacts['electrabel']

    electrabel.invokeFactory('organization', 'travaux', title=u'Travaux 1', organization_type=u'sa')

    params = {'title': u"SWDE",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'eau vive",
              'number': u'1',
              'use_parent_address': False
              }
    contacts.invokeFactory('organization', 'swde', **params)
    swde = contacts['swde']

    # Persons creation (in directory)
    params = {'lastname': u'Courant',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1981, 11, 22),
              'email': u'jean.courant@electrabel.be',
              'phone': u'012/345.678',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'électron",
              'number': u'1',
              'use_parent_address': False
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
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'eau vive",
              'number': u'1',
              'use_parent_address': False
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
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de l'eau vive",
              'number': u'1',
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
              }
    sergerobinet.invokeFactory('held_position', 'agent-swde', **params)
    bernardlermitte.invokeFactory('held_position', 'agent-swde', **params)

    params = {'start_date': datetime.date(2005, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(electrabel)),
              'label': u'Agent',
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
                createContentInContainer(mail, 'dmsmainfile', title='', file=file_object,
                                         scan_id='0509999000000%02d' % i)

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
    orgas_cycle = cycle(registry[ORGANIZATIONS_REGISTRY])
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
                      #temporary in comment because it doesn't pass in test and case probably errors when deleting site
                      #'in_reply_to': [RelationValue(intids.getId(inmail))],
                      'recipients': [RelationValue(recipients_cycle.next())],
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
        api.group.create('encodeurs', '1 Encodeurs courrier entrant')
        site['incoming-mail'].manage_addLocalRoles('encodeurs', ['Contributor', 'Reader'])
        site['contacts'].manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
#        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname='encodeurs', username='scanner')
        api.group.add_user(groupname='encodeurs', username='encodeur')
    if api.group.get('dir_general') is None:
        api.group.create('dir_general', '1 Directeur général')
        api.group.add_user(groupname='dir_general', username='dirg')
        site['outgoing-mail'].manage_addLocalRoles('dir_general', ['Contributor'])
        site['contacts'].manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])
    if api.group.get('expedition') is None:
        api.group.create('expedition', '1 Expédition courrier sortant')
        site['outgoing-mail'].manage_addLocalRoles('expedition', ['Contributor'])
        site['contacts'].manage_addLocalRoles('expedition', ['Contributor', 'Editor', 'Reader'])
        api.group.add_user(groupname='expedition', username='scanner')
        api.group.add_user(groupname='expedition', username='encodeur')


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
    pf = contacts['personnel-folder']
    site.portal_types.directory.filter_content_types = True
    api.content.transition(obj=pf, transition='show_internally')
    alsoProvides(pf, IActionsPanelFolder)
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
    persons = {
        'dirg': {'pers': {'lastname': u'DG', 'firstname': u'Maxime', 'gender': u'M', 'person_title': u'Monsieur',
                 'zip_code': u'5000', 'city': u'Namur', 'street': u"Rue de l'électron",
                 'number': u'1', 'use_parent_address': False},
                 'fcts': [{'position': RelationValue(intids.getId(own_orga['direction-generale'])),
                           'label': u'Directeur général', 'start_date': datetime.date(2016, 6, 15), 'end_date': None,
                           'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                           'email': u'maxime.dirg@macommune.be', 'phone': u'012/345.678', 'use_parent_address': False},
                          {'position': RelationValue(intids.getId(own_orga['direction-generale']['grh'])),
                           'label': u'Directeur du personnel', 'start_date': datetime.date(2012, 9, 1),
                           'end_date': datetime.date(2016, 6, 14), 'use_parent_address': False,
                           'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                           'email': u'maxime.dirg@macommune.be', 'phone': u'012/345.678'}]},
        'chef': {'pers': {'lastname': u'Chef', 'firstname': u'Michel', 'gender': u'M', 'person_title': u'Monsieur',
                 'zip_code': u'4000', 'city': u'Liège', 'street': u"Rue du cimetière",
                 'number': u'2', 'use_parent_address': False},
                 'fcts': [{'position': RelationValue(intids.getId(own_orga['direction-generale']['secretariat'])),
                           'label': u'Responsable secrétariat', 'start_date': None, 'end_date': None,
                           'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                           'email': u'michel.chef@macommune.be', 'phone': u'012/345.679', 'use_parent_address': False},
                          {'position': RelationValue(intids.getId(own_orga['direction-generale']['grh'])),
                           'label': u'Responsable GRH', 'start_date': None, 'end_date': None,
                           'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                           'email': u'michel.chef@macommune.be', 'phone': u'012/345.679',
                           'use_parent_address': False}]},
        'agent': {'pers': {'lastname': u'Agent', 'firstname': u'Fred', 'gender': u'M', 'person_title': u'Monsieur',
                  'zip_code': u'7000', 'city': u'Mons', 'street': u"Rue de la place",
                  'number': u'3', 'use_parent_address': False},
                  'fcts': [{'position': RelationValue(intids.getId(own_orga['direction-generale']['secretariat'])),
                            'label': u'Agent secrétariat', 'start_date': None, 'end_date': None,
                            'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                            'email': u'fred.agent@macommune.be', 'phone': u'012/345.670', 'use_parent_address': False},
                           {'position': RelationValue(intids.getId(own_orga['direction-generale']['grh'])),
                            'label': u'Agent GRH', 'start_date': None, 'end_date': None,
                            'zip_code': u'0010', 'city': u'Ma ville', 'street': u'Rue de la commune', 'number': u'1',
                            'email': u'fred.agent@macommune.be', 'phone': u'012/345.670',
                            'use_parent_address': False}]},
    }

    normalizer = getUtility(IIDNormalizer)
    for person in persons:
        pers = api.content.create(container=pf, type='person', id=person, userid=person, **persons[person]['pers'])
        for fct_dic in persons[person]['fcts']:
            api.content.create(container=pers, id=normalizer.normalize(fct_dic['label']), type='held_position',
                               **fct_dic)


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
             'task.back_in_to_do|', 'task.back_in_progress|', 'task.back_in_realized|',
             'dmsoutgoingmail.back_to_agent|', 'dmsoutgoingmail.back_to_creation|',
             'dmsoutgoingmail.back_to_service_chief|', 'dmsoutgoingmail.back_to_print|',
             'dmsoutgoingmail.back_to_be_signed|', 'dmsoutgoingmail.back_to_scanned|']


def configure_faceted_folder(folder, xml=None, default_UID=None):
    """Configure faceted navigation for incoming-mail folder."""
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
        (50, 'templates/d-print', os.path.join(dpath, 'd-print.odt')),
        (100, 'templates/om/header', os.path.join(dpath, 'om-header.odt')),
        (105, 'templates/om/footer', os.path.join(dpath, 'om-footer.odt')),
        (110, 'templates/om/intro', os.path.join(dpath, 'om-intro.odt')),
        (120, 'templates/om/ending', os.path.join(dpath, 'om-ending.odt')),
        (200, 'templates/om/base', os.path.join(dpath, 'om-base.odt')),
        (210, 'templates/om/receipt', os.path.join(dpath, 'om-receipt.odt')),
    ]


def add_templates(site):
    """Create pod templates."""
    from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES
    for path, title in [('templates', _(u"Templates")), ('templates/om', _(u"Outgoing mail"))]:
        parts = path.split('/')
        id = parts[-1]
        parent = site.unrestrictedTraverse('/'.join(parts[:-1]))
        if not base_hasattr(parent, id):
            folderid = parent.invokeFactory("Folder", id=id, title=title)
            tplt_fld = getattr(parent, folderid)

            template_types = POD_TEMPLATE_TYPES.keys() + ['Folder', 'DashboardPODTemplate']
            tplt_fld.setLocallyAllowedTypes(template_types)
            tplt_fld.setImmediatelyAddableTypes(template_types)
            tplt_fld.setConstrainTypesMode(1)
            tplt_fld.setExcludeFromNav(True)
            api.content.transition(obj=tplt_fld, transition='show_internally')
            alsoProvides(tplt_fld, INextPrevNotNavigable)
            logger.info("'%s' folder created" % path)

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
                dic['functions'] = [(add_file, [], {'attr': 'odt_file', 'filepath': ospath})]
                ret.append(dic)
        return ret

    data = {
        10: {'title': _(u'Mail listing template'), 'type': 'DashboardPODTemplate', 'trans': ['show_internally'],
             'attrs': {'pod_formats': ['odt'],
                       'dashboard_collections': [b.UID for b in
                                                 get_dashboard_collections(site['incoming-mail']['mail-searches'])
                                                 if b.id == 'all_mails'],
                       # cond: check c10 reception date (display link), check output_format (generation view)
                       'tal_condition': "python:request.get('c10[]', False) or request.get('output_format', False)"}},
        50: {'title': _(u'Print template'), 'type': 'DashboardPODTemplate', 'trans': ['show_internally'],
             'attrs': {'pod_formats': ['odt'],
                       'tal_condition': "python: context.restrictedTraverse('odm-utils').is_odt_activated()",
                       'dashboard_collections': get_dashboard_collections(site['outgoing-mail']['mail-searches'],
                                                                          uids=True)}},
        100: {'title': _(u'Header template'), 'type': 'SubTemplate', 'trans': ['show_internally']},
        105: {'title': _(u'Footer template'), 'type': 'SubTemplate', 'trans': ['show_internally']},
        110: {'title': _(u'Intro template'), 'type': 'SubTemplate', 'trans': ['show_internally']},
        120: {'title': _(u'Ending template'), 'type': 'SubTemplate', 'trans': ['show_internally']},
    }

    templates = combine_data(data, test=lambda x: x < 200)
    cids = create(templates, pos=True)

    data = {
        200: {'title': _(u'Base template'), 'type': 'ConfigurablePODTemplate', 'trans': ['show_internally'],
              # 'style_template': [cids[1].UID()]
              'attrs': {'pod_formats': ['odt'], 'pod_portal_types': ['dmsoutgoingmail'], 'merge_templates':
                        [{'pod_context_name': u'doc_entete', 'do_rendering': False, 'template': cids[100].UID()},
                         {'pod_context_name': u'doc_intro', 'do_rendering': False, 'template': cids[110].UID()},
                         {'pod_context_name': u'doc_fin', 'do_rendering': False, 'template': cids[120].UID()},
                         {'pod_context_name': u'doc_pied_page', 'do_rendering': False, 'template': cids[105].UID()}]}},
#                       'context_variables': [{'name': u'do_mailing', 'value': u'1'}]}},
        210: {'title': _(u'Receipt template'), 'type': 'ConfigurablePODTemplate', 'trans': ['show_internally'],
              # 'style_template': [cids[1].UID()]
              'attrs': {'pod_formats': ['odt'], 'pod_portal_types': ['dmsoutgoingmail'], 'merge_templates':
                        [{'pod_context_name': u'doc_entete', 'do_rendering': False, 'template': cids[100].UID()},
                         {'pod_context_name': u'doc_intro', 'do_rendering': False, 'template': cids[110].UID()},
                         {'pod_context_name': u'doc_fin', 'do_rendering': False, 'template': cids[120].UID()},
                         {'pod_context_name': u'doc_pied_page', 'do_rendering': False, 'template': cids[105].UID()}],
                        'context_variables': [{'name': u'PD', 'value': u'True'},
                                              {'name': u'PC', 'value': u'True'},
                                              {'name': u'PVS', 'value': u'False'}]}},
    }

    templates = combine_data(data, test=lambda x: x >= 200)
    cids = create(templates, pos=True, cids=cids)


# Singles steps

def create_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    add_templates(context.getSite())


def update_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list)
    return '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret])


def override_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list, force=True)
    return '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret])
