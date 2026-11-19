# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod


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

        if self.is_in_part("t"):  # final steps, adding om_templates_generation external method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_8(context).run()
