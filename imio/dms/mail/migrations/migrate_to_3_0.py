# -*- coding: utf-8 -*-
import transaction
from collective.ckeditortemplates.setuphandlers import FOLDER as default_cke_templ_folder
from collective.contact.plonegroup.config import get_registry_organizations
from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.task.content.task import Task
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from copy import deepcopy
from datetime import datetime
from dexterity.localroles.utils import update_roles_in_fti
from dexterity.localroles.utils import update_security_index
from eea.facetednavigation.criteria.interfaces import ICriteria
from imio.dms.mail import _tr as _
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import GE_CONFIG
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import MAIN_FOLDERS
from imio.dms.mail.content.behaviors import default_creating_group
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IActionsPanelFolderOnlyAdd
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.setuphandlers import add_oem_templates
from imio.dms.mail.setuphandlers import add_templates
from imio.dms.mail.setuphandlers import blacklistPortletCategory
from imio.dms.mail.setuphandlers import configure_iem_rolefields
from imio.dms.mail.setuphandlers import createOMailCollections
from imio.dms.mail.setuphandlers import list_templates
from imio.dms.mail.setuphandlers import order_1st_level
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.setuphandlers import setup_classification
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.utils import create_period_folder_max
from imio.dms.mail.utils import ensure_set_field
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import is_in_user_groups
from imio.dms.mail.utils import is_valid_identifier
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_solr_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.helpers.content import find
from imio.helpers.emailer import get_mail_host
from imio.helpers.security import get_environment
from imio.helpers.workflow import remove_state_transitions
from imio.migrator.migrator import Migrator
from imio.pyutils.system import get_git_tag
from imio.pyutils.system import load_var
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from plone.dexterity.interfaces import IDexterityFTI
from plone.i18n.normalizer import IIDNormalizer
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.CPUtils.Extensions.utils import mark_last_version
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from unidecode import unidecode
from zExceptions import Redirect
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.event import notify
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import json
import logging
import os


logger = logging.getLogger('imio.dms.mail')


class Migrate_To_3_0(Migrator):  # noqa

    def __init__(self, context, disable_linkintegrity_checks=False):
        Migrator.__init__(self, context, disable_linkintegrity_checks=disable_linkintegrity_checks)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']
        self.acl = self.portal['acl_users']
        self.contacts = self.portal['contacts']
        self.existing_settings = {}
        self.config = {'om_mt': [], 'flds': None}
        load_var(os.path.join(BLDT_DIR, '30_config.dic'), self.config)
        self.none_mail_type = False
        self.batch_value = int(os.getenv('BATCH', '0'))
        self.commit_value = int(os.getenv('COMMIT', '0'))

    def savepoint_flush(self):
        transaction.savepoint(True)
        self.portal._p_jar.cacheGC()

    def set_fingerpointing(self, activate=None, itself=True):
        """Activate/deactivate some fingerpointing settings.
        :param activate: list of previous values ([True, True]) needed to reactivate and returned at deactivation
        :param itself: change audit_registry value to not register this special change
        :return: list of previous values
        """
        ret = []
        fp_fields = ['audit_lifecycle', 'audit_workflow']
        if itself:  # registry
            if activate:
                fp_fields.append('audit_registry')
                activate.append(activate.pop(0))  # put at end the orig audit_registry value
            else:
                fp_fields.insert(0, 'audit_registry')
        for i, fp_field in enumerate(fp_fields):
            key = 'collective.fingerpointing.interfaces.IFingerPointingSettings.{}'.format(fp_field)
            ret.append(api.portal.get_registry_record(key))
            if activate is None:
                api.portal.set_registry_record(key, False)
            else:
                api.portal.set_registry_record(key, activate[i])
        return ret

    def run(self):
        logger.info('Migrating to imio.dms.mail 3.0...')
        self.log_mem('START')
        if self.config['om_mt']:
            logger.info('Loaded config {}'.format(self.config))
            mtypes = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types',
                                                    default=[])
            mtypes = [dic.get('mt_value', dic.get('value')) for dic in mtypes]
            smodes = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                    'omail_send_modes', default=[])
            if smodes:
                smodes = [dic.get('mt_value', dic.get('value')) for dic in smodes]
            else:  # will be set later in update_config
                smodes = [dic['nid'] for dic in self.config['om_mt']]
            oids = [dic['oid'] for dic in self.config['om_mt']]
            if not [mt for mt in mtypes if mt not in oids]:  # configured mail types are handled in 30_config
                logger.info('OM MAIL_TYPE WILL BE SET TO NONE')
                self.none_mail_type = True
            stop = False
            for dic in self.config['om_mt']:
                mtype = dic['oid']
                if mtype not in mtypes:
                    logger.warning(u"config mtype '{}' not in '{}'".format(mtype, mtypes))
                smode = dic['nid']
                if smode not in smodes:
                    stop = True
                    logger.error(u"config sm '{}' not in '{}'".format(smode, smodes))
            if stop:
                raise Exception('Bad config file 30_config.dic')

        if self.config['flds'] is None:  # not in config file
            if 'folders' not in self.portal:  # first time migration
                self.config['flds'] = True
            else:
                rec_name = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields'
                showed = [dic['field_name'] for dic in api.portal.get_registry_record(rec_name)]
                if u'IClassificationFolder.classification_folders' in showed:  # activated
                    self.config['flds'] = True
                else:
                    self.config['flds'] = False

        for mt in ('mail_types', 'omail_types'):
            mtr = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(mt)
            self.existing_settings[mt] = api.portal.get_registry_record(mtr)

        if self.is_in_part('a'):  # install and upgrade products
            # check if oo port or solr port must be changed
            update_solr_config()
            active_solr = api.portal.get_registry_record('collective.solr.active', default=None)
            if active_solr:
                logger.info('Deactivating solr')
                api.portal.set_registry_record('collective.solr.active', False)

            self.upgradeProfile('collective.documentgenerator:default')
            update_oo_config()

            self.cleanRegistries()

            self.correct_actions()

            self.correct_groups()

            self.install(['collective.ckeditortemplates', 'collective.fingerpointing'])
            if default_cke_templ_folder in self.portal:
                api.content.delete(obj=self.portal[default_cke_templ_folder])
            self.upgradeProfile('collective.contact.core:default')
            transaction.commit()
            self.upgradeProfile('collective.task:default')
            self.upgradeProfile('collective.dms.mailcontent:default')
            self.upgradeProfile('plonetheme.imioapps:default')

            self.runProfileSteps('plonetheme.imioapps', steps=['viewlets'],
                                 run_dependencies=False)  # to hide messages-viewlet
            self.runProfileSteps('plonetheme.imioapps', profile='dmsmailskin', steps=['viewlets'],
                                 run_dependencies=False)  # to hide colophon
            if not self.portal.portal_quickinstaller.isProductInstalled('imio.pm.wsclient'):
                self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-configure-wsclient'], profile='singles')
            self.runProfileSteps('collective.contact.importexport', steps=['plone.app.registry'],
                                 run_dependencies=False)

            self.do_prior_updates()

            self.install(['collective.classification.folder', 'collective.js.tooltipster', 'imio.helpers',
                          'Products.cron4plone'])
            self.ps.runAllImportStepsFromProfile('profile-collective.js.tooltipster:themes')

        if self.is_in_part('b'):  # idm steps, config, folders
            self.runProfileSteps('imio.dms.mail', steps=['actions', 'atcttool', 'catalog', 'controlpanel',
                                                         'plone.app.registry', 'repositorytool', 'rolemap', 'typeinfo',
                                                         'viewlets'])
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

            orig = self.set_fingerpointing()
            self.runProfileSteps('imio.dms.mail', profile='singles', steps=['imiodmsmail-contact-import-pipeline'],
                                 run_dependencies=False)
            self.set_fingerpointing(orig)
            self.update_config()
            if self.config['flds']:
                self.runProfileSteps('imio.dms.mail', profile='singles', steps=['imiodmsmail-activate_classification'],
                                     run_dependencies=False)
            else:
                self.runProfileSteps('imio.dms.mail', profile='singles',
                                     steps=['imiodmsmail-deactivate_classification'], run_dependencies=False)
            self.runProfileSteps('imio.dms.mail', profile='examples', steps=['imiodmsmail-configureImioDmsMail'],
                                 run_dependencies=False)
            # clean example users wrongly added by previous migration
            self.clean_examples()

        if self.is_in_part('c'):  # workflow
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
            # update permissions, roles and reindex allowedRolesAndUsers
            count = self.portal.portal_workflow.updateRoleMappings()
            logger.info('Updated {} items'.format(count))

        if self.is_in_part('d'):  # update site
            # do various global adaptations
            self.update_site()
            self.update_tasks()

        if self.is_in_part('e'):  # update dmsincomingmails
            # update dmsincomingmails
            self.update_dmsincomingmails()

        if self.is_in_part('f'):  # insert incoming emails
            # do various adaptations for dmsincoming_email
            self.insert_incoming_emails()

        if self.is_in_part('g'):  # insert outgoing emails
            self.insert_outgoing_emails()
            createOMailCollections(self.portal['outgoing-mail']['mail-searches'])
            self.check_previously_migrated_collections()

        # self.catalog.refreshCatalog(clear=1)  # do not work because some indexes use catalog in construction !

        if self.is_in_part('i'):  # move incoming mails (long time, batchable)
            self.move_dmsincomingmails()

        if self.is_in_part('j'):  # move outgoing mails (long time, batchable)
            self.move_dmsoutgoingmails()

        if self.is_in_part('m'):  # update held positions
            self.update_catalog1()

        if self.is_in_part('n'):  # update dmsmainfile (middle time, batchable)
            self.update_catalog2()

        if self.is_in_part('o'):  # update dmsommainfile
            self.update_catalog3()

        if self.is_in_part('p'):  # update appendixfile
            self.update_catalog4()

        if self.is_in_part('q'):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            self.upgradeAll(omit=[u'imio.dms.mail:default', u'collective.js.chosen:default',
                                  u'collective.z3cform.chosen:default'])

        if self.is_in_part('r'):  # update templates
            # TEMPORARY to 3.0.39
            # brains = api.content.find(context=self.portal.templates.om)
            # for brain in brains:
            #     brain.getObject().reindexObject(['enabled'])
            # # labels query field
            # self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry'])
            # # labels index on om
            # # remove accented chars grom orig_sender_email
            # for brain in self.catalog(portal_type=('dmsincoming_email', 'dmsoutgoingmail')):
            #     obj = brain.getObject()
            #     ose = getattr(obj, 'orig_sender_email')
            #     if ose and ose != unidecode(ose):
            #         obj.orig_sender_email = unidecode(ose)
            #     if brain.portal_type == 'dmsoutgoingmail':
            #         obj.reindexObject(['labels'])
            # TEMPORARY to 3.0.40
            # configure MailHost
            # if get_environment() == 'prod':
            #     mail_host = get_mail_host()
            #     mail_host.smtp_queue = True
            #     mail_host.smtp_queue_directory = "mailqueue"
            #     # (re)start the mail queue
            #     mail_host._stopQueueProcessorThread()
            #     mail_host._startQueueProcessorThread()
            #
            # # upgrade classification.folder to replace chosen by select2
            # self.upgradeProfile('collective.dms.basecontent:default')
            # self.upgradeProfile('collective.classification.folder:default')
            # END

            self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])
            self.cleanRegistries()
            api.portal.set_registry_record('imio.dms.mail.product_version', safe_unicode(get_git_tag(BLDT_DIR)))
            # update templates
            self.portal['templates'].moveObjectToPosition('d-im-listing-tab', 3)
            self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-create-templates',
                                                         'imiodmsmail-update-templates'], profile='singles')

        if self.is_in_part('s'):  # update quick installer
            # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
            self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

            for prod in ['collective.behavior.talcondition', 'collective.ckeditor', 'collective.compoundcriterion',
                         'collective.contact.core', 'collective.contact.duplicated', 'collective.contact.facetednav',
                         'collective.contact.importexport', 'collective.contact.plonegroup',
                         'collective.contact.widget', 'collective.dms.basecontent', 'collective.dms.batchimport',
                         'collective.dms.mailcontent', 'collective.documentgenerator',
                         'collective.eeafaceted.batchactions', 'collective.eeafaceted.collectionwidget',
                         'collective.eeafaceted.dashboard', 'collective.eeafaceted.z3ctable',
                         'collective.js.tooltipster', 'collective.task', 'collective.wfadaptations',
                         'dexterity.localroles', 'dexterity.localrolesfield',
                         'eea.facetednavigation', 'eea.jquery', 'imio.actionspanel', 'imio.dashboard', 'imio.dms.mail',
                         'imio.helpers', 'imio.history', 'imio.pm.wsclient', 'plonetheme.imioapps']:
                mark_last_version(self.portal, product=prod)

        if self.is_in_part('x'):  # clear solr
            active_solr = api.portal.get_registry_record('collective.solr.active', default=None)
            if active_solr is not None:
                if not active_solr:
                    logger.info('Activating solr')
                    api.portal.set_registry_record('collective.solr.active', True)
                logger.info('Clearing solr on %s' % self.portal.absolute_url_path())
                maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
                maintenance.clear()

        if self.is_in_part('y'):  # sync solr (long time, batchable)
            self.sync_solr()

        self.log_mem('END')
        logger.info("Really finished at {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
            update_transitions_auc_config(['dmsincomingmail'])
        update_transitions_levels_config(['dmsincomingmail'])
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
            if obj.title != _(titles[oid]):
                obj.title = _(titles[oid])
                obj.reindexObject()

        # update folder period
        if getattr(self.portal[MAIN_FOLDERS['dmsincomingmail']], 'folder_period', None) is None:
            setattr(self.portal[MAIN_FOLDERS['dmsincomingmail']], 'folder_period', u'week')
        if getattr(self.portal[MAIN_FOLDERS['dmsoutgoingmail']], 'folder_period', None) is None:
            setattr(self.portal[MAIN_FOLDERS['dmsoutgoingmail']], 'folder_period', u'week')

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager',
        #                               'Site Administrator'), acquire=0)
        self.portal.manage_permission('plone.restapi: Use REST API', ('Manager', 'Site Administrator', 'Member'),
                                      acquire=0)
        # registry
        api.portal.set_registry_record(name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.'
                                            'allowed', value=False)

        if 'doc' in self.portal['messages-config'] and \
                u'version 3.0' not in self.portal['messages-config']['doc'].text.raw:
            api.content.delete(self.portal['messages-config']['doc'])
        # not added if already exists
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
        if api.group.get('gestion_contacts') is None:
            api.group.create('gestion_contacts', '1 Gestion doublons contacts')
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
        to_add = {  # additional roles needed for outgoing emails
            'to_be_signed': {'encodeur': {'roles': ['Contributor', 'Editor', 'Reviewer']}},
            'sent': {'encodeur': {'roles': ['Reviewer']}},
        }
        send_modes = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                                    'omail_send_modes')
        email_modes = [sm['value'] for sm in send_modes if sm['value'].startswith('email') and sm['active']]
        change2 = False
        if email_modes:
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
                folder.reindexObject(['enabled'])
                alsoProvides(folder, IActionsPanelFolderOnlyAdd)
                alsoProvides(folder, INextPrevNotNavigable)
                noLongerProvides(folder, IActionsPanelFolder)
                noLongerProvides(folder, IActionsPanelFolderAll)
        # add _editeur as contact contributor
        s_orgs = get_registry_organizations()
        for folder in (self.contacts, self.contacts['contact-lists-folder']['common']):
            dic = folder.__ac_local_roles__
            for uid in s_orgs:
                dic["%s_editeur" % uid] = ['Contributor']  # an agent could add a contact on an email im
            folder._p_changed = True
        for fld in api.content.find(context=self.contacts['contact-lists-folder'], portal_type='Folder'):
            folder = fld.getObject()
            dic = folder.__ac_local_roles__
            if '{}_encodeur'.format(folder.id) not in dic:
                continue
            dic["%s_editeur" % folder.id] = ['Contributor', 'Editor', 'Reader']
            folder._p_changed = True

        # protect objects
        for obj in (
                self.portal['incoming-mail'], self.portal['incoming-mail']['mail-searches'],
                self.portal['outgoing-mail'], self.portal['outgoing-mail']['mail-searches'],
                self.portal['tasks'], self.portal['tasks']['task-searches'],
                self.portal['contacts'], self.portal['contacts']['orgs-searches'],
                self.portal['contacts']['hps-searches'], self.portal['contacts']['persons-searches'],
                self.portal['contacts']['cls-searches'], self.portal['contacts']['plonegroup-organization'],
                self.portal['contacts']['personnel-folder'], self.portal['contacts']['contact-lists-folder'],
                self.portal['contacts']['contact-lists-folder']['common'],
                self.portal['folders'], self.portal['folders']['folder-searches'], self.portal['tree'],
                self.portal['templates'], self.portal['templates']['om'], self.portal['templates']['om']['common'],
                self.portal['templates']['oem']):
            alsoProvides(obj, IProtectedItem)
        for brain in self.catalog(portal_type='DashboardCollection'):
            alsoProvides(brain.getObject(), IProtectedItem)
        for tup in list_templates():
            try:
                obj = self.portal.restrictedTraverse(tup[1])
                alsoProvides(obj, IProtectedItem)
            except AttributeError:
                pass

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
        mt_2_sm = {dic['oid']: dic['nid'] for dic in self.config['om_mt']}
        ensure = False
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder'):
            ensure = True
            logger.info('Updates dmsoutgoingmails to ensure creating_group field is set')
        unk_mt = {}
        brains = self.catalog.searchResults(portal_type='dmsoutgoingmail')
        for brain in brains:
            obj = brain.getObject()
            if ensure:
                self.ensure_creating_group(obj, index=False)  # assigned_group index
            if not getattr(obj, 'send_modes'):
                # set send_modes following mail_type
                if self.config['om_mt'] and obj.mail_type:
                    if obj.mail_type in mt_2_sm:
                        obj.send_modes = [mt_2_sm[obj.mail_type]]
                        if self.none_mail_type:
                            obj.mail_type = None
                    else:
                        unk_mt.setdefault(obj.mail_type, 0)
                        unk_mt[obj.mail_type] += 1
                        logger.error(u"Unknown mail_type '{}' on {}".format(obj.mail_type, obj.absolute_url()))
                else:
                    obj.send_modes = ['post']
            obj.reindexObject(idxs=['Subject', 'assigned_group', 'enabled', 'mail_type', 'markers'])
        if unk_mt:
            logger.error("THERE ARE UNKNOWN MAIL TYPES. WE HAVE TO UPDATE 30_config.dic !")
            for mt in unk_mt:
                logger.error(u"value '{}' found {} times".format(mt, unk_mt[mt]))

        omf = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields')
        mtypes = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types',
                                                default=[])
        if ([dic for dic in omf if dic['field_name'] == 'mail_type'] or
                [dic for dic in mtypes if dic['active']]):
            n_mtypes = []
            remove_mtype = True
            for mtype in mtypes:
                brains = self.catalog.searchResults(portal_type='dmsoutgoingmail', mail_type=mtype['value'])
                if brains:
                    logger.warning("mtype '{}' is yet used after migration, on {} OMs".format(mtype, len(brains)))
                    remove_mtype = False
                else:
                    mtype['active'] = False
                n_mtypes.append(mtype)
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types', n_mtypes)
            if remove_mtype:
                logger.info("Disabling om mail_type field, no more used")
                n_omf = [dic for dic in omf if dic['field_name'] != 'mail_type']
                if len(n_omf) != len(omf):
                    api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields',
                                                   n_omf)
                # remove collections column
                brains = self.catalog(portal_type='DashboardCollection', path='/'.join(self.omf.getPhysicalPath()))
                for brain in brains:
                    col = brain.getObject()
                    buf = list(col.customViewFields)
                    if u'mail_type' in buf:
                        buf.remove(u'mail_type')
                        col.customViewFields = tuple(buf)
                # remove filter
                folder = self.omf['mail-searches']
                criterias = ICriteria(folder)
                criterion = criterias.get('c9')
                if not criterion.hidden:
                    criterion.hidden = True
                    criterias.criteria._p_changed = 1

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

    def correct_groups(self):
        for group in api.group.get_groups():
            for principal in api.user.get_users(group=group):
                user = self.acl.getUserById(principal.id)
                if user is None:  # we have a group
                    logger.info("Removing principal '{}' from group '{}'".format(principal.id, group.id))
                    for user in api.user.get_users(group=principal):
                        api.group.add_user(user=user, group=group)
                    api.group.remove_user(user=principal, group=group)

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

    def update_mailtype_config(self):
        idnormalizer = getUtility(IIDNormalizer)
        for mt, ptype in (('mail_types', ['dmsincomingmail', 'dmsincoming_email']), ('omail_types', 'dmsoutgoingmail')):
            mtr = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(mt)
            mail_types = self.existing_settings[mt]
            new_mt = []
            change = False
            for dic in mail_types:
                new_dic = dict(dic)
                if 'mt_value' in dic:
                    change = True
                    new_dic = {'value': dic['mt_value'], 'dtitle': dic['mt_title'], 'active': dic['mt_active']}
                if not is_valid_identifier(new_dic['value']):
                    change = True
                    old_value = new_dic['value']
                    new_dic['value'] = safe_unicode(idnormalizer.normalize(old_value))
                    for brain in self.catalog(portal_type=ptype, mail_type=old_value):
                        obj = brain.getObject()
                        obj.mail_type = new_dic['value']
                        obj.reindexObject(['mail_type'])
                new_mt.append(new_dic)
            if change:
                api.portal.set_registry_record(mtr, new_mt)

    def update_config(self):
        # modify settings following new structure and correct id if necessary
        self.update_mailtype_config()
        # set default send_modes values
        if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes',
                                              default=[]):
            smodes = []
            for dic in self.config['om_mt']:
                if dic['nid'] not in [dc['value'] for dc in smodes]:  # avoid duplicates
                    smodes.append({'value': dic['nid'], 'dtitle': dic['t'], 'active': dic['a']})
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes', smodes)
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
        # update wsclient settings
        from imio.pm.wsclient.browser.vocabularies import pm_meeting_config_id_vocabulary
        orig_call = pm_meeting_config_id_vocabulary.__call__
        from imio.dms.mail.subscribers import wsclient_configuration_changed
        from plone.registry.interfaces import IRecordModifiedEvent
        gsm = getGlobalSiteManager()
        prefix = 'imio.pm.wsclient.browser.settings.IWS4PMClientSettings'
        gen_acts = api.portal.get_registry_record('{}.generated_actions'.format(prefix))
        is_activated = False
        changes = False
        new_acts = []
        for act in gen_acts:
            new_act = dict(act)
            if act['permissions'] != 'Modify view template':
                is_activated = True
            if act['condition'] == u"python: context.getPortalTypeName() in ('dmsincomingmail', )":
                changes = True
                new_act['condition'] = u"python: context.getPortalTypeName() in ('dmsincomingmail', " \
                                       u"'dmsincoming_email')"
            new_acts.append(new_act)
        if changes:
            if not is_activated:
                gsm.unregisterHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
                pm_meeting_config_id_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
                    [SimpleTerm(u'meeting-config-college')])
            api.portal.set_registry_record('{}.generated_actions'.format(prefix), new_acts)
            if not is_activated:
                gsm.registerHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
                pm_meeting_config_id_vocabulary.__call__ = orig_call

        # define default preservation value
        if (not api.portal.get_registry_record('imio.dms.mail.dv_clean_days') and
                not api.portal.get_registry_record('imio.dms.mail.dv_clean_date')):
            api.portal.set_registry_record('imio.dms.mail.dv_clean_days', 180)
        # define default folder_period
        if not api.portal.get_registry_record('imio.dms.mail.imail_folder_period'):
            api.portal.set_registry_record('imio.dms.mail.imail_folder_period', u'week')
        if not api.portal.get_registry_record('imio.dms.mail.omail_folder_period'):
            api.portal.set_registry_record('imio.dms.mail.omail_folder_period', u'week')

        # define subfolder period
        if not api.portal.get_registry_record('imio.dms.mail.imail_folder_period'):
            api.portal.set_registry_record('imio.dms.mail.imail_folder_period', u'week')
        if not api.portal.get_registry_record('imio.dms.mail.omail_folder_period'):
            api.portal.set_registry_record('imio.dms.mail.omail_folder_period', u'week')
        # cron4plone settings
        cron_configlet = getUtility(ICronConfiguration, 'cron4plone_config')
        if not cron_configlet.cronjobs:
            # Syntax: m h dom mon command.
            cron_configlet.cronjobs = [u'45 18 1,15 * portal/@@various-utils/dv_images_clean']
        # update actionspanel transitions config
        key = 'imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'
        values = api.portal.get_registry_record(key)
        new_values = []
        for val in values:
            if val.startswith('dmsincomingmail.'):
                email_val = val.replace('dmsincomingmail.', 'dmsincoming_email.')
                if email_val not in values:
                    new_values.append(email_val)
        if new_values:
            api.portal.set_registry_record(key, list(values) + new_values)

    def update_dmsincomingmails(self):
        ensure = False
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'):
            ensure = True
            logger.info('Updates dmsincomingmails to ensure creating_group field is set')
        for i, brain in enumerate(self.catalog(portal_type='dmsincomingmail'), 1):
            obj = brain.getObject()
            obj.reindexObject(['markers'])
            if obj.assigned_user is None and brain.review_state == 'closed':
                for status in obj.workflow_history['incomingmail_workflow']:
                    if status['action'] == 'close':
                        userid = status['actor']
                        if is_in_user_groups(suffixes=IM_EDITOR_SERVICE_FUNCTIONS, org_uid=obj.treating_groups,
                                             user=api.user.get(userid)):
                            obj.assigned_user = userid
                            obj.reindexObject(['assigned_user'])
                        break
            if ensure:
                self.ensure_creating_group(obj, index=True)
            if self.commit_value and i % self.commit_value == 0:
                logger.info('On dmsincomingmail update {}'.format(i))
                transaction.commit()

    def move_dmsincomingmails(self):
        logger.info('Moving dmsincomingmails')
        orig = self.set_fingerpointing()
        imf_path = '/'.join(self.imf.getPhysicalPath())
        counter_dic = {}
        brains = self.catalog(portal_type=['dmsincomingmail', 'dmsincoming_email'],
                              sort_on='organization_type', path={'query': imf_path, 'depth': 1})
        moved = 0
        for brain in brains:
            moved += 1
            if self.batch_value and moved > self.batch_value:  # so it is possible to run this step partially
                break
            obj = brain.getObject()
            if obj.reception_date is None:
                logger.warning("Found None reception_date on '{}'".format(brain.getPath()))
                obj.reception_date = obj.creation_date.asdatetime().replace(tzinfo=None)
                # will be reindexed after move
            new_container = create_period_folder_max(self.imf, obj.reception_date, counter_dic, max_nb=1000)
            try:
                api.content.move(obj, new_container)
            except Exception as exc:
                try:
                    logger.error("Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.getPath(),
                                                                          exc.__class__.__name__, exc))
                except Exception:
                    logger.error("Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.Title,
                                                                          exc.__class__.__name__, exc))
            # obj.reindexObject(['getObjPositionInParent', 'path'])
            if self.commit_value and moved % self.commit_value == 0:
                logger.info('On dmsincomingmail move {}'.format(moved))
                transaction.commit()
        logger.info('Moved {} on {} dmsincomingmails'.format(moved, len(brains)))
        self.set_fingerpointing(orig)

    def move_dmsoutgoingmails(self):
        logger.info('Moving dmsoutgoingmails')
        orig = self.set_fingerpointing()
        omf_path = '/'.join(self.omf.getPhysicalPath())
        counter_dic = {}
        brains = self.catalog(portal_type='dmsoutgoingmail', sort_on='created',
                              path={'query': omf_path, 'depth': 1})
        moved = 0
        for brain in brains:
            moved += 1
            if self.batch_value and moved > self.batch_value:  # so it is possible to run this step partially
                break
            obj = brain.getObject()
            new_container = create_period_folder_max(self.omf, obj.creation_date, counter_dic, max_nb=1000)
            try:
                api.content.move(obj, new_container)
            except Exception as exc:
                try:
                    logger.error("Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.getPath(),
                                                                          exc.__class__.__name__, exc))
                except Exception:
                    logger.error("Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.Title,
                                                                          exc.__class__.__name__, exc))
            if self.commit_value and moved % self.commit_value == 0:
                logger.info('On dmsoutgoingmail move {}'.format(moved))
                transaction.commit()
        logger.info('Moved {} on {} dmsoutgoingmails'.format(moved, len(brains)))
        self.set_fingerpointing(orig)

    def update_catalog1(self):
        """ Update catalog or objects """
        # Lowercased hp email
        logger.info('Updating held_positions')
        brains = self.catalog.searchResults(portal_type='held_position')
        for brain in brains:
            obj = brain.getObject()
            if not obj.email:
                continue
            obj.email = obj.email.lower()
            obj.reindexObject(idxs=['contact_source', 'email'])
        logger.info('Updated {} brains'.format(len(brains)))
        # Reindex internal_reference_no
        self.reindexIndexes(['internal_reference_no'], update_metadata=True)
        # Ensure creating_group field is set
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder'):
            logger.info('Updates contacts to ensure creating_group field is set')
            self.set_creating_group_on_types(GE_CONFIG['contact_group_encoder']['pt'],
                                             GE_CONFIG['contact_group_encoder']['idx'])

    def update_catalog2(self):
        """ Update catalog or objects """
        # Clean and update
        logger.info('Updating dmsmainfile')
        brains = self.catalog.searchResults(portal_type='dmsmainfile')
        updated = 0
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            roles = obj.rolesOfPermission('Modify portal content')
            # already migrated ?
            if [role['name'] for role in roles if role['selected'] == 'SELECTED' and
                    role['name'] == 'DmsFile Contributor']:
                continue
            if self.batch_value and updated > self.batch_value:  # so it is possible to run this step partially
                break
            updated += 1
            # we removed those useless attributes
            for attr in ('conversion_finished', 'just_added'):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # specific: we update modification permission on incomingmail main file
            obj.manage_permission('Modify portal content', ('DmsFile Contributor', 'Manager', 'Site Administrator'),
                                  acquire=0)
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=['SearchableText', 'sender_index', 'markers'])
            if self.commit_value and updated % self.commit_value == 0:
                logger.info('On dmsmainfile update {}'.format(updated))
                transaction.commit()
        logger.info('Updated {} on {} dmsmainfiles'.format(updated, len(brains)))

    def update_catalog3(self):
        """ Update catalog or objects """
        # Clean and update
        logger.info('Updating dmsommainfile')
        brains = self.catalog.searchResults(portal_type='dmsommainfile')
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            # we removed those useless attributes
            for attr in ('conversion_finished', 'just_added'):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=['SearchableText', 'sender_index', 'markers'])
            if self.commit_value and i % self.commit_value == 0:
                logger.info('On dmsommainfile update {}'.format(i))
                transaction.commit()
        logger.info('Updated {} dmsommainfiles'.format(len(brains)))

    def update_catalog4(self):
        """ Update catalog or objects """
        # Clean and update
        logger.info('Updating dmsappendixfile')
        brains = self.catalog.searchResults(portal_type='dmsappendixfile')
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            # we removed those useless attributes
            for attr in ('conversion_finished', 'just_added'):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # specific: we update delete permission
            obj.manage_permission('Delete objects', ('Contributor', 'Editor', 'Manager', 'Site Administrator'),
                                  acquire=1)
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=['SearchableText', 'sender_index', 'markers'])
            if self.commit_value and i % self.commit_value == 0:
                logger.info('On dmsappendixfile update {}'.format(i))
                transaction.commit()
        logger.info('Updated {} dmsappendixfiles'.format(len(brains)))

    def clean_examples(self):
        brains = find(unrestricted=True, context=self.portal['outgoing-mail'], portal_type='dmsoutgoingmail',
                      id='reponse1')
        if not brains:
            logger.info('Cleaning wrongly added demo users')
            pf = self.portal['contacts']['personnel-folder']
            for userid in ['encodeur', 'dirg', 'chef', 'agent', 'agent1', 'lecteur']:
                for brain in find(unrestricted=True, context=pf, portal_type='person', id=userid):
                    api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
                user = api.user.get(userid=userid)
                if user is None:
                    continue
                logger.info("Deleting user '%s'" % userid)
                try:
                    api.user.delete(user=user)
                except Redirect:
                    pass

    def update_tasks(self):
        # change klass on task
        count = 0
        for brain in self.catalog(portal_type='task'):
            obj = brain.getObject()
            if obj.__class__ != Task:
                # old_class_name='plone.dexterity.content.Container',
                migrate_base_class_to_new_class(obj, new_class_name='collective.task.content.task.Task')
                obj.reindexObjectSecurity()
                count += 1
        if count:
            logger.info('TASKS class corrected : {}'.format(count))

    def ensure_creating_group(self, obj, index=False):
        try:
            owner = obj.getOwner()
        except AttributeError:
            userid = obj.owner_info()['id']
            owner = self.portal.acl_users.getUserById(userid)
            if owner is not None:
                obj.changeOwnership(owner, recursive=False)
                # obj.reindexObjectSecurity()  not needed because userid is not changed
        if ensure_set_field(obj, 'creating_group', default_creating_group(owner)) and index:
            obj.reindexObject(['assigned_group'])

    def set_creating_group_on_types(self, types, index):
        for brain in self.portal.portal_catalog.unrestrictedSearchResults(portal_type=types):
            obj = brain._unrestrictedGetObject()
            self.ensure_creating_group(obj, index=bool(index))

    def sync_solr(self):
        full_key = 'collective.solr.port'
        configured_port = api.portal.get_registry_record(full_key, default=None)
        if configured_port is None:
            return
        active_solr = api.portal.get_registry_record('collective.solr.active', default=None)
        if not active_solr:
            logger.info('Activating solr')
            api.portal.set_registry_record('collective.solr.active', True)
        logger.info('Syncing solr on %s' % self.portal.absolute_url_path())
        response = self.portal.REQUEST.RESPONSE
        original = response.write
        response.write = lambda x: x  # temporarily ignore output
        maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
        maintenance.sync()  # BATCHED
        response.write = original


def migrate(context):
    Migrate_To_3_0(context).run()
