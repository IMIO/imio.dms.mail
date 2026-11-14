# -*- coding: utf-8 -*-
from collective.documentviewer.settings import GlobalSettings
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.iconifiedcategory.utils import get_category_icon_url
from collective.iconifiedcategory.utils import update_all_categorized_elements
from collective.quickupload.browser.quickupload_settings import IQuickUploadControlPanel
from imio.dms.mail.interfaces import IReqDashboard
from imio.dms.mail.interfaces import IReqDashboardBatchActions
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.batching import batch_delete_files
from imio.helpers.batching import batch_get_keys
from imio.helpers.batching import batch_handle_key
from imio.helpers.batching import batch_hashed_filename
from imio.helpers.batching import batch_loop_else
from imio.helpers.batching import batch_skip_key
from imio.helpers.batching import can_delete_batch_files
from imio.helpers.setup import load_type_from_package
from plone import api
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_7(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # batch approval limit setting and new iemail_creating_group setting
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            # "doc" file format replaced by "docx"
            for key in ("omail_formats_mainfile", "omail_esign_formats", "request_esign_formats"):
                rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(key)
                formats = api.portal.get_registry_record(rec, default=None)
                if formats and "doc" in formats:
                    api.portal.set_registry_record(rec, [fmt == "doc" and "docx" or fmt for fmt in formats])
            # odt, ods and odp are split from word, excel and ppt in imio.helpers: still convert them
            gsettings = GlobalSettings(self.portal)
            gsettings.auto_layout_file_types = list(gsettings.auto_layout_file_types) + [
                ftype for ftype in ("odt", "ods", "odp") if ftype not in gsettings.auto_layout_file_types
            ]
            # mark requests tab to add count on
            req_folder = self.portal.get("requests")
            if req_folder is not None and not ICountableTab.providedBy(req_folder):
                alsoProvides(req_folder, ICountableTab)
                req_folder.reindexObject(idxs="object_provides")
                logger.info("requests folder marked as countable tab")
            # new "export to pdf" actions on dmsoutgoingmail and sign_request, "export to zip" on mails and folders
            for type_name in ("dmsincomingmail", "dmsincoming_email", "dmsoutgoingmail", "sign_request",
                              "ClassificationFolder", "ClassificationSubfolder"):
                load_type_from_package(type_name, "imio.dms.mail:default")
            # d-print templates replaced by the "export to pdf" forms: disabled, not yet removed
            for tid in ("d-print-to-sign", "d-print-signed"):
                tmpl = self.portal["templates"]["om"].get(tid)
                if tmpl is not None and tmpl.enabled:
                    tmpl.enabled = False
                    tmpl.reindexObject(idxs=["enabled"])
            # corrected collections
            self.normalize_compound_criterion_values()
            # batch actions on requests dashboard
            if req_folder is not None:
                col_folder = req_folder["requests-searches"]
                noLongerProvides(col_folder, IReqDashboard)
                alsoProvides(col_folder, IReqDashboardBatchActions)
                for brain in api.content.find(context=col_folder, portal_type="DashboardCollection"):
                    obj = brain.getObject()
                    if u"select_row" not in obj.customViewFields:
                        obj.customViewFields = (u"select_row",) + tuple(obj.customViewFields)
            # new iconified.js for sign/approve icons on dmsoutgoingmail and sign_request
            self.runProfileSteps("imio.dms.mail", steps=["jsregistry"])
            # icon_url stored by 3.1 migration before categories commit has bad image scale
            icons = {brain.UID: get_category_icon_url(brain._unrestrictedGetObject())
                     for brain in self.catalog.unrestrictedSearchResults(
                         object_provides="collective.iconifiedcategory.content.category.ICategory")}
            fixed = 0
            for brain in self.catalog.unrestrictedSearchResults(
                    portal_type=["dmsincomingmail", "dmsincoming_email", "dmsoutgoingmail"]):
                obj = brain._unrestrictedGetObject()
                elements = getattr(obj, "categorized_elements", None) or {}
                if any(infos["icon_url"] != icons.get(infos["category_uid"], infos["icon_url"])
                       for infos in elements.values()):
                    # sort (default) sets _p_changed
                    update_all_categorized_elements(obj, limited=True, sort=False)
                    obj._p_changed = True
                    fixed += 1
            logger.info("categorized_elements icon_url corrected on %d mails", fixed)
            # unique id for each uploaded file: no 'file already exists' error
            IQuickUploadControlPanel(self.portal).set_object_unique_id(True)

        if self.is_in_part("f"):
            # appendix files now get scan_id, conv_from_uid and esigned in categorized_elements
            # paths only, to avoid waking up all objects before batching
            candidates = set(brain.getPath() for brain in self.catalog.unrestrictedSearchResults(
                portal_type=["dmsoutgoingmail", "sign_request"]))
            parents = sorted(set(brain.getPath().rsplit("/", 1)[0] for brain in
                                 self.catalog.unrestrictedSearchResults(portal_type="dmsappendixfile")) & candidates)
            pklfile = batch_hashed_filename("imio.dms.mail.migrate_to_3_1_7.pkl", ("f",))
            batch_keys, batch_config = batch_get_keys(pklfile, loop_length=len(parents), log=True)
            for path in parents:
                if batch_skip_key(path, batch_keys, batch_config):
                    continue
                parent = self.portal.unrestrictedTraverse(path)
                update_all_categorized_elements(parent, limited=True, sort=False)
                parent._p_changed = True
                if batch_handle_key(path, batch_keys, batch_config):
                    break
            else:
                batch_loop_else(batch_keys, batch_config)
            if can_delete_batch_files(batch_keys, batch_config):
                batch_delete_files(batch_keys, batch_config, log=True)
            logger.info("categorized_elements updated on %d containers with appendix files", len(parents))

        if self.is_in_part("t"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_7(context).run()
