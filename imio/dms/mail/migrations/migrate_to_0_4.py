# -*- coding: utf-8 -*-

from zope.component import getUtility
from Products.CMFPlone.utils import base_hasattr
from plone import api
from collective.behavior.talcondition.utils import applyExtender
from imio.migrator.migrator import Migrator
from imio.dms.mail.setuphandlers import configure_incoming_mail
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

    def migrateTalCondition(self):
        """ Migrate collective.behavior.talcondition """
        applyExtender(self.portal, meta_types=('Collection', ))
        obj = self.portal['incoming-mail']['collections']['to_validate']
        obj.roles_bypassing_talcondition = ['Manager', 'Site Administrator']
        conditions = {
            'created': "python: object.restrictedTraverse('idm-utils').created_col_cond()",
            'proposed_to_manager': "python: object.restrictedTraverse('idm-utils').proposed_to_manager_col_cond()",
            'proposed_to_service_chief': "python: object.restrictedTraverse('idm-utils').proposed_to_serv_chief_col_cond()",
        }
        for state in conditions:
            obj = self.portal['incoming-mail']['collections']['searchfor_%s' % state]
            if not obj.tal_condition:
                obj.tal_condition = conditions[state]
                obj.roles_bypassing_talcondition = ['Manager', 'Site Administrator']

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.4...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', ['actions', 'repositorytool', ])
        self.reinstall([
            'imio.dashboard:default',
            ])

        im_folder = self.portal['incoming-mail']
        configure_incoming_mail(im_folder)

        col_folder = im_folder['collections']

        # remove collections
        for collection in col_folder.listFolderContents():
            if collection.portal_type != 'DashboardCollection':
                api.content.delete(collection)

        # re-create dashboard collections
        createIMCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')

        self.migrateTalCondition()

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
