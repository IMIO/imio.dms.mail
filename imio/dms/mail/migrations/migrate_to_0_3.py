# -*- coding: utf-8 -*-

from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_3(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.3...')
        self.cleanRegistries()
        self.upgradeAll()
        self.reinstall(['imio.dms.mail:default'])
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_3(context).run()
