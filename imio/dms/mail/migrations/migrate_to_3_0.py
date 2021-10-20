# -*- coding: utf-8 -*-
from collective.ckeditortemplates.setuphandlers import FOLDER as default_cke_templ_folder
from collective.contact.plonegroup.config import get_registry_organizations
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from copy import deepcopy
from dexterity.localroles.utils import update_roles_in_fti
from dexterity.localroles.utils import update_security_index
from imio.dms.mail import _tr as _
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IActionsPanelFolderOnlyAdd
from imio.dms.mail.setuphandlers import add_oem_templates
from imio.dms.mail.setuphandlers import add_templates
from imio.dms.mail.setuphandlers import blacklistPortletCategory
from imio.dms.mail.setuphandlers import configure_iem_rolefields
from imio.dms.mail.setuphandlers import createOMailCollections
from imio.dms.mail.setuphandlers import order_1st_level
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.setuphandlers import setup_classification
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_solr_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.migrator.migrator import Migrator
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility
from zope.event import notify
from zope.interface import alsoProvides

import json
import logging

from zope.interface import noLongerProvides

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_3_0(Migrator):  # noqa

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']
        self.contacts = self.portal['contacts']
        self.existing_settings = {}

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
        self.upgradeProfile('collective.contact.core:default')
        self.upgradeProfile('collective.task:default')
        self.upgradeProfile('collective.dms.mailcontent:default')
        self.upgradeProfile('plonetheme.imioapps:default')

        self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'])  # to hide messages-viewlet
        self.runProfileSteps('plonetheme.imioapps', profile='dmsmailskin', steps=['viewlets'])  # to hide colophon
        if not self.portal.portal_quickinstaller.isProductInstalled('imio.pm.wsclient'):
            self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-configure-wsclient'], profile='singles')
        self.runProfileSteps('collective.contact.importexport', steps=['plone.app.registry'])

        self.do_prior_updates()

        self.install(['collective.classification.folder', 'collective.js.tooltipster'])
        self.ps.runAllImportStepsFromProfile('profile-collective.js.tooltipster:themes')

        self.runProfileSteps('imio.dms.mail', steps=['atcttool', 'controlpanel', 'plone.app.registry', 'repositorytool',
                                                     'typeinfo', 'viewlets'])

        # remove to_print related.
        self.remove_to_print()

        # copy localroles from dmsincomingmail to dmsincoming_email
        imfti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(imfti, 'localroles')
        iemfti = getUtility(IDexterityFTI, name='dmsincoming_email')
        setattr(iemfti, 'localroles', deepcopy(lr))
        configure_iem_rolefields(self.portal)

        if api.group.get('createurs_dossier') is None:
            api.group.create('createurs_dossier', '1 Créateurs dossiers')
            for user in api.user.get_users(groupname='dir_general'):
                api.group.add_user(groupname='createurs_dossier', user=user)
        setup_classification(self.portal)
        # xml has been modified since first upgrade
        reimport_faceted_config(self.portal.folders['folder-searches'], xml='classificationfolders-searches.xml',
                                default_UID=self.portal.folders['folder-searches']['all_folders'].UID())
        order_1st_level(self.portal)

        self.runProfileSteps('imio.dms.mail', profile='singles', steps=['imiodmsmail-contact-import-pipeline'])
        self.update_config()
        self.runProfileSteps('imio.dms.mail', profile='examples', steps=['imiodmsmail-configureImioDmsMail'])
        self.runProfileSteps('imio.dms.mail', profile='examples', steps=['imiodmsmail-add-test-folders'])

        # reset workflow
        self.runProfileSteps('imio.dms.mail', steps=['workflow'])
        # Apply workflow adaptations
        applied_adaptations = [dic['adaptation'] for dic in get_applied_adaptations()]
        if applied_adaptations:
            success, errors = apply_from_registry(reapply=True)
            if errors:
                logger.error("Problem applying wf adaptations: %d errors" % errors)
        if 'imio.dms.mail.wfadaptations.TaskServiceValidation' not in applied_adaptations:
            update_task_workflow(self.portal)

        self.portal.portal_workflow.updateRoleMappings()  # update permissions, roles and reindex allowedRolesAndUsers

        # do various global adaptations
        self.update_site()

        # update dmsincomingmails
        self.update_dmsincomingmails()

        # do various adaptations for dmsincoming_email and dmsoutgoing_email
        self.insert_incoming_emails()
        self.insert_outgoing_emails()
        createOMailCollections(self.portal['outgoing-mail']['mail-searches'])

        self.check_previously_migrated_collections()

        # self.catalog.refreshCatalog(clear=1)  # do not work because some indexes use catalog in construction !
        self.update_catalog()

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # update templates
        add_templates(self.portal)
        self.portal['templates'].moveObjectToPosition('d-im-listing-tab', 3)
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-update-templates'], profile='singles')

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['collective.behavior.talcondition', 'collective.ckeditor', 'collective.compoundcriterion',
                     'collective.contact.facetednav', 'collective.contact.importexport', 'collective.dms.basecontent',
                     'collective.eeafaceted.batchactions', 'collective.eeafaceted.dashboard',
                     'collective.eeafaceted.z3ctable', 'collective.wfadaptations', 'collective.z3cform.chosen',
                     'eea.facetednavigation', 'imio.actionspanel', 'imio.dms.mail', 'imio.history', 'imio.pm.wsclient',
                     'plonetheme.imioapps']:
            mark_last_version(self.portal, product=prod)

        # self.refreshDatabase()
        self.finish()

    def do_prior_updates(self):
        # clean dmsconfig to avoid duplications in wf_from_to
        for typ in ('dmsincomingmail', 'dmsoutgoingmail'):
            config = get_dms_config(['wf_from_to', typ, 'n_plus'])
            for direction in ('from', 'to'):
                current_lst = config[direction]
                new_lst = []
                for tup in current_lst:
                    if tup not in new_lst:
                        new_lst.append(tup)
                if len(current_lst) != len(new_lst):
                    set_dms_config(['wf_from_to', typ, 'n_plus', direction], new_lst)
        # update dms config wf_from_to with mark_as_sent transition
        nplus_to = get_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'])
        if ('sent', 'mark_as_sent') not in nplus_to:
            nplus_to.insert(0, ('sent', 'mark_as_sent'))
            set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], nplus_to)
            update_transitions_levels_config(['dmsoutgoingmail'])
        # update dms config wf_from_to with close transition
        nplus_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'])
        if ('closed', 'close') not in nplus_to:
            nplus_to.insert(0, ('closed', 'close'))
            set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'], nplus_to)
            update_transitions_levels_config(['dmsincomingmail'])
            update_transitions_auc_config(['dmsincomingmail'])
        # remove doing_migration from wfadaptations parameters (added by 2.3 migration)
        change = False
        record = []
        adaptations = get_applied_adaptations()
        for info in adaptations:
            if 'doing_migration' in info['parameters']:
                del info['parameters']['doing_migration']
                change = True
            if (info['adaptation'] == u'imio.dms.mail.wfadaptations.OMServiceValidation' and 'validated_from_created'
                    not in info['parameters']):
                value = u'imio.dms.mail.wfadaptations.OMToPrint' in [dic['adaptation'] for dic in adaptations]
                info['parameters']['validated_from_created'] = value
                change = True
            info['parameters'] = json.dumps(info['parameters'], sort_keys=True).decode('utf8')
            record.append(info)
        if change:
            api.portal.set_registry_record(RECORD_NAME, record)

    def update_site(self):
        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.3':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

        # update portal title
        self.portal.title = 'Gestion du courrier 3.0'

        # update tabs
        titles = {'incoming-mail': 'incoming_mail_tab', 'outgoing-mail': 'outgoing_mail_tab', 'folders': 'folders_tab',
                  'tasks': 'tasks_tab', 'contacts': 'contacts_tab', 'templates': 'templates_tab',
                  'tree': 'classification_tree_tab'}
        for oid in titles:
            obj = self.portal[oid]
            obj.title = _(titles[oid])
            obj.reindexObject()

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager',
        #                               'Site Administrator'), acquire=0)
        self.portal.manage_permission('plone.restapi: Use REST API', ('Manager', 'Site Administrator', 'Member'),
                                      acquire=0)
        # registry
        api.portal.set_registry_record(name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.'
                                            'allowed', value=False)

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
        configure_ckeditor(self.portal, custom='ged', filtering='disabled')

        # update templates layout and create oem folders
        self.portal.templates.setLayout('folder_listing')
        add_oem_templates(self.portal)
        record = self.registry.records.get('collective.contact.plonegroup.browser.settings.'
                                           'IContactPlonegroupConfig.organizations')
        notify(RecordModifiedEvent(record, [], []))

        # add group
        if api.group.get('lecteurs_globaux_cs') is None:
            api.group.create('lecteurs_globaux_cs', '2 Lecteurs Globaux CS')
        # change local roles
        to_add = {
            'to_be_signed': {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor']},
                             'lecteurs_globaux_cs': {'roles': ['Reader']}},
            'sent': {'dir_general': {'roles': ['Reader', 'Reviewer']},
                     'lecteurs_globaux_cs': {'roles': ['Reader']}},
        }
        change1 = update_roles_in_fti('dmsoutgoingmail', to_add, notify=False)
        to_add = {
            'to_be_signed': {'encodeur': {'roles': ['Contributor', 'Editor', 'Reviewer']}},
            'sent': {'encodeur': {'roles': ['Reviewer']}},
        }
        change2 = update_roles_in_fti('dmsoutgoingmail', to_add, keyname='treating_groups', notify=False)
        if change1 or change2:
            update_security_index(('dmsoutgoingmail',), trace=10000)

        # update IActionsPanelFolderOnlyAdd interface
        for fld in (self.portal['templates']['om'], self.portal['templates']['oem'],
                    self.contacts['contact-lists-folder']):
            # we search uid folders but also manually created folders
            folders = api.content.find(context=fld, portal_type='Folder')
            for brain in folders:
                folder = brain.getObject()
                if folder == fld:
                    continue
                alsoProvides(folder, IActionsPanelFolderOnlyAdd)
                alsoProvides(folder, INextPrevNotNavigable)
                noLongerProvides(folder, IActionsPanelFolder)
                noLongerProvides(folder, IActionsPanelFolderAll)

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
        """The partially added dmsoutgoing_email is not used... We clean what's configured..."""
        # Set send_modes on dmsoutgoingmails
        brains = self.catalog.searchResults(portal_type='dmsoutgoingmail')
        for brain in brains:
            obj = brain.getObject()
            if not getattr(obj, 'send_modes'):
                obj.send_modes = ['post']
            obj.reindexObject(idxs=['Subject', 'enabled'])

        # allowed types
        self.omf.setConstrainTypesMode(1)
        # self.omf.setLocallyAllowedTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        self.omf.setLocallyAllowedTypes(['dmsoutgoingmail'])
        # self.omf.setImmediatelyAddableTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        self.omf.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        # diff
        pdiff = api.portal.get_tool('portal_diff')
        # pdiff.setDiffForPortalType('dmsoutgoing_email', {'any': "Compound Diff for Dexterity types"})
        if 'dmsoutgoing_email' in pdiff._pt_diffs:
            del pdiff._pt_diffs['dmsoutgoing_email']
            pdiff._p_changed = 1
        # collections
        brains = self.catalog.searchResults(portal_type='DashboardCollection',
                                            path='/'.join(self.omf.getPhysicalPath()))
        for brain in brains:
            col = brain.getObject()
            new_lst = []
            change = False
            for dic in col.query:
                # if dic['i'] == 'portal_type' and len(dic['v']) == 1 and dic['v'][0] == 'dmsoutgoingmail':
                #     dic['v'] = ['dmsoutgoingmail', 'dmsoutgoing_email']
                #     change = True
                if dic['i'] == 'portal_type' and len(dic['v']) == 2 and 'dmsoutgoing_email' in dic['v']:
                    dic['v'] = ['dmsoutgoingmail']
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst
            # add send_modes column
            buf = list(col.customViewFields)
            if u'send_modes' not in buf:
                if 'mail_type' in buf:
                    buf.insert(buf.index('mail_type'), u'send_modes')
                else:
                    buf.append(u'send_modes')
                col.customViewFields = tuple(buf)

    def check_previously_migrated_collections(self):
        # check if changes have been persisted from lower migrations
        # TODO
        pass

    def correct_actions(self):
        pa = self.portal.portal_actions
        if 'portlet' in pa:
            api.content.rename(obj=pa['portlet'], new_id='object_portlet')
            set_portlet(self.portal)

    def remove_to_print(self):
        applied_adaptations = [dic['adaptation'] for dic in get_applied_adaptations()]
        if u'imio.dms.mail.wfadaptations.OMToPrint' not in applied_adaptations:
            return
        logger.info('Removing to_print')
        # clean dms config
        config = get_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'])
        if ('to_print', 'set_to_print') in config:
            config.remove(('to_print', 'set_to_print'))
            set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], value=config)
            update_transitions_levels_config(['dmsoutgoingmail'])

        # clean local roles
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        lrg = lr['static_config']
        if 'to_print' in lrg:
            logger.info("static to_print: '{}'".format(lrg.pop('to_print')))
        lrg = lr['treating_groups']
        if 'to_print' in lrg:
            logger.info("treating_groups to_print: '{}'".format(lrg.pop('to_print')))
        lrg = lr['recipient_groups']
        if 'to_print' in lrg:
            logger.info("recipient_groups to_print: '{}'".format(lrg.pop('to_print')))
        lr._p_changed = True

        # remove collection
        folder = self.omf['mail-searches']
        if 'searchfor_to_print' in folder:
            api.content.delete(obj=folder['searchfor_to_print'])
        col = folder['om_treating']
        query = list(col.query)
        modif = False
        for dic in query:
            if dic['i'] == 'review_state' and 'to_print' in dic['v']:
                modif = True
                dic['v'].remove('to_print')
        if modif:
            col.query = query

        # update remark states
        lst = (api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states')
               or [])
        if 'to_print' in lst:
            lst.remove('to_print')
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states',
                                           lst)

        trs = {'set_to_print': 'set_validated', 'back_to_print': 'back_to_validated'}
        wkf = self.wfTool['outgoingmail_workflow']
        for i, brain in enumerate(self.catalog(portal_type='dmsoutgoingmail'), 1):
            obj = brain.getObject()
            # update history
            wfh = []
            for status in obj.workflow_history.get('outgoingmail_workflow'):
                # replace old state by new one
                if status['review_state'] == 'to_print':
                    status['review_state'] = 'validated'
                # replace old transition by new one
                if status['action'] in trs:
                    status['action'] = trs[status['action']]
                wfh.append(status)
            obj.workflow_history['outgoingmail_workflow'] = tuple(wfh)
            # update state_group (use dms_config), state
            if brain.review_state == 'to_print':
                obj.reindexObject(idxs=['review_state', 'state_group'])

        record = api.portal.get_registry_record(RECORD_NAME)
        api.portal.set_registry_record(RECORD_NAME, [d for d in record if d['adaptation'] !=
                                                     u'imio.dms.mail.wfadaptations.OMToPrint'])

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
        # im fields order to new field config
        im_fo = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order',
                                               default=[])
        if im_fo:
            if 'orig_sender_email' not in im_fo:
                im_fo.insert(im_fo.index('sender'), 'orig_sender_email')
            if 'IClassificationFolder.classification_categories' not in im_fo:
                idx = im_fo.index('internal_reference_no')
                im_fo.insert(idx, 'IClassificationFolder.classification_folders')
                im_fo.insert(idx, 'IClassificationFolder.classification_categories')
            imf = [{"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in im_fo]
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields', imf)
            del self.registry.records['imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order']
        # om fields order to new field config
        om_fo = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order',
                                               default=[])
        if om_fo:
            if 'send_modes' not in om_fo:
                try:
                    idx = om_fo.index('mail_type')
                except ValueError:
                    idx = len(om_fo)
                om_fo.insert(idx, 'send_modes')
                om_fo += ['email_status', 'email_subject', 'email_sender', 'email_recipient', 'email_cc',
                          'email_attachments', 'email_body']
            if 'orig_sender_email' not in om_fo:
                om_fo.insert(om_fo.index('recipients'), 'orig_sender_email')
            if 'IClassificationFolder.classification_categories' not in om_fo:
                idx = om_fo.index('internal_reference_no')
                om_fo.insert(idx, 'IClassificationFolder.classification_folders')
                om_fo.insert(idx, 'IClassificationFolder.classification_categories')
            omf = [{"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in om_fo]
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields', omf)
            del self.registry.records['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order']
        # general config
        if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                              'users_hidden_in_dashboard_filter'):
            api.portal.set_registry_record(
                'imio.dms.mail.browser.settings.IImioDmsMailConfig.users_hidden_in_dashboard_filter', ['scanner'])

        # reimport faceted
        criterias = (
            (self.imf['mail-searches'], 'im-mail', 'all_mails', 'imail_group_encoder'),
            (self.omf['mail-searches'], 'om-mail', 'all_mails', 'omail_group_encoder'),
            (self.portal['tasks']['task-searches'], 'im-task', 'all_tasks', '___'),
            (self.contacts['orgs-searches'], 'organizations', 'all_orgs', 'contact_group_encoder'),
            (self.contacts['persons-searches'], 'persons', 'all_persons', 'contact_group_encoder'),
            (self.contacts['hps-searches'], 'held-positions', 'all_hps', 'contact_group_encoder'),
            (self.contacts['cls-searches'], 'contact-lists', 'all_cls', 'contact_group_encoder'),
        )
        for folder, xml_start, default_id, ge_config in criterias:
            reimport_faceted_config(folder, xml='{}-searches.xml'.format(xml_start),
                                    default_UID=folder[default_id].UID())
            if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(ge_config),
                                              default=False):
                reimport_faceted_config(folder, xml='mail-searches-group-encoder.xml',
                                        default_UID=folder[default_id].UID())

        # update maybe bad local roles (because this record change wasn't handled)
        record = getUtility(IRegistry).records.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                   'org_templates_encoder_can_edit')
        notify(RecordModifiedEvent(record, [], []))

    def update_dmsincomingmails(self):
        for i, brain in enumerate(self.catalog(portal_type='dmsincomingmail', review_state='closed'), 1):
            obj = brain.getObject()
            if i == 1:
                view = IdmUtilsMethods(obj, obj.REQUEST)
            if obj.assigned_user is None:
                for status in obj.workflow_history['incomingmail_workflow']:
                    if status['action'] == 'close':
                        username = status['actor']
                        if view.is_in_user_groups(suffixes=IM_EDITOR_SERVICE_FUNCTIONS, org_uid=obj.treating_groups,
                                                  user=api.user.get(username)):
                            obj.assigned_user = username
                            obj.reindexObject(['assigned_user'])
                        break

    def update_catalog(self):
        """ Update catalog or objects """
        # Lowercased hp email
        brains = self.catalog.searchResults(portal_type='held_position')
        for brain in brains:
            obj = brain.getObject()
            if not obj.email:
                continue
            obj.email = obj.email.lower()
            obj.reindexObject(idxs=['contact_source', 'email'])
        # Clean and update
        brains = self.catalog.searchResults(portal_type=('dmsmainfile', 'dmsommainfile', 'dmsappendixfile'))
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            if i % 10000 == 0:
                logger.info('On file brain {}'.format(i))
            # we removed those useless attributes
            for attr in ('conversion_finished', 'just_added'):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # we update delete permission
            if brain.portal_type == 'dmsappendixfile':
                obj.manage_permission('Delete objects', ('Contributor', 'Editor', 'Manager', 'Site Administrator'),
                                      acquire=1)
            # we update modification permission on incomingmail main file
            if brain.portal_type == 'dmsmainfile':
                obj.manage_permission('Modify portal content', ('DmsFile Contributor', 'Manager', 'Site Administrator'),
                                      acquire=0)
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=['SearchableText', 'sender_index'])


def migrate(context):
    Migrate_To_3_0(context).run()
