# -*- coding: utf-8 -*-
from collective.querynextprev.interfaces import INextPrevNotNavigable
from eea.facetednavigation.interfaces import IHidePloneLeftColumn
from imio.dms.mail.interfaces import IPersonnelDashboardBatchActions
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.dms.mail.setuphandlers import add_db_col_folder
from imio.dms.mail.setuphandlers import blacklistPortletCategory
from imio.dms.mail.setuphandlers import configure_faceted_folder
from imio.dms.mail.setuphandlers import createPersonnelCollections
from plone import api
from Products.CMFPlone.utils import base_hasattr
from zope.interface import alsoProvides

import logging


logger = logging.getLogger("imio.dms.mail")


def setup_personnel_dashboard(portal):
    """Convert personnel-folder from z3c.table listing to faceted dashboard."""
    contacts = portal["contacts"]
    pf = contacts["personnel-folder"]
    # allow Folder type for the searches subfolder
    pf.setLocallyAllowedTypes(["person", "Folder"])
    pf.setImmediatelyAddableTypes(["person"])
    # create personnel-searches dashboard subfolder
    if not base_hasattr(pf, "personnel-searches"):
        col_folder = add_db_col_folder(pf, "personnel-searches", u"Personnel searches", u"Personnel")
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IPersonnelDashboardBatchActions)
        alsoProvides(col_folder, IHidePloneLeftColumn)
        blacklistPortletCategory(col_folder)
        createPersonnelCollections(col_folder)
        configure_faceted_folder(
            col_folder, xml="personnel-searches.xml", default_UID=col_folder["all_personnel"].UID()
        )
    pf.setDefaultPage("personnel-searches")
    if hasattr(pf, "layout"):
        del pf.layout
    logger.info("Converted personnel-folder to faceted dashboard")


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
            self.clean_catalog()
            # DMS-995: convert personnel-folder to faceted dashboard
            setup_personnel_dashboard(self.portal)

        if self.is_in_part("t"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_4(context).run()
