# -*- coding: utf-8 -*-
from collective.querynextprev.interfaces import INextPrevNotNavigable
from ftw.labels.interfaces import ILabelRoot
from imio.dms.mail import _tr as _
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.helpers.setup import load_type_from_package
from imio.helpers.workflow import do_transitions
from Products.CMFPlone.utils import base_hasattr
from zope.interface import alsoProvides

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_6(Migrate_To_3_1):  # noqa

    def run_parts(self):

        if self.is_in_part("c"):
            # update settings
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            # reload types for behavior
            load_type_from_package("sign_request", "imio.dms.mail:default")  # new type
            self.runProfileSteps("imio.dms.mail", steps=["rolemap"])
            # folder
            if not base_hasattr(self.portal, "requests"):
                folderid = self.portal.invokeFactory("Folder", id="requests", title=_(u"requests_tab"))
                req_folder = getattr(self.portal, folderid)
                alsoProvides(req_folder, INextPrevNotNavigable)
                alsoProvides(req_folder, ILabelRoot)
                # alsoProvides(req_folder, ICountableTab)
                alsoProvides(req_folder, IProtectedItem)

                req_folder.setConstrainTypesMode(1)
                req_folder.setLocallyAllowedTypes(["sign_request"])
                req_folder.setImmediatelyAddableTypes(["sign_request"])
                do_transitions(req_folder, ["show_internally"])
                logger.info("requests folder created")

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()


def migrate(context):
    Migrate_To_3_1_6(context).run()
