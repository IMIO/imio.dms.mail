# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1


class Migrate_To_3_1_8(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("t"):  # final steps, adding om_templates_generation external method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_8(context).run()
