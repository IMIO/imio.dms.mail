# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseIncomingMail
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.wfadaptations import IMPreManagerValidation
from imio.dms.mail.wfadaptations import IMServiceValidation


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
        clean_borg_cache(self.portal.REQUEST)
        
        self.permissions_incoming_mail()

        self.pw.doActionFor(self.imail, "back_to_agent")
        self.pw.doActionFor(self.imail, "back_to_creation")
        clean_borg_cache(self.portal.REQUEST)
        change_user(self.portal, "encodeur")

        self.assertHasNoPerms("lecteur", self.imail)

    def test_permissions_incoming_mail_wfadapt_service_validation(self):
        change_user(self.portal)
        params = {
            "validation_level": 1,
            "state_title": u"À valider par le chef de service",
            "forward_transition_title": u"Proposer au chef de service",
            "backward_transition_title": u"Renvoyer au chef de service",
            "function_title": u"N+1",
        }
        sva = IMServiceValidation()
        sva.patch_workflow("incomingmail_workflow", **params)

        self.assertHasNoPerms("chef", self.imail)
