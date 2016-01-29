# -*- coding: utf-8 -*-

import logging

from zope.component import getUtility

from plone import api
from plone.registry.interfaces import IRegistry

from Products.CPUtils.Extensions.utils import mark_last_version
from imio.helpers.catalog import addOrUpdateColumns
from imio.migrator.migrator import Migrator

from ..setuphandlers import blacklistPortletCategory

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_1_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')

    def update_dmsmainfile(self):
        """ Update searchabletext """
        brains = self.catalog.searchResults(portal_type='dmsmainfile')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def update_dmsincomingmail(self):
        """ Update searchabletext """
        brains = self.catalog.searchResults(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def add_view_field(self, fldname, folder, ids=[], before=''):
        """ Insert view field on DashboardCollection """
        crit = {'portal_type': 'DashboardCollection',
                'path': {'query': '/'.join(folder.getPhysicalPath()), 'depth': 1}}
        if ids:
            crit['id'] = ids
        brains = self.catalog.searchResults(crit)
        for brain in brains:
            col = brain.getObject()
            fields = list(col.getCustomViewFields())
            # if already activated, we pass
            if fldname in fields:
                continue
            # find before position
            i = len(fields)
            if before:
                try:
                    i = fields.index(before)
                except ValueError:
                    pass
            fields.insert(i, fldname)
            col.setCustomViewFields(tuple(fields))

    def run(self):
        logger.info('Migrating to imio.dms.mail 1.1...')
        self.cleanRegistries()
        im_folder = self.portal['incoming-mail']

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        # apply contact faceted config
#        reimport_faceted_config(self.portal)

        # activate field on DashboardCollection
        self.add_view_field('mail_type', im_folder['mail-searches'], before='CreationDate')
        self.add_view_field('sender', im_folder['mail-searches'], before='CreationDate')

        # update searchabletext
        self.update_dmsmainfile()
        self.update_dmsincomingmail()

        # add metadata in portal_catalog
        addOrUpdateColumns(self.portal, columns=('mail_type',))

        # block parent portlets on contacts
        blacklistPortletCategory(self.portal, self.portal['contacts'])

        # add local roles
        self.portal['contacts'].manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])

#        self.upgradeAll()

        for prod in ['imio.dms.mail']:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_1_1(context).run()
