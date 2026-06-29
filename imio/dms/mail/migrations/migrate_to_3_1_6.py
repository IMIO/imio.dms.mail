# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_6(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            self.fix_localroles_json_quoting()

        if self.is_in_part("t"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_6(context).run()
