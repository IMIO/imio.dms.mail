# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseIncomingMail
from imio.dms.mail.wfadaptations import IMPreManagerValidation


class TestPermissionsIncomingMailWfAdapt(TestPermissionsBaseIncomingMail):
    def test_permissions_incoming_mail_wfadapt_pre_manager(self):
        change_user(self.portal)
        params = {
            "state_title": u"À valider avant le DG",
            "forward_transition_title": u"Proposer pour prévalidation DG",
            "backward_transition_title": u"Renvoyer pour prévalidation DG",
        }
        pmva = IMPreManagerValidation()
        pmva.patch_workflow("incomingmail_workflow", **params)
        
        self.permissions_incoming_mail()
        