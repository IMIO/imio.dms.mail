# -*- coding: utf-8 -*-

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from collective.wfadaptations.api import apply_from_registry
from imio.dms.mail import _tr as _
from imio.dms.mail.utils import update_solr_config
from imio.migrator.migrator import Migrator
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility

import logging


# createStateCollections
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_3_0(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
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
        if frontpage.Title() == 'Gestion du courrier 2.2':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

        # update portal title
        self.portal.title = 'Gestion du courrier 3.0'

        functions = api.portal.get_registry_record(FUNCTIONS_REGISTRY)
        for dic in functions:
            if dic['fct_id'] == u'encodeur':
                dic['fct-title'] = u'Créateur CS'

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager',
        #                               'Site Administrator'), acquire=0)

        # add group
        if api.group.get('lecteurs_globaux_ce') is None:
            api.group.create('lecteurs_globaux_ce', '2 Lecteurs Globaux CE')
        # change local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        for state in ['proposed_to_manager', 'proposed_to_service_chief',
                      'proposed_to_agent', 'in_treatment', 'closed']:
            if 'lecteurs_globaux_ce' not in lrsc[state]:
                lrsc[state]['lecteurs_globaux_ce'] = {'roles': ['Reader']}
        # We need to indicate that the object has been modified and must be "saved"
        lr._p_changed = True

        if 'new-version' not in self.portal['messages-config']:
            'TO BE CONTINUED' / 1

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
                if dic['i'] == 'portal_type' and len(dic['v']) == 1 and dic['v'][0] == 'dmsincomingmail':
                    dic['v'] = ['dmsincomingmail', 'dmsincoming_email']
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst

    def insert_outgoing_emails(self):
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
        # check if changes have been persisted
        # TO BE DONE
        pass

    def run(self):
        logger.info('Migrating to imio.dms.mail 3.0...')

        # check if oo port or solr port must be changed
        update_solr_config()
        update_oo_config()

        self.cleanRegistries()

        self.upgradeProfile('collective.dms.mailcontent:default')

        self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'])

        self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry', 'typeinfo', 'workflow'])

        self.portal.portal_workflow.updateRoleMappings()
        # Apply workflow adaptations
        RECORD_NAME = 'collective.wfadaptations.applied_adaptations'
        if api.portal.get_registry_record(RECORD_NAME, default=False):
            success, errors = apply_from_registry()
            if errors:
                logger.error("Problem applying wf adaptations: %d errors" % errors)

        # do various global adaptations
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

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_3_0(context).run()
