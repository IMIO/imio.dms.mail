# -*- coding: utf-8 -*-

from imio.migrator.migrator import Migrator
from Products.CMFPlone.utils import base_hasattr

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_3_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def importImioDmsMailStep(self, step_ids):
        ''' Set ILocking behavior and reinstall workflow'''
        for step_id in step_ids:
            self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:default', step_id)

    def createNotEncodedPerson(self):
        ''' add not encoded person if not exists'''
        if not base_hasattr(self.portal.contacts, 'notencoded'):
            self.portal.contacts.invokeFactory('person', 'notencoded', lastname=u'Non encodé')
            self.portal.contacts.folder_position('top', 'notencoded')

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.3.1...')
        self.cleanRegistries()
        self.reinstall(['imio.actionspanel:default'])
        self.importImioDmsMailStep(('typeinfo', 'workflow', 'update-workflow-rolemap'))
        self.createNotEncodedPerson()
        self.upgradeAll()
        self.portal.portal_workflow.updateRoleMappings()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_3_1(context).run()
