# -*- coding: utf-8 -*-

from collective.ckeditortemplates.setuphandlers import FOLDER as default_cke_templ_folder
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from imio.dms.mail import _tr as _
from imio.dms.mail.setuphandlers import add_oem_templates
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.utils import update_solr_config
from imio.migrator.migrator import Migrator
from plone import api
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility
from zope.event import notify

import logging


logger = logging.getLogger('imio.dms.mail')


class Migrate_To_3_0(Migrator):  # noqa

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']
        self.existing_settings = {}

    # TODO update searchabletext of all main files to include external id

    def run(self):
        logger.info('Migrating to imio.dms.mail 3.0...')

        # check if oo port or solr port must be changed
        update_solr_config()
        update_oo_config()

        self.cleanRegistries()

        self.correct_actions()

        for mt in ('mail_types', 'omail_types'):
            mtr = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(mt)
            self.existing_settings[mt] = api.portal.get_registry_record(mtr)

        self.install(['collective.ckeditortemplates'])
        if default_cke_templ_folder in self.portal:
            api.content.delete(obj=self.portal[default_cke_templ_folder])
        self.upgradeProfile('collective.documentgenerator:default')

        self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'])  # to hide messages-viewlet

        self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry', 'repositorytool', 'typeinfo', 'workflow'])

        # TODO Add close wf adaptation
        # Apply workflow adaptations
        applied_adaptations = [dic['adaptation'] for dic in get_applied_adaptations()]
        if applied_adaptations:
            success, errors = apply_from_registry()
            if errors:
                logger.error("Problem applying wf adaptations: %d errors" % errors)
        if 'imio.dms.mail.wfadaptations.TaskServiceValidation' not in applied_adaptations:
            update_task_workflow(self.portal)
        self.portal.portal_workflow.updateRoleMappings()

        # do various global adaptations
        self.update_config()
        self.update_site()

        # do various adaptations for dmsincoming_email and dmsoutgoing_email
        self.insert_incoming_emails()
        self.insert_outgoing_emails()
        self.check_previously_migrated_collections()

        # self.catalog.refreshCatalog(clear=1)

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['eea.facetednavigation', 'plonetheme.imio.apps']:
            mark_last_version(self.portal, product=prod)

        # self.refreshDatabase()
        self.finish()

    def update_site(self):
        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.3':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

        # update portal title
        self.portal.title = 'Gestion du courrier 3.0'

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager',
        #                               'Site Administrator'), acquire=0)

        if 'doc' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['doc'])
        add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="https://docs.imio.be/'
                    u'imio-doc/ia.docs/" target="_blank">documentation en ligne de la '
                    u'version 3.0</a>, dont <a href="https://docs.imio.be/imio-doc/ia.docs/changelog" '
                    u'target="_blank">les nouvelles fonctionnalités</a> ainsi que d\'autres documentations liées.</p>',
                    msg_type='significant', can_hide=True, req_roles=['Authenticated'], activate=True)
        # update ckeditor config
        ckp = self.portal.portal_properties.ckeditor_properties
        ckp.manage_changeProperties(toolbar='CustomOld')
        configure_ckeditor(self.portal, custom='ged')
        # update templates layout and create oem folders
        self.portal.templates.setLayout('folder_listing')
        add_oem_templates(self.portal)
        record = getUtility(IRegistry).records.get('collective.contact.plonegroup.browser.settings.'
                                                   'IContactPlonegroupConfig.organizations')
        notify(RecordModifiedEvent(record, [], []))


    def insert_incoming_emails(self):
        # allowed types
        self.imf.setConstrainTypesMode(1)
        self.imf.setLocallyAllowedTypes(['dmsincomingmail', 'dmsincoming_email'])
        self.imf.setImmediatelyAddableTypes(['dmsincomingmail', 'dmsincoming_email'])
        # diff
        pdiff = api.portal.get_tool('portal_diff')
        pdiff.setDiffForPortalType('dmsincoming_email', {'any': "Compound Diff for Dexterity types"})
        # collections
        brains = self.catalog.searchResults(portal_type='DashboardCollection',
                                            path='/'.join(self.imf.getPhysicalPath()))
        for brain in brains:
            col = brain.getObject()
            new_lst = []
            change = False
            for dic in col.query:
                if dic['i'] == 'portal_type' and len(dic['v']) == 1 and dic['v'][0] == 'dmsincomingmail':  # i_e ok
                    dic['v'] = ['dmsincomingmail', 'dmsincoming_email']
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst

    def insert_outgoing_emails(self):
        # TODO set send_modes on all existing om
        return
        # TODO to be removed ! will not use this new type
        # allowed types
        self.omf.setConstrainTypesMode(1)
        self.omf.setLocallyAllowedTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        self.omf.setImmediatelyAddableTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        # diff
        pdiff = api.portal.get_tool('portal_diff')
        pdiff.setDiffForPortalType('dmsoutgoing_email', {'any': "Compound Diff for Dexterity types"})
        # collections
        brains = self.catalog.searchResults(portal_type='DashboardCollection',
                                            path='/'.join(self.omf.getPhysicalPath()))
        for brain in brains:
            col = brain.getObject()
            new_lst = []
            change = False
            for dic in col.query:
                if dic['i'] == 'portal_type' and len(dic['v']) == 1 and dic['v'][0] == 'dmsoutgoingmail':
                    dic['v'] = ['dmsoutgoingmail', 'dmsoutgoing_email']
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst

    def check_previously_migrated_collections(self):
        # check if changes have been persisted from lower migrations
        # TODO
        pass

    def correct_actions(self):
        pa = self.portal.portal_actions
        if 'portlet' in pa:
            api.content.rename(obj=pa['portlet'], new_id='object_portlet')
            set_portlet(self.portal)

    def update_config(self):
        # modify settings following new structure
        for mt in ('mail_types', 'omail_types'):
            mtr = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(mt)
            mail_types = self.existing_settings[mt]
            new_mt = []
            for dic in mail_types:
                if 'mt_value' in dic:
                    new_mt.append({'value': dic['mt_value'], 'dtitle': dic['mt_title'], 'active': dic['mt_active']})
            if new_mt:
                api.portal.set_registry_record(mtr, new_mt)
        # add new setting values
        if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes',
                                              default=False):
            modes = [
                {'value': u'post', 'dtitle': u'Lettre', 'active': True},
                {'value': u'post_registered', 'dtitle': u'Lettre recommandée', 'active': True},
                {'value': u'email', 'dtitle': u'Email', 'active': True},
            ]
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes', modes)
        # order send_modes
        om_fo = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order')
        if 'send_modes' not in om_fo:
            try:
                idx = om_fo.index('mail_type')
            except ValueError:
                idx = len(om_fo)
            om_fo.insert(idx, 'send_modes')
            email_flds = ['email_status', 'email_subject', 'email_sender', 'email_recipient', 'email_cc',
                          'email_attachments', 'email_body']
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order',
                                           om_fo + email_flds)


def migrate(context):
    Migrate_To_3_0(context).run()
