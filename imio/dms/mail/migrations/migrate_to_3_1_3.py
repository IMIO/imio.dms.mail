# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1_2 import Migrate_To_3_1_2
from plone import api

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_3(Migrate_To_3_1_2):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            logger.info("Adding imail_send_modes registry record and backfilling send_modes on incoming mails")
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])

            rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_send_modes"
            if not api.portal.get_registry_record(rec, default=None):
                api.portal.set_registry_record(rec, [
                    {"value": u"post", "dtitle": u"Courrier", "active": True},
                    {"value": u"post_registered", "dtitle": u"Courrier recommandé", "active": True},
                    {"value": u"email", "dtitle": u"Email", "active": True},
                ])

            catalog = api.portal.get_tool("portal_catalog")
            for brain in catalog(portal_type=("dmsincomingmail", "dmsincoming_email")):
                obj = brain.getObject()
                if not getattr(obj, "send_modes", None):
                    obj.send_modes = [u"email"] if obj.portal_type == "dmsincoming_email" else [u"post"]

        if self.is_in_part("g"):  # final steps
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_3(context).run()
