# -*- coding: utf-8 -*-

from zope.component import getUtility

from plone import api
from plone.registry.interfaces import IRegistry

from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_1_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)

    def update_dmsmainfile(self):
        """ Update searchabletext """
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(portal_type='dmsmainfile')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def update_dmsincomingmail(self):
        """ Update searchabletext """
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def run(self):
        logger.info('Migrating to imio.dms.mail 1.1...')
        self.cleanRegistries()

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        # apply contact faceted config
#        reimport_faceted_config(self.portal)

        # update searchabletext
        self.update_dmsmainfile()
        self.update_dmsincomingmail()

#        self.upgradeAll()

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_1_1(context).run()
