# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.permissions_base import TestPermissionsBaseIncomingMail
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.wfadaptations import IMPreManagerValidation
from imio.dms.mail.wfadaptations import IMServiceValidation
from plone import api


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

        api.user.create(email="test@test.com", username="premanager", password="Password#1")
        api.group.add_user(groupname="pre_manager", username="premanager")
        
        self.permissions_incoming_mail()

        self.pw.doActionFor(self.imail, "back_to_agent")
        self.pw.doActionFor(self.imail, "back_to_creation")
        change_user(self.portal, "encodeur")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("premanager", self.imail)

        self.pw.doActionFor(self.imail, "propose_to_pre_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.imail)
        self.assertEqual(
            self.get_perms("dirg", self.imail),
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
        self.assertHasNoPerms("agent", self.imail)
        self.assertHasNoPerms("agent1", self.imail)
        self.assertEqual(
            self.get_perms("encodeur", self.imail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("premanager", self.imail),
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

        change_user(self.portal, "premanager")
        self.pw.doActionFor(self.imail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("premanager", self.imail),
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

        change_user(self.portal, "dirg")
        self.pw.doActionFor(self.imail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("premanager", self.imail),
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

        change_user(self.portal, "agent")
        self.pw.doActionFor(self.imail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("premanager", self.imail),
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

        self.pw.doActionFor(self.imail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("premanager", self.imail),
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

    def test_permissions_incoming_mail_wfadapt_service_validation(self):
        return True # This test is not implemented yet
        # change_user(self.portal)
        # params = {
        #     "validation_level": 1,
        #     "state_title": u"À valider par le chef de service",
        #     "forward_transition_title": u"Proposer au chef de service",
        #     "backward_transition_title": u"Renvoyer au chef de service",
        #     "function_title": u"N+1",
        # }
        # sva = IMServiceValidation()
        # sva.patch_workflow("incomingmail_workflow", **params)
        # clean_borg_cache(self.portal.REQUEST)
        