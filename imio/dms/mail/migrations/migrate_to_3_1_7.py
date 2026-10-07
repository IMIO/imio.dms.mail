# -*- coding: utf-8 -*-
from collective.documentviewer.settings import GlobalSettings
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.setup import load_type_from_package
from plone import api
from zope.interface import alsoProvides

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

        if self.is_in_part("t"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_7(context).run()
