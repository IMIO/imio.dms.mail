# -*- coding: utf-8 -*-
from collective.ckeditortemplates.setuphandlers import FOLDER as default_cke_templ_folder
from collective.contact.plonegroup.config import get_registry_organizations
from collective.documentgenerator.utils import update_oo_config
# from collective.documentviewer.settings import GlobalSettings
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.task.content.task import Task
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
# from dexterity.localroles.utils import fti_configuration
from dexterity.localroles.utils import update_roles_in_fti
from dexterity.localroles.utils import update_security_index
from eea.facetednavigation.criteria.interfaces import ICriteria
from imio.dms.mail import _tr as _
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import GE_CONFIG
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import MAIN_FOLDERS
from imio.dms.mail.content.behaviors import default_creating_group
from imio.dms.mail.examples import add_special_model_mail
# from imio.dms.mail.interfaces import IPersonnelFolder
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IActionsPanelFolderOnlyAdd
from imio.dms.mail.interfaces import IProtectedItem
# from imio.dms.mail.setuphandlers import configure_fpaudit
# from imio.dms.mail.relations_utils import rebuild_relations
from imio.dms.mail.setuphandlers import add_oem_templates
from imio.dms.mail.setuphandlers import blacklistPortletCategory
from imio.dms.mail.setuphandlers import configure_iem_rolefields
from imio.dms.mail.setuphandlers import createOMailCollections
from imio.dms.mail.setuphandlers import list_templates
from imio.dms.mail.setuphandlers import order_1st_level
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.setuphandlers import setup_classification
from imio.dms.mail.setuphandlers import update_task_workflow
# from imio.dms.mail.utils import modifyFileInBlob
# from imio.dms.mail.utils import PREVIEW_DIR
# from imio.dms.mail.utils import create_personnel_content
from imio.dms.mail.utils import create_period_folder_max
from imio.dms.mail.utils import ensure_set_field
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import is_in_user_groups
from imio.dms.mail.utils import is_valid_identifier
from imio.dms.mail.utils import message_status
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_solr_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
# from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import find
# from imio.helpers.security import get_user_from_criteria
# from imio.helpers.setup import load_type_from_package
# from imio.helpers.setup import remove_gs_step
# from imio.helpers.workflow import do_transitions
from imio.migrator.migrator import Migrator
from imio.pyutils.system import get_git_tag
from imio.pyutils.system import load_var
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from plone.dexterity.interfaces import IDexterityFTI
from plone.i18n.normalizer import IIDNormalizer
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
# from Products.CMFCore.ActionInformation import Action
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.CPUtils.Extensions.utils import mark_last_version
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from zExceptions import Redirect
# from zope.annotation import IAnnotations
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.event import notify
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import json
import logging
import OFS
import os
import transaction


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_0(Migrator):  # noqa
    def __init__(self, context, disable_linkintegrity_checks=False):
        Migrator.__init__(self, context, disable_linkintegrity_checks=disable_linkintegrity_checks)
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.acl = self.portal["acl_users"]
        self.contacts = self.portal["contacts"]
        self.existing_settings = {}
        self.config = {"om_mt": [], "flds": None}
        load_var(os.path.join(BLDT_DIR, "30_config.dic"), self.config)
        self.none_mail_type = False
        self.batch_value = int(os.getenv("BATCH", "0"))
        self.commit_value = int(os.getenv("COMMIT", "0"))

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
        fp_fields = ["audit_lifecycle", "audit_workflow"]
        if itself:  # registry
            if activate:
                fp_fields.append("audit_registry")
                activate.append(activate.pop(0))  # put at end the orig audit_registry value
            else:
                fp_fields.insert(0, "audit_registry")
        for i, fp_field in enumerate(fp_fields):
            key = "collective.fingerpointing.interfaces.IFingerPointingSettings.{}".format(fp_field)
            ret.append(api.portal.get_registry_record(key))
            if activate is None:
                api.portal.set_registry_record(key, False)
            else:
                api.portal.set_registry_record(key, activate[i])
        return ret

    def run(self):
        logger.info("Migrating to imio.dms.mail 3.0...")
        self.log_mem("START")
        if self.config.get("om_mt"):
            logger.info("Loaded config {}".format(self.config))
            mtypes = api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types", default=[]
            )
            mtypes = [dic.get("mt_value", dic.get("value")) for dic in mtypes]
            smodes = api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig." "omail_send_modes", default=[]
            )
            if smodes:
                smodes = [dic.get("mt_value", dic.get("value")) for dic in smodes]
            else:  # will be set later in update_config
                smodes = [dic["nid"] for dic in self.config["om_mt"]]
            oids = [dic["oid"] for dic in self.config["om_mt"]]
            if not [mt for mt in mtypes if mt not in oids]:  # configured mail types are handled in 30_config
                logger.info("OM MAIL_TYPE WILL BE SET TO NONE")
                self.none_mail_type = True
            stop = False
            for dic in self.config["om_mt"]:
                mtype = dic["oid"]
                if mtype not in mtypes:
                    logger.warning(u"config mtype '{}' not in '{}'".format(mtype, mtypes))
                smode = dic["nid"]
                if smode not in smodes:
                    stop = True
                    logger.error(u"config sm '{}' not in '{}'".format(smode, smodes))
            if stop:
                raise Exception("Bad config file 30_config.dic")

        if "flds" in self.config and self.config["flds"] is None:
            if "folders" not in self.portal:  # first time migration
                self.config["flds"] = True
            else:
                rec_name = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields"
                showed = [dic["field_name"] for dic in api.portal.get_registry_record(rec_name)]
                if u"IClassificationFolder.classification_folders" in showed:  # activated
                    self.config["flds"] = True
                else:
                    self.config["flds"] = False

        for mt in ("mail_types", "omail_types"):
            mtr = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(mt)
            self.existing_settings[mt] = api.portal.get_registry_record(mtr)

        if self.is_in_part("a"):  # install and upgrade products
            # check if oo port or solr port must be changed
            update_solr_config()
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr:
                logger.info("Deactivating solr")
                api.portal.set_registry_record("collective.solr.active", False)

            self.upgradeProfile("collective.documentgenerator:default")
            update_oo_config()

            self.cleanRegistries()

            self.correct_actions()

            self.correct_groups()

            self.install(["collective.ckeditortemplates", "collective.fingerpointing"])
            if default_cke_templ_folder in self.portal:
                api.content.delete(obj=self.portal[default_cke_templ_folder])
            self.upgradeProfile("collective.contact.core:default")
            transaction.commit()
            self.upgradeProfile("collective.task:default")
            self.upgradeProfile("collective.dms.mailcontent:default")
            self.upgradeProfile("plonetheme.imioapps:default")

            self.runProfileSteps(
                "plonetheme.imioapps", steps=["viewlets"], run_dependencies=False
            )  # to hide messages-viewlet
            self.runProfileSteps(
                "plonetheme.imioapps", profile="dmsmailskin", steps=["viewlets"], run_dependencies=False
            )  # to hide colophon
            if not self.portal.portal_quickinstaller.isProductInstalled("imio.pm.wsclient"):
                self.runProfileSteps("imio.dms.mail", steps=["imiodmsmail-configure-wsclient"], profile="singles")
            self.runProfileSteps(
                "collective.contact.importexport", steps=["plone.app.registry"], run_dependencies=False
            )

            self.do_prior_updates()

            self.install(
                ["collective.classification.folder", "collective.js.tooltipster", "imio.helpers", "Products.cron4plone"]
            )
            self.ps.runAllImportStepsFromProfile("profile-collective.js.tooltipster:themes")

        if self.is_in_part("b"):  # idm steps, config, folders
            self.runProfileSteps(
                "imio.dms.mail",
                steps=[
                    "actions",
                    "atcttool",
                    "catalog",
                    "controlpanel",
                    "plone.app.registry",
                    "repositorytool",
                    "rolemap",
                    "typeinfo",
                    "viewlets",
                ],
            )
            # remove to_print related.
            self.remove_to_print()

            # copy localroles from dmsincomingmail to dmsincoming_email
            imfti = getUtility(IDexterityFTI, name="dmsincomingmail")
            lr = getattr(imfti, "localroles")
            iemfti = getUtility(IDexterityFTI, name="dmsincoming_email")
            setattr(iemfti, "localroles", deepcopy(lr))
            configure_iem_rolefields(self.portal)

            if api.group.get("createurs_dossier") is None:
                api.group.create("createurs_dossier", "1 Créateurs dossiers")
                for user in api.user.get_users(groupname="dir_general"):
                    api.group.add_user(groupname="createurs_dossier", user=user)
            setup_classification(self.portal)
            # xml has been modified since first upgrade
            reimport_faceted_config(
                self.portal.folders["folder-searches"],
                xml="classificationfolders-searches.xml",
                default_UID=self.portal.folders["folder-searches"]["all_folders"].UID(),
            )
            order_1st_level(self.portal)

            orig = self.set_fingerpointing()
            self.runProfileSteps(
                "imio.dms.mail",
                profile="singles",
                steps=["imiodmsmail-contact-import-pipeline"],
                run_dependencies=False,
            )
            self.set_fingerpointing(orig)
            self.update_config()
            if self.config["flds"]:
                self.runProfileSteps(
                    "imio.dms.mail",
                    profile="singles",
                    steps=["imiodmsmail-activate_classification"],
                    run_dependencies=False,
                )
            else:
                self.runProfileSteps(
                    "imio.dms.mail",
                    profile="singles",
                    steps=["imiodmsmail-deactivate_classification"],
                    run_dependencies=False,
                )
            self.runProfileSteps(
                "imio.dms.mail",
                profile="examples",
                steps=["imiodmsmail-configure-imio-dms-mail"],
                run_dependencies=False,
            )
            # clean example users wrongly added by previous migration
            self.clean_examples()

        if self.is_in_part("c"):  # workflow
            # reset workflow
            self.runProfileSteps("imio.dms.mail", steps=["workflow"])
            # Apply workflow adaptations
            applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()]
            if applied_adaptations:
                success, errors = apply_from_registry(reapply=True)
                if errors:
                    logger.error("Problem applying wf adaptations: %d errors" % errors)
            if "imio.dms.mail.wfadaptations.TaskServiceValidation" not in applied_adaptations:
                update_task_workflow(self.portal)
            # update permissions, roles and reindex allowedRolesAndUsers
            count = self.portal.portal_workflow.updateRoleMappings()
            logger.info("Updated {} items".format(count))

        if self.is_in_part("d"):  # update site
            # do various global adaptations
            self.update_site()
            self.update_tasks()

        if self.is_in_part("e"):  # update dmsincomingmails
            # update dmsincomingmails
            self.update_dmsincomingmails()

        if self.is_in_part("f"):  # insert incoming emails
            # do various adaptations for dmsincoming_email
            self.insert_incoming_emails()

        if self.is_in_part("g"):  # insert outgoing emails
            self.insert_outgoing_emails()
            createOMailCollections(self.portal["outgoing-mail"]["mail-searches"])
            self.check_previously_migrated_collections()

        # self.catalog.refreshCatalog(clear=1)  # do not work because some indexes use catalog in construction !

        if self.is_in_part("i"):  # move incoming mails (long time, batchable)
            self.move_dmsincomingmails()

        if self.is_in_part("j"):  # move outgoing mails (long time, batchable)
            self.move_dmsoutgoingmails()

        if self.is_in_part("m"):  # update held positions
            self.update_catalog1()

        if self.is_in_part("n"):  # update dmsmainfile (middle time, batchable)
            self.update_catalog2()

        if self.is_in_part("o"):  # update dmsommainfile
            self.update_catalog3()

        if self.is_in_part("p"):  # update appendixfile
            self.update_catalog4()

        if self.is_in_part("q"):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            self.upgradeAll(
                omit=[u"imio.dms.mail:default", u"collective.js.chosen:default", u"collective.z3cform.chosen:default"]
            )

        if self.is_in_part("r"):  # update templates
            old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
            new_version = safe_unicode(get_git_tag(BLDT_DIR))
            logger.info("Current migration from version {} to {}".format(old_version, new_version))
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
            # add autolink plugin to ckeditor
            # ckprops = self.portal.portal_properties.ckeditor_properties
            # if ckprops.hasProperty('plugins'):
            #     plugins_list = list(ckprops.getProperty('plugins'))
            #     autolink_plugin = "autolink;/++resource++ckeditor/plugins/autolink/plugin.js"
            #     if autolink_plugin not in plugins_list:
            #         plugins_list.append(autolink_plugin)
            #         ckprops.manage_changeProperties(plugins=plugins_list)
            # TEMPORARY to 3.0.47
            # self.runProfileSteps('imio.dms.mail', steps=['actions',])
            # TEMPORARY to 3.0.48
            # alsoProvides(self.portal["folders"], INextPrevNotNavigable)
            # alsoProvides(self.portal["folders"]['folder-searches'], IClassificationFoldersDashboardBatchActions)
            # TEMPORARY to 3.0.50
            # brains = self.catalog(portal_type='DashboardCollection',
            #                       path='/'.join(self.portal.folders.getPhysicalPath()))
            # for brain in brains:
            #     col = brain.getObject()
            #     buf = list(col.customViewFields)
            #     if u'select_row' not in buf:
            #         buf.insert(0, u'select_row')
            #         col.customViewFields = tuple(buf)
            # TEMPORARY to 3.0.51
            # self.reindexIndexes(['email'], update_metadata=True,
            #                     portal_types=['dmsincoming_email', 'dmsoutgoingmail', 'held_position', 'organization',
            #                                   'person'])
            # TEMPORARY to 3.0.55
            # pf = self.portal.contacts['personnel-folder']
            # if not IPersonnelFolder.providedBy(pf):
            #     reimport_faceted_config(self.portal.folders['folder-searches'],
            #                             xml='classificationfolders-searches.xml',
            #                             default_UID=self.portal.folders['folder-searches']['all_folders'].UID())
            #     brains = self.catalog(portal_type='DashboardCollection',
            #                           path='/'.join(self.portal.folders.getPhysicalPath()))
            #     for brain in brains:
            #         col = brain.getObject()
            #         buf = list(col.customViewFields)
            #         if (u'classification_tree_identifiers' in buf and
            #               buf.index(u'classification_tree_identifiers') != 1):
            #             buf.remove(u'classification_tree_identifiers')
            #             buf.insert(1, u'classification_tree_identifiers')
            #             col.customViewFields = tuple(buf)
            #         if u'classification_folder_title' not in buf:
            #             buf.remove(u'pretty_link')
            #             buf.insert(2, u'classification_subfolder_title')
            #             buf.insert(2, u'classification_folder_title')
            #             col.customViewFields = tuple(buf)
            #         if u'ModificationDate' in buf:
            #             buf.remove(u'ModificationDate')
            #             buf.remove(u'review_state')
            #             col.customViewFields = tuple(buf)
            #
            #     # plonegroup change
            #     load_type_from_package('person', 'profile-collective.contact.core:default')  # schema policy
            #     load_type_from_package('person', 'profile-imio.dms.mail:default')  # behaviors
            #     self.upgradeProfile('collective.contact.plonegroup:default')
            #     # not important if person mailtype metadata is not cleaned. Otherwise, all objects are considered
            #     self.reindexIndexes(['mail_type', 'userid'], update_metadata=False,
            #                         portal_types=['held_position', 'person'])  # remove userid values
            #     alsoProvides(pf, IPersonnelFolder)
            #     pf.layout = 'personnel-listing'
            #     pf.manage_permission('collective.contact.plonegroup: Write user link fields',
            #                          ('Manager', 'Site Administrator'), acquire=0)
            #     pf.manage_permission('collective.contact.plonegroup: Read user link fields',
            #                          ('Manager', 'Site Administrator'), acquire=0)
            #     transaction.commit()  # avoid ConflictError after rebuild_relations
            #
            # # rebuild relations to update rel objects referencing removed schema interface (long process)
            # finished = rebuild_relations(self.portal)
            # TEMPORARY to 3.0.56
            # add personnel persons and hps for all functions: redo again after bug correction
            # remove_gs_step('imiodmsmail-refreshCatalog')  # because dependencies have changed
            # for udic in get_user_from_criteria(self.portal, email=''):
            #     groups = get_plone_groups_for_user(user_id=udic['userid'])
            #     create_personnel_content(udic['userid'], groups, primary=True)
            # if 'plus' not in self.portal:
            #     logger.info('Added plus page and excluded some folders')
            #     obj = api.content.create(container=self.portal, type='Document', id='plus', title=u'● ● ●')
            #     do_transitions(obj, ['show_internally'])
            #     alsoProvides(obj, IProtectedItem)
            #     order_1st_level(self.portal)
            #     for oid in ('contacts', 'templates', 'tree'):
            #         obj = self.portal[oid]
            #         obj.exclude_from_nav = True
            #         obj.reindexObject()
            # gsettings = GlobalSettings(self.portal)
            # gsettings.auto_select_layout = False
            # self.cleanRegistries()
            # self.upgradeProfile('collective.classification.folder:default')
            # self.upgradeProfile('collective.messagesviewlet:default')
            # self.upgradeProfile('collective.contact.facetednav:default')
            # # default view
            # for wkf in ('ConfigurablePODTemplate', 'DashboardPODTemplate', 'PODTemplate', 'SubTemplate',
            #             'dmsappendixfile', 'dmsmainfile', 'dmsommainfile'):  # annex ?
            #     load_type_from_package(wkf, 'profile-imio.dms.mail:default')
            # self.wfTool.setChainForPortalTypes(('ContentCategoryGroup',), '(Default)')
            # self.wfTool.setChainForPortalTypes(('ContentCategory',), ())
            # self.runProfileSteps('imio.dms.mail', steps=['actions'])
            # self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-add-test-annexes-types'], profile='examples')
            # for brain in self.catalog(portal_type=('MailingLoopTemplate', 'StyleTemplate')):
            #     brain.getObject().setLayout('view')
            # if 'annex' not in api.portal.get_registry_record('externaleditor.externaleditor_enabled_types'):
            #     eet = ['PODTemplate', 'ConfigurablePODTemplate', 'DashboardPODTemplate', 'SubTemplate',
            #            'StyleTemplate', 'dmsommainfile', 'MailingLoopTemplate', 'annex']
            #     api.portal.set_registry_record('externaleditor.externaleditor_enabled_types', eet)
            # collection_folder = self.portal['folders']['folder-searches']
            # reimport_faceted_config(collection_folder, xml='classificationfolders-searches.xml',
            #                         default_UID=collection_folder["all_folders"].UID())
            # brains = self.catalog(portal_type='DashboardCollection',
            #                       path='/'.join(self.portal.folders.getPhysicalPath()))
            # for brain in brains:
            #     col = brain.getObject()
            #     buf = list(col.customViewFields)
            #     if u'classification_folder_archived' not in buf:
            #         buf.insert(buf.index(u'classification_folder_title'), u'classification_folder_archived')
            #         col.customViewFields = tuple(buf)
            #     if u'classification_subfolder_archived' not in buf:
            #         buf.insert(buf.index(u'classification_subfolder_title'), u'classification_subfolder_archived')
            #         col.customViewFields = tuple(buf)
            # finished = self.reindexIndexes(['classification_folders'], update_metadata=True,
            #                                portal_types=['dmsincomingmail', 'dmsincoming_email', 'dmsoutgoingmail'])
            # TEMPORARY to 3.0.57
            # faceted_configs = (
            #     (self.imf["mail-searches"], "im-mail", "all_mails"),
            #     (self.omf["mail-searches"], "om-mail", "all_mails"),
            #     (self.portal["tasks"]["task-searches"], "im-task", "all_tasks"),
            #     (self.portal["folders"]["folder-searches"], "classificationfolders", "all_folders"),
            # )
            # for folder, xml_start, default_id in faceted_configs:
            #     reimport_faceted_config(
            #         folder, xml="{}-searches.xml".format(xml_start), default_UID=folder[default_id].UID()
            #     )
            # TEMPORARY TO 3.0.59
            # finished = self.reindexIndexes(
            #     ["yesno_value", "classification_categories", "classification_folders"],  # for solr index
            #     update_metadata=True,
            #     portal_types=[
            #         "ClassificationFolder",
            #         "ClassificationSubfolder",
            #         "dmsincomingmail",
            #         "dmsincoming_email",
            #         "dmsoutgoingmail",
            #     ],
            # )
            # if finished:
            #     brains = self.catalog(portal_type="DashboardCollection", path="/".join(self.omf.getPhysicalPath()))
            #     for brain in brains:
            #         if not brain.id.startswith("searchfor_") or brain.id == "searchfor_scanned":
            #             continue
            #         col = brain.getObject()
            #         if col.sort_on != "created":
            #             col.sort_on = "created"
            #     # load_type_from_package('dmsoutgoingmail', 'profile-imio.dms.mail:default')  # schema policy
            #     omf = api.portal.get_registry_record(
            #         "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields", default=[]
            #     )
            #     om_fns = [dic["field_name"] for dic in omf]
            #     if "email_bcc" not in om_fns:
            #         omf.insert(om_fns.index("email_cc") + 1,
            #                    {"field_name": "email_bcc", "read_tal_condition": u"", "write_tal_condition": u""})
            #         api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields",
            #                                        omf)
            #     # new omail_bcc_email_default setting field
            #     self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry'])
            # TEMPORARY TO 3.0.60
            # active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            # if active_solr:
            #     logger.info("Deactivating solr")
            #     api.portal.set_registry_record("collective.solr.active", False)
            # self.install(["imio.fpaudit"])
            # configure_fpaudit(self.portal)
            # self.upgradeProfile("collective.contact.core:default")
            # # create new group
            # if api.group.get("audit_contacts") is None:
            #     api.group.create("audit_contacts", "1 Audit contacts")
            # # replace isEml marker by dvConvError and old image by new one
            # brains = self.catalog.unrestrictedSearchResults(portal_type="dmsmainfile", markers="isEml")
            # blobs = []
            # for brain in brains:
            #     obj = brain._unrestrictedGetObject()
            #     obj.reindexObject(idxs=["markers"])
            #     annot = IAnnotations(obj).get("collective.documentviewer", "")
            #     btree = annot.get("blob_files")
            #     if btree is None:
            #         continue
            #     for name in ["large", "normal"]:
            #         blob = btree.get("{}/dump_1.jpg".format(name))
            #         if blob and blob not in blobs:
            #             blobs.append(blob)
            # for blob in blobs:
            #     modifyFileInBlob(blob, os.path.join(PREVIEW_DIR, "previsualisation_eml_normal.jpg"))
            # # actions and new registry
            # self.runProfileSteps("imio.dms.mail", steps=["actions", "plone.app.registry"])
            # registry = getUtility(IRegistry)
            # to_del_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.iemail_manual_forward_transition"
            # if to_del_key in registry.records:
            #     old_mft = registry.get(to_del_key, default=None)
            #     logger.info("Deleting registry key '{}' with value '{}'".format(to_del_key, old_mft))
            #     del registry.records[to_del_key]
            #     state_set_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.iemail_state_set"
            #     state_set = api.portal.get_registry_record(state_set_key, default=[]) or []
            #     if not state_set:
            #         if old_mft == u"agent":
            #             new_mft = u"proposed_to_agent"
            #         elif old_mft == u"manager":
            #             new_mft = u"proposed_to_manager"
            #         elif old_mft == u"n_plus_h":
            #             new_mft = u"_n_plus_h_"
            #         elif old_mft == u"n_plus_l":
            #             new_mft = u"_n_plus_l_"
            #         else:
            #             new_mft = u"created"
            #         state_set.append(
            #             {
            #                 u"forward": u"agent",
            #                 u"transfer_email_pat": u"",
            #                 u"original_email_pat": u"",
            #                 u"tal_condition_1": u"",
            #                 u"state_value": new_mft
            #             })
            #         api.portal.set_registry_record(state_set_key, state_set)
            #     routing_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.iemail_routing"
            #     routing = api.portal.get_registry_record(routing_key, default=[]) or []
            #     routing.append(
            #         {
            #             u"forward": u"agent",
            #             u"transfer_email_pat": u"",
            #             u"original_email_pat": u"",
            #             u"tal_condition_1": u"python: agent_id and 'encodeurs' in modules['imio.dms.mail.utils']."
            #                                 u"current_user_groups_ids(userid=agent_id)",
            #             u"user_value": u"_empty_",
            #             u"tal_condition_2": u"",
            #             u"tg_value": u"_empty_",
            #         }
            #     )
            #     routing.append(
            #         {
            #             u"forward": u"agent",
            #             u"transfer_email_pat": u"",
            #             u"original_email_pat": u"",
            #             u"tal_condition_1": u"",
            #             u"user_value": u"_transferer_",
            #             u"tal_condition_2": u"",
            #             u"tg_value": u"_hp_",
            #         })
            #     api.portal.set_registry_record(routing_key, routing)
            # # cron4plone settings
            # cron_configlet = getUtility(ICronConfiguration, "cron4plone_config")
            # if not [cj for cj in cron_configlet.cronjobs or [] if "cron_read_label_handling" in cj]:
            #     if not cron_configlet.cronjobs:
            #         cron_configlet.cronjobs = []
            #     # Syntax: m h dom mon command.
            #     cron_configlet.cronjobs.append(u"59 3 * * portal/@@various-utils/cron_read_label_handling")
            #     cron_configlet._p_changed = True
            # # localroles settings correction
            # lr, fti = fti_configuration(portal_type="dmsoutgoingmail")
            # lrs = lr["static_config"]
            # change = False
            # for state in lrs:
            #     if "encodeurs" not in lrs[state]:
            #         continue
            #     if lrs[state]["encodeurs"]["roles"] == ["Reader"]:
            #         del lrs[state]["encodeurs"]
            #         change = True
            # if change:
            #     fti.localroles._p_changed = True
            #     update_security_index(["dmsoutgoingmail"])
            # TEMPORARY TO 3.0.61
            # set versioning again after transmogrifier possible mislead
            pr_tool = api.portal.get_tool("portal_repository")
            if not pr_tool._versionable_content_types:
                pr_tool._versionable_content_types = [u'ATDocument', u'ATNewsItem', u'Document', u'Event', u'Link',
                                                      u'News Item', u'dmsincomingmail', u'dmsincoming_email',
                                                      u'dmsoutgoingmail', u'task']
            if not pr_tool._version_policy_mapping:
                pr_tool._version_policy_mapping = {u'dmsoutgoingmail': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'task': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'ATDocument': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'dmsincomingmail': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'ATNewsItem': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'Document': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'dmsincoming_email': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'Link': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'News Item': [u'at_edit_autoversion', u'version_on_revert'],
                                                   u'Event': [u'at_edit_autoversion', u'version_on_revert']}
            # added missing value in config
            key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
            values = list(api.portal.get_registry_record(key, default=[]))
            if values and "task.back_in_created2|" not in values:
                values.append("task.back_in_created2|")
                api.portal.set_registry_record(key, values)
            # Update config wsclient to Delib
            self.upgradeProfile("imio.pm.wsclient:default")
            from imio.pm.wsclient.browser.vocabularies import pm_item_data_vocabulary
            rkey = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.field_mappings"
            rvalue = api.portal.get_registry_record(rkey, default=None)
            fns = [dic["field_name"] for dic in rvalue or []]
            if fns:
                if u"ignore_validation_for" not in fns:
                    fns.append(u"ignore_validation_for")
                    rvalue.append({"field_name": u"ignore_validation_for", "expression": u"string:groupsInCharge"})
                if u"annexes" in fns:
                    fns.remove(u"annexes")
                    rvalue = [item for item in rvalue if item["field_name"] != u"annexes"]
                for field_mapping in rvalue:
                    if u"@@IncomingmailWSClient" in field_mapping["expression"]:
                        field_mapping["expression"] = field_mapping["expression"].replace(
                            u"@@IncomingmailWSClient", u"@@IncomingmailRestWSClient"
                        )
                orig_call = pm_item_data_vocabulary.__call__
                pm_item_data_vocabulary.__call__ = lambda self0, ctxt: SimpleVocabulary(
                    [SimpleTerm(fn) for fn in fns]
                )
                api.portal.set_registry_record(rkey, rvalue)
                pm_item_data_vocabulary.__call__ = orig_call
            # imio.pm.wsclient permission
            self.portal.manage_permission(
                "WS Client Access",
                ("Manager", "Site Administrator", "Contributor", "Editor", "Owner", "Reader", "Reviewer"),
                acquire=0,
            )
            self.portal.manage_permission("WS Client Send", ("Manager", "Site Administrator", "Editor"), acquire=0)
            # cron4plone settings
            cron_configlet = getUtility(ICronConfiguration, "cron4plone_config")
            if u"45 18 1,15 * portal/@@various-utils/dv_images_clean" in cron_configlet.cronjobs:
                index = cron_configlet.cronjobs.index(u"45 18 1,15 * portal/@@various-utils/dv_images_clean")
                cron_configlet.cronjobs.pop(index)
                cron_configlet._p_changed = True

            # adding omail_post_mailing option
            self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry'])
            api.portal.set_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_post_mailing", False
            )
            # Uninstall imio.dms.soap2pm
            installer = api.portal.get_tool("portal_quickinstaller")
            if installer.isProductInstalled("imio.dms.soap2pm"):
                installer.uninstallProducts(["imio.dms.soap2pm"])

            # TEMPORARY TO 3.0.62
            # Update dashboard pod templates
            self.portal["templates"]["export-users-groups"].max_objects = 0
            self.portal["templates"]["all-contacts-export"].max_objects = 0
            # END

            finished = True  # can be eventually returned and set by batched method
            if finished and old_version != new_version:
                zope_app = self.portal
                while not isinstance(zope_app, OFS.Application.Application):
                    zope_app = zope_app.aq_parent
                if "cputils_install" not in zope_app.objectIds():
                    manage_addExternalMethod(zope_app, "cputils_install", "", "CPUtils.utils", "install")
                ret = zope_app.cputils_install(zope_app)
                ret = ret.replace("<div>Those methods have been added: ", "").replace("</div>", "")
                if ret:
                    logger.info('CPUtils added methods: "{}"'.format(ret.replace("<br />", ", ")))
                if message_status("doc", older=timedelta(days=90), to_state="inactive"):
                    logger.info("doc message deactivated")
                self.runProfileSteps("imio.dms.mail", steps=["cssregistry", "jsregistry"])
                if ARCHIVE_SITE:
                    cssr = self.portal.portal_css
                    if not cssr.getResource("imiodmsmail_archives.css").getEnabled():
                        cssr.updateStylesheet("imiodmsmail_archives.css", enabled=True)
                        cssr.cookResources()
                self.cleanRegistries()
                # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
                self.registry["collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete"] = False
                # version
                api.portal.set_registry_record("imio.dms.mail.product_version", new_version)
                end = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d-%H%M")
                if old_version != new_version:
                    if "new-version" in self.portal["messages-config"]:
                        api.content.delete(self.portal["messages-config"]["new-version"])
                    # with solr, bug in col.iconifiedcategory.content.events.categorized_content_container_moved
                    # self.portal["messages-config"].REQUEST.set("defer_categorized_content_created_event", True)
                    add_message(
                        "new-version",
                        "Maj version",
                        u"<p><strong>iA.docs a été mis à jour de la version {} à la version {}</strong>. Vous "
                        u"pouvez consulter les changements en cliquant sur le numéro de version en bas de page."
                        u"</p>".format(old_version, new_version),
                        msg_type="significant",
                        can_hide=True,
                        end=end,
                        req_roles=["Authenticated"],
                        activate=True,
                    )
                # model om mail
                add_special_model_mail(self.portal)
                # update templates
                self.runProfileSteps(
                    "imio.dms.mail",
                    steps=["imiodmsmail-create-templates", "imiodmsmail-update-templates"],
                    profile="singles",
                )
                self.portal["templates"].moveObjectToPosition("d-im-listing-tab-details", 4)  # TEMPORARY
                # add audit_log action 3.0.60  TEMPORARY
                # category = self.portal.portal_actions.get('user')
                # if "audit-contacts" not in category.objectIds():
                #     uid = self.portal.templates["audit-contacts"].UID()
                #     action = Action(
                #         "audit-contacts",
                #         title="Audit contacts",
                #         i18n_domain="imio.dms.mail",
                #         url_expr="string:${{portal_url}}/document-generation?template_uid={}&"
                #                  "output_format=ods".format(uid),
                #         available_expr="python:context.restrictedTraverse('@@various-utils').is_in_user_groups("
                #                        "['audit_contacts'], user=member)",
                #         permissions=("View",),
                #         visible=False,
                #     )
                #     category._setObject("audit-contacts", action)
                #     pos = category.getObjectPosition("logout")
                #     category.moveObjectToPosition("audit-contacts", pos)
            # if active_solr:
            #     logger.info("Activating solr")
            #     api.portal.set_registry_record("collective.solr.active", True)

        if self.is_in_part("s"):  # update quick installer
            for prod in [
                "collective.behavior.talcondition",
                "collective.ckeditor",
                "collective.ckeditortemplates",
                "collective.classification.folder",
                "collective.classification.tree",
                "collective.compoundcriterion",
                "collective.contact.core",
                "collective.contact.duplicated",
                "collective.contact.facetednav",
                "collective.contact.importexport",
                "collective.contact.plonegroup",
                "collective.contact.widget",
                "collective.dms.basecontent",
                "collective.dms.batchimport",
                "collective.dms.mailcontent",
                "collective.dms.scanbehavior",
                "collective.documentgenerator",
                "collective.eeafaceted.batchactions",
                "collective.eeafaceted.collectionwidget",
                "collective.eeafaceted.dashboard",
                "collective.eeafaceted.z3ctable",
                "collective.js.tooltipster",
                "collective.messagesviewlet",
                "collective.task",
                "collective.wfadaptations",
                "collective.z3cform.select2",
                "dexterity.localroles",
                "dexterity.localrolesfield",
                "eea.facetednavigation",
                "eea.jquery",
                "imio.actionspanel",
                "imio.dashboard",
                "imio.dms.mail",
                "imio.helpers",
                "imio.history",
                "imio.pm.wsclient",
                "plonetheme.imioapps",
            ]:
                mark_last_version(self.portal, product=prod)

        if self.is_in_part("x"):  # clear solr
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr is not None:
                if not active_solr:
                    logger.info("Activating solr")
                    api.portal.set_registry_record("collective.solr.active", True)
                logger.info("Clearing solr on %s" % self.portal.absolute_url_path())
                maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
                maintenance.clear()

        if self.is_in_part("y"):  # sync solr (long time, batchable)
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr is not None:
                if not active_solr:
                    logger.info("Activating solr")
                    api.portal.set_registry_record("collective.solr.active", True)
                self.sync_solr()

        self.log_mem("END")
        logger.info("Really finished at {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.finish()

    def do_prior_updates(self):
        # clean dmsconfig to avoid duplications in wf_from_to
        for typ in ("dmsincomingmail", "dmsoutgoingmail"):
            config = get_dms_config(["wf_from_to", typ, "n_plus"])
            for direction in ("from", "to"):
                current_lst = config[direction]
                new_lst = []
                for tup in current_lst:
                    if tup not in new_lst:
                        new_lst.append(tup)
                if len(current_lst) != len(new_lst):
                    set_dms_config(["wf_from_to", typ, "n_plus", direction], new_lst)
        # update dms config wf_from_to with mark_as_sent transition
        nplus_to = get_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"])
        if ("sent", "mark_as_sent") not in nplus_to:
            nplus_to.insert(0, ("sent", "mark_as_sent"))
            set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"], nplus_to)
        update_transitions_levels_config(["dmsoutgoingmail"])
        # update dms config wf_from_to with close transition
        nplus_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus", "to"])
        if ("closed", "close") not in nplus_to:
            nplus_to.insert(0, ("closed", "close"))
            set_dms_config(["wf_from_to", "dmsincomingmail", "n_plus", "to"], nplus_to)
            update_transitions_auc_config(["dmsincomingmail"])
        update_transitions_levels_config(["dmsincomingmail"])
        # remove doing_migration from wfadaptations parameters (added by 2.3 migration)
        change = False
        record = []
        adaptations = get_applied_adaptations()
        for info in adaptations:
            if "doing_migration" in info["parameters"]:
                del info["parameters"]["doing_migration"]
                change = True
            if (
                info["adaptation"] == u"imio.dms.mail.wfadaptations.OMServiceValidation"
                and "validated_from_created" not in info["parameters"]
            ):
                value = u"imio.dms.mail.wfadaptations.OMToPrint" in [dic["adaptation"] for dic in adaptations]
                info["parameters"]["validated_from_created"] = value
                change = True
            info["parameters"] = json.dumps(info["parameters"], sort_keys=True).decode("utf8")
            record.append(info)
        if change:
            api.portal.set_registry_record(RECORD_NAME, record)

    def update_site(self):
        # update front-page
        frontpage = self.portal["front-page"]
        if frontpage.Title() == "Gestion du courrier 2.3":
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype="text/html")

        # update portal title
        self.portal.title = "Gestion du courrier 3.0"

        # update tabs
        titles = {
            "incoming-mail": "incoming_mail_tab",
            "outgoing-mail": "outgoing_mail_tab",
            "folders": "folders_tab",
            "tasks": "tasks_tab",
            "contacts": "contacts_tab",
            "templates": "templates_tab",
            "tree": "classification_tree_tab",
        }
        for oid in titles:
            obj = self.portal[oid]
            if obj.title != _(titles[oid]):
                obj.title = _(titles[oid])
                obj.reindexObject()

        # update folder period
        if getattr(self.portal[MAIN_FOLDERS["dmsincomingmail"]], "folder_period", None) is None:
            setattr(self.portal[MAIN_FOLDERS["dmsincomingmail"]], "folder_period", u"week")
        if getattr(self.portal[MAIN_FOLDERS["dmsoutgoingmail"]], "folder_period", None) is None:
            setattr(self.portal[MAIN_FOLDERS["dmsoutgoingmail"]], "folder_period", u"week")

        # self.portal.manage_permission('imio.dms.mail: Write creating group field', ('Manager',
        #                               'Site Administrator'), acquire=0)
        self.portal.manage_permission(
            "plone.restapi: Use REST API", ("Manager", "Site Administrator", "Member"), acquire=0
        )
        # registry
        api.portal.set_registry_record(
            name="Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings." "allowed", value=False
        )

        if (
            "doc" in self.portal["messages-config"]
            and u"version 3.0" not in self.portal["messages-config"]["doc"].text.raw
        ):
            api.content.delete(self.portal["messages-config"]["doc"])
        # not added if already exists
        add_message(
            "doc",
            "Documentation",
            u'<p>Vous pouvez consulter la <a href="https://docs.imio.be/'
            u'imio-doc/ia.docs/" target="_blank">documentation en ligne de la '
            u'version 3.0</a>, dont <a href="https://docs.imio.be/imio-doc/ia.docs/changelog" '
            u'target="_blank">les nouvelles fonctionnalités</a> ainsi que d\'autres documentations liées.</p>',
            msg_type="significant",
            can_hide=True,
            req_roles=["Authenticated"],
            activate=True,
        )

        # update ckeditor config
        ckp = self.portal.portal_properties.ckeditor_properties
        ckp.manage_changeProperties(toolbar="CustomOld")
        configure_ckeditor(self.portal, custom="ged", filtering="disabled")

        # update templates layout and create oem folders
        self.portal.templates.setLayout("folder_listing")
        add_oem_templates(self.portal)
        record = self.registry.records.get(
            "collective.contact.plonegroup.browser.settings." "IContactPlonegroupConfig.organizations"
        )
        notify(RecordModifiedEvent(record, [], []))

        # add group
        if api.group.get("gestion_contacts") is None:
            api.group.create("gestion_contacts", "1 Gestion doublons contacts")
        if api.group.get("lecteurs_globaux_cs") is None:
            api.group.create("lecteurs_globaux_cs", "2 Lecteurs Globaux CS")
        # change local roles
        to_add = {
            "to_be_signed": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
            "sent": {"dir_general": {"roles": ["Reader", "Reviewer"]}, "lecteurs_globaux_cs": {"roles": ["Reader"]}},
        }
        change1 = update_roles_in_fti("dmsoutgoingmail", to_add, notify=False)
        to_add = {  # additional roles needed for outgoing emails
            "to_be_signed": {"encodeur": {"roles": ["Contributor", "Editor", "Reviewer"]}},
            "sent": {"encodeur": {"roles": ["Reviewer"]}},
        }
        send_modes = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig." "omail_send_modes"
        )
        email_modes = [sm["value"] for sm in send_modes if sm["value"].startswith("email") and sm["active"]]
        change2 = False
        if email_modes:
            change2 = update_roles_in_fti("dmsoutgoingmail", to_add, keyname="treating_groups", notify=False)
        if change1 or change2:
            update_security_index(("dmsoutgoingmail",), trace=10000)

        # update IActionsPanelFolderOnlyAdd interface
        for fld in (
            self.portal["templates"]["om"],
            self.portal["templates"]["oem"],
            self.contacts["contact-lists-folder"],
        ):
            # we search uid folders but also manually created folders
            folders = api.content.find(context=fld, portal_type="Folder")
            for brain in folders:
                folder = brain.getObject()
                if folder == fld:
                    continue
                folder.reindexObject(["enabled"])
                alsoProvides(folder, IActionsPanelFolderOnlyAdd)
                alsoProvides(folder, INextPrevNotNavigable)
                noLongerProvides(folder, IActionsPanelFolder)
                noLongerProvides(folder, IActionsPanelFolderAll)
        # add _editeur as contact contributor
        s_orgs = get_registry_organizations()
        for folder in (self.contacts, self.contacts["contact-lists-folder"]["common"]):
            dic = folder.__ac_local_roles__
            for uid in s_orgs:
                dic["%s_editeur" % uid] = ["Contributor"]  # an agent could add a contact on an email im
            folder._p_changed = True
        for fld in api.content.find(context=self.contacts["contact-lists-folder"], portal_type="Folder"):
            folder = fld.getObject()
            dic = folder.__ac_local_roles__
            if "{}_encodeur".format(folder.id) not in dic:
                continue
            dic["%s_editeur" % folder.id] = ["Contributor", "Editor", "Reader"]
            folder._p_changed = True

        # protect objects
        for obj in (
            self.portal["incoming-mail"],
            self.portal["incoming-mail"]["mail-searches"],
            self.portal["outgoing-mail"],
            self.portal["outgoing-mail"]["mail-searches"],
            self.portal["tasks"],
            self.portal["tasks"]["task-searches"],
            self.portal["contacts"],
            self.portal["contacts"]["orgs-searches"],
            self.portal["contacts"]["hps-searches"],
            self.portal["contacts"]["persons-searches"],
            self.portal["contacts"]["cls-searches"],
            self.portal["contacts"]["plonegroup-organization"],
            self.portal["contacts"]["personnel-folder"],
            self.portal["contacts"]["contact-lists-folder"],
            self.portal["contacts"]["contact-lists-folder"]["common"],
            self.portal["folders"],
            self.portal["folders"]["folder-searches"],
            self.portal["tree"],
            self.portal["templates"],
            self.portal["templates"]["om"],
            self.portal["templates"]["om"]["common"],
            self.portal["templates"]["oem"],
        ):
            alsoProvides(obj, IProtectedItem)
        for brain in self.catalog(portal_type="DashboardCollection"):
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
        self.imf.setLocallyAllowedTypes(["dmsincomingmail", "dmsincoming_email"])
        self.imf.setImmediatelyAddableTypes(["dmsincomingmail", "dmsincoming_email"])
        # diff
        pdiff = api.portal.get_tool("portal_diff")
        pdiff.setDiffForPortalType("dmsincoming_email", {"any": "Compound Diff for Dexterity types"})
        # collections
        brains = self.catalog.searchResults(
            portal_type="DashboardCollection", path="/".join(self.imf.getPhysicalPath())
        )
        for brain in brains:
            col = brain.getObject()
            new_lst = []
            change = False
            for dic in col.query:
                if dic["i"] == "portal_type" and len(dic["v"]) == 1 and dic["v"][0] == "dmsincomingmail":  # i_e ok
                    dic["v"] = ["dmsincomingmail", "dmsincoming_email"]
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst

    def insert_outgoing_emails(self):
        """The partially added dmsoutgoing_email is not used... We clean what's configured..."""
        # Set send_modes on dmsoutgoingmails
        mt_2_sm = {dic["oid"]: dic["nid"] for dic in self.config["om_mt"]}
        ensure = False
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder"):
            ensure = True
            logger.info("Updates dmsoutgoingmails to ensure creating_group field is set")
        unk_mt = {}
        brains = self.catalog.searchResults(portal_type="dmsoutgoingmail")
        for brain in brains:
            obj = brain.getObject()
            if ensure:
                self.ensure_creating_group(obj, index=False)  # assigned_group index
            if not getattr(obj, "send_modes"):
                # set send_modes following mail_type
                if self.config["om_mt"] and obj.mail_type:
                    if obj.mail_type in mt_2_sm:
                        obj.send_modes = [mt_2_sm[obj.mail_type]]
                        if self.none_mail_type:
                            obj.mail_type = None
                    else:
                        unk_mt.setdefault(obj.mail_type, 0)
                        unk_mt[obj.mail_type] += 1
                        logger.error(u"Unknown mail_type '{}' on {}".format(obj.mail_type, obj.absolute_url()))
                else:
                    obj.send_modes = ["post"]
            obj.reindexObject(idxs=["Subject", "assigned_group", "enabled", "mail_type", "markers"])
        if unk_mt:
            logger.error("THERE ARE UNKNOWN MAIL TYPES. WE HAVE TO UPDATE 30_config.dic !")
            for mt in unk_mt:
                logger.error(u"value '{}' found {} times".format(mt, unk_mt[mt]))

        omf = api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields")
        mtypes = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types", default=[]
        )
        if [dic for dic in omf if dic["field_name"] == "mail_type"] or [dic for dic in mtypes if dic["active"]]:
            n_mtypes = []
            remove_mtype = True
            for mtype in mtypes:
                brains = self.catalog.searchResults(portal_type="dmsoutgoingmail", mail_type=mtype["value"])
                if brains:
                    logger.warning("mtype '{}' is yet used after migration, on {} OMs".format(mtype, len(brains)))
                    remove_mtype = False
                else:
                    mtype["active"] = False
                n_mtypes.append(mtype)
            api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types", n_mtypes)
            if remove_mtype:
                logger.info("Disabling om mail_type field, no more used")
                n_omf = [dic for dic in omf if dic["field_name"] != "mail_type"]
                if len(n_omf) != len(omf):
                    api.portal.set_registry_record(
                        "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields", n_omf
                    )
                # remove collections column
                brains = self.catalog(portal_type="DashboardCollection", path="/".join(self.omf.getPhysicalPath()))
                for brain in brains:
                    col = brain.getObject()
                    buf = list(col.customViewFields)
                    if u"mail_type" in buf:
                        buf.remove(u"mail_type")
                        col.customViewFields = tuple(buf)
                # remove filter
                folder = self.omf["mail-searches"]
                criterias = ICriteria(folder)
                criterion = criterias.get("c9")
                if not criterion.hidden:
                    criterion.hidden = True
                    criterias.criteria._p_changed = 1

        # allowed types
        self.omf.setConstrainTypesMode(1)
        self.omf.setLocallyAllowedTypes(["dmsoutgoingmail"])
        self.omf.setImmediatelyAddableTypes(["dmsoutgoingmail"])
        # diff
        pdiff = api.portal.get_tool("portal_diff")
        # pdiff.setDiffForPortalType('dmsoutgoing_email', {'any': "Compound Diff for Dexterity types"})
        if "dmsoutgoing_email" in pdiff._pt_diffs:
            del pdiff._pt_diffs["dmsoutgoing_email"]
            pdiff._p_changed = 1
        # collections
        brains = self.catalog.searchResults(
            portal_type="DashboardCollection", path="/".join(self.omf.getPhysicalPath())
        )
        for brain in brains:
            col = brain.getObject()
            new_lst = []
            change = False
            for dic in col.query:
                # if dic['i'] == 'portal_type' and len(dic['v']) == 1 and dic['v'][0] == 'dmsoutgoingmail':
                #     dic['v'] = ['dmsoutgoingmail', 'dmsoutgoing_email']
                #     change = True
                if dic["i"] == "portal_type" and len(dic["v"]) == 2 and "dmsoutgoing_email" in dic["v"]:
                    dic["v"] = ["dmsoutgoingmail"]
                    change = True
                new_lst.append(dic)
            if change:
                col.query = new_lst
            # add send_modes column
            buf = list(col.customViewFields)
            if u"send_modes" not in buf:
                if "mail_type" in buf:
                    buf.insert(buf.index("mail_type"), u"send_modes")
                else:
                    buf.append(u"send_modes")
                col.customViewFields = tuple(buf)

    def check_previously_migrated_collections(self):
        # check if changes have been persisted from lower migrations
        # TODO
        pass

    def correct_actions(self):
        pa = self.portal.portal_actions
        if "portlet" in pa:
            api.content.rename(obj=pa["portlet"], new_id="object_portlet")
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
        applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()]
        if u"imio.dms.mail.wfadaptations.OMToPrint" not in applied_adaptations:
            return
        logger.info("Removing to_print")
        # clean dms config
        config = get_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"])
        if ("to_print", "set_to_print") in config:
            config.remove(("to_print", "set_to_print"))
            set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"], value=config)
            update_transitions_levels_config(["dmsoutgoingmail"])

        # clean local roles
        fti = getUtility(IDexterityFTI, name="dmsoutgoingmail")
        lr = getattr(fti, "localroles")
        lrg = lr["static_config"]
        if "to_print" in lrg:
            logger.info("static to_print: '{}'".format(lrg.pop("to_print")))
        lrg = lr["treating_groups"]
        if "to_print" in lrg:
            logger.info("treating_groups to_print: '{}'".format(lrg.pop("to_print")))
        lrg = lr["recipient_groups"]
        if "to_print" in lrg:
            logger.info("recipient_groups to_print: '{}'".format(lrg.pop("to_print")))
        lr._p_changed = True

        # remove collection
        folder = self.omf["mail-searches"]
        if "searchfor_to_print" in folder:
            api.content.delete(obj=folder["searchfor_to_print"])
        col = folder["om_treating"]
        query = list(col.query)
        modif = False
        for dic in query:
            if dic["i"] == "review_state" and "to_print" in dic["v"]:
                modif = True
                dic["v"].remove("to_print")
        if modif:
            col.query = query

        # update remark states
        lst = (
            api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states")
            or []
        )
        if "to_print" in lst:
            lst.remove("to_print")
            api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states", lst)

        trs = {"set_to_print": "set_validated", "back_to_print": "back_to_validated"}
        for i, brain in enumerate(self.catalog(portal_type="dmsoutgoingmail"), 1):
            obj = brain.getObject()
            # update history
            wfh = []
            for status in obj.workflow_history.get("outgoingmail_workflow"):
                # replace old state by new one
                if status["review_state"] == "to_print":
                    status["review_state"] = "validated"
                # replace old transition by new one
                if status["action"] in trs:
                    status["action"] = trs[status["action"]]
                wfh.append(status)
            obj.workflow_history["outgoingmail_workflow"] = tuple(wfh)
            # update state_group (use dms_config), state
            if brain.review_state == "to_print":
                obj.reindexObject(idxs=["review_state", "state_group"])

        record = api.portal.get_registry_record(RECORD_NAME)
        api.portal.set_registry_record(
            RECORD_NAME, [d for d in record if d["adaptation"] != u"imio.dms.mail.wfadaptations.OMToPrint"]
        )

    def update_mailtype_config(self):
        idnormalizer = getUtility(IIDNormalizer)
        for mt, ptype in (("mail_types", ["dmsincomingmail", "dmsincoming_email"]), ("omail_types", "dmsoutgoingmail")):
            mtr = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(mt)
            mail_types = self.existing_settings[mt]
            new_mt = []
            change = False
            for dic in mail_types:
                new_dic = dict(dic)
                if "mt_value" in dic:
                    change = True
                    new_dic = {"value": dic["mt_value"], "dtitle": dic["mt_title"], "active": dic["mt_active"]}
                if not is_valid_identifier(new_dic["value"]):
                    change = True
                    old_value = new_dic["value"]
                    new_dic["value"] = safe_unicode(idnormalizer.normalize(old_value))
                    for brain in self.catalog(portal_type=ptype, mail_type=old_value):
                        obj = brain.getObject()
                        obj.mail_type = new_dic["value"]
                        obj.reindexObject(["mail_type"])
                new_mt.append(new_dic)
            if change:
                api.portal.set_registry_record(mtr, new_mt)

    def update_config(self):
        # modify settings following new structure and correct id if necessary
        self.update_mailtype_config()
        # set default send_modes values
        if not api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes", default=[]
        ):
            smodes = []
            for dic in self.config["om_mt"]:
                if dic["nid"] not in [dc["value"] for dc in smodes]:  # avoid duplicates
                    smodes.append({"value": dic["nid"], "dtitle": dic["t"], "active": dic["a"]})
            api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes", smodes)
        # im fields order to new field config
        im_fo = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order", default=[]
        )
        if im_fo:
            if "orig_sender_email" not in im_fo:
                im_fo.insert(im_fo.index("sender"), "orig_sender_email")
            if "IClassificationFolder.classification_categories" not in im_fo:
                idx = im_fo.index("internal_reference_no")
                im_fo.insert(idx, "IClassificationFolder.classification_folders")
                im_fo.insert(idx, "IClassificationFolder.classification_categories")
            imf = [{"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in im_fo]
            api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields", imf)
            del self.registry.records["imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields_order"]
        # om fields order to new field config
        om_fo = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order", default=[]
        )
        if om_fo:
            if "send_modes" not in om_fo:
                try:
                    idx = om_fo.index("mail_type")
                except ValueError:
                    idx = len(om_fo)
                om_fo.insert(idx, "send_modes")
                om_fo += [
                    "email_status",
                    "email_subject",
                    "email_sender",
                    "email_recipient",
                    "email_cc",
                    "email_attachments",
                    "email_body",
                ]
            if "orig_sender_email" not in om_fo:
                om_fo.insert(om_fo.index("recipients"), "orig_sender_email")
            if "IClassificationFolder.classification_categories" not in om_fo:
                idx = om_fo.index("internal_reference_no")
                om_fo.insert(idx, "IClassificationFolder.classification_folders")
                om_fo.insert(idx, "IClassificationFolder.classification_categories")
            omf = [{"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in om_fo]
            api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields", omf)
            del self.registry.records["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields_order"]
        # general config
        if not api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig." "users_hidden_in_dashboard_filter"
        ):
            api.portal.set_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.users_hidden_in_dashboard_filter", ["scanner"]
            )

        # reimport faceted
        criterias = (
            (self.imf["mail-searches"], "im-mail", "all_mails", "imail_group_encoder"),
            (self.omf["mail-searches"], "om-mail", "all_mails", "omail_group_encoder"),
            (self.portal["tasks"]["task-searches"], "im-task", "all_tasks", "___"),
            (self.contacts["orgs-searches"], "organizations", "all_orgs", "contact_group_encoder"),
            (self.contacts["persons-searches"], "persons", "all_persons", "contact_group_encoder"),
            (self.contacts["hps-searches"], "held-positions", "all_hps", "contact_group_encoder"),
            (self.contacts["cls-searches"], "contact-lists", "all_cls", "contact_group_encoder"),
        )
        for folder, xml_start, default_id, ge_config in criterias:
            reimport_faceted_config(
                folder, xml="{}-searches.xml".format(xml_start), default_UID=folder[default_id].UID()
            )
            if api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(ge_config), default=False
            ):
                reimport_faceted_config(
                    folder, xml="mail-searches-group-encoder.xml", default_UID=folder[default_id].UID()
                )

        # update maybe bad local roles (because this record change wasn't handled)
        record = getUtility(IRegistry).records.get(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig." "org_templates_encoder_can_edit"
        )
        notify(RecordModifiedEvent(record, [], []))
        # update wsclient settings
        from imio.pm.wsclient.browser.vocabularies import pm_meeting_config_id_vocabulary

        orig_call = pm_meeting_config_id_vocabulary.__call__
        from imio.dms.mail.subscribers import wsclient_configuration_changed
        from plone.registry.interfaces import IRecordModifiedEvent

        gsm = getGlobalSiteManager()
        prefix = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings"
        gen_acts = api.portal.get_registry_record("{}.generated_actions".format(prefix))
        is_activated = False
        changes = False
        new_acts = []
        for act in gen_acts:
            new_act = dict(act)
            if act["permissions"] != "Modify view template":
                is_activated = True
            if act["condition"] == u"python: context.getPortalTypeName() in ('dmsincomingmail', )":
                changes = True
                new_act["condition"] = (
                    u"python: context.getPortalTypeName() in ('dmsincomingmail', 'dmsincoming_email')"
                )
            new_acts.append(new_act)
        if changes:
            if not is_activated:
                gsm.unregisterHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
                pm_meeting_config_id_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
                    [SimpleTerm(u"meeting-config-college")]
                )
            api.portal.set_registry_record("{}.generated_actions".format(prefix), new_acts)
            if not is_activated:
                gsm.registerHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
                pm_meeting_config_id_vocabulary.__call__ = orig_call

        # define default preservation value
        if not api.portal.get_registry_record("imio.dms.mail.dv_clean_days") and not api.portal.get_registry_record(
            "imio.dms.mail.dv_clean_date"
        ):
            api.portal.set_registry_record("imio.dms.mail.dv_clean_days", 180)
        # define default folder_period
        if not api.portal.get_registry_record("imio.dms.mail.imail_folder_period"):
            api.portal.set_registry_record("imio.dms.mail.imail_folder_period", u"week")
        if not api.portal.get_registry_record("imio.dms.mail.omail_folder_period"):
            api.portal.set_registry_record("imio.dms.mail.omail_folder_period", u"week")

        # define subfolder period
        if not api.portal.get_registry_record("imio.dms.mail.imail_folder_period"):
            api.portal.set_registry_record("imio.dms.mail.imail_folder_period", u"week")
        if not api.portal.get_registry_record("imio.dms.mail.omail_folder_period"):
            api.portal.set_registry_record("imio.dms.mail.omail_folder_period", u"week")
        # update actionspanel transitions config
        key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
        values = api.portal.get_registry_record(key)
        new_values = []
        for val in values:
            if val.startswith("dmsincomingmail."):
                email_val = val.replace("dmsincomingmail.", "dmsincoming_email.")
                if email_val not in values:
                    new_values.append(email_val)
        if new_values:
            api.portal.set_registry_record(key, list(values) + new_values)

    def update_dmsincomingmails(self):
        ensure = False
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder"):
            ensure = True
            logger.info("Updates dmsincomingmails to ensure creating_group field is set")
        for i, brain in enumerate(self.catalog(portal_type="dmsincomingmail"), 1):
            obj = brain.getObject()
            obj.reindexObject(["markers"])
            if obj.assigned_user is None and brain.review_state == "closed":
                for status in obj.workflow_history["incomingmail_workflow"]:
                    if status["action"] == "close":
                        userid = status["actor"]
                        if is_in_user_groups(
                            suffixes=IM_EDITOR_SERVICE_FUNCTIONS, org_uid=obj.treating_groups, user=api.user.get(userid)
                        ):
                            obj.assigned_user = userid
                            obj.reindexObject(["assigned_user"])
                        break
            if ensure:
                self.ensure_creating_group(obj, index=True)
            if self.commit_value and i % self.commit_value == 0:
                logger.info("On dmsincomingmail update {}".format(i))
                transaction.commit()

    def move_dmsincomingmails(self):
        logger.info("Moving dmsincomingmails")
        orig = self.set_fingerpointing()
        imf_path = "/".join(self.imf.getPhysicalPath())
        counter_dic = {}
        brains = self.catalog(
            portal_type=["dmsincomingmail", "dmsincoming_email"],
            sort_on="organization_type",
            path={"query": imf_path, "depth": 1},
        )
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
                    logger.error(
                        "Cannot move '{}', '{}': {} '{}'".format(
                            brain.UID, brain.getPath(), exc.__class__.__name__, exc
                        )
                    )
                except Exception:
                    logger.error(
                        "Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.Title, exc.__class__.__name__, exc)
                    )
            # obj.reindexObject(['getObjPositionInParent', 'path'])
            if self.commit_value and moved % self.commit_value == 0:
                logger.info("On dmsincomingmail move {}".format(moved))
                transaction.commit()
        logger.info("Moved {} on {} dmsincomingmails".format(moved, len(brains)))
        self.set_fingerpointing(orig)

    def move_dmsoutgoingmails(self):
        logger.info("Moving dmsoutgoingmails")
        orig = self.set_fingerpointing()
        omf_path = "/".join(self.omf.getPhysicalPath())
        counter_dic = {}
        brains = self.catalog(portal_type="dmsoutgoingmail", sort_on="created", path={"query": omf_path, "depth": 1})
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
                    logger.error(
                        "Cannot move '{}', '{}': {} '{}'".format(
                            brain.UID, brain.getPath(), exc.__class__.__name__, exc
                        )
                    )
                except Exception:
                    logger.error(
                        "Cannot move '{}', '{}': {} '{}'".format(brain.UID, brain.Title, exc.__class__.__name__, exc)
                    )
            if self.commit_value and moved % self.commit_value == 0:
                logger.info("On dmsoutgoingmail move {}".format(moved))
                transaction.commit()
        logger.info("Moved {} on {} dmsoutgoingmails".format(moved, len(brains)))
        self.set_fingerpointing(orig)

    def update_catalog1(self):
        """Update catalog or objects"""
        # Lowercased hp email
        logger.info("Updating held_positions")
        brains = self.catalog.searchResults(portal_type="held_position")
        for brain in brains:
            obj = brain.getObject()
            if not obj.email:
                continue
            obj.email = obj.email.lower()
            obj.reindexObject(idxs=["contact_source", "email"])
        logger.info("Updated {} brains".format(len(brains)))
        # Reindex internal_reference_no
        self.reindexIndexes(["internal_reference_no"], update_metadata=True)
        # Ensure creating_group field is set
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder"):
            logger.info("Updates contacts to ensure creating_group field is set")
            self.set_creating_group_on_types(
                GE_CONFIG["contact_group_encoder"]["pt"], GE_CONFIG["contact_group_encoder"]["idx"]
            )

    def update_catalog2(self):
        """Update catalog or objects"""
        # Clean and update
        logger.info("Updating dmsmainfile")
        brains = self.catalog.searchResults(portal_type="dmsmainfile")
        updated = 0
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            roles = obj.rolesOfPermission("Modify portal content")
            # already migrated ?
            if [
                role["name"]
                for role in roles
                if role["selected"] == "SELECTED" and role["name"] == "DmsFile Contributor"
            ]:
                continue
            if self.batch_value and updated > self.batch_value:  # so it is possible to run this step partially
                break
            updated += 1
            # we removed those useless attributes
            for attr in ("conversion_finished", "just_added"):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # specific: we update modification permission on incomingmail main file
            obj.manage_permission(
                "Modify portal content", ("DmsFile Contributor", "Manager", "Site Administrator"), acquire=0
            )
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=["SearchableText", "sender_index", "markers"])
            if self.commit_value and updated % self.commit_value == 0:
                logger.info("On dmsmainfile update {}".format(updated))
                transaction.commit()
        logger.info("Updated {} on {} dmsmainfiles".format(updated, len(brains)))

    def update_catalog3(self):
        """Update catalog or objects"""
        # Clean and update
        logger.info("Updating dmsommainfile")
        brains = self.catalog.searchResults(portal_type="dmsommainfile")
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            # we removed those useless attributes
            for attr in ("conversion_finished", "just_added"):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=["SearchableText", "sender_index", "markers"])
            if self.commit_value and i % self.commit_value == 0:
                logger.info("On dmsommainfile update {}".format(i))
                transaction.commit()
        logger.info("Updated {} dmsommainfiles".format(len(brains)))

    def update_catalog4(self):
        """Update catalog or objects"""
        # Clean and update
        logger.info("Updating dmsappendixfile")
        brains = self.catalog.searchResults(portal_type="dmsappendixfile")
        for i, brain in enumerate(brains, 1):
            obj = brain.getObject()
            # we removed those useless attributes
            for attr in ("conversion_finished", "just_added"):
                if base_hasattr(obj, attr):
                    delattr(obj, attr)
            # specific: we update delete permission
            obj.manage_permission(
                "Delete objects", ("Contributor", "Editor", "Manager", "Site Administrator"), acquire=1
            )
            # we remove left portlet
            blacklistPortletCategory(obj)
            # we update SearchableText to include short relevant scan_id
            # we update sender_index that can be empty after a clear and rebuild !!
            obj.reindexObject(idxs=["SearchableText", "sender_index", "markers"])
            if self.commit_value and i % self.commit_value == 0:
                logger.info("On dmsappendixfile update {}".format(i))
                transaction.commit()
        logger.info("Updated {} dmsappendixfiles".format(len(brains)))

    def clean_examples(self):
        brains = find(
            unrestricted=True, context=self.portal["outgoing-mail"], portal_type="dmsoutgoingmail", id="reponse1"
        )
        if not brains:
            logger.info("Cleaning wrongly added demo users")
            pf = self.portal["contacts"]["personnel-folder"]
            for userid in ["encodeur", "dirg", "chef", "agent", "agent1", "lecteur"]:
                for brain in find(unrestricted=True, context=pf, portal_type="person", id=userid):
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
        for brain in self.catalog(portal_type="task"):
            obj = brain.getObject()
            if obj.__class__ != Task:
                # old_class_name='plone.dexterity.content.Container',
                migrate_base_class_to_new_class(obj, new_class_name="collective.task.content.task.Task")
                obj.reindexObjectSecurity()
                count += 1
        if count:
            logger.info("TASKS class corrected : {}".format(count))

    def ensure_creating_group(self, obj, index=False):
        try:
            owner = obj.getOwner()
        except AttributeError:
            userid = obj.owner_info()["id"]
            owner = self.portal.acl_users.getUserById(userid)
            if owner is not None:
                obj.changeOwnership(owner, recursive=False)
                # obj.reindexObjectSecurity()  not needed because userid is not changed
        if ensure_set_field(obj, "creating_group", default_creating_group(owner)) and index:
            obj.reindexObject(["assigned_group"])

    def set_creating_group_on_types(self, types, index):
        for brain in self.portal.portal_catalog.unrestrictedSearchResults(portal_type=types):
            obj = brain._unrestrictedGetObject()
            self.ensure_creating_group(obj, index=bool(index))

    def sync_solr(self):
        full_key = "collective.solr.port"
        configured_port = api.portal.get_registry_record(full_key, default=None)
        if configured_port is None:
            return
        active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
        if not active_solr:
            logger.info("Activating solr")
            api.portal.set_registry_record("collective.solr.active", True)
        logger.info("Syncing solr on %s" % self.portal.absolute_url_path())
        response = self.portal.REQUEST.RESPONSE
        original = response.write
        response.write = lambda x: x  # temporarily ignore output
        maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
        maintenance.sync()  # BATCHED
        response.write = original


def migrate(context):
    Migrate_To_3_0(context).run()
