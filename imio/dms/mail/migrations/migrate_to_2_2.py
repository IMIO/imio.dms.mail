# -*- coding: utf-8 -*-

from collective.documentgenerator.utils import update_oo_config
from imio.dms.mail import _tr
from imio.migrator.migrator import Migrator
from plone import api
from Products.CPUtils.Extensions.utils import mark_last_version

import logging


# createStateCollections
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def update_site(self):
        # add documentation message
        if u'⏺' not in api.portal.get_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                                        'contact_source_metadata_content'):
            api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                           'contact_source_metadata_content',
                                           u'{gft} ⏺ {number}, {street}, {zip_code}, {city} ⏺ {email}')
        api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                       'display_below_content_title_on_views', True)
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
        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.1':
            frontpage.setTitle(_tr("front_page_title"))
            frontpage.setDescription(_tr("front_page_descr"))
            frontpage.setText(_tr("front_page_text"), mimetype='text/html')

    def check_roles(self):
        # check user roles
        for user in api.user.get_users():
            roles = api.user.get_roles(user=user)
            for role in roles:
                if role in ['Member', 'Authenticated'] or (role == 'Batch importer' and user.id == 'scanner'):
                    continue
                elif role == 'Manager':
                    self.portal.acl_users.source_groups.addPrincipalToGroup(user.id, 'Administrators')
                    api.user.revoke_roles(user=user, roles=['Manager'])
                elif role == 'Site Administrator':
                    self.portal.acl_users.source_groups.addPrincipalToGroup(user.id, 'Site Administrators')
                    api.user.revoke_roles(user=user, roles=['Site Administrator'])
                else:
                    logger.warn("User '{}' has role: {}".format(user.id, role))
        # check group roles
        for group in api.group.get_groups():
            roles = api.group.get_roles(group=group)
            for role in roles:
                if (role == 'Authenticated' or (role == 'Manager' and group.id == 'Administrators') or
                        (role == 'Site Administrator' and group.id == 'Site Administrators') or
                        (role == 'Reviewer' and group.id == 'Reviewers')):
                    continue
                else:
                    logger.warn("Group '{}' has role: {}".format(group.id, role))

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.2...')
        self.cleanRegistries()

        self.upgradeProfile('collective.contact.core:default')

        self.check_roles()

        self.runProfileSteps('imio.dms.mail', steps=['browserlayer', 'plone.app.registry', 'viewlets'])

        # check if oo port must be changed
        update_oo_config()

        self.update_site()

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['collective.ckeditor', 'plone.app.versioningbehavior', 'eea.jquery', 'collective.js.fancytree',
                     'plone.formwidget.masterselect', 'collective.quickupload', 'collective.behavior.talcondition',
                     'collective.contact.plonegroup', 'collective.contact.widget', 'collective.dms.basecontent',
                     'collective.eeafaceted.batchactions', 'collective.eeafaceted.collectionwidget',
                     'collective.eeafaceted.dashboard', 'collective.eeafaceted.z3ctable', 'collective.messagesviewlet',
                     'collective.querynextprev', 'collective.wfadaptations', 'collective.z3cform.chosen',
                     'dexterity.localroles', 'imio.actionspanel', 'imio.dashboard', 'imio.dms.mail', 'imio.history',
                     'plone.formwidget.datetime', 'plonetheme.imioapps']:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_2(context).run()
