# -*- coding: utf-8 -*-
from collective.iconifiedcategory.behaviors.iconifiedcategorization import IIconifiedCategorizationMarker
from collective.iconifiedcategory.content.events import content_updated
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import update_all_categorized_elements
from collective.messagesviewlet.utils import add_message
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from datetime import datetime
from datetime import timedelta
from dexterity.localroles.utils import fti_configuration
from imio.dms.mail import _tr as _
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.setuphandlers import setup_iconified_categories
from imio.dms.mail.utils import message_status
from imio.dms.mail.utils import update_solr_config
from imio.helpers.batching import batch_delete_files
from imio.helpers.batching import batch_get_keys
from imio.helpers.batching import batch_globally_finished
from imio.helpers.batching import batch_handle_key
from imio.helpers.batching import batch_hashed_filename
from imio.helpers.batching import batch_loop_else
from imio.helpers.batching import batch_skip_key
from imio.helpers.batching import can_delete_batch_files
from imio.helpers.content import object_values
from imio.helpers.setup import load_type_from_package
from imio.helpers.setup import load_workflow_from_package
from imio.migrator.migrator import Migrator
from imio.pyutils.system import get_git_tag
from plone import api
from plone.registry.events import RecordModifiedEvent
from Products.CMFPlone.utils import safe_unicode
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.component import getGlobalSiteManager
from zope.event import notify
from zope.interface import alsoProvides
from zope.lifecycleevent import IObjectModifiedEvent

import logging
import OFS
import os
import transaction


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1(Migrator):  # noqa
    def __init__(self, context, disable_linkintegrity_checks=False):
        Migrator.__init__(self, context, disable_linkintegrity_checks=disable_linkintegrity_checks)
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.acl = self.portal["acl_users"]
        self.contacts = self.portal["contacts"]
        self.batch_value = int(os.getenv("BATCH", "0"))
        self.commit_value = int(os.getenv("COMMIT", "0"))

    def savepoint_flush(self):
        transaction.savepoint(True)
        self.portal._p_jar.cacheGC()

    def run(self):
        old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
        new_version = safe_unicode(get_git_tag(BLDT_DIR))
        logger.info("Migrating from version {} to {}".format(old_version, new_version))
        self.log_mem("START")

        if self.is_in_part("a"):  # install and upgrade products
            # check if oo port or solr port must be changed
            update_solr_config()
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr:
                logger.info("Deactivating solr")
                api.portal.set_registry_record("collective.solr.active", False)

        if self.is_in_part("b"):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            # collective.contact.facetednav
            # collective.iconifiedcategory (on existing objects, folders only if the first time)
            # imio.pm.wsclient
            self.upgradeAll(omit=[u"imio.dms.mail:default"])

        if self.is_in_part("c"):
            # we have to separate batched reindexIndexes in different parts because pkl file is deleted after finished
            if api.group.get("esign_watchers") is None:  # first run
                api.group.create("esign_watchers", "2 Observateurs module signature")

                self.runProfileSteps("imio.dms.mail", steps=["cssregistry", "jsregistry"])

                # Update dashboard pod templates
                self.portal["templates"]["export-users-groups"].max_objects = 0
                self.portal["templates"]["all-contacts-export"].max_objects = 0

                # Update imio.pm.wsclient generated actions translations
                notify(RecordModifiedEvent(
                    self.registry.records.get(
                        "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
                    [],
                    api.portal.get_registry_record(
                        "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
                ))

            # update workflow
            if "signed" not in self.portal.portal_workflow["outgoingmail_workflow"].states:
                reset = load_workflow_from_package("outgoingmail_workflow", "imio.dms.mail:default")
                applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()
                                       if dic["workflow"] == "outgoingmail_workflow"]
                if reset:
                    logger.info("outgoingmail_workflow reloaded")
                    for name in applied_adaptations:
                        success, errors = apply_from_registry(reapply=True, name=name)
                        if errors:
                            raise Exception("Problem applying wf adaptations '%s': %d errors" % (name, errors))
                else:
                    raise Exception("outgoingmail_workflow not reloaded !")

                # update localroles
                lr, fti = fti_configuration(portal_type="dmsoutgoingmail")
                changes = False
                if "imio.dms.mail.content.behaviors.IDmsMailCreatingGroup" in fti.behaviors:
                    lrcg = lr["creating_group"]
                    if "signed" not in lrcg:
                        changes = True
                        lrcg["signed"] = {CREATING_GROUP_SUFFIX: {"roles": ["Reader", "Reviewer"]}}
                    if "to_be_signed" in lrcg and CREATING_GROUP_SUFFIX in lrcg["to_be_signed"] and "Editor" in \
                            lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"]:
                        changes = True
                        # correction !
                        lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"].remove("Editor")
                lrsc = lr["static_config"]
                if "signed" not in lrsc:
                    changes = True
                    lrsc["signed"] = {
                        "expedition": {"roles": ["Editor", "Reviewer"]},
                        "encodeurs": {"roles": ["Reader"]},
                        "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
                        "lecteurs_globaux_cs": {"roles": ["Reader"]},
                    }
                lrtg = lr["treating_groups"]
                if "signed" not in lrtg:
                    changes = True
                    lrtg["signed"] = {
                        "editeur": {"roles": ["Reader"]},
                        "encodeur": {"roles": ["Reader", "Reviewer"]},
                        "lecteur": {"roles": ["Reader"]},
                    }
                if "to_be_signed" in lrtg and "encodeur" in lrtg["to_be_signed"] and "Editor" in \
                        lrtg["to_be_signed"]["encodeur"]["roles"]:
                    changes = True
                    # correction !
                    lrtg["to_be_signed"]["encodeur"]["roles"].remove("Editor")
                lrrg = lr["recipient_groups"]
                if "signed" not in lrrg:
                    changes = True
                    lrrg["signed"] = {
                        "editeur": {"roles": ["Reader"]},
                        "encodeur": {"roles": ["Reader"]},
                        "lecteur": {"roles": ["Reader"]},
                    }
                applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()
                                       if dic["workflow"] == "outgoingmail_workflow"]
                if u"imio.dms.mail.wfadaptations.OMServiceValidation" in applied_adaptations:
                    if "signed" in lrtg and "n_plus_1" not in lrtg["signed"]:
                        changes = True
                        lrtg["signed"]["n_plus_1"] = {"roles": ["Reader"]}
                    if "signed" in lrrg and "n_plus_1" not in lrrg["signed"]:
                        changes = True
                        lrrg["signed"]["n_plus_1"] = {"roles": ["Reader"]}

                if changes:
                    lr._p_changed = True

                # change back confirmation message
                key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
                values = list(api.portal.get_registry_record(key, default=[]))
                if values and "dmsoutgoingmail.back_to_signed|" not in values:
                    values.append("dmsoutgoingmail.back_to_signed|")
                    api.portal.set_registry_record(key, values)

            # update permissions, roles and reindex allowedRolesAndUsers
            finished = self.reindexIndexes(['allowedRolesAndUsers'], portal_types=['dmsoutgoingmail'])
            logger.info("Part c is {}finished".format("" if finished else "not "))

        if self.is_in_part("d"):
            finished = self.reindexIndexes(['allowedRolesAndUsers'],
                                           portal_types=['dmsommainfile', "dmsappendixfile", "task"])
            logger.info("Part d is {}finished".format("" if finished else "not "))

        if self.is_in_part("e"):
            # reindex om markers
            finished = self.reindexIndexes(['markers'], portal_types=['dmsoutgoingmail'])
            logger.info("Part e is {}finished".format("" if finished else "not "))

        if self.is_in_part("f"):
            a_t_f = self.portal["annexes_types"]
            if "incoming_dms_files" not in a_t_f:
                self.runProfileSteps("collective.dms.basecontent", steps=["actions"])  # for actions columns
                self.runProfileSteps("imio.dms.mail", steps=["catalog", "plone.app.registry", "actions"])
                load_type_from_package("dmsoutgoingmail", "imio.dms.mail:default")  # ISigningBehavior behavior
                load_type_from_package("held_position", "imio.dms.mail:default")  # IUsagesBehavior behavior
                load_type_from_package("dmsmainfile", "collective.dms.basecontent:default")  # iconified
                load_type_from_package("dmsmainfile", "imio.dms.mail:default")
                load_type_from_package("dmsommainfile", "imio.dms.mail:default")  # iconified
                load_type_from_package("dmsappendixfile", "imio.dms.mail:default")  # iconified
                load_type_from_package("dmsappendixfile", "imio.dms.mail:default")  # iconified
                setup_iconified_categories(self.portal)
                a_t_f["annexes"].title = _("Folders Appendix Files")
                alsoProvides(a_t_f["annexes"], IProtectedItem)
                a_t_f["annexes"].reindexObject()
                self.context.runImportStepFromProfile(u'imio.dms.mail:examples', u'imiodmsmail-add-test-annexes-types')

            gsm = getGlobalSiteManager()
            gsm.unregisterHandler(content_updated, (IIconifiedCategorizationMarker, IObjectModifiedEvent))
            in_dms_cat = calculate_category_id(a_t_f["incoming_dms_files"]["incoming-dms-file"])
            in_appendix_cat = calculate_category_id(a_t_f["incoming_appendix_files"]["incoming-appendix-file"])
            out_dms_cat = calculate_category_id(a_t_f["outgoing_dms_files"]["outgoing-dms-file"])
            out_appendix_cat = calculate_category_id(a_t_f["outgoing_appendix_files"]["outgoing-appendix-file"])
            values_to_set = {
                "incoming": {
                    "dmsmainfile": (in_dms_cat, None, None, None),
                    "dmsappendixfile": (in_appendix_cat, None, None, None),
                },
                "outgoing": {
                    "dmsommainfile": (out_dms_cat, False, False, False),
                    "dmsappendixfile": (out_appendix_cat, False, False, False),
                },
            }

            portal_types = ["dmsincomingmail", "dmsincoming_email", "dmsoutgoingmail"]
            brains = self.portal.portal_catalog.unrestrictedSearchResults(portal_type=portal_types)
            pklfile = batch_hashed_filename('imio.dms.mail.migrate_to_3_1.pkl', ("f", portal_types))
            batch_keys, batch_config = batch_get_keys(pklfile, loop_length=len(brains), log=True)
            for brain in brains:
                key = brain.UID
                if batch_skip_key(key, batch_keys, batch_config):
                    continue
                files = object_values(brain.getObject(), ["DmsFile", "ImioDmsFile", "DmsAppendixFile"])
                if files:
                    ppt = brain.portal_type in ("dmsincomingmail", "dmsincoming_email") and "incoming" or "outgoing"
                    for fl_obj in files:
                        if not hasattr(fl_obj, "content_category"):
                            values = values_to_set[ppt][fl_obj.portal_type]
                            for attr, val in zip(
                                    ("content_category", "to_approve", "approved", "to_print"), values):
                                if val is not None:
                                    setattr(fl_obj, attr, val)
                            fl_obj.reindexObject(["content_category_uid"])
                    update_all_categorized_elements(brain.getObject())
                if batch_handle_key(key, batch_keys, batch_config):
                    break
            else:
                batch_loop_else(batch_keys, batch_config)
            if can_delete_batch_files(batch_keys, batch_config):
                batch_delete_files(batch_keys, batch_config, log=True)

        if self.is_in_part("g"):
            old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
            new_version = safe_unicode(get_git_tag(BLDT_DIR))
            logger.info("Current migration from version {} to {}".format(old_version, new_version))

            # Update dashboard pod templates
            # self.portal["templates"]["export-users-groups"].max_objects = 0
            # self.portal["templates"]["all-contacts-export"].max_objects = 0
            #
            # # Update imio.pm.wsclient generated actions translations
            # notify(RecordModifiedEvent(
            #     self.registry.records.get("imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
            #     [],
            #     api.portal.get_registry_record(
            #         "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
            # ))

            # signing
            # self.runProfileSteps("collective.dms.basecontent", steps=["actions"])  # for actions columns
            # self.runProfileSteps("imio.dms.mail", steps=["catalog", "plone.app.registry", "actions"])
            # load_type_from_package("dmsoutgoingmail", "profile-imio.dms.mail:default")  # ISigningBehavior behavior
            # load_type_from_package("held_position", "profile-imio.dms.mail:default")  # IUsagesBehavior behavior
            # load_type_from_package("dmsappendixfile", "profile-imio.dms.mail:default")  # iconified
            # load_type_from_package("dmsommainfile", "profile-imio.dms.mail:default")  # iconified

            # Update wf changes
            # finished1 = finished2 = finished3 = finished4 = True
            # reset = load_workflow_from_package("outgoingmail_workflow", "imio.dms.mail:default")
            # applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()
            #                        if dic["workflow"] == "outgoingmail_workflow"]
            # if reset:
            #     logger.info("outgoingmail_workflow reloaded")
            #     for name in applied_adaptations:
            #         success, errors = apply_from_registry(reapply=True, name=name)
            #         if errors:
            #             logger.error("Problem applying wf adaptations '%s': %d errors" % (name, errors))
            #     # update permissions, roles and reindex allowedRolesAndUsers
            #     # count = self.portal.portal_workflow.updateRoleMappings()  out of memory
            #     # logger.info("Updated {} items".format(count))
            #     finished1 = self.reindexIndexes(['allowedRolesAndUsers'], portal_types=['dmsoutgoingmail'])
            #     if finished1:
            #         finished2 = self.reindexIndexes(['allowedRolesAndUsers'],
            #                                         portal_types=['dmsommainfile', "dmsappendixfile", "task"])
            #     else:
            #         finished2 = False
            # else:
            #     logger.error("outgoingmail_workflow not reloaded !")
            #
            # # update localroles
            # finished = finished1 and finished2
            # if finished:
            #     lr, fti = fti_configuration(portal_type="dmsoutgoingmail")
            #     changes = False
            #     if "imio.dms.mail.content.behaviors.IDmsMailCreatingGroup" in fti.behaviors:
            #         lrcg = lr["creating_group"]
            #         if "signed" not in lrcg:
            #             changes = True
            #             lrcg["signed"] = {CREATING_GROUP_SUFFIX: {"roles": ["Reader", "Reviewer"]}}
            #         if "to_be_signed" in lrcg and CREATING_GROUP_SUFFIX in lrcg["to_be_signed"] and "Editor" in \
            #                 lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"]:
            #             changes = True
            #             # correction !
            #             lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"].remove("Editor")
            #     lrsc = lr["static_config"]
            #     if "signed" not in lrsc:
            #         changes = True
            #         lrsc["signed"] = {
            #             "expedition": {"roles": ["Editor", "Reviewer"]},
            #             "encodeurs": {"roles": ["Reader"]},
            #             "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
            #             "lecteurs_globaux_cs": {"roles": ["Reader"]},
            #         }
            #     lrtg = lr["treating_groups"]
            #     if "signed" not in lrtg:
            #         changes = True
            #         lrtg["signed"] = {
            #             "editeur": {"roles": ["Reader"]},
            #             "encodeur": {"roles": ["Reader", "Reviewer"]},
            #             "lecteur": {"roles": ["Reader"]},
            #         }
            #     if "to_be_signed" in lrtg and "encodeur" in lrtg["to_be_signed"] and "Editor" in \
            #             lrtg["to_be_signed"]["encodeur"]["roles"]:
            #         changes = True
            #         # correction !
            #         lrtg["to_be_signed"]["encodeur"]["roles"].remove("Editor")
            #     lrrg = lr["recipient_groups"]
            #     if "signed" not in lrrg:
            #         changes = True
            #         lrrg["signed"] = {
            #             "editeur": {"roles": ["Reader"]},
            #             "encodeur": {"roles": ["Reader"]},
            #             "lecteur": {"roles": ["Reader"]},
            #         }
            #     if u"imio.dms.mail.wfadaptations.OMServiceValidation" in applied_adaptations:
            #         if "signed" in lrtg and "n_plus_1" not in lrtg["signed"]:
            #             changes = True
            #             lrtg["signed"]["n_plus_1"] = {"roles": ["Reader"]}
            #         if "signed" in lrrg and "n_plus_1" not in lrrg["signed"]:
            #             changes = True
            #             lrrg["signed"]["n_plus_1"] = {"roles": ["Reader"]}
            #
            #     if changes:
            #         lr._p_changed = True
            #
            #     # change back confirmation message
            #     key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
            #     values = list(api.portal.get_registry_record(key, default=[]))
            #     if values and "dmsoutgoingmail.back_to_signed|" not in values:
            #         values.append("dmsoutgoingmail.back_to_signed|")
            #         api.portal.set_registry_record(key, values)
            #
            #     # add signed collection
            #     col_folder = self.portal["outgoing-mail"]["mail-searches"]
            #     createStateCollections(self.portal["outgoing-mail"]["mail-searches"], "dmsoutgoingmail")
            #     pos = col_folder.getObjectPosition("searchfor_to_be_signed")
            #     col_folder.moveObjectToPosition("searchfor_signed", pos + 1)
            #
            #     # reindex om markers
            #     finished3 = self.reindexIndexes(['markers'], portal_types=['dmsoutgoingmail'])
            # finished = finished and finished3

            # imio.annex integration to dms files with iconified category
            # load_type_from_package("dmsmainfile", "imio.dms.mail:default")
            # load_type_from_package("dmsommainfile", "imio.dms.mail:default")
            # load_type_from_package("dmsappendixfile", "imio.dms.mail:default")
            # setup_iconified_categories(self.portal)
            # a_t_f = self.portal["annexes_types"]
            # a_t_f["annexes"].title = _("Folders Appendix Files")
            # alsoProvides(a_t_f["annexes"], IProtectedItem)
            # a_t_f["annexes"].reindexObject()
            # self.context.runImportStepFromProfile(u'imio.dms.mail:examples', u'imiodmsmail-add-test-annexes-types')
            # if finished:
            #     files = self.portal.portal_catalog.unrestrictedSearchResults(
            #         portal_type=["dmsmainfile", "dmsommainfile", "dmsappendixfile"])
            #
            #     def update_category(obj):
            #         incoming_dms_category = a_t_f["incoming_dms_files"]["incoming-dms-file"]
            #         incoming_appendix_category = a_t_f["incoming_appendix_files"]["incoming-appendix-file"]
            #         outgoing_dms_category = a_t_f["outgoing_dms_files"]["outgoing-dms-file"]
            #         outgoing_appendix_category = a_t_f["outgoing_appendix_files"]["outgoing-appendix-file"]
            #         if not hasattr(obj, "content_category"):
            #             category = None
            #             if obj.portal_type == "dmsmainfile":
            #                 category = incoming_dms_category
            #             elif obj.portal_type == "dmsommainfile":
            #                 category = outgoing_dms_category
            #             elif obj.portal_type == "dmsappendixfile":
            #                 parent_type = obj.getObject().aq_parent.portal_type
            #                 if parent_type in ("dmsincomingmail", "dmsincoming_email"):
            #                     category = incoming_appendix_category
            #                 elif parent_type == "dmsoutgoingmail":
            #                     category = outgoing_appendix_category
            #             return calculate_category_id(category)
            #         return obj.content_category
            #
            #     def post_update_category(obj):
            #         category = get_category_object(obj, obj.content_category)
            #         update_categorized_elements(obj.aq_parent, obj, category)
            #     finished4 = self.set_attribute(files, "content_category", func=update_category,
            #                                    post_func=post_update_category)
            #     finished4 = finished4 and self.set_attribute(files, "to_approve", False)
            #     finished4 = finished4 and self.set_attribute(files, "approved", False)
            #     finished4 = finished4 and self.set_attribute(files, "to_print", False)
            # finished = finished and finished4
            # END

            # finished = True  # can be eventually returned and set by batched method
            if old_version != new_version:
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
                now = datetime.now()
                end = (now + timedelta(days=30)).strftime("%Y%m%d-%H%M")
                if old_version != new_version:
                    if "new-version" in self.portal["messages-config"]:
                        api.content.delete(self.portal["messages-config"]["new-version"])
                    # with solr, bug in col.iconifiedcategory.content.events.categorized_content_container_moved
                    # self.portal["messages-config"].REQUEST.set("defer_categorized_content_created_event", True)
                    add_message(
                        "new-version",
                        "Maj version",
                        u"<p><strong>iA.docs a été mis à jour le {} de la version {} à la version {}</strong>. Vous "
                        u"pouvez consulter les changements en cliquant sur le numéro de version en bas de page."
                        u"</p>".format(now.strftime("%d-%m-%Y"), old_version, new_version),
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
            # if active_solr:
            #     logger.info("Activating solr")
            #     api.portal.set_registry_record("collective.solr.active", True)

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

    def set_attribute(self, brains, attribute_name, func=None, post_func=None, batch=1000):
        """
        Batched method to set an attribute
        :param brains: catalog brains list
        :param attribute_name: attribute name to set
        :param func: function to infer value from brain
        :param post_func: function to call after setting attribute on object
        :param batch: batch size
        :return: True if finished, False if not
        """
        if not callable(func):
            value = func
            func = lambda x: value  # noqa E731
        if post_func is None:
            post_func = lambda x: None  # noqa E731
        pghandler = ZLogHandler(steps=batch)
        pghandler.init('sync', len(brains))
        pklfile = batch_hashed_filename('imio.dms.mail.{}.pkl'.format(attribute_name))
        batch_keys, batch_config = batch_get_keys(pklfile, loop_length=len(brains))
        for i, b in enumerate(brains):
            uid = b.UID
            if batch_skip_key(uid, batch_keys, batch_config):
                continue
            obj = b.getObject()
            value = func(b)
            setattr(obj, attribute_name, value)
            obj._p_changed = True
            post_func(obj)
            if pghandler:
                pghandler.report(i)
            if batch_handle_key(uid, batch_keys, batch_config):
                break
        else:
            batch_loop_else(batch_keys, batch_config)
        if can_delete_batch_files(batch_keys, batch_config):
            batch_delete_files(batch_keys, batch_config)
        if pghandler:
            pghandler.finish()
        return batch_globally_finished(batch_keys, batch_config)


def migrate(context):
    Migrate_To_3_1(context).run()
