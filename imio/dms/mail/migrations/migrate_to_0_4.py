# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.container import contained
from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.registry.interfaces import IRegistry
from imio.dashboard.utils import _updateDefaultCollectionFor
from imio.helpers.catalog import addOrUpdateIndexes
from imio.migrator.migrator import Migrator
from imio.dms.mail.setuphandlers import configure_incoming_mail_folder
from imio.dms.mail.setuphandlers import createIMCollections
from imio.dms.mail.setuphandlers import createStateCollections

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_4(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def runProfileSteps(self, profile, steps):
        ''' Run specific steps for profile '''
        for step_id in steps:
            self.portal.portal_setup.runImportStepFromProfile('profile-%s:default' % profile, step_id)

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

    def replaceCollections(self):
        """ Replace Collection by DashboardCollection """
        col_folder = self.portal['incoming-mail']['collections']
        col_folder.setLocallyAllowedTypes(['DashboardCollection'])
        col_folder.setImmediatelyAddableTypes(['DashboardCollection'])
        if col_folder.getDefaultPage() == 'all_mails':
            col_folder.setDefaultPage(None)
        if col_folder.title == u'Collections: ne pas effacer':
            col_folder.title = u'Recherches'

        # remove collections
        for collection in col_folder.listFolderContents():
            if collection.portal_type != 'DashboardCollection':
                api.content.delete(collection)

        # re-create dashboard collections
        createIMCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.4...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', ['actions', 'controlpanel', 'portlets', 'repositorytool'])
        self.runProfileSteps('collective.dms.mailcontent', ['controlpanel'])
        self.runProfileSteps('collective.contact.plonegroup', ['controlpanel'])
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
        self.replaceCollections()

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
        im_folder = self.portal['incoming-mail']
        configure_incoming_mail_folder(im_folder)
        _updateDefaultCollectionFor(im_folder, im_folder['collections']['all_mails'].UID())

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
