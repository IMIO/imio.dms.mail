# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from plone import api

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_4(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # add rename_title action
            self.runProfileSteps("imio.dms.mail", steps=["actions", "plone.app.registry"])
            rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_send_modes"
            if not api.portal.get_registry_record(rec, default=None):
                api.portal.set_registry_record(rec, [
                    {"value": u"post", "dtitle": u"Courrier", "active": True},
                    {"value": u"post_registered", "dtitle": u"Courrier recommandé", "active": True},
                    {"value": u"email", "dtitle": u"Email", "active": True},
                ])

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_4(context).run()
