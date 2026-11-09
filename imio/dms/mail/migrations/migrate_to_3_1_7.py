# -*- coding: utf-8 -*-
from collective.documentviewer.settings import GlobalSettings
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.iconifiedcategory.utils import get_category_icon_url
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.dms.mail.interfaces import IReqDashboard
from imio.dms.mail.interfaces import IReqDashboardBatchActions
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.setup import load_type_from_package
from plone import api
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_7(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
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
            # new "export to pdf" actions on dmsoutgoingmail and sign_request
            load_type_from_package("dmsoutgoingmail", "imio.dms.mail:default")
            load_type_from_package("sign_request", "imio.dms.mail:default")
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
            # appendix files now get scan_id, conv_from_uid and esigned in categorized_elements
            parents = set()
            for brain in api.content.find(portal_type="dmsappendixfile"):
                parent = brain.getObject().__parent__
                if parent.portal_type in ("dmsoutgoingmail", "sign_request"):
                    parents.add(parent)
            for parent in parents:
                update_all_categorized_elements(parent, limited=True, sort=False)
                parent._p_changed = True
            logger.info("categorized_elements updated on %d containers with appendix files", len(parents))
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

        if self.is_in_part("t"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_7(context).run()
