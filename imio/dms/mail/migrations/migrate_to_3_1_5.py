# -*- coding: utf-8 -*-
from imio.dms.mail.interfaces import IPersonnelFolder
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.dms.mail.setuphandlers import create_personnel_dashboard
from imio.helpers.setup import load_type_from_package
from Products.CMFPlone.utils import base_hasattr
from zope.interface import noLongerProvides

import logging


logger = logging.getLogger("imio.dms.mail")


def setup_personnel_dashboard(portal):
    """Convert personnel-folder from z3c.table listing to faceted dashboard."""
    contacts = portal["contacts"]
    pf = contacts["personnel-folder"]
    pf.setLocallyAllowedTypes(["person", "Folder"])
    pf.setImmediatelyAddableTypes(["person"])
    create_personnel_dashboard(pf)
    if base_hasattr(pf, "layout"):
        del pf.layout
    if IPersonnelFolder.providedBy(pf):
        noLongerProvides(pf, IPersonnelFolder)
    logger.info("Converted personnel-folder to faceted dashboard")


class Migrate_To_3_1_5(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # update settings
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            # reload types for behavior
            load_type_from_package("annex", "imio.dms.mail:default")  # behavior
            load_type_from_package("ConfigurablePODTemplate", "imio.dms.mail:default")  # behavior
            load_type_from_package("SubTemplate", "imio.dms.mail:default")  # behavior
            # DMS-995: convert personnel-folder to faceted dashboard
            setup_personnel_dashboard(self.portal)

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_5(context).run()
