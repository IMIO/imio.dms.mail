# -*- coding: utf-8 -*-

from zope.component import getUtility
from Products.CMFPlone.utils import base_hasattr
from plone import api
from collective.behavior.talcondition.utils import applyExtender
from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_4(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def runProfileSteps(self, profile, steps):
        ''' Run specific steps for profile '''
        for step_id in steps:
            self.portal.portal_setup.runImportStepFromProfile('profile-%s:default' % profile, step_id)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.4...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', ['actions', 'repositorytool', ])
        #self.reinstall([])
        #self.runProfileSteps('collective.dms.scanbehavior', ['catalog'])

        # Migrate collective.behavior.talcondition
        applyExtender(self.portal, meta_types=('Collection', ))
        obj = self.portal['incoming-mail']['collections']['to_validate']
        obj.roles_bypassing_talcondition = ['Manager', 'Site Administrator']

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
