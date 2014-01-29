# -*- coding: utf-8 -*-

from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def _deleteOldLocalRoles(self):
        """ Delete old local roles """
        logger.info("Delete old local roles.")
        brains = self.portal.portal_catalog(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            groups = obj.treating_groups
            if groups:
                obj.manage_delLocalRoles(groups)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.2...')
        self._deleteOldLocalRoles()


def migrate(context):
    '''
    '''
    Migrate_To_0_2(context).run()
