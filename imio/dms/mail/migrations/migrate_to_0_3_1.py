# -*- coding: utf-8 -*-

from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_3_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.3.1...')
        self.cleanRegistries()
        self.reinstall(['imio.actionspanel:default'])
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:default',
                                                          'typeinfo')
        self.upgradeAll()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_3_1(context).run()
