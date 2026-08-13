# -*- coding: utf-8 -*-
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_6(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # Update d-print model
            self.update_print_template()
            # Correct localroles config
            self.fix_localroles_json_quoting()
            # update settings
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            # DMS-995: convert personnel-folder to faceted dashboard
            self.setup_personnel_dashboard()
            # DMS-1217, DMS-605: allow empty annex titles, default to file name
            self.remove_category_predefined_titles()
            catalog = self.portal.portal_catalog
            for brain in catalog.unrestrictedSearchResults(portal_type="person",
                                                           object_provides=IPersonnelContact.__identifier__):
                # brain._unrestrictedGetObject().reindexObject(idxs=["usages", "primary_organization"])
                brain._unrestrictedGetObject().reindexObject(idxs=["usages"])

        if self.is_in_part("g"):  # 3.1.6 sign_request
            self.add_sign_request()

        if self.is_in_part("t"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_6(context).run()
