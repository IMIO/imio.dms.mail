# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.setup import load_type_from_package

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_5(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # update settings
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            # reload types for behavior
            load_type_from_package("ConfigurablePODTemplate", "imio.dms.mail:default")  # behavior
            load_type_from_package("SubTemplate", "imio.dms.mail:default")  # behavior

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_5(context).run()
