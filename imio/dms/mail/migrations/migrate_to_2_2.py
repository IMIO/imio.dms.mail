# -*- coding: utf-8 -*-

from collective.documentgenerator.utils import update_oo_config
from imio.migrator.migrator import Migrator
from plone import api
from plone.registry.interfaces import IRegistry
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility

import logging


# createStateCollections
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def update_site(self):
        # add documentation message
        pass

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.2...')
        self.cleanRegistries()

        self.upgradeProfile('collective.contact.core:default')

        self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry', 'viewlets'])
        # check if oo port must be changed
        update_oo_config()

        api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                       'contact_source_metadata_content',
                                       u'{gft} ↈ {number}, {street}, {zip_code}, {city} ↈ {email}')

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in []:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_2(context).run()
