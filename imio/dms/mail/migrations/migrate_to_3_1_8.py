# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.setup import load_type_from_package
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_8(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # Correct external method names
            self.rename_external_methods()
            # Add new external method
            if "docs_om_temp_deactivation" not in self.portal.objectIds():
                manage_addExternalMethod(
                    self.portal, "docs_om_temp_deactivation", "", "imio.dms.mail.maintenance",
                    "om_temp_deactivation"
                )
            # sign request appendix files got a scan_id without scan_id reindex. Few ones: no batching
            sr_brains = self.catalog.unrestrictedSearchResults(portal_type="sign_request")
            sr_paths = set(brain.getPath() for brain in sr_brains)
            brains = [brain for brain in self.catalog.unrestrictedSearchResults(portal_type="dmsappendixfile")
                      if brain.getPath().rsplit("/", 1)[0] in sr_paths]
            for brain in brains:
                brain._unrestrictedGetObject().reindexObject(idxs=["scan_id"])
            logger.info("scan_id reindexed on %d sign request appendix files", len(brains))
            # new "export to zip" action on mails, sign requests and folders
            for type_name in ("dmsincomingmail", "dmsincoming_email", "dmsoutgoingmail", "sign_request",
                              "ClassificationFolder", "ClassificationSubfolder"):
                load_type_from_package(type_name, "imio.dms.mail:default")

        if self.is_in_part("t"):  # final steps, adding om_templates_generation external method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_8(context).run()
