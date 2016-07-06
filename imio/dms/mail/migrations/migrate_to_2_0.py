# -*- coding: utf-8 -*-

import logging

from zope.component import getUtility
from zope.interface import alsoProvides

from plone import api
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr

from Products.CPUtils.Extensions.utils import mark_last_version
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.helpers.catalog import addOrUpdateColumns
from imio.migrator.migrator import Migrator

from ..interfaces import IOMDashboard, ITaskDashboard
from ..setuphandlers import (_, configure_om_rolefields, createIMailCollections, add_db_col_folder,
                             createStateCollections, createOMailCollections, configure_faceted_folder,
                             createTaskCollections)

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_0(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def delete_outgoing_examples(self):
        for brain in self.catalog(portal_type='dmsoutgoingmail', id=['reponse1', 'reponse2', 'reponse3', 'reponse4',
                                  'reponse5', 'reponse6', 'reponse7', 'reponse8', 'reponse9']):
            api.content.delete(obj=brain.getObject())

    def create_tasks_folder(self):
        if base_hasattr(self.portal['incoming-mail'], 'task-searches'):
            api.content.delete(obj=self.portal['incoming-mail']['task-searches'])
        if not base_hasattr(self.portal, 'tasks'):
            self.portal.invokeFactory("Folder", id='tasks', title=_(u"Tasks"))
            tsk_folder = getattr(self.portal, 'tasks')
            self.portal.moveObjectToPosition('tasks', self.portal.getObjectPosition('contacts'))
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
            self.portal.portal_workflow.doActionFor(tsk_folder, "show_internally")
            logger.info('tasks folder created')

    def update_site(self):
        # publish outgoing-mail folder
        if api.content.get_state(self.omf) != 'internally_published':
            api.content.transition(obj=self.omf, to_state="internally_published")
        # add group
        if api.group.get('expedition') is None:
            api.group.create('expedition', '1 Expédition courrier sortant')
        # rename group title
        encodeurs = api.group.get('encodeurs')
        if encodeurs.getProperty('title') != '1 Encodeurs courrier entrant':
            self.portal.portal_groups.editGroup('encodeurs', title='1 Encodeurs courrier entrant')
        # add new collection to_treat_in_my_group
        createIMailCollections(self.imf['mail-searches'])
        # update permission
        if 'Site Administrator' not in [dic['name'] for dic in
                                        self.portal.rolesOfPermission("imio.dms.mail : Write userid field")
                                        if dic['selected'] == 'SELECTED']:
            self.portal.manage_permission('imio.dms.mail : Write userid field', ('Manager', 'Site Administrator'),
                                          acquire=0)

    def configure_dashboard(self):
        """ add DashboardCollection """
        alsoProvides(self.omf, INextPrevNotNavigable)
        alsoProvides(self.omf, IOMDashboard)
        self.omf.setConstrainTypesMode(0)
        col_folder = add_db_col_folder(self.omf, 'mail-searches', _("Outgoing mail searches"),
                                       _('Outgoing mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOMDashboard)
        self.omf.moveObjectToPosition('mail-searches', 0)

        createOMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsoutgoingmail')
        configure_faceted_folder(col_folder, xml='om-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())
        self.omf.setConstrainTypesMode(1)
        configure_faceted_folder(self.omf, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())
        # add metadata in portal_catalog
        addOrUpdateColumns(self.portal, columns=('in_out_date',))

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.0...')
        self.cleanRegistries()
        self.delete_outgoing_examples()
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'plone.app.registry', 'typeinfo'])
        self.runProfileSteps('imio.dms.mail', profile='examples',
                             steps=['imiodmsmail-addOwnPersonnel', 'imiodmsmail-configureImioDmsMail'])

        # do various global adaptations
        self.update_site()

        # configure dashboard on omf
        self.configure_dashboard()

        # manage task for both incoming and outgoing mails
        self.create_tasks_folder()

        # configure role fields on dmsoutgoingmail
        configure_om_rolefields(self.portal)

        # set front-page folder as not next/prev navigable
        if not INextPrevNotNavigable.providedBy(self.portal['front-page']):
            alsoProvides(self.portal['front-page'], INextPrevNotNavigable)

        # refresh some indexes
        brains = self.catalog.searchResults(portal_type=['dmsincomingmail'])
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['in_out_date'])
        # self.upgradeAll()

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in []:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_0(context).run()
