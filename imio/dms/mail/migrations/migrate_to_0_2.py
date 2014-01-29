# -*- coding: utf-8 -*-

from zope.annotation import IAnnotations
from zope.component import getUtility
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes

from imio.migrator.migrator import Migrator
from imio.project.core.config import CHILDREN_BUDGET_INFOS_ANNOTATION_KEY
from imio.project.core.events import _updateParentsBudgetInfos

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def _deleteOldLocalRoles(self):
        import ipdb; ipdb.set_trace()
        """ Delete old local roles """
        logger.info("Delete old local roles.")
        brains = self.portal.portal_catalog(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            userid = obj.threating_groups
            obj.manage_delLocalRoles(userid)

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.2...')
        self._deleteLocalRoles()


def migrate(context):
    '''
    '''
    Migrate_To_0_2(context).run()
