# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_groups_mgt
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_groups_mgt
from collective.contact.plonegroup.subscribers import group_deleted as pg_group_deleted
from collective.documentgenerator.utils import update_oo_config
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.messagesviewlet.utils import add_message
from collective.wfadaptations.api import add_applied_adaptation
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from eea.facetednavigation.widgets.storage import Criterion
from imio.dms.mail import AUC_RECORD
from imio.dms.mail import _tr as _
from imio.dms.mail import wfadaptations
from imio.dms.mail.setuphandlers import createTaskCollections
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.subscribers import group_deleted
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_solr_config
from imio.dms.mail.wfadaptations import IMPreManagerValidation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import TaskServiceValidation
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.migrator.migrator import Migrator
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from Products.CPUtils.Extensions.utils import mark_last_version
from Products.PluggableAuthService.interfaces.events import IGroupDeletedEvent
from zope.component import getUtility
from zope.component import globalSiteManager
from zope.interface import alsoProvides

import logging


logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_3(Migrator):  # noqa

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']
        self.wtool = self.portal.portal_workflow

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.3...')

        # check if oo port or solr port must be changed
        update_solr_config()
        update_oo_config()

        # add new dms config used in update_transitions_levels_config
        if 'wf_from_to' not in get_dms_config():
            set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'from'],
                           [('created', 'back_to_creation'), ('proposed_to_manager', 'back_to_manager')])
            set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],
                           [('proposed_to_agent', 'propose_to_agent')])
            set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'from'], [('created', 'back_to_creation')])
            set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'],
                           [('to_be_signed', 'propose_to_be_signed')])

        self.cleanRegistries()

        self.correct_actions()
        auc_stored = self.registry[AUC_RECORD]

        self.upgradeProfile('collective.contact.plonegroup:default')
        self.install(['collective.contact.importexport', 'collective.fontawesome'])
        self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'])  # to hide messages-viewlet
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'plone.app.registry'], run_dependencies=False)

        # add new task collection
        createTaskCollections(self.portal['tasks']['task-searches'])

        # migrate assigned_user_check
        self.update_assigned_user_check(auc_stored)

        # remove service_chief related
        self.remove_service_chief()

        # do various global adaptations
        self.update_site()

        # update daterange criteria
        self.update_dashboards()

        # update templates
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-update-templates'], profile='singles')

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['collective.contact.core', 'collective.contact.widget', 'collective.dms.batchimport',
                     'collective.dms.mailcontent', 'collective.eeafaceted.batchactions',
                     'collective.eeafaceted.collectionwidget', 'collective.eeafaceted.dashboard',
                     'collective.eeafaceted.z3ctable', 'collective.fingerpointing', 'collective.messagesviewlet',
                     'collective.wfadaptations', 'collective.z3cform.datetimewidget', 'communesplone.layout',
                     'eea.facetednavigation', 'eea.jquery', 'imio.actionspanel', 'imio.dashboard', 'imio.dms.mail',
                     'imio.history', 'plone.formwidget.autocomplete', 'plone.formwidget.contenttree',
                     'plonetheme.classic', 'plonetheme.imio.apps']:
            mark_last_version(self.portal, product=prod)

        # self.refreshDatabase()
        self.finish()

    def correct_actions(self):
        pa = self.portal.portal_actions
        if 'portlet' in pa:
            api.content.rename(obj=pa['portlet'], new_id='object_portlet')
            set_portlet(self.portal)

    def update_assigned_user_check(self, auc_stored):
        if isinstance(auc_stored, str):
            return  # already migrated
        skip = u'imio.dms.mail.wfadaptations.IMSkipProposeToServiceChief' in \
               [dic['adaptation'] for dic in get_applied_adaptations()]
        if auc_stored and skip:
            value = u'mandatory'
        elif auc_stored:
            value = u'n_plus_1'
        else:
            value = u'no_check'
        self.registry[AUC_RECORD] = value

    def update_site(self):
        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.2':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')
        # update portal title
        self.portal.title = 'Gestion du courrier 2.3'
        # set om folder as default page
        self.portal.templates.setDefaultPage('om')
        # change permission to remove dashboard from user menu
        self.portal.manage_permission('Portlets: Manage own portlets', ('Manager', 'Site Administrator'), acquire=0)
        # clean old messages
        if 'doc' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['doc'])
        add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="https://docs.imio.be/'
                    u'imio-doc/ia.docs/" target="_blank">documentation en ligne de la '
                    u'version 2.3</a>, dont <a href="https://docs.imio.be/imio-doc/ia.docs/changelog" '
                    u'target="_blank">les nouvelles fonctionnalités</a> ainsi que d\'autres documentations liées.</p>',
                    msg_type='significant', can_hide=True, req_roles=['Authenticated'], activate=True)
        if 'new-version' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['new-version'])
        # update plonegroup
        if not get_registry_groups_mgt():
            set_registry_groups_mgt(['dir_general', 'encodeurs', 'expedition'])
            functions = get_registry_functions()
            for dic in functions:
                if dic['fct_id'] == u'encodeur':
                    dic['fct_title'] = u'Créateur CS'
            set_registry_functions(functions)
        # add group
        if api.group.get('lecteurs_globaux_ce') is None:
            api.group.create('lecteurs_globaux_ce', '2 Lecteurs Globaux CE')
        # change local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        for state in ['proposed_to_manager', 'proposed_to_n_plus_1',
                      'proposed_to_agent', 'in_treatment', 'closed']:
            if state in lrsc:
                if 'lecteurs_globaux_ce' not in lrsc[state]:
                    lrsc[state]['lecteurs_globaux_ce'] = {'roles': ['Reader']}
        lr._p_changed = True   # We need to indicate that the object has been modified and must be "saved"
        # mark tabs to add count on
        for folder_id in ('incoming-mail', 'outgoing-mail', 'tasks'):
            folder = self.portal[folder_id]
            if not ICountableTab.providedBy(folder):
                alsoProvides(folder, ICountableTab)
                folder.reindexObject(idxs='object_provides')

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
        logger.info('Modifying workflows')
        for folder in (self.imf['mail-searches'], self.omf['mail-searches']):
            if 'searchfor_proposed_to_service_chief' in folder:
                api.content.delete(obj=folder['searchfor_proposed_to_service_chief'])

        # clean dms config
        for ptype in ('dmsincomingmail', 'dmsoutgoingmail', 'task'):
            config = get_dms_config(['review_levels', ptype])
            if '_validateur' in config:
                del config['_validateur']
                set_dms_config(keys=['review_levels', ptype], value=config)
            config = get_dms_config(['review_states', ptype])
            if 'proposed_to_service_chief' in config:
                del config['proposed_to_service_chief']
                set_dms_config(keys=['review_states', ptype], value=config)

        def remove_localrole_validateur(dic1):
            for state1 in dic1:
                if 'validateur' in dic1[state1]:
                    del dic1[state1]['validateur']

        # clean local roles
        for ptype in ('dmsincomingmail', 'dmsoutgoingmail'):
            fti = getUtility(IDexterityFTI, name=ptype)
            lr = getattr(fti, 'localroles')
            lrg = lr['static_config']
            if 'proposed_to_service_chief' in lrg:
                del lrg['proposed_to_service_chief']
                remove_localrole_validateur(lrg)
            lrg = lr['treating_groups']
            if 'proposed_to_service_chief' in lrg:
                del lrg['proposed_to_service_chief']
                remove_localrole_validateur(lrg)
            lrg = lr['recipient_groups']
            if 'proposed_to_service_chief' in lrg:
                del lrg['proposed_to_service_chief']
                remove_localrole_validateur(lrg)
            lr._p_changed = True
        # on task
        fti = getUtility(IDexterityFTI, name='task')
        lr = getattr(fti, 'localroles')
        lrg = lr['assigned_group']
        if 'validateur' in lrg['to_do']:
            remove_localrole_validateur(lrg)
        lrg = lr['parents_assigned_groups']
        if 'validateur' in lrg['to_do']:
            remove_localrole_validateur(lrg)
        lr._p_changed = True

        # update registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        for entry in ('dmsincomingmail.back_to_service_chief|', 'dmsoutgoingmail.back_to_service_chief|'):
            if entry not in lst:
                break
            lst.remove(entry)
        else:
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)

        # update remark states
        for attr in ('imail_remark_states', 'omail_remark_states'):
            lst = (api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(attr))
                   or [])
            if 'proposed_to_service_chief' in lst:
                lst.remove('proposed_to_service_chief')
                api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(attr),
                                               lst)

        # Manage workflows and wfadaptations
        functions = get_registry_functions()
        if 'validateur' not in [fct['fct_id'] for fct in functions]:
            return  # apply the following only once

        def remove_adaptation_from_registry(name):
            record = api.portal.get_registry_record(RECORD_NAME)
            api.portal.set_registry_record(RECORD_NAME, [d for d in record if d['adaptation'] != name])

        # reset workflows
        self.runProfileSteps('imio.dms.mail', steps=['workflow'])
        # self.portal.portal_workflow.updateRoleMappings()  # done later

        # Apply workflow adaptations if necessary
        applied_wfa = [dic['adaptation'] for dic in get_applied_adaptations()]
        n_plus_1_params = {'validation_level': 1, 'state_title': u'À valider par le chef de service',
                           'forward_transition_title': u'Proposer au chef de service',
                           'backward_transition_title': u'Renvoyer au chef de service',
                           'function_title': u'N+1'}
        task_adapt = True
        for wkf, acr in (('incomingmail_workflow', 'IM'), ('outgoingmail_workflow', 'OM')):
            if u'imio.dms.mail.wfadaptations.{}SkipProposeToServiceChief'.format(acr) in applied_wfa:
                remove_adaptation_from_registry(u'imio.dms.mail.wfadaptations.{}SkipProposeToServiceChief'.format(acr))
                task_adapt = False
                if acr == 'OM':
                    folder = self.omf['mail-searches']
                    if folder['to_validate'].enabled:
                        folder['to_validate'].enabled = False
                        folder['to_validate'].reindexObject()
            else:
                logger.info('Applying {}ServiceValidation wf adaptation'.format(acr))
                sva = getattr(wfadaptations, '{}ServiceValidation'.format(acr))()
                adapt_is_applied = sva.patch_workflow(wkf, **n_plus_1_params)
                if adapt_is_applied:
                    add_applied_adaptation('imio.dms.mail.wfadaptations.{}ServiceValidation'.format(acr),
                                           wkf, True, **n_plus_1_params)

        # update task_workflow
        update_task_workflow(self.portal)
        if task_adapt:
            tsva = TaskServiceValidation()
            adapt_is_applied = tsva.patch_workflow('task_workflow', **{})
            if adapt_is_applied:
                add_applied_adaptation('imio.dms.mail.wfadaptations.TaskServiceValidation', 'task_workflow', False)
        else:
            # update collections
            folder = self.portal['tasks']['task-searches']
            for cid in ('to_assign', 'to_close'):
                if folder[cid].enabled:
                    folder[cid].enabled = False
                    folder[cid].reindexObject()

        invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')

        # replace EmergencyZoneAdaptation
        im_workflow = self.wtool['incomingmail_workflow']
        if u'imio.dms.mail.wfadaptations.EmergencyZone' in applied_wfa:
            state = im_workflow.states['proposed_to_manager']
            state.title = u'À valider par le CZ'.encode('utf8')
            for tr, tit in (('back_to_manager', u'Renvoyer au CZ'), ('propose_to_manager', u'Proposer au CZ')):
                transition = im_workflow.transitions[tr]
                transition.title = tit.encode('utf8')
            logger.info('Removing EmergencyZone wf adaptation')
            remove_adaptation_from_registry(u'imio.dms.mail.wfadaptations.EmergencyZone')

        # redo OMToPrintAdaptation
        if u'imio.dms.mail.wfadaptations.OMToPrint' in applied_wfa:
            logger.info('Applying OMToPrint wf adaptation')
            tpa = OMToPrintAdaptation()
            tpa.patch_workflow('outgoingmail_workflow')

        # redo IMPreManagerValidation
        if u'imio.dms.mail.wfadaptations.IMPreManagerValidation' in applied_wfa:
            logger.info('Applying IMPreManagerValidation wf adaptation')
            params = [dic['parameters'] for dic in get_applied_adaptations()
                      if dic['adaptation'] == u'imio.dms.mail.wfadaptations.IMPreManagerValidation'][0]
            remove_adaptation_from_registry(u'imio.dms.mail.wfadaptations.IMPreManagerValidation')
            del params['collection_title']
            pmva = IMPreManagerValidation()
            adapt_is_applied = pmva.patch_workflow('incomingmail_workflow', **params)
            if adapt_is_applied:
                add_applied_adaptation('imio.dms.mail.wfadaptations.IMPreManagerValidation',
                                       'incoming_mail', False, **params)

        # update wf history to replace review_state and correct history
        config = {'dmsincomingmail': {'wf': 'incomingmail_workflow',
                                      'st': {'proposed_to_service_chief': 'proposed_to_n_plus_1'},
                                      'tr': {'propose_to_service_chief': 'propose_to_n_plus_1',
                                             'back_to_service_chief': 'back_to_n_plus_1'}},
                  'dmsoutgoingmail': {'wf': 'outgoingmail_workflow',
                                      'st': {'proposed_to_service_chief': 'proposed_to_n_plus_1'},
                                      'tr': {'propose_to_service_chief': 'propose_to_n_plus_1',
                                             'back_to_service_chief': 'back_to_n_plus_1'}}
                  }
        for pt in config:
            for brain in self.catalog(portal_type=pt):
                obj = brain.getObject()
                # update history
                wfh = []
                wkf = self.wtool[config[pt]['wf']]
                for status in obj.workflow_history.get(config[pt]['wf']):
                    # replace old state by new one
                    if status['review_state'] in config[pt]['st']:
                        status['review_state'] = config[pt]['st'][status['review_state']]
                    # replace old transition by new one
                    if status['action'] in config[pt]['tr']:
                        status['action'] = config[pt]['tr'][status['action']]
                    wfh.append(status)
                obj.workflow_history[config[pt]['wf']] = tuple(wfh)
                # update permissions and roles
                wkf.updateRoleMappingsFor(obj)
                # update state_group (use dms_config), permissions, state
                obj.reindexObject(idxs=['allowedRolesAndUsers', 'review_state', 'state_group'])
                for child in obj.objectValues():
                    child.reindexObject(idxs=['allowedRolesAndUsers'])

        # migrate plone groups
        # First unregister group deletion handlers
        globalSiteManager.unregisterHandler(pg_group_deleted, (IGroupDeletedEvent,))
        globalSiteManager.unregisterHandler(group_deleted, (IGroupDeletedEvent,))
        # move users from _validateur to _n_plus_1
        for group in api.group.get_groups():
            if group.id.endswith('_validateur'):
                org = group.id.split('_')[0]
                np1group = api.group.get('{}_n_plus_1'.format(org))
                if np1group:
                    for user in api.user.get_users(group=group):
                        api.group.add_user(group=np1group, user=user)
                        api.group.remove_user(group=group, user=user)
                api.group.delete(group=group)
        # register again group deletion handlers
        globalSiteManager.registerHandler(pg_group_deleted, (IGroupDeletedEvent,))
        globalSiteManager.registerHandler(group_deleted, (IGroupDeletedEvent,))

        # remove validateur function
        functions = get_registry_functions()
        if 'validateur' in [fct['fct_id'] for fct in functions]:
            set_registry_functions([fct for fct in functions if fct['fct_id'] != 'validateur'])


def migrate(context):
    Migrate_To_2_3(context).run()
