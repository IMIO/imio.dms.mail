# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseOutgoingMail
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.wfadaptations import IMServiceValidation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation


class TestPermissionsOutgoingMailWfAdapt(TestPermissionsBaseOutgoingMail):
    def test_permissions_outgoing_mail_wfadapt_service_validation(self):
        change_user(self.portal)
        params = {
            "state_title": u"À valider par le chef de service",
            "forward_transition_title": u"Proposer au chef de service",
            "backward_transition_title": u"Renvoyer au chef de service",
            "function_title": u"N+1",
        }
        sva = IMServiceValidation()
        sva.patch_workflow("outgoingmail_workflow", **params)

        self.assertHasNoPerms("chef", self.omail)

    def test_permissions_outgoing_mail_wfadapt_to_print(self):
        change_user(self.portal)
        tpa = OMToPrintAdaptation()
        tpa.patch_workflow("outgoingmail_workflow")

        self.assertHasNoPerms("chef", self.omail)
