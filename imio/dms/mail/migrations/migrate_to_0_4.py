# -*- coding: utf-8 -*-

from zope.component import getUtility
from Products.CMFPlone.utils import base_hasattr
from plone import api
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

    def replaceCollections(self):
        """ Replace Collection by DashboardCollection """
        col_folder = self.portal['incoming-mail']['collections']
        col_folder.setLocallyAllowedTypes(['DashboardCollection'])
        col_folder.setImmediatelyAddableTypes(['DashboardCollection'])

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
        self.runProfileSteps('imio.dms.mail', ['actions', 'repositorytool', 'portlets'])
        self.reinstall([
            'imio.dashboard:default',
        ])

        self.replaceCollections()

        im_folder = self.portal['incoming-mail']
        configure_incoming_mail_folder(im_folder)

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
