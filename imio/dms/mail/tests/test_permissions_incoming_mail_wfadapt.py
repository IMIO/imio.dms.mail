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

        api.user.create(email="test@test.be", username="premanager", password="Password#1")
        api.group.add_user(groupname="pre_manager", username="premanager")

        self.permissions_incoming_mail()

        self.pw.doActionFor(self.imail, "back_to_agent")
        self.pw.doActionFor(self.imail, "back_to_creation")
        change_user(self.portal, "encodeur")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("premanager", self.imail)
        self.assertHasNoPerms("premanager", self.file)
        self.assertHasNoPerms("premanager", self.annex)
        self.assertHasNoPerms("premanager", self.task)

        self.pw.doActionFor(self.imail, "propose_to_pre_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.imail)
        self.assertOnlyViewPerms("dirg", self.imail)
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

        self.assertHasNoPerms("lecteur", self.file)
        self.assertOnlyViewPerms("dirg", self.file)
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("premanager", self.file),
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

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertOnlyViewPerms("dirg", self.annex)
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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
            self.get_perms("premanager", self.annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        # Potential problem
        self.assertHasNoPerms("premanager", self.task)

        change_user(self.portal, "premanager")
        self.pw.doActionFor(self.imail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertOnlyViewPerms("premanager", self.imail)
        self.assertOnlyViewPerms("premanager", self.file)
        self.assertOnlyViewPerms("premanager", self.annex)
        self.assertHasNoPerms("premanager", self.task)

        change_user(self.portal, "dirg")
        self.pw.doActionFor(self.imail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertOnlyViewPerms("premanager", self.imail)
        self.assertOnlyViewPerms("premanager", self.file)
        self.assertOnlyViewPerms("premanager", self.annex)
        self.assertHasNoPerms("premanager", self.task)

        change_user(self.portal, "agent")
        self.pw.doActionFor(self.imail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertOnlyViewPerms("premanager", self.imail)
        self.assertOnlyViewPerms("premanager", self.file)
        self.assertOnlyViewPerms("premanager", self.annex)
        self.assertHasNoPerms("premanager", self.task)

        self.pw.doActionFor(self.imail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertOnlyViewPerms("premanager", self.imail)
        self.assertOnlyViewPerms("premanager", self.file)
        self.assertOnlyViewPerms("premanager", self.annex)
        self.assertHasNoPerms("premanager", self.task)

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
        clean_borg_cache(self.portal.REQUEST)

        org_uid = self.portal.contacts["plonegroup-organization"]["direction-generale"]["grh"].UID()
        api.group.add_user(groupname="%s_n_plus_1" % org_uid, username="chef")

        self.permissions_incoming_mail()

        change_user(self.portal)
        self.pw.doActionFor(self.imail, "back_to_n_plus_1")
        self.pw.doActionFor(self.imail, "back_to_creation")
        change_user(self.portal, "encodeur")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("chef", self.imail)
        self.assertHasNoPerms("chef", self.file)
        self.assertHasNoPerms("chef", self.annex)
        self.assertHasNoPerms("chef", self.task)

        self.pw.doActionFor(self.imail, "propose_to_manager")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("chef", self.imail)
        self.assertHasNoPerms("chef", self.file)
        self.assertHasNoPerms("chef", self.annex)
        self.assertHasNoPerms("chef", self.task)

        change_user(self.portal, "dirg")
        self.pw.doActionFor(self.imail, "propose_to_n_plus_1")
        clean_borg_cache(self.portal.REQUEST)

        self.assertHasNoPerms("lecteur", self.imail)
        self.assertEqual(
            self.get_perms("dirg", self.imail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
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
            self.get_perms("chef", self.imail),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertHasNoPerms("lecteur", self.file)
        self.assertEqual(
            self.get_perms("dirg", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", self.file)
        self.assertHasNoPerms("agent1", self.file)
        self.assertEqual(
            self.get_perms("encodeur", self.file),
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
            self.get_perms("chef", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertHasNoPerms("lecteur", self.annex)
        self.assertEqual(
            self.get_perms("dirg", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": True,
                "imio.dms.mail: Write treating group field": True,
            },
        )
        self.assertHasNoPerms("agent", self.annex)
        self.assertHasNoPerms("agent1", self.annex)
        self.assertEqual(
            self.get_perms("encodeur", self.annex),
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
            self.get_perms("chef", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": True,
            },
        )

        self.assertHasNoPerms("lecteur", self.task)
        self.assertHasNoPerms("dirg", self.task)
        self.assertHasNoPerms("agent", self.task)
        self.assertHasNoPerms("agent1", self.task)
        self.assertEqual(
            self.get_perms("encodeur", self.task),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": False,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("chef", self.task)

        change_user(self.portal, "chef")
        self.imail.assigned_user = 'agent'
        self.pw.doActionFor(self.imail, "propose_to_agent")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("chef", self.imail),
            {
                "Access contents information": True,
                "Add portal content": True,
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
        self.assertEqual(
            self.get_perms("chef", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
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
        self.assertEqual(
            self.get_perms("chef", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("chef", self.task)

        change_user(self.portal, "agent")
        self.pw.doActionFor(self.imail, "treat")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("chef", self.imail),
            {
                "Access contents information": True,
                "Add portal content": True,
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
        self.assertEqual(
            self.get_perms("chef", self.file),
            {
                "Access contents information": True,
                "Add portal content": True,
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
        self.assertEqual(
            self.get_perms("chef", self.annex),
            {
                "Access contents information": True,
                "Add portal content": True,
                "Delete objects": True,
                "Modify portal content": True,
                "Request review": True,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("chef", self.task)

        self.pw.doActionFor(self.imail, "close")
        clean_borg_cache(self.portal.REQUEST)

        self.assertEqual(
            self.get_perms("chef", self.imail),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("chef", self.file),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertEqual(
            self.get_perms("chef", self.annex),
            {
                "Access contents information": True,
                "Add portal content": False,
                "Delete objects": False,
                "Modify portal content": False,
                "Request review": False,
                "Review portal content": True,
                "View": True,
                "collective.dms.basecontent: Add DmsFile": False,
                "imio.dms.mail: Write mail base fields": False,
                "imio.dms.mail: Write treating group field": False,
            },
        )
        self.assertHasNoPerms("chef", self.task)
