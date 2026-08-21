# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_7(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            self.update_print_templates()
            self.activate_request_printing()
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])

        if self.is_in_part("d"):
            # the dashboard print indicator now follows to_print instead of the file format
            finished = self.reindexIndexes(["markers"], portal_types=["dmsoutgoingmail"])
            logger.info("Part d is {}finished".format("" if finished else "not "))

        if self.is_in_part("t"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_7(context).run()
