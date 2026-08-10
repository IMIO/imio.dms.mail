# -*- coding: utf-8 -*-
from collective.documentgenerator.utils import update_oo_config
from collective.iconifiedcategory.behaviors.iconifiedcategorization import IIconifiedCategorizationMarker
from collective.iconifiedcategory.content.events import content_updated
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import update_all_categorized_elements
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.quickupload.browser.quickupload_settings import IQuickUploadControlPanel
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from datetime import datetime
from datetime import timedelta
from dexterity.localroles.utils import fti_configuration
from ftw.labels.interfaces import ILabelRoot
from imio.dms.mail import _tr as _
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import DEFAULT_DISPLAYED_TABS
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.interfaces import IPersonnelFolder
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.interfaces import IReqDashboard
from imio.dms.mail.setuphandlers import add_db_col_folder
from imio.dms.mail.setuphandlers import configure_faceted_folder
from imio.dms.mail.setuphandlers import configure_signrequest_rolefields
from imio.dms.mail.setuphandlers import create_personnel_dashboard
from imio.dms.mail.setuphandlers import createReqCollections
from imio.dms.mail.setuphandlers import createStateCollections
from imio.dms.mail.setuphandlers import order_1st_level
from imio.dms.mail.setuphandlers import setup_iconified_categories
from imio.dms.mail.utils import message_status
from imio.dms.mail.utils import update_solr_config
from imio.helpers.batching import batch_delete_files
from imio.helpers.batching import batch_get_keys
from imio.helpers.batching import batch_handle_key
from imio.helpers.batching import batch_hashed_filename
from imio.helpers.batching import batch_loop_else
from imio.helpers.batching import batch_skip_key
from imio.helpers.batching import can_delete_batch_files
from imio.helpers.content import object_values
from imio.helpers.setup import load_type_from_package
from imio.helpers.setup import load_workflow_from_package
from imio.helpers.workflow import do_transitions
from imio.migrator.migrator import Migrator
from imio.pyutils.system import get_git_tag
from plone import api
from plone.registry.events import RecordModifiedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from zope.component import getGlobalSiteManager
from zope.event import notify
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.lifecycleevent import IObjectModifiedEvent

import ast
import json
import logging
import OFS
import os


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
        self.old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
        self.new_version = safe_unicode(get_git_tag(BLDT_DIR))

    def run_parts(self):
        """Run some parts between b and x."""
        if self.is_in_part("c"):  # various, update workflow, localroles and security
            # Update d-print model
            obj = self.portal.templates.om["d-print"]
            api.content.rename(obj=obj, new_id="d-print-to-sign", safe_id=False)
            if obj.tal_condition == "python: context.restrictedTraverse('odm-utils').is_odt_activated()":
                obj.tal_condition = ("python: object.portal_workflow.getInfoFor(object, 'review_state') in "
                                     "('created', 'validated', 'to_print')")
                obj.title = _(u"To sign files print template")
                obj.reindexObject(idxs=["Title", "sortable_title", "SearchableText"])
            else:
                logger.error("d-print template has not expected condition: '{}'".format(obj.tal_condition))
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
                        if name == u"imio.dms.mail.wfadaptations.OMToPrint":
                            name = u"imio.dms.mail.wfadaptations.OMToPrintAdaptation"
                            record = api.portal.get_registry_record("collective.wfadaptations.applied_adaptations")
                            new_record = []
                            for dic in record:
                                new_dic = dict(dic)
                                if new_dic["adaptation"] == u"imio.dms.mail.wfadaptations.OMToPrint":
                                    new_dic["adaptation"] = name
                                new_record.append(new_dic)
                            api.portal.set_registry_record("collective.wfadaptations.applied_adaptations", new_record)
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

                # update om_to_email and om_treating collection
                for col_id in ("om_to_email", "om_treating"):
                    col = self.omf["mail-searches"].get(col_id)
                    if col:
                        new_lst = []
                        change = False
                        for dic in col.query:
                            if dic["i"] == "review_state" and len(dic["v"]) == 1 and dic["v"][0] == "to_be_signed":
                                dic["v"] = ["signed"]
                                change = True
                            new_lst.append(dic)
                        if change:
                            col.query = new_lst

                # change back confirmation message
                key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
                values = list(api.portal.get_registry_record(key, default=[]))
                changes = False
                if values and "dmsoutgoingmail.back_to_signed|" not in values:
                    values.append("dmsoutgoingmail.back_to_signed|")
                    changes = True
                if changes:
                    api.portal.set_registry_record(key, values)

            # clean catalog
            self.clean_catalog()
            # update permissions, roles and reindex allowedRolesAndUsers
            finished = self.reindexIndexes(['allowedRolesAndUsers'], portal_types=['dmsoutgoingmail'])
            logger.info("Part c is {}finished".format("" if finished else "not "))

        if self.is_in_part("d"):  # finish security update
            finished = self.reindexIndexes(['allowedRolesAndUsers'],
                                           portal_types=['dmsommainfile', "dmsappendixfile", "task"])
            logger.info("Part d is {}finished".format("" if finished else "not "))

        if self.is_in_part("e"):
            # reindex om markers
            finished = self.reindexIndexes(['markers'], portal_types=['dmsoutgoingmail'])
            logger.info("Part e is {}finished".format("" if finished else "not "))

        if self.is_in_part("f"):  # reload types, added categories and update items using categories
            a_t_f = self.portal["annexes_types"]
            if "incoming_dms_files" not in a_t_f:
                self.runProfileSteps("collective.dms.basecontent", steps=["actions"])  # for actions columns
                odt_only = self.registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile")
                self.runProfileSteps("imio.dms.mail", steps=["catalog", "plone.app.registry", "actions"])
                if odt_only is not None:
                    del self.registry.records["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile"]
                    if odt_only:
                        formats = ["odt"]
                    else:
                        formats = ["odt", "pdf", "doc"]
                    api.portal.set_registry_record(
                        "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_formats_mainfile",
                        formats
                    )

                load_type_from_package("dmsoutgoingmail", "imio.dms.mail:default")  # ISigningBehavior behavior
                load_type_from_package("held_position", "imio.dms.mail:default")  # IUsagesBehavior behavior
                load_type_from_package("dmsmainfile", "collective.dms.basecontent:default")  # iconified
                load_type_from_package("dmsmainfile", "imio.dms.mail:default")
                load_type_from_package("dmsommainfile", "imio.dms.mail:default")  # iconified
                load_type_from_package("dmsappendixfile", "imio.dms.mail:default")  # iconified
                load_type_from_package("dmsappendixfile", "imio.dms.mail:default")  # iconified
                load_type_from_package("annex", "imio.dms.mail:default")  # behavior
                load_type_from_package("ConfigurablePODTemplate", "imio.dms.mail:default")  # content category, behavior
                load_type_from_package("SubTemplate", "imio.dms.mail:default")  # behavior
                setup_iconified_categories(self.portal)
                a_t_f["annexes"].title = _("Folders Appendix Files")
                alsoProvides(a_t_f["annexes"], IProtectedItem)
                a_t_f["annexes"].reindexObject()
                self.context.runImportStepFromProfile(u'imio.dms.mail:examples', u'imiodmsmail-add-test-annexes-types')
                templates = self.catalog.unrestrictedSearchResults(portal_type=["ConfigurablePODTemplate"])
                category_id = calculate_category_id(self.portal["annexes_types"]["outgoing_dms_files"]
                                                    ["outgoing-dms-file"])
                for template in templates:
                    obj = template.getObject()
                    if not obj.default_content_category:
                        obj.default_content_category = category_id

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

        if self.is_in_part("g"):  # 3.1.6 sign_request
            self.add_sign_request()

        if self.is_in_part("t"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()
                # setting QuickUpload simultaneous uploads limit to 1
                IQuickUploadControlPanel(self.portal).set_sim_upload_limit(1)
                # updated existing templates
                brains = self.catalog.unrestrictedSearchResults(
                    portal_type=["ConfigurablePODTemplate"], path='/'.join(self.portal.templates.om.getPhysicalPath()))
                doc_cb_download_uid = self.portal.templates.om["download_barcode"].UID()
                ending_pos = self.portal.templates.om.getObjectPosition("ending")
                self.portal.templates.om.moveObjectToPosition("download_barcode", ending_pos + 1)
                for brain in brains:
                    obj = brain.getObject()
                    merge_templates = [dic["template"] for dic in obj.merge_templates
                                       if dic["pod_context_name"] == "doc_cb_download"]
                    if not merge_templates:
                        merge_templates = list(obj.merge_templates)
                        merge_templates.append(
                            {"pod_context_name": u"doc_cb_download", "do_rendering": False,
                             "template": doc_cb_download_uid})
                        obj.merge_templates = merge_templates
                # Changed permission after plone.restapi installation
                self.portal.manage_permission("plone.restapi: Use REST API", ("Member",), acquire=0)

    def run(self):
        self.run_initialization()

        if self.is_in_part("a"):
            self.solr_deactivate()

        if self.is_in_part("b"):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            # collective.contact.facetednav
            # collective.iconifiedcategory (on existing objects, folders only if the first time)
            # imio.pm.wsclient
            # collective.contact.plonegroup
            self.upgradeAll(omit=[u"imio.dms.mail:default"])

        self.run_parts()

        if self.is_in_part("x"):  # clear solr
            self.solr_clear()

        if self.is_in_part("y"):  # sync solr (long time, batchable)
            self.solr_sync()

        self.run_finish()

    def run_initialization(self):
        """run method initialization"""
        logger.info("Migrating from version {} to {}".format(self.old_version, self.new_version))
        self.log_mem("START")

    def run_finalization(self):
        """run method finalization"""
        zope_app = self.portal
        while not isinstance(zope_app, OFS.Application.Application):
            zope_app = zope_app.aq_parent
        update_oo_config()
        if "cputils_install" not in zope_app.objectIds():
            manage_addExternalMethod(zope_app, "cputils_install", "", "CPUtils.utils", "install")
        ret = zope_app.cputils_install(zope_app)
        ret = ret.replace("<div>Those methods have been added: ", "").replace("</div>", "")
        if ret:
            logger.info('CPUtils added methods: "{}"'.format(ret.replace("<br />", ", ")))
        if message_status("doc", older=timedelta(days=90), to_state="inactive"):
            logger.info("doc message deactivated")
        self.runProfileSteps("imio.dms.mail", steps=["cssregistry", "jsregistry"])
        cssr = self.portal.portal_css
        if ARCHIVE_SITE and not cssr.getResource("imiodmsmail_archives.css").getEnabled():
            cssr.updateStylesheet("imiodmsmail_archives.css", enabled=True)
        cssr.cookResources()
        self.cleanRegistries()
        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry["collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete"] = False
        # version
        api.portal.set_registry_record("imio.dms.mail.product_version", self.new_version)
        now = datetime.now()
        end = (now + timedelta(days=30)).strftime("%Y%m%d-%H%M")
        if self.old_version != self.new_version:
            if "new-version" in self.portal["messages-config"]:
                api.content.delete(self.portal["messages-config"]["new-version"])
            # with solr, bug in col.iconifiedcategory.content.events.categorized_content_container_moved
            # self.portal["messages-config"].REQUEST.set("defer_categorized_content_created_event", True)
            add_message(
                "new-version",
                "Maj version",
                u"<p><strong>iA.docs a été mis à jour le {} de la version {} à la version {}</strong>. Vous "
                u"pouvez consulter les changements en cliquant sur le numéro de version en bas de page."
                u"</p>".format(now.strftime("%d-%m-%Y"), self.old_version, self.new_version),
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
        # update front-page
        frontpage = self.portal["front-page"]
        if frontpage.Title() == "Gestion du courrier 3.0":
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype="text/html")
        # update portal title
        self.portal.title = "Gestion du courrier 3.1"

    def run_finish(self):
        """run method finish"""
        self.log_mem("END")
        logger.info("Really finished at {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.finish()

    def clean_catalog(self):
        """clean catalog for bad unindexed entries"""
        pc = self.portal.portal_catalog
        _c = pc._catalog
        cleaned = 0
        for path in list(_c.uids.keys()):
            if pc.resolve_path(path) is None:
                cleaned += 1
                rid = _c.uids.get(path)
                logger.warn("Removing stale entry '{}'".format(path))
                try:
                    # get a "ExtendedPathIndex Attempt to unindex nonexistent object" message but do the job
                    pc.uncatalog_object(path)
                except Exception:
                    if rid is not None:
                        if rid in _c.data:
                            del _c.data[rid]
                        if rid in _c.paths:
                            del _c.paths[rid]
                        del _c.uids[path]
                        _c._length.change(-1)

    def solr_deactivate(self):
        """Deactivates solr if activated and updates ports"""
        active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
        if active_solr:
            self.upgradeProfile("collective.solr:default")
            self.runProfileSteps("collective.solr", steps=["plone.app.registry"])
            logger.info("Deactivating solr")
            api.portal.set_registry_record("collective.solr.active", False)
        update_solr_config()

    def solr_clear(self):
        """Reactivates and clears solr"""
        active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
        if active_solr is not None:
            if not active_solr:
                logger.info("Activating solr")
                api.portal.set_registry_record("collective.solr.active", True)
            logger.info("Clearing solr on %s" % self.portal.absolute_url_path())
            maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
            maintenance.clear()

    def solr_sync(self):
        """Reactivates and syncs solr"""
        active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
        if active_solr is not None:
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

    def add_sign_request(self):
        """sign_request type and workflow, requests folder, related settings."""
        # reload type and workflow
        load_type_from_package("sign_request", "imio.dms.mail:default", create=True)  # new type
        load_workflow_from_package("sign_request_workflow", "imio.dms.mail:default", create=True)  # new workflow
        wtool = api.portal.get_tool("portal_workflow")
        if "sign_request_workflow" not in wtool.getChainForPortalType("sign_request"):
            wtool.setChainForPortalTypes(("sign_request",), ("sign_request_workflow",))
            # reapply permissions on existing sign_request
            wtool.updateRoleMappings()

        self.runProfileSteps("imio.dms.mail", steps=["rolemap"])

        # folder
        if not base_hasattr(self.portal, "requests"):
            # configure the local roles per state for the sign_request rolefields
            configure_signrequest_rolefields(self.portal)

            folderid = self.portal.invokeFactory("Folder", id="requests", title=_(u"requests_tab"))
            req_folder = getattr(self.portal, folderid)
            req_folder.setExcludeFromNav(True)
            alsoProvides(req_folder, INextPrevNotNavigable)
            alsoProvides(req_folder, ILabelRoot)
            # alsoProvides(req_folder, ICountableTab)
            alsoProvides(req_folder, IProtectedItem)
            # add searches
            col_folder = add_db_col_folder(req_folder, "requests-searches", _("Requests searches"), _("Requests"))
            alsoProvides(col_folder, INextPrevNotNavigable)
            alsoProvides(col_folder, IReqDashboard)
            createReqCollections(col_folder)
            createStateCollections(col_folder, "sign_request")
            configure_faceted_folder(col_folder, xml="requests-searches.xml",
                                     default_UID=col_folder["all_requests"].UID())
            # configure faceted
            configure_faceted_folder(
                req_folder, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_requests"].UID()
            )

            req_folder.setConstrainTypesMode(1)
            req_folder.setLocallyAllowedTypes(["sign_request"])
            req_folder.setImmediatelyAddableTypes(["sign_request"])
            do_transitions(req_folder, ["show_internally"])
            logger.info("requests folder created")
            order_1st_level(self.portal)

        # signrequest settings
        if not api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.request_esign_formats"):
            api.portal.set_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.request_esign_formats", ["odt", "pdf"])
        if not api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.request_fields"):
            fields = [
                "IBasic.title",
                "IBasic.description",
                "treating_groups",
                "ITask.assigned_user",
                "recipient_groups",
                "ISignRequestSigningBehavior.signers",
                "ISignRequestSigningBehavior.esign",
            ]
            api.portal.set_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.request_fields", [
                    {"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in fields
                ]
            )

        # change back confirmation message
        key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
        values = list(api.portal.get_registry_record(key, default=[]))
        if values and "sign_request.back_to_creation|" not in values:
            values.extend(["sign_request.back_to_creation|",
                           "sign_request.back_to_approve|",
                           "sign_request.back_to_be_signed|",
                           "sign_request.back_to_signed|", ])
            api.portal.set_registry_record(key, values)

        # sign request categories
        setup_iconified_categories(self.portal)

        # corrected collections
        for col_id in ("searchfor_to_approve", "to_approve", "in_esign_sessions"):
            col_folder = self.omf["mail-searches"].get(col_id)
            if col_folder is not None and col_folder.sort_on != u"created":
                col_folder.sort_on = u"created"

        # restrict the outgoing-mail in_esign_sessions collection
        om_esign_col = self.omf["mail-searches"].get("in_esign_sessions")
        if om_esign_col is not None:
            query = list(om_esign_col.query)
            if not any(dic.get("i") == "portal_type" for dic in query):
                query.insert(
                    0,
                    {
                        "i": "portal_type",
                        "o": "plone.app.querystring.operation.selection.is",
                        "v": ["dmsoutgoingmail"],
                    },
                )
                om_esign_col.query = query

        # first level tabs are now driven by the displayed_tabs setting
        if not api.portal.get_registry_record("imio.dms.mail.displayed_tabs"):
            np = self.portal.portal_properties.navtree_properties
            displayed = []
            for tab_id in DEFAULT_DISPLAYED_TABS:
                if tab_id == "folders":
                    visible = "ClassificationFolders" not in list(np.metaTypesNotToList)
                elif tab_id == "tree":
                    visible = "ClassificationContainer" not in list(np.metaTypesNotToList)
                else:
                    visible = base_hasattr(self.portal, tab_id)
                if visible:
                    displayed.append(tab_id)
            api.portal.set_registry_record(
                "imio.dms.mail.displayed_tabs", displayed)
            unlisted = [t for t in np.metaTypesNotToList
                        if t not in ("ClassificationFolders", "ClassificationContainer")]
            if list(np.metaTypesNotToList) != unlisted:
                np.manage_changeProperties(metaTypesNotToList=unlisted)

    def fix_localroles_json_quoting(self):
        """Fixes JSON quoting in localroles configuration"""
        fixed = []
        for fti in self.portal.portal_types.objectValues():
            localroles = getattr(fti, "localroles", None)
            if not localroles:
                continue
            changed = False
            for keyname, states in localroles.items():
                if not isinstance(states, dict):
                    continue
                for state, principals in states.items():
                    for principal, cfg in principals.items():
                        rel = cfg.get("rel", "")
                        if not rel:
                            continue
                        try:
                            json.loads(rel)
                            continue  # already valid JSON -> skip
                        except (ValueError, TypeError):
                            pass
                        try:
                            cfg["rel"] = json.dumps(ast.literal_eval(rel))
                        except (ValueError, SyntaxError):
                            logger.error("Cannot normalize rel %r on %s/%s/%s/%s",
                                         rel, fti.getId(), keyname, state, principal)
                            continue
                        changed = True
            if changed:
                localroles._p_changed = True
                fixed.append(fti.getId())
        logger.info("Normalized localroles 'rel' on portal types: %s", fixed)

    def setup_personnel_dashboard(self):
        """Convert personnel-folder from z3c.table listing to faceted dashboard."""
        pf = self.contacts["personnel-folder"]
        if IPersonnelFolder.providedBy(pf):
            noLongerProvides(pf, IPersonnelFolder)
        pf.setLocallyAllowedTypes(["person", "Folder"])
        pf.setImmediatelyAddableTypes(["person"])
        create_personnel_dashboard(pf)
        pf.setLayout("facetednavigation_view")
        pf.setLocallyAllowedTypes(["person"])
        pf.setDefaultPage(None)
        logger.info("Converted personnel-folder to faceted dashboard")


def migrate(context):  # noqa
    Migrate_To_3_1(context).run()
