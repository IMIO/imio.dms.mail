# -*- coding: utf-8 -*-

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from imio.dms.mail import _tr as _
from imio.migrator.migrator import Migrator
from plone import api
from plone.registry.interfaces import IRegistry
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility

import logging


# createStateCollections
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_3_0(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def update_site(self):
        # add documentation message
        if 'doc' not in self.portal['messages-config']:
            add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="http://www.imio.be/'
                        u'support/documentation/topic/cp_app_ged" target="_blank">documentation en ligne de la '
                        u'dernière version</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                        can_hide=True, req_roles=['Authenticated'], activate=True)

        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.1':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

        # update portal title
        self.portal.title = 'Gestion du courrier 3.0'

        functions = api.portal.get_registry_record(FUNCTIONS_REGISTRY)
        for dic in functions:
            if dic['fct_id'] == u'encodeur':
                dic['fct-title'] = u'Créateur CS'

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager', 'Site Administrator'),
        #                              acquire=0)

    def run(self):
        logger.info('Migrating to imio.dms.mail 3.0...')
        self.cleanRegistries()

        self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry'])

        # check if oo port must be changed
        update_oo_config()

        # do various global adaptations
        self.update_site()

        # self.catalog.refreshCatalog(clear=1)

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        # self.upgradeAll(omit=['imio.dms.mail:default'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in []:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_3_0(context).run()
