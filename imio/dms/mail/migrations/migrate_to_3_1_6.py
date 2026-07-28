# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1


class Migrate_To_3_1_6(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # update settings
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])

        if self.is_in_part("f"):  # 3.1.6 sign_request
            self.add_sign_request()

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_6(context).run()
