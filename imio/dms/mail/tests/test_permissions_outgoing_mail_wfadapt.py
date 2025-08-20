# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseOutgoingMail
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.wfadaptations import IMServiceValidation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation


class TestPermissionsOutgoingMailWfAdapt(TestPermissionsBaseOutgoingMail):
    def test_permissions_outgoing_mail_wfadapt_service_validation(self):
        return True  # This test is not implemented yet
        # change_user(self.portal)
        # params = {
        #     "state_title": u"À valider par le chef de service",
        #     "forward_transition_title": u"Proposer au chef de service",
        #     "backward_transition_title": u"Renvoyer au chef de service",
        #     "function_title": u"N+1",
        # }
        # sva = IMServiceValidation()
        # sva.patch_workflow("outgoingmail_workflow", **params)
        # clean_borg_cache(self.portal.REQUEST)

    def test_permissions_outgoing_mail_wfadapt_to_print(self):
        change_user(self.portal)
        tpa = OMToPrintAdaptation()
        tpa.patch_workflow("outgoingmail_workflow")
        clean_borg_cache(self.portal.REQUEST)

        self.permissions_outgoing_mail()

        self.pw.doActionFor(self.omail, "back_to_print")
        clean_borg_cache(self.portal.REQUEST)
        change_user(self.portal, "encodeur")

        self.assertEqual(
            self.get_perms("lecteur", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("dirg", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("agent", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("agent1", self.omail)
        self.assertEqual(
            self.get_perms("encodeur", self.omail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
