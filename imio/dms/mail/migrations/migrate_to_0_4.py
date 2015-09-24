# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.container import contained
from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.registry.interfaces import IRegistry
from imio.helpers.catalog import addOrUpdateIndexes
from imio.migrator.migrator import Migrator

from ..setuphandlers import _, configure_faceted_folder, configure_task_rolefields
from ..setuphandlers import add_db_col_folder
from ..setuphandlers import createIMailCollections, createIMTaskCollections, createStateCollections

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_4(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def delete_portlet(self, obj, portlet):
        """ Delete the defined portlet on obj """
        ann = IAnnotations(obj)
        columnkey = 'plone.leftcolumn'
        if not 'plone.portlets.contextassignments' in ann:
            logger.error("No portlets defined in this context")
        elif not columnkey in ann['plone.portlets.contextassignments']:
            logger.error("Column '%s' not found in portlets definition" % columnkey)
        elif not portlet in ann['plone.portlets.contextassignments'][columnkey]:
            logger.error("Portlet '%s' in '%s' not found in portlets definition" % (portlet, columnkey))
        else:
            fixing_up = contained.fixing_up
            contained.fixing_up = True
            del ann['plone.portlets.contextassignments'][columnkey][portlet]
            # revert our fixing_up customization
            contained.fixing_up = fixing_up

    def replaceCollections(self, im_folder):
        """ Replace Collection by DashboardCollection """
        if 'collections' in im_folder:
            api.content.delete(im_folder['collections'])

        im_folder.setConstrainTypesMode(0)
        col_folder = add_db_col_folder(im_folder, 'mail-searches', _("Incoming mail searches"),
                                       _('Incoming mails'))
        im_folder.moveObjectToPosition('mail-searches', 0)

        # re-create dashboard collections
        createIMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')
        configure_faceted_folder(col_folder, xml='im-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        col_folder = add_db_col_folder(im_folder, 'task-searches', _("Tasks searches"),
                                       _("I.M. tasks"))
        im_folder.moveObjectToPosition('task-searches', 1)
        createIMTaskCollections(col_folder)
        createStateCollections(col_folder, 'task')
        configure_faceted_folder(col_folder, xml='im-task-searches.xml',
                                 default_UID=col_folder['all_tasks'].UID())

        im_folder.setConstrainTypesMode(1)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.4...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'controlpanel', 'portlets', 'repositorytool'])
        self.runProfileSteps('collective.dms.mailcontent', steps=['controlpanel'])
        self.runProfileSteps('collective.contact.plonegroup', steps=['controlpanel'])
        self.reinstall([
            'collective.messagesviewlet:messages',
            'imio.dashboard:default',
        ])
        self.upgradeProfile('collective.task:default')

        registry = getUtility(IRegistry)
        # set jqueryui autocomplete to False. If not contact autocomplete doesn't work
        registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        # delete old dmsmail portlet
        self.delete_portlet(self.portal, 'portlet_maindmsmail')

        # replace collections by Dashboard collections
        im_folder = self.portal['incoming-mail']
        self.replaceCollections(im_folder)

        # add new indexes for dashboard
        addOrUpdateIndexes(self.portal, indexInfos={'mail_type': ('FieldIndex', {}),
                                                    'mail_date': ('DateIndex', {}),
                                                    'in_out_date': ('DateIndex', {}),
                                                    })
#        catalog = api.portal.get_tool('portal_catalog')
#        brains = catalog.searchResults(portal_type='dmsincomingmail')
#        for brain in brains:
#            brain.getObject().reindexObject(idxs=['mail_type', 'mail_date', 'in_out_date'])

        # set dashboard on incoming mail
        configure_faceted_folder(im_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=im_folder['mail-searches']['all_mails'].UID())

        # set task local roles configuration
        configure_task_rolefields(self.portal)

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
