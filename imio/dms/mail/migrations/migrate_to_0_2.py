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
            for groups in (obj.treating_groups, obj.recipient_groups):
                if groups:
                    obj.manage_delLocalRoles(groups)

    def _replacePrincipalIdsByOrganizationUids(self):
        logger.info("Replace principal ids of localrolefields by organization uids.")
        brains = self.portal.portal_catalog(portal_type='dmsincomingmail')

        def split_principals(principals):
            ret = []
            for principal_id in principals:
                ret.append(principal_id.split('_')[0])
            return ret

        for brain in brains:
            obj = brain.getObject()
            if obj.treating_groups:
                obj.treating_groups = split_principals(obj.treating_groups)
            if obj.recipient_groups:
                obj.recipient_groups = split_principals(obj.recipient_groups)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.2...')
        self._deleteOldLocalRoles()
        self._replacePrincipalIdsByOrganizationUids()


def migrate(context):
    '''
    '''
    Migrate_To_0_2(context).run()
