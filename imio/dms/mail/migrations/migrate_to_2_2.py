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

        if u'⏺' not in api.portal.get_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                                        'contact_source_metadata_content'):
            api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                           'contact_source_metadata_content',
                                           u'{gft} ⏺ {number}, {street}, {zip_code}, {city} ⏺ {email}')
        if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order'):
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order', [
                'IDublinCore.title', 'IDublinCore.description', 'sender', 'treating_groups', 'ITask.assigned_user',
                'recipient_groups', 'reception_date', 'ITask.due_date', 'mail_type', 'reply_to',
                'ITask.task_description', 'external_reference_no', 'original_mail_date', 'internal_reference_no'])
        if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order'):
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order', [
                'IDublinCore.title', 'IDublinCore.description', 'recipients', 'treating_groups', 'ITask.assigned_user',
                'sender', 'recipient_groups', 'mail_type', 'mail_date', 'reply_to', 'ITask.task_description',
                'ITask.due_date', 'outgoing_date', 'external_reference_no', 'internal_reference_no'])

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
