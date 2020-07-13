# -*- coding: utf-8 -*-

from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_groups_mgt
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_groups_mgt
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.widgets.storage import Criterion
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_solr_config
from imio.migrator.migrator import Migrator
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility

import logging

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_2_1(Migrator):  # noqa

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.2.1...')

        # check if oo port or solr port must be changed
        update_solr_config()
        update_oo_config()

        self.cleanRegistries()

        self.correct_actions()

        self.install(['collective.contact.importexport'])
        self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'])  # to hide messages-viewlet
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'plone.app.registry'])

        # remove service_chief related
        self.remove_service_chief()

        # do various global adaptations
        self.update_site()

        # update daterange criteria
        self.update_dashboards()

        # update templates
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-update-templates'], profile='singles')

        # set showNumberOfItems on to_treat in_my_group only if SkipProposeToServiceChief adaptation was applied
        wf_adapts = api.portal.get_registry_record('collective.wfadaptations.applied_adaptations', default=[])
        user_check = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig'
                                                    '.assigned_user_check')
        if 'imio.dms.mail.wfadaptations.IMSkipProposeToServiceChief' in [adapt['adaptation'] for adapt in wf_adapts]:
            if not user_check and not self.imf['mail-searches']['to_treat_in_my_group'].showNumberOfItems:
                self.imf['mail-searches']['to_treat_in_my_group'].showNumberOfItems = True  # noqa

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['eea.facetednavigation', 'plonetheme.imio.apps']:
            mark_last_version(self.portal, product=prod)

        # self.refreshDatabase()
        self.finish()

    def correct_actions(self):
        pa = self.portal.portal_actions
        if 'portlet' in pa:
            api.content.rename(obj=pa['portlet'], new_id='object_portlet')
            set_portlet(self.portal)

    def update_site(self):
        # change permission to remove dashboard from user menu
        self.portal.manage_permission('Portlets: Manage own portlets', ('Manager', 'Site Administrator'), acquire=0)
        # clean old messages
        if 'doc' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['doc'])
            add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="https://docs.imio.be/'
                        u'imio-doc/ia.docs/" target="_blank">documentation en ligne de la '
                        u'dernière version</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                        can_hide=True, req_roles=['Authenticated'], activate=False)
        if 'new-version' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['new-version'])
            add_message('new-version', 'Nouvelles fonctionnalités', u'<p>Vous pouvez consulter la <a href="https://'
                        u'www.imio.be/" target="_blank">liste des nouvelles fonctionnalités</a></p>',
                        msg_type='significant', can_hide=True, req_roles=['Authenticated'], activate=False)
        # update plonegroup
        if not get_registry_groups_mgt():
            set_registry_groups_mgt(['dir_general', 'encodeurs', 'expedition'])
            functions = get_registry_functions()
            for dic in functions:
                if dic['fct_id'] == u'encodeur':
                    dic['fct_title'] = u'Créateur CS'
                    # TODO remove validateur when no more used on task and om
                elif dic['fct_id'] == u'validateur':
                    dic['fct_management'] = True
            set_registry_functions(functions)
        # add group
        if api.group.get('lecteurs_globaux_ce') is None:
            api.group.create('lecteurs_globaux_ce', '2 Lecteurs Globaux CE')
        # change local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        for state in ['proposed_to_manager', 'proposed_to_service_chief',
                      'proposed_to_agent', 'in_treatment', 'closed']:
            if state in lrsc:
                if 'lecteurs_globaux_ce' not in lrsc[state]:
                    lrsc[state]['lecteurs_globaux_ce'] = {'roles': ['Reader']}
        # We need to indicate that the object has been modified and must be "saved"
        lr._p_changed = True

    def update_dashboards(self):
        # update daterange criteria
        brains = api.content.find(object_provides=IFacetedNavigable.__identifier__)
        for brain in brains:
            obj = brain.getObject()
            criterion = ICriteria(obj)
            for key, criteria in criterion.items():
                if criteria.get("widget") != "daterange":
                    continue
                if criteria.get("usePloneDateFormat") is True:
                    continue
                logger.info("Upgrade daterange widget for faceted {0}".format(obj))
                position = criterion.criteria.index(criteria)
                values = criteria.__dict__
                values["usePloneDateFormat"] = True
                values["labelStart"] = u'Start date'
                values["labelEnd"] = u'End date'
                criterion.criteria[position] = Criterion(**values)
                criterion.criteria._p_changed = 1

    def remove_service_chief(self):
        # remove collection
        if 'searchfor_proposed_to_service_chief' in self.imf['mail-searches']:
            api.content.delete(obj=self.imf['mail-searches']['searchfor_proposed_to_service_chief'])
        # clean dms config
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        if '_validateur' in config:
            del config['_validateur']
            set_dms_config(keys=['review_levels', 'dmsincomingmail'], value=config)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        if 'proposed_to_service_chief' in config:
            del config['proposed_to_service_chief']
            set_dms_config(keys=['review_states', 'dmsincomingmail'], value=config)
        # clean local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrg = lr['static_config']
        if 'proposed_to_service_chief' in lrg:
            del lrg['proposed_to_service_chief']
        lrg = lr['treating_groups']
        if 'proposed_to_service_chief' in lrg:
            del lrg['proposed_to_service_chief']
        lrg = lr['recipient_groups']
        if 'proposed_to_service_chief' in lrg:
            del lrg['proposed_to_service_chief']
        lr._p_changed = True
        # update registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsincomingmail.back_to_service_chief|' in lst:
            lst.remove('dmsincomingmail.back_to_service_chief|')
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)
        # update remark states
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states')
        if 'proposed_to_service_chief' in lst:
            lst.remove('proposed_to_service_chief')
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states',
                                           lst)
        # reindex im
        for brain in self.catalog():
            brain.getObject().reindexObject(idxs=['state_group'])  # state_group use dms_config


def migrate(context):
    Migrate_To_2_2_1(context).run()
