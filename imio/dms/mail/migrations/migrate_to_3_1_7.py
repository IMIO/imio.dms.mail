# -*- coding: utf-8 -*-
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from zope.interface import alsoProvides

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_7(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # mark requests tab to add count on
            req_folder = self.portal.get("requests")
            if req_folder is not None and not ICountableTab.providedBy(req_folder):
                alsoProvides(req_folder, ICountableTab)
                req_folder.reindexObject(idxs="object_provides")
                logger.info("requests folder marked as countable tab")

        if self.is_in_part("t"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_7(context).run()
