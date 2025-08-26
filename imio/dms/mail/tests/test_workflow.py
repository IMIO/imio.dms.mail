# -*- coding: utf-8 -*-
""" workflow tests for this package."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import get_dms_config

import unittest


class TestWorkflows(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pw = self.portal.portal_workflow

    def test_im_workflow0(self):
        """Check workflow"""
        self.imw = self.pw["incomingmail_workflow"]
        self.assertSetEqual(
            set(self.imw.states), {"created", "proposed_to_manager", "proposed_to_agent", "in_treatment", "closed"}
        )
        self.assertSetEqual(
            set(self.imw.transitions),
            {
                "back_to_creation",
                "back_to_manager",
                "back_to_agent",
                "back_to_treatment",
                "propose_to_manager",
                "propose_to_agent",
                "treat",
                "close",
            },
        )
        self.assertSetEqual(set(self.imw.states["created"].transitions), {"propose_to_manager", "propose_to_agent"})
        self.assertSetEqual(
            set(self.imw.states["proposed_to_manager"].transitions), {"back_to_creation", "propose_to_agent"}
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_agent"].transitions),
            {"back_to_creation", "back_to_manager", "treat", "close"},
        )
        self.assertSetEqual(set(self.imw.states["in_treatment"].transitions), {"back_to_agent", "close"})
        self.assertSetEqual(set(self.imw.states["closed"].transitions), {"back_to_treatment", "back_to_agent"})
        # default annotations
        wf_from_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus"])
        self.assertSetEqual(set(wf_from_to["to"]), {("closed", "close"), ("proposed_to_agent", "propose_to_agent")})

    def test_om_workflow0(self):
        """Check workflow"""
        self.omw = self.pw["outgoingmail_workflow"]
        self.assertSetEqual(set(self.omw.states), {"created", "scanned", "to_be_signed", "signed", "sent"})
        self.assertSetEqual(
            set(self.omw.transitions),
            {
                "back_to_creation",
                "back_to_agent",
                "back_to_scanned",
                "back_to_be_signed",
                "back_to_signed",
                "set_scanned",
                "propose_to_be_signed",
                "mark_as_sent",
                "mark_as_signed",
            },
        )
        self.assertSetEqual(
            set(self.omw.states["created"].transitions), {"set_scanned", "propose_to_be_signed", "mark_as_sent"}
        )
        self.assertSetEqual(set(self.omw.states["scanned"].transitions), {"mark_as_sent", "back_to_agent"})
        self.assertSetEqual(set(self.omw.states["to_be_signed"].transitions),
                            {"mark_as_sent", "mark_as_signed", "back_to_creation"})
        self.assertSetEqual(
            set(self.omw.states["signed"].transitions),
            {"back_to_be_signed", "back_to_scanned", "back_to_creation", "mark_as_sent"}
        )
        self.assertSetEqual(
            set(self.omw.states["sent"].transitions),
            {"back_to_be_signed", "back_to_signed", "back_to_scanned", "back_to_creation"}
        )
        # related
        folder = self.portal["outgoing-mail"]["mail-searches"]
        self.assertFalse(folder["to_validate"].enabled)

    def test_task_workflow0(self):
        """Check workflow"""
        self.tw = self.pw["task_workflow"]
        self.assertSetEqual(set(self.tw.states), {"created", "to_assign", "to_do", "in_progress", "realized", "closed"})
        self.assertSetEqual(
            set(self.tw.transitions),
            {
                "back_in_created",
                "back_in_created2",
                "back_in_to_assign",
                "back_in_to_do",
                "back_in_progress",
                "back_in_realized",
                "do_to_assign",
                "auto_do_to_do",
                "do_to_do",
                "do_in_progress",
                "do_realized",
                "do_closed",
            },
        )
        self.assertSetEqual(set(self.tw.states["created"].transitions), {"do_to_assign"})
        self.assertSetEqual(
            set(self.tw.states["to_assign"].transitions), {"back_in_created", "auto_do_to_do", "do_to_do"}
        )
        self.assertSetEqual(
            set(self.tw.states["to_do"].transitions), {"back_in_created2", "do_in_progress", "do_realized"}
        )
        self.assertSetEqual(set(self.tw.states["in_progress"].transitions), {"back_in_to_do", "do_realized"})
        self.assertSetEqual(
            set(self.tw.states["realized"].transitions), {"back_in_to_do", "back_in_progress", "do_closed"}
        )
        self.assertSetEqual(set(self.tw.states["closed"].transitions), {"back_in_realized"})
        # related
        folder = self.portal["tasks"]["task-searches"]
        self.assertFalse(folder["to_assign"].enabled)
        self.assertFalse(folder["to_close"].enabled)
