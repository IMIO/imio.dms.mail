# -*- coding: utf-8 -*-
""" wfadaptations.py tests for this package."""
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.wfadaptations.api import add_applied_adaptation
from datetime import datetime
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.dmsmail import AssignedUserValidator
from imio.dms.mail.dmsmail import IMEdit
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import sub_create
from imio.dms.mail.wfadaptations import IMServiceValidation
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import getUtility
from zope.interface import Interface
from zope.interface import Invalid
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory

import unittest
import zope.event


class TestIMServiceValidation1(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pw = self.portal.portal_workflow
        self.imw = self.pw["incomingmail_workflow"]
        api.group.create("abc_group_encoder", "ABC group encoder")
        self.imail = sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "test", **{"title": u"test"}
        )
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_im_workflow1(self):
        """Check workflow"""
        self.assertSetEqual(
            set(self.imw.states),
            {"created", "proposed_to_manager", "proposed_to_n_plus_1", "proposed_to_agent", "in_treatment", "closed"},
        )
        self.assertSetEqual(
            set(self.imw.transitions),
            {
                "back_to_creation",
                "back_to_manager",
                "back_to_n_plus_1",
                "back_to_agent",
                "back_to_treatment",
                "propose_to_manager",
                "propose_to_n_plus_1",
                "propose_to_agent",
                "treat",
                "close",
            },
        )
        self.assertSetEqual(
            set(self.imw.states["created"].transitions),
            {"propose_to_manager", "propose_to_n_plus_1", "propose_to_agent"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_manager"].transitions),
            {"back_to_creation", "propose_to_n_plus_1", "propose_to_agent"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_n_plus_1"].transitions),
            {"back_to_creation", "back_to_manager", "propose_to_agent", "close"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_agent"].transitions),
            {"back_to_creation", "back_to_manager", "back_to_n_plus_1", "treat", "close"},
        )
        self.assertSetEqual(set(self.imw.states["in_treatment"].transitions), {"back_to_agent", "close"})
        self.assertSetEqual(
            set(self.imw.states["closed"].transitions), {"back_to_n_plus_1", "back_to_treatment", "back_to_agent"}
        )

    def test_IMServiceValidation1(self):
        """
        Test IMServiceValidation adaptations
        """
        # is function added
        self.assertIn("n_plus_1", [fct["fct_id"] for fct in get_registry_functions()])
        # is local roles modified
        for ptype in ("dmsincomingmail", "dmsincoming_email"):
            fti = getUtility(IDexterityFTI, name=ptype)
            lr = getattr(fti, "localroles")
            self.assertIn("proposed_to_n_plus_1", lr["static_config"], ptype)
            self.assertIn("proposed_to_n_plus_1", lr["treating_groups"], ptype)
            self.assertIn("proposed_to_n_plus_1", lr["recipient_groups"], ptype)
        for ptype in ("ClassificationFolder", "ClassificationSubfolder"):
            fti = getUtility(IDexterityFTI, name=ptype)
            lr = getattr(fti, "localroles")
            self.assertIn("n_plus_1", lr["treating_groups"]["active"], ptype)
            self.assertIn("n_plus_1", lr["recipient_groups"]["active"], ptype)
        # check collection
        folder = self.portal["incoming-mail"]["mail-searches"]
        self.assertIn("searchfor_proposed_to_n_plus_1", folder)
        self.assertEqual(folder.getObjectPosition("searchfor_proposed_to_agent"), 13)
        self.assertEqual(folder.getObjectPosition("searchfor_proposed_to_n_plus_1"), 12)
        self.assertFalse(folder["to_treat_in_my_group"].showNumberOfItems)
        # check annotations
        config = get_dms_config(["review_levels", "dmsincomingmail"])
        self.assertIn("_n_plus_1", config)
        config = get_dms_config(["review_states", "dmsincomingmail"])
        self.assertIn("proposed_to_n_plus_1", config)
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertIn("propose_to_n_plus_1", config)
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertEqual(config["proposed_to_manager"].values()[0][0], "propose_to_n_plus_1")
        self.assertEqual(config["proposed_to_agent"].values()[0][1], "back_to_n_plus_1")
        wf_from_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus"])
        self.assertListEqual(
            wf_from_to["to"],
            [
                ("closed", "close"),
                ("proposed_to_agent", "propose_to_agent"),
                ("proposed_to_n_plus_1", "propose_to_n_plus_1"),
            ],
        )
        # check vocabularies
        factory = getUtility(IVocabularyFactory, u"collective.eeafaceted.collectionwidget.cachedcollectionvocabulary")
        self.assertEqual(len(factory(folder, folder)), 16)
        factory = getUtility(IVocabularyFactory, u"imio.dms.mail.IMReviewStatesVocabulary")
        self.assertEqual(len(factory(folder)), 6)
        # check configuration
        lst = api.portal.get_registry_record("imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions")
        self.assertIn("dmsincomingmail.back_to_n_plus_1|", lst)
        self.assertIn("dmsincoming_email.back_to_n_plus_1|", lst)
        lst = api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states")
        self.assertIn("proposed_to_n_plus_1", lst)

    def test_ImioDmsIncomingMailWfConditionsAdapter_can_do_transition1(self):
        # imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        # creation is made earlier otherwise wf_from_to['to'] is again at default value ??????????????
        self.assertEqual(api.content.get_state(self.imail), "created")
        adapted = self.imail.wf_conditions()
        change_user(self.portal, "encodeur")
        # no treating_group: NOK
        self.assertTupleEqual(self.pw.getTransitionsFor(self.imail), ())
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        # tg ok, following states
        self.imail.treating_groups = get_registry_organizations()[0]
        self.assertListEqual(
            [dic["id"] for dic in self.pw.getTransitionsFor(self.imail)], ["propose_to_manager", "propose_to_n_plus_1"]
        )
        api.portal.set_registry_record(AUC_RECORD, "no_check")
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))  # has higher level
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_1"))
        # tg ok, following states: no more n_plus_1 user
        groupname = "{}_n_plus_1".format(self.imail.treating_groups)
        api.group.remove_user(groupname=groupname, username="chef")
        self.assertFalse(group_has_user(groupname))
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))  # no user
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))
        # tg ok, assigner_user nok, auc ok
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))  # no user
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))  # ok because no n+1 level
        # tg ok, assigner_user nok, auc nok
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        # tg ok, state ok, assigner_user ok, auc nok
        self.imail.assigned_user = "chef"
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname, username="chef")
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_1"))
        api.content.transition(self.imail, "propose_to_n_plus_1")
        change_user(self.portal, "chef")
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_n_plus_1")
        # tg ok, state ok, assigner_user nok, auc nok
        self.imail.assigned_user = None
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        self.assertTrue(adapted.can_do_transition("back_to_creation"))
        self.assertTrue(adapted.can_do_transition("back_to_manager"))
        self.assertFalse(adapted.can_do_transition("unknown"))
        # WE DO TRANSITION
        self.imail.assigned_user = "chef"
        api.content.transition(self.imail, "propose_to_agent")
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_agent")
        self.assertTrue(adapted.can_do_transition("back_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("back_to_creation"))
        self.assertFalse(adapted.can_do_transition("back_to_manager"))
        # we remove n+1 users
        api.group.remove_user(groupname=groupname, username="chef")
        self.assertFalse(adapted.can_do_transition("back_to_n_plus_1"))
        self.assertTrue(adapted.can_do_transition("back_to_creation"))
        self.assertTrue(adapted.can_do_transition("back_to_manager"))

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond1(self):
        folder = self.portal["incoming-mail"]["mail-searches"]
        col = folder["searchfor_proposed_to_n_plus_1"]
        n_plus_1_view = IdmUtilsMethods(col, col.REQUEST)
        self.assertFalse(n_plus_1_view.proposed_to_n_plus_col_cond())
        self.change_user("encodeur")
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        self.change_user("agent")
        self.assertFalse(n_plus_1_view.proposed_to_n_plus_col_cond())
        api.group.add_user(groupname="abc_group_encoder", username="agent")
        self.change_user("agent")  # relog to "refresh" getGroups
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        api.group.remove_user(groupname="abc_group_encoder", username="agent")
        self.change_user("dirg")
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())
        self.change_user("chef")
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())

    def test_treating_groups_change_on_edit1(self):
        """Test only treating_groups change while the state is on a service validation level"""
        self.assertEqual(api.content.get_state(self.imail), "created")
        view = IdmUtilsMethods(self.imail, self.imail.REQUEST)
        adapted = self.imail.wf_conditions()
        edit_view = IMEdit(self.imail, self.imail.REQUEST)
        auv = AssignedUserValidator(self.imail, edit_view.request, edit_view, "fld", "widget")
        change_user(self.portal, "encodeur")
        org1, org2 = get_registry_organizations()[0:2]
        groupname1 = "{}_n_plus_1".format(org1)
        groupname2 = "{}_n_plus_1".format(org2)
        self.assertTrue(group_has_user(groupname2))
        # with api.env.adopt_roles(['Manager']):
        api.group.remove_user(groupname=groupname1, username="chef")
        self.assertFalse(group_has_user(groupname1))
        self.imail.treating_groups = org1
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))  # no user
        self.imail.treating_groups = org2
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_1"))
        # with api.env.adopt_roles(['Manager']):
        api.content.transition(self.imail, "propose_to_n_plus_1")
        # we check assigned_user requirement
        edit_view.request.form["form.widgets.treating_groups"] = [org1]
        self.assertEqual(api.portal.get_registry_record(AUC_RECORD), "n_plus_1")
        self.assertIsNone(auv.validate(None))
        # with api.env.adopt_roles(['Manager']):
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        self.assertRaises(Invalid, auv.validate, None)
        # notify modification
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        self.imail.treating_groups = org1
        zope.event.notify(ObjectModifiedEvent(self.imail, Attributes(Interface, "treating_groups")))
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_agent")


class TestIMServiceValidation2(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pw = self.portal.portal_workflow
        self.imw = self.pw["incomingmail_workflow"]
        self.imail = sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "test", **{"title": u"test"}
        )
        api.group.create("abc_group_encoder", "ABC group encoder")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )
        sva = IMServiceValidation()
        n_plus_2_params = {
            "validation_level": 2,
            "state_title": u"Valider par le chef de département",
            "forward_transition_title": u"Proposer au chef de département",
            "backward_transition_title": u"Renvoyer au chef de département",
            "function_title": u"chef de département",
        }
        adapt_is_applied = sva.patch_workflow("incomingmail_workflow", **n_plus_2_params)
        if adapt_is_applied:
            add_applied_adaptation(
                "imio.dms.mail.wfadaptations.IMServiceValidation", "incomingmail_workflow", True, **n_plus_2_params
            )
        for uid in get_registry_organizations():
            self.portal.acl_users.source_groups.addPrincipalToGroup("chef", "%s_n_plus_2" % uid)

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_im_workflow2(self):
        """Check workflow"""
        self.assertSetEqual(
            set(self.imw.states),
            {
                "created",
                "proposed_to_manager",
                "proposed_to_n_plus_2",
                "proposed_to_n_plus_1",
                "proposed_to_agent",
                "in_treatment",
                "closed",
            },
        )
        self.assertSetEqual(
            set(self.imw.transitions),
            {
                "back_to_creation",
                "back_to_manager",
                "back_to_n_plus_2",
                "back_to_n_plus_1",
                "back_to_agent",
                "back_to_treatment",
                "propose_to_manager",
                "propose_to_n_plus_2",
                "propose_to_n_plus_1",
                "propose_to_agent",
                "treat",
                "close",
            },
        )
        self.assertSetEqual(
            set(self.imw.states["created"].transitions),
            {"propose_to_manager", "propose_to_n_plus_2", "propose_to_n_plus_1", "propose_to_agent"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_manager"].transitions),
            {"back_to_creation", "propose_to_n_plus_2", "propose_to_n_plus_1", "propose_to_agent"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_n_plus_2"].transitions),
            {"back_to_creation", "back_to_manager", "propose_to_n_plus_1", "propose_to_agent", "close"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_n_plus_1"].transitions),
            {"back_to_creation", "back_to_manager", "back_to_n_plus_2", "propose_to_agent", "close"},
        )
        self.assertSetEqual(
            set(self.imw.states["proposed_to_agent"].transitions),
            {"back_to_creation", "back_to_manager", "back_to_n_plus_2", "back_to_n_plus_1", "treat", "close"},
        )
        self.assertSetEqual(set(self.imw.states["in_treatment"].transitions), {"back_to_agent", "close"})
        self.assertSetEqual(
            set(self.imw.states["closed"].transitions),
            {"back_to_n_plus_2", "back_to_n_plus_1", "back_to_treatment", "back_to_agent"},
        )

    def test_IMServiceValidation2(self):
        """
        Test IMServiceValidation adaptations
        """
        # is function added
        self.assertIn("n_plus_2", [fct["fct_id"] for fct in get_registry_functions()])
        # is local roles modified
        for ptype in ("dmsincomingmail", "dmsincoming_email"):
            fti = getUtility(IDexterityFTI, name=ptype)
            lr = getattr(fti, "localroles")
            self.assertIn("proposed_to_n_plus_2", lr["static_config"], ptype)
            self.assertIn("proposed_to_n_plus_2", lr["treating_groups"], ptype)
            self.assertIn("proposed_to_n_plus_2", lr["recipient_groups"], ptype)
        for ptype in ("ClassificationFolder", "ClassificationSubfolder"):
            fti = getUtility(IDexterityFTI, name=ptype)
            lr = getattr(fti, "localroles")
            self.assertIn("n_plus_2", lr["treating_groups"]["active"], ptype)
            self.assertIn("n_plus_2", lr["recipient_groups"]["active"], ptype)
        # check collection
        folder = self.portal["incoming-mail"]["mail-searches"]
        self.assertIn("searchfor_proposed_to_n_plus_2", folder)
        self.assertEqual(folder.getObjectPosition("searchfor_proposed_to_agent"), 14)
        self.assertEqual(folder.getObjectPosition("searchfor_proposed_to_n_plus_1"), 13)
        self.assertEqual(folder.getObjectPosition("searchfor_proposed_to_n_plus_2"), 12)
        self.assertFalse(folder["to_treat_in_my_group"].showNumberOfItems)
        # check annotations
        config = get_dms_config(["review_levels", "dmsincomingmail"])
        self.assertIn("_n_plus_2", config)
        config = get_dms_config(["review_states", "dmsincomingmail"])
        self.assertIn("proposed_to_n_plus_2", config)
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertIn("propose_to_n_plus_2", config)
        self.assertTrue(all(config["propose_to_n_plus_2"].values()))  # all is True
        self.assertTrue(all(config["propose_to_n_plus_1"].values()))  # all is True
        self.assertFalse(any(config["propose_to_agent"].values()))  # all is False
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertEqual(config["proposed_to_manager"].values()[0][0], "propose_to_n_plus_2")
        self.assertEqual(config["proposed_to_n_plus_2"].values()[0][0], "propose_to_n_plus_1")
        self.assertEqual(config["proposed_to_n_plus_1"].values()[0][1], "back_to_n_plus_2")
        self.assertEqual(config["proposed_to_agent"].values()[0][1], "back_to_n_plus_1")
        wf_from_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus"])
        self.assertListEqual(
            wf_from_to["to"],
            [
                ("closed", "close"),
                ("proposed_to_agent", "propose_to_agent"),
                ("proposed_to_n_plus_1", "propose_to_n_plus_1"),
                ("proposed_to_n_plus_2", "propose_to_n_plus_2"),
            ],
        )
        # check vocabularies
        factory = getUtility(IVocabularyFactory, u"collective.eeafaceted.collectionwidget.cachedcollectionvocabulary")
        self.assertEqual(len(factory(folder, folder)), 17)
        factory = getUtility(IVocabularyFactory, u"imio.dms.mail.IMReviewStatesVocabulary")
        self.assertEqual(len(factory(folder)), 7)
        # check configuration
        lst = api.portal.get_registry_record("imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions")
        self.assertIn("dmsincomingmail.back_to_n_plus_2|", lst)
        self.assertIn("dmsincoming_email.back_to_n_plus_2|", lst)
        lst = api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states")
        self.assertIn("proposed_to_n_plus_2", lst)

    def test_ImioDmsIncomingMailWfConditionsAdapter_can_do_transition2(self):
        # imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        # creation is made earlier otherwise wf_from_to['to'] is again at default value ??????????????
        self.assertEqual(api.content.get_state(self.imail), "created")
        adapted = self.imail.wf_conditions()
        change_user(self.portal, "encodeur")
        # no treating_group: NOK
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        # tg ok, following states
        self.imail.treating_groups = get_registry_organizations()[0]
        api.portal.set_registry_record(AUC_RECORD, "no_check")
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_2"))
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        # tg ok, following states: no more n_plus_ user
        groupname2 = "{}_n_plus_2".format(self.imail.treating_groups)
        api.group.remove_user(groupname=groupname2, username="chef")
        self.assertFalse(group_has_user(groupname2))
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_2"))
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        groupname1 = "{}_n_plus_1".format(self.imail.treating_groups)
        api.group.remove_user(groupname=groupname1, username="chef")
        self.assertFalse(group_has_user(groupname1))
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_2"))
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))
        # tg ok, assigner_user nok, auc ok
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))  # no user
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))  # ok because no n+1 level
        # tg ok, assigner_user nok, auc nok
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        # tg ok, state ok, assigner_user ok, auc nok
        self.imail.assigned_user = "chef"
        self.assertTrue(adapted.can_do_transition("propose_to_agent"))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname2, username="chef")
        api.content.transition(self.imail, "propose_to_n_plus_2")
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_n_plus_2")
        # tg ok, state ok, assigner_user nok, auc nok
        self.imail.assigned_user = None
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        self.assertTrue(adapted.can_do_transition("back_to_creation"))
        self.assertTrue(adapted.can_do_transition("back_to_manager"))
        # WE DO TRANSITION
        api.group.add_user(groupname=groupname1, username="chef")
        with api.env.adopt_roles(["Reviewer"]):
            api.content.transition(self.imail, "propose_to_n_plus_1")
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_n_plus_1")
        self.assertFalse(adapted.can_do_transition("propose_to_agent"))
        self.assertTrue(adapted.can_do_transition("back_to_n_plus_2"))
        self.assertFalse(adapted.can_do_transition("back_to_creation"))
        self.assertFalse(adapted.can_do_transition("back_to_manager"))
        # we remove n+2 users
        api.group.remove_user(groupname=groupname2, username="chef")
        self.assertFalse(adapted.can_do_transition("back_to_n_plus_2"))
        self.assertTrue(adapted.can_do_transition("back_to_creation"))
        self.assertTrue(adapted.can_do_transition("back_to_manager"))
        # WE DO TRANSITION
        self.imail.assigned_user = "chef"
        with api.env.adopt_roles(["Reviewer"]):
            api.content.transition(self.imail, "propose_to_agent")
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_agent")
        self.assertTrue(adapted.can_do_transition("back_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("back_to_n_plus_2"))
        self.assertFalse(adapted.can_do_transition("back_to_creation"))
        self.assertFalse(adapted.can_do_transition("back_to_manager"))
        # we remove n+1 users
        api.group.remove_user(groupname=groupname1, username="chef")
        api.group.add_user(groupname=groupname2, username="chef")
        self.assertTrue(adapted.can_do_transition("back_to_n_plus_2"))
        self.assertFalse(adapted.can_do_transition("back_to_n_plus_1"))
        self.assertFalse(adapted.can_do_transition("back_to_creation"))
        self.assertFalse(adapted.can_do_transition("back_to_manager"))

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond2(self):
        folder = self.portal["incoming-mail"]["mail-searches"]
        col1 = folder["searchfor_proposed_to_n_plus_1"]
        n_plus_1_view = IdmUtilsMethods(col1, col1.REQUEST)
        col2 = folder["searchfor_proposed_to_n_plus_2"]
        n_plus_2_view = IdmUtilsMethods(col2, col2.REQUEST)
        self.assertFalse(n_plus_2_view.proposed_to_n_plus_col_cond())
        self.change_user("encodeur")
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        self.change_user("agent")
        self.assertFalse(n_plus_2_view.proposed_to_n_plus_col_cond())
        api.group.add_user(groupname="abc_group_encoder", username="agent")
        self.change_user("agent")  # refresh getGroups
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        api.group.remove_user(groupname="abc_group_encoder", username="agent")
        self.change_user("dirg")
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        self.change_user("chef")
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())
        # Set N+2 to user, have to get an organization UID first
        contacts = self.portal["contacts"]
        own_orga = contacts["plonegroup-organization"]
        departments = own_orga.listFolderContents(contentFilter={"portal_type": "organization"})
        self.portal.acl_users.source_groups.addPrincipalToGroup("agent1", "%s_n_plus_2" % departments[5].UID())
        self.change_user("agent1")
        self.assertTrue(n_plus_1_view.proposed_to_n_plus_col_cond())  # can view lower level collection
        self.assertTrue(n_plus_2_view.proposed_to_n_plus_col_cond())

    def test_treating_groups_change_on_edit2(self):
        """Test only treating_groups change while the state is on a service validation level"""
        self.assertEqual(api.content.get_state(self.imail), "created")
        view = IdmUtilsMethods(self.imail, self.imail.REQUEST)
        adapted = self.imail.wf_conditions()
        edit_view = IMEdit(self.imail, self.imail.REQUEST)
        auv = AssignedUserValidator(self.imail, edit_view.request, edit_view, "fld", "widget")
        change_user(self.portal, "encodeur")
        org1, org2 = get_registry_organizations()[0:2]
        groupname1_1 = "{}_n_plus_1".format(org1)
        groupname1_2 = "{}_n_plus_2".format(org1)
        groupname2_1 = "{}_n_plus_1".format(org2)
        groupname2_2 = "{}_n_plus_2".format(org2)
        # N+2 has no user but n+1 has users
        self.assertTrue(group_has_user(groupname2_1))
        self.assertTrue(group_has_user(groupname2_2))
        api.group.remove_user(groupname=groupname1_2, username="chef")
        self.assertFalse(group_has_user(groupname1_2))  # no user
        self.assertTrue(group_has_user(groupname1_1))
        self.imail.treating_groups = org1
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_2"))  # no user
        self.imail.treating_groups = org2
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_2"))
        api.content.transition(self.imail, "propose_to_n_plus_2")
        # we check assigned_user requirement
        edit_view.request.form["form.widgets.treating_groups"] = [org1]
        self.assertEqual(api.portal.get_registry_record(AUC_RECORD), "n_plus_1")
        self.assertIsNone(auv.validate(None))
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        self.assertIsNone(auv.validate(None))
        # notify modification
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        self.imail.treating_groups = org1
        zope.event.notify(ObjectModifiedEvent(self.imail, Attributes(Interface, "treating_groups")))
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_n_plus_1")
        # N+2 has no user and n+1 has no user
        api.group.remove_user(groupname=groupname1_1, username="chef")
        self.assertFalse(group_has_user(groupname1_1))  # no user
        self.assertFalse(group_has_user(groupname1_2))  # no user
        with api.env.adopt_roles(["Reviewer"]):
            api.content.transition(self.imail, "back_to_creation")
        self.assertEqual(api.content.get_state(self.imail), "created")
        self.assertFalse(adapted.can_do_transition("propose_to_n_plus_2"))  # no user
        self.imail.treating_groups = org2
        self.assertTrue(adapted.can_do_transition("propose_to_n_plus_2"))
        api.content.transition(self.imail, "propose_to_n_plus_2")
        # we check assigned_user requirement
        edit_view.request.form["form.widgets.treating_groups"] = [org1]
        self.assertEqual(api.portal.get_registry_record(AUC_RECORD), "n_plus_1")
        self.assertIsNone(auv.validate(None))
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        self.assertRaises(Invalid, auv.validate, None)
        # notify modification
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        self.imail.treating_groups = org1
        zope.event.notify(ObjectModifiedEvent(self.imail, Attributes(Interface, "treating_groups")))
        self.assertEqual(api.content.get_state(self.imail), "proposed_to_agent")
