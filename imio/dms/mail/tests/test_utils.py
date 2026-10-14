# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_organizations
from collective.labels.interfaces import ILabeling
from datetime import datetime
from datetime import timedelta
from imio.dms.mail import _tr
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.dmsmail import IMEdit
from imio.dms.mail.dmsmail import IMView
from imio.dms.mail.dmsmail import OMEdit
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import add_remove_values_in_registry_list
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import create_period_folder
from imio.dms.mail.utils import create_period_folder_max
from imio.dms.mail.utils import create_personnel_content
from imio.dms.mail.utils import create_read_label_cron_task
from imio.dms.mail.utils import current_user_groups_ids
from imio.dms.mail.utils import do_next_transition
from imio.dms.mail.utils import Dummy
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import ensure_set_field
from imio.dms.mail.utils import get_allowed_content_types
from imio.dms.mail.utils import get_context_with_request
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import invalidate_users_groups
from imio.dms.mail.utils import is_hp_used_in_signer_rules
from imio.dms.mail.utils import is_n_plus_level_obsolete
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import sub_create
from imio.dms.mail.utils import update_solr_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.dms.mail.utils import UtilsMethods
from imio.dms.mail.utils import VariousUtilsMethods
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_object
from imio.helpers.test_helpers import ImioTestHelpers
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from plone.base.utils import base_hasattr
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry import field as reg_field
from plone.registry import Record
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import safe_unicode
from six import StringIO
from unittest.mock import patch
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility

import os
import unittest


class TestUtils(unittest.TestCase, ImioTestHelpers):
    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        api.group.create("abc_group_encoder", "ABC group encoder")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.catalog = self.portal.portal_catalog
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.contacts = self.portal["contacts"]

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_dms_config(self):
        annot = IAnnotations(self.portal)
        set_dms_config(["a"], value="dict")
        lst = set_dms_config(["a", "b"], value="list")
        self.assertTrue(isinstance(annot["imio.dms.mail"], PersistentDict))
        self.assertTrue(isinstance(annot["imio.dms.mail"]["a"], PersistentDict))
        self.assertTrue(isinstance(annot["imio.dms.mail"]["a"]["b"], PersistentList))
        lst.append(1)
        self.assertEqual(get_dms_config(["a", "b"]), [1])
        set_dms_config(["a", "b"], value="plone")
        self.assertTrue(isinstance(annot["imio.dms.mail"]["a"]["b"], str))
        self.assertEqual(get_dms_config(["a", "b"]), "plone")
        # force
        lst = set_dms_config(["a", "b"], value="other", force=False)
        self.assertEqual(get_dms_config(["a", "b"]), "plone")  # not changed
        lst = set_dms_config(["a", "b"], value="other")
        self.assertEqual(get_dms_config(["a", "b"]), "other")  # changed
        # missing
        self.assertRaises(KeyError, get_dms_config, ["c"])
        self.assertIsNone(get_dms_config(["c"], missing_key_handling=True))
        self.assertDictEqual(get_dms_config(["c"], missing_key_handling=True, missing_key_value={}), {})

    def test_add_remove_values_in_registry_list(self):
        """add_remove_values_in_registry_list adds/removes/reorders values idempotently"""
        key = "imio.dms.mail.displayed_tabs"
        api.portal.set_registry_record(key, ["incoming-mail", "outgoing-mail"])
        # add a new value
        self.assertTrue(add_remove_values_in_registry_list(key, to_add=("requests",)))
        self.assertIn("requests", api.portal.get_registry_record(key))
        # adding an already present value does nothing
        self.assertFalse(add_remove_values_in_registry_list(key, to_add=("requests",)))
        # remove a value
        self.assertTrue(add_remove_values_in_registry_list(key, to_remove=("outgoing-mail",)))
        self.assertNotIn("outgoing-mail", api.portal.get_registry_record(key))
        # removing an absent value does nothing
        self.assertFalse(add_remove_values_in_registry_list(key, to_remove=("outgoing-mail",)))
        # order reorders known values first, unknown keep relative order
        self.assertTrue(add_remove_values_in_registry_list(key, order=["requests", "incoming-mail"]))
        self.assertEqual(api.portal.get_registry_record(key), ["requests", "incoming-mail"])
        # order already respected does nothing
        self.assertFalse(add_remove_values_in_registry_list(key, order=["requests", "incoming-mail"]))
        # add + order in one call
        self.assertTrue(add_remove_values_in_registry_list(key, to_add=("tasks",), order=["tasks", "requests"]))
        self.assertEqual(api.portal.get_registry_record(key), ["tasks", "requests", "incoming-mail"])

    def test_list_wf_states_sign_request(self):
        states = [state for state, title in list_wf_states(self.portal, "sign_request")]
        self.assertEqual(states, ["created", "to_approve", "to_be_signed", "signed", "closed"])

    def test_get_allowed_content_types_sign_request(self):
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.request_esign_formats", ["odt", "pdf"]
        )
        self.assertEqual(
            get_allowed_content_types(portal_type="sign_request"),
            ["application/vnd.oasis.opendocument.text", "application/pdf"],
        )

    def test_ensure_set_field(self):
        now1 = datetime.now()
        imail = sub_create(self.imf, "dmsincomingmail", now1, "my-id")
        # reception_date is not set and this attribute doesn't exist on object
        self.assertNotIn("reception_date", imail.__dict__)
        # but the following give a wrong information
        self.assertTrue(hasattr(imail, "reception_date"))
        self.assertTrue(base_hasattr(imail, "reception_date"))
        self.assertEqual(imail.reception_date, None)
        self.assertEqual(getattr(imail, "reception_date", "Missing"), None)
        # we set really the attribute
        self.assertTrue(ensure_set_field(imail, "reception_date"))
        self.assertIn("reception_date", imail.__dict__)
        self.assertEqual(imail.reception_date, None)  # None is set by default
        # we try to set again but it's not set because a value is already set
        self.assertFalse(ensure_set_field(imail, "reception_date", now1))
        self.assertEqual(imail.reception_date, None)
        # we set with another option
        self.assertTrue(ensure_set_field(imail, "reception_date", now1, replace_none=True))
        self.assertEqual(imail.reception_date, now1)
        # we cannot set anymore
        now2 = datetime.now()
        self.assertFalse(ensure_set_field(imail, "reception_date", now2, replace_none=True))
        self.assertEqual(imail.reception_date, now1)
        # delete the attr
        delattr(imail, "reception_date")
        self.assertTrue(ensure_set_field(imail, "reception_date", now2))
        self.assertEqual(imail.reception_date, now2)

    def test_group_has_user(self):
        self.assertFalse(group_has_user("xxx", "delete"))
        self.assertFalse(group_has_user("xxx"))  # group not found
        self.assertFalse(group_has_user("abc_group_encoder"))  # no user
        self.assertTrue(group_has_user("abc_group_encoder", "add"))  # we are adding a user
        api.group.add_user(groupname="abc_group_encoder", username="chef")
        self.change_user("siteadmin")
        self.assertTrue(group_has_user("abc_group_encoder"))  # group has one user
        self.assertFalse(group_has_user("abc_group_encoder", "remove"))  # we are removing the only one user

    def test_update_transitions_levels_config(self):
        # dmsincomingmail #
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"created", "proposed_to_manager", "proposed_to_agent", "closed"})
        self.assertEqual(config["created"], config["proposed_to_manager"])
        self.assertEqual(config["created"], config["proposed_to_agent"])
        self.assertEqual(config["created"], config["closed"])
        for state in config:
            for org in config[state]:
                self.assertEqual(config[state][org], ("propose_to_agent", "from_states", None), state)
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create("{}_n_plus_1".format(org1), "N+1")
        set_dms_config(
            ["wf_from_to", "dmsincomingmail", "n_plus", "to"],
            [
                ("closed", "close"),
                ("proposed_to_agent", "propose_to_agent"),
                ("proposed_to_n_plus_1", "propose_to_n_plus_1"),
            ],
        )
        update_transitions_levels_config(["dmsincomingmail"])
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertEqual(config["proposed_to_n_plus_1"][org1], ("propose_to_agent", "from_states", False))
        self.assertEqual(config["proposed_to_manager"][org1], ("propose_to_agent", "from_states", None))
        self.assertEqual(config["proposed_to_manager"][org2], ("propose_to_agent", "from_states", None))
        self.assertEqual(config["proposed_to_agent"][org1], ("propose_to_agent", "from_states", None))
        self.assertEqual(config["closed"][org1], ("propose_to_agent", "from_states", None))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(["dmsincomingmail"], "add", "{}_n_plus_1".format(org1))
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertEqual(config["proposed_to_n_plus_1"][org1], ("propose_to_agent", "from_states", True))
        self.assertEqual(config["proposed_to_manager"][org1], ("propose_to_n_plus_1", "from_states", None))
        self.assertEqual(config["proposed_to_manager"][org2], ("propose_to_agent", "from_states", None))
        self.assertEqual(config["proposed_to_agent"][org1], ("propose_to_agent", "back_to_n_plus_1", None))
        self.assertEqual(config["proposed_to_agent"][org2], ("propose_to_agent", "from_states", None))

        # dmsoutgoingmail #
        config = get_dms_config(["transitions_levels", "dmsoutgoingmail"])
        self.assertSetEqual(set(config.keys()), {"created", "to_be_signed", "sent"})
        self.assertEqual(config["created"], config["to_be_signed"])
        for state in config:
            for org in config[state]:
                self.assertEqual(config[state][org], ("", "", None))
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create("{}_n_plus_1".format(org1), "N+1")
        set_dms_config(
            ["wf_from_to", "dmsoutgoingmail", "n_plus", "to"],
            [("sent", "mark_as_sent"), ("to_be_signed", "propose_to_be_signed"), ("validated", "set_validated")],
        )
        update_transitions_levels_config(["dmsoutgoingmail"])
        config = get_dms_config(["transitions_levels", "dmsoutgoingmail"])
        self.assertEqual(config["created"][org1], ("", "", None))
        self.assertEqual(config["to_be_signed"][org1], ("", "", None))
        self.assertEqual(config["created"][org2], ("", "", None))
        self.assertEqual(config["to_be_signed"][org2], ("", "", None))
        self.assertEqual(config["proposed_to_n_plus_1"][org1], ("set_validated", "", False))
        self.assertEqual(config["proposed_to_n_plus_1"][org2], ("set_validated", "", False))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(["dmsoutgoingmail"], "add", "{}_n_plus_1".format(org1))
        config = get_dms_config(["transitions_levels", "dmsoutgoingmail"])
        self.assertEqual(config["created"][org1], ("propose_to_n_plus_1", "", None))
        self.assertEqual(config["to_be_signed"][org1], ("", "back_to_n_plus_1", None))
        self.assertEqual(config["created"][org2], ("", "", None))
        self.assertEqual(config["to_be_signed"][org2], ("", "", None))
        self.assertEqual(config["proposed_to_n_plus_1"][org1], ("set_validated", "", True))
        self.assertEqual(config["proposed_to_n_plus_1"][org2], ("set_validated", "", False))

        # task #
        config = get_dms_config(["transitions_levels", "task"])
        for org in config["created"]:
            self.assertEqual(config["created"][org], ("", ""))
        for org in config["to_do"]:
            self.assertEqual(config["to_do"][org], ("", "back_in_created2"))
        org1, org2 = get_registry_organizations()[0:2]
        # we simulate the adding of a level without user
        api.group.create("{}_n_plus_1".format(org1), "N+1")
        update_transitions_levels_config(["task"])
        config = get_dms_config(["transitions_levels", "task"])
        self.assertEqual(config["to_do"][org1], ("", "back_in_created2"))
        self.assertEqual(config["to_do"][org2], ("", "back_in_created2"))
        # we simulate the adding of a level and a user
        update_transitions_levels_config(["task"], "add", "{}_n_plus_1".format(org1))
        config = get_dms_config(["transitions_levels", "task"])
        self.assertEqual(config["created"][org1], ("do_to_assign", ""))
        self.assertEqual(config["to_do"][org1], ("", "back_in_to_assign"))
        self.assertEqual(config["created"][org2], ("", ""))
        self.assertEqual(config["to_do"][org2], ("", "back_in_created2"))

    def test_update_transitions_auc_config(self):
        api.portal.set_registry_record(AUC_RECORD, "no_check")
        # no check
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"close", "propose_to_agent"})
        self.assertTrue(all(config["propose_to_agent"].values()))  # can always do transition
        self.assertTrue(all(config["close"].values()))  # can always do transition
        # n_plus_1
        api.portal.set_registry_record(AUC_RECORD, "n_plus_1")
        # only one transition
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"close", "propose_to_agent"})
        self.assertTrue(all(config["propose_to_agent"].values()))
        self.assertTrue(all(config["close"].values()))
        # we simulate the adding of a level without user
        org1, org2 = get_registry_organizations()[0:2]
        api.group.create("{}_n_plus_1".format(org1), "N+1")
        set_dms_config(
            ["wf_from_to", "dmsincomingmail", "n_plus", "to"],
            [
                ("closed", "close"),
                ("proposed_to_agent", "propose_to_agent"),
                ("proposed_to_n_plus_1", "propose_to_n_plus_1"),
            ],
        )
        update_transitions_auc_config("dmsincomingmail")
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"close", "propose_to_n_plus_1", "propose_to_agent"})
        self.assertTrue(all(config["propose_to_n_plus_1"].values()))
        self.assertTrue(all(config["propose_to_agent"].values()))
        self.assertTrue(all(config["close"].values()))
        # we simulate the adding of a level and a user
        update_transitions_auc_config("dmsincomingmail", "add", "{}_n_plus_1".format(org1))
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertTrue(config["propose_to_n_plus_1"][org1])
        self.assertFalse(config["propose_to_agent"][org1])  # cannot do transition because user
        self.assertTrue(config["propose_to_agent"][org2])
        # mandatory
        # reset config
        set_dms_config(["transitions_auc", "dmsincomingmail"], value="dict")
        set_dms_config(
            ["wf_from_to", "dmsincomingmail", "n_plus", "to"],
            [("closed", "close"), ("proposed_to_agent", "propose_to_agent")],
        )
        api.portal.set_registry_record(AUC_RECORD, "mandatory")
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertFalse(any(config["propose_to_agent"].values()))  # all is False
        self.assertTrue(all(config["close"].values()))
        # we simulate the adding of a level without user
        set_dms_config(
            ["wf_from_to", "dmsincomingmail", "n_plus", "to"],
            [
                ("closed", "close"),
                ("proposed_to_agent", "propose_to_agent"),
                ("proposed_to_n_plus_1", "propose_to_n_plus_1"),
            ],
        )
        update_transitions_auc_config("dmsincomingmail")
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"close", "propose_to_n_plus_1", "propose_to_agent"})
        self.assertFalse(any(config["propose_to_n_plus_1"].values()))  # all is False
        self.assertFalse(any(config["propose_to_agent"].values()))  # all is False
        self.assertTrue(all(config["close"].values()))
        # we simulate the adding of a level and a user
        update_transitions_auc_config("dmsincomingmail", "add", "{}_n_plus_1".format(org1))
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertTrue(config["propose_to_n_plus_1"][org1])  # can do transition because user
        self.assertFalse(config["propose_to_n_plus_1"][org2])
        self.assertFalse(config["propose_to_agent"][org1])
        self.assertFalse(config["propose_to_agent"][org2])

    def test_highest_review_level(self):
        self.assertIsNone(highest_review_level("a_type", ""))
        self.assertIsNone(highest_review_level("dmsincomingmail", ""))
        self.assertEqual(highest_review_level("dmsincomingmail", "['dir_general']"), "dir_general")
        set_dms_config(
            ["review_levels", "dmsincomingmail"],
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"}),
                ]
            ),
        )
        self.assertEqual(highest_review_level("dmsincomingmail", "['111_n_plus_1']"), "_n_plus_1")

    def test_list_wf_states(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        self.assertEqual(list_wf_states(imail, "unknown"), [])
        self.assertEqual(
            [s_id for s_id, s_tit in list_wf_states(imail, "task")],
            ["created", "to_assign", "to_do", "in_progress", "realized", "closed"],
        )
        # We rename a state id
        states = imail.portal_workflow.task_workflow.states
        states.manage_renameObject("to_do", "NEW")
        # use cache
        self.assertEqual(
            [s_id for s_id, s_tit in list_wf_states(imail, "task")],
            ["created", "to_assign", "to_do", "in_progress", "realized", "closed"],
        )
        invalidate_cachekey_volatile_for("imio.dms.mail.utils.list_wf_states.task")
        # 'imio.dms.mail.utils.list_wf_states
        self.assertEqual(
            [s_id for s_id, s_tit in list_wf_states(imail, "task")],
            ["created", "to_assign", "in_progress", "realized", "closed", "NEW"],
        )

    def test_back_or_again_state(self):
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "test",
            **{
                "assigned_user": "agent",
                "title": "test",
                "treating_groups": self.pgof["direction-generale"]["secretariat"].UID(),
            }
        )
        self.assertEqual(back_or_again_state(imail), "")  # initial state: no action
        api.content.transition(obj=imail, transition="propose_to_manager")
        self.assertEqual(back_or_again_state(imail), "")  # second state: empty
        api.content.transition(obj=imail, transition="propose_to_agent")
        self.assertEqual(back_or_again_state(imail), "")  # third state: empty
        api.content.transition(obj=imail, transition="back_to_manager")
        self.assertEqual(back_or_again_state(imail), "back")  # we have a back action starting with back_
        api.content.transition(obj=imail, transition="back_to_creation")
        self.assertEqual(back_or_again_state(imail), "back")  # we have a back action starting with back_
        self.assertEqual(
            back_or_again_state(imail, transitions=["back_to_creation"]), "back"
        )  # we have a back action found in transitions parameter
        api.content.transition(obj=imail, transition="propose_to_agent")
        self.assertEqual(back_or_again_state(imail), "again")  # third state again

    def test_get_scan_id(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        obj = createContentInContainer(imail, "dmsmainfile", id="testid1.pdf", scan_id="010999900000690")
        self.assertListEqual(get_scan_id(obj), ["010999900000690", "IMIO010999900000690", "690"])

    def test_UtilsMethods_current_user_groups_ids(self):
        self.change_user("dirg")
        self.assertSetEqual(
            set(current_user_groups_ids(api.user.get_current())),
            {
                "AuthenticatedUsers",
                "audit_contacts",
                "createurs_dossier",
                "dir_general",
                "lecteurs_globaux_cs",
                "{}_lecteur".format(self.portal["contacts"]["plonegroup-organization"]["direction-generale"].UID()),
            },
        )

    def test_UtilsMethods_highest_scan_id(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.highest_scan_id(), "dmsmainfiles: '9', highest scan_id: '010999900000009'")

    def test_UtilsMethods_is_in_user_groups(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertListEqual(current_user_groups_ids(api.user.get_current()), ["Administrators", "AuthenticatedUsers"])
        # current user is Manager
        self.assertTrue(view.is_in_user_groups(groups=["abc"]))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], admin=False))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], admin=False, test="all"))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], admin=False, suffixes=["general"]))
        # current user is not Manager
        self.change_user("dirg")
        self.assertSetEqual(
            set(current_user_groups_ids(api.user.get_current())),
            {
                "AuthenticatedUsers",
                "audit_contacts",
                "createurs_dossier",
                "dir_general",
                "lecteurs_globaux_cs",
                "{}_lecteur".format(self.portal["contacts"]["plonegroup-organization"]["direction-generale"].UID()),
            },
        )
        # with groups
        self.assertFalse(view.is_in_user_groups(groups=["abc"]))
        self.assertTrue(view.is_in_user_groups(groups=["abc", "dir_general"]))
        self.assertFalse(view.is_in_user_groups(groups=["abc", "dir_general"], test="all"))
        self.assertTrue(view.is_in_user_groups(groups=["AuthenticatedUsers", "dir_general"], test="all"))
        self.assertFalse(view.is_in_user_groups(groups=["dir_general"], test="other"))
        # with suffixes
        self.assertTrue(view.is_in_user_groups(suffixes=["general"]))
        self.assertTrue(view.is_in_user_groups(groups=["abc"], suffixes=["general"]))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], suffixes=["general"], test="all"))
        self.assertTrue(view.is_in_user_groups(groups=["AuthenticatedUsers"], suffixes=["general"], test="all"))
        # with org_uid, but without suffixes: not considered
        self.assertFalse(view.is_in_user_groups(groups=["abc"], org_uid="dir"))
        self.assertTrue(view.is_in_user_groups(groups=["abc", "dir_general"], org_uid="dir"))
        self.assertFalse(view.is_in_user_groups(groups=["abc", "dir_general"], test="all", org_uid="dir"))
        self.assertFalse(view.is_in_user_groups(groups=["dir_general"], test="other", org_uid="dir"))
        # with org_uid and suffixes
        self.assertTrue(view.is_in_user_groups(suffixes=["general"], org_uid="dir"))
        self.assertFalse(view.is_in_user_groups(suffixes=["general"], org_uid="wrong"))
        self.assertTrue(view.is_in_user_groups(groups=["abc"], suffixes=["general"], org_uid="dir"))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], suffixes=["general"], org_uid="wrong"))
        self.assertTrue(view.is_in_user_groups(groups=["dir_general"], suffixes=["general"], org_uid="wrong"))
        self.assertFalse(view.is_in_user_groups(groups=["abc"], test="all", suffixes=["general"], org_uid="dir"))
        self.assertTrue(view.is_in_user_groups(groups=["dir_general"], test="all", suffixes=["general"], org_uid="dir"))
        self.change_user("agent")
        self.assertFalse(view.is_in_user_groups(suffixes=["general"], org_uid="dir"))
        self.assertTrue(view.is_in_user_groups(groups=["AuthenticatedUsers"], suffixes=["general"], org_uid="dir"))
        self.assertTrue(view.is_in_user_groups(suffixes=["general"], org_uid="dir", user=api.user.get("dirg")))

    def test_VariousMethods_cron_read_label_handling(self):
        obj = self.portal
        view = VariousUtilsMethods(obj, obj.REQUEST)
        view.cron_read_label_handling()  # ok without config
        ev_uid = self.contacts["plonegroup-organization"]["evenements"].UID()
        imail = sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id", recipient_groups=[ev_uid]
        )
        labeling = ILabeling(imail)
        self.assertNotIn("lu", labeling.storage)
        cron_tasks = set_dms_config(["read_label_cron", "agent"], PersistentDict())
        cron_tasks["end"] = datetime.now()
        cron_tasks["orgs"] = {ev_uid}
        view.cron_read_label_handling()
        self.assertIn("lu", labeling.storage)
        self.assertIn("agent", labeling.storage["lu"])
        reset_dms_config()

    def test_VariousMethods_is_unprotected(self):
        obj = self.portal["front-page"]
        view = VariousUtilsMethods(obj, obj.REQUEST)
        self.assertTrue(view.is_unprotected(), "obj {} is protected !!".format(obj))
        for obj in (
            self.portal["incoming-mail"],
            self.portal["incoming-mail"]["mail-searches"],
            self.portal["outgoing-mail"],
            self.portal["outgoing-mail"]["mail-searches"],
            self.portal["tasks"],
            self.portal["tasks"]["task-searches"],
            self.portal["contacts"],
            self.portal["contacts"]["orgs-searches"],
            self.portal["contacts"]["hps-searches"],
            self.portal["contacts"]["persons-searches"],
            self.portal["contacts"]["cls-searches"],
            self.portal["contacts"]["plonegroup-organization"],
            self.portal["contacts"]["personnel-folder"],
            self.portal["contacts"]["contact-lists-folder"],
            self.portal["contacts"]["contact-lists-folder"]["common"],
            self.portal["folders"],
            self.portal["folders"]["folder-searches"],
            self.portal["tree"],
            self.portal["templates"],
            self.portal["templates"]["om"],
            self.portal["templates"]["om"]["common"],
        ):
            view = VariousUtilsMethods(obj, obj.REQUEST)
            self.assertFalse(view.is_unprotected(), "obj {} is unprotected !!".format(obj))
        for brain in self.catalog(
            portal_type=[
                "DashboardCollection",
                "DashboardPODTemplate",
                "StyleTemplate",
                "SubTemplate",
                "MailingLoopTemplate",
                "ConfigurablePODTemplate",
            ]
        ):
            obj = brain.getObject()
            if obj.id == "main" and not obj.absolute_url_path().endswith("/om/main"):  # we pass copy made in setup
                continue
            view = VariousUtilsMethods(obj, obj.REQUEST)
            self.assertFalse(view.is_unprotected(), "obj {} is unprotected !!".format(obj.absolute_url_path()))

    def test_VariousMethods_pg_organizations(self):
        obj = self.portal
        view = VariousUtilsMethods(obj, obj.REQUEST)
        pgo_contacts = self.portal["contacts"]["plonegroup-organization"]

        # pg_orgs in dict
        pgo = view.pg_organizations(output="dict")
        self.assertEqual(
            pgo,
            [
                (pgo_contacts["direction-generale"].UID(), "Direction générale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction générale - Secrétariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction générale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction générale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financière", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financière - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financière - Comptabilité",
                    "a",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - Bâtiments", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["evenements"].UID(), "Événements", "a"),
                (pgo_contacts["college-communal"].UID(), "Collège communal", "a"),
            ],
        )

        # pg_orgs in csv
        pgo = view.pg_organizations()
        self.assertEqual(
            pgo,
            """{};Direction générale
{};Direction générale - Secrétariat
{};Direction générale - GRH
{};Direction générale - Communication
{};Direction financière
{};Direction financière - Budgets
{};Direction financière - Comptabilité
{};Direction technique
{};Direction technique - Bâtiments
{};Direction technique - Voiries
{};Événements
{};Collège communal""".format(
                pgo_contacts["direction-generale"].UID(),
                pgo_contacts["direction-generale"]["secretariat"].UID(),
                pgo_contacts["direction-generale"]["grh"].UID(),
                pgo_contacts["direction-generale"]["communication"].UID(),
                pgo_contacts["direction-financiere"].UID(),
                pgo_contacts["direction-financiere"]["budgets"].UID(),
                pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                pgo_contacts["direction-technique"].UID(),
                pgo_contacts["direction-technique"]["batiments"].UID(),
                pgo_contacts["direction-technique"]["voiries"].UID(),
                pgo_contacts["evenements"].UID(),
                pgo_contacts["college-communal"].UID(),
            ),
        )

        # pg_orgs in csv with status
        pgo = view.pg_organizations(with_status=True)
        self.assertEqual(
            pgo,
            """{};Direction générale;a
{};Direction générale - Secrétariat;a
{};Direction générale - GRH;a
{};Direction générale - Communication;a
{};Direction financière;a
{};Direction financière - Budgets;a
{};Direction financière - Comptabilité;a
{};Direction technique;a
{};Direction technique - Bâtiments;a
{};Direction technique - Voiries;a
{};Événements;a
{};Collège communal;a""".format(
                pgo_contacts["direction-generale"].UID(),
                pgo_contacts["direction-generale"]["secretariat"].UID(),
                pgo_contacts["direction-generale"]["grh"].UID(),
                pgo_contacts["direction-generale"]["communication"].UID(),
                pgo_contacts["direction-financiere"].UID(),
                pgo_contacts["direction-financiere"]["budgets"].UID(),
                pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                pgo_contacts["direction-technique"].UID(),
                pgo_contacts["direction-technique"]["batiments"].UID(),
                pgo_contacts["direction-technique"]["voiries"].UID(),
                pgo_contacts["evenements"].UID(),
                pgo_contacts["college-communal"].UID(),
            ),
        )

        # After activating one organisation
        from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY

        org_uids = api.portal.get_registry_record(ORGANIZATIONS_REGISTRY) or []
        org_uids.append(pgo_contacts["conseil-communal"].UID())
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, org_uids)
        pgo = view.pg_organizations(output="dict")
        self.assertEqual(
            pgo,
            [
                (pgo_contacts["direction-generale"].UID(), "Direction générale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction générale - Secrétariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction générale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction générale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financière", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financière - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financière - Comptabilité",
                    "a",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - Bâtiments", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["evenements"].UID(), "Événements", "a"),
                (pgo_contacts["college-communal"].UID(), "Collège communal", "a"),
                (pgo_contacts["conseil-communal"].UID(), "Conseil communal", "a"),
            ],
        )

        # With both activated and not activated organizations
        pgo = view.pg_organizations(output="dict", only_activated="0")
        self.assertEqual(
            pgo,
            [
                (pgo_contacts["direction-generale"].UID(), "Direction générale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction générale - Secrétariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction générale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["informatique"].UID(),
                    "Direction générale - Informatique",
                    "na",
                ),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction générale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financière", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financière - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financière - Comptabilité",
                    "a",
                ),
                (pgo_contacts["direction-financiere"]["taxes"].UID(), "Direction financière - Taxes", "na"),
                (
                    pgo_contacts["direction-financiere"]["marches-publics"].UID(),
                    "Direction financière - Marchés publics",
                    "na",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - Bâtiments", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["direction-technique"]["urbanisme"].UID(), "Direction technique - Urbanisme", "na"),
                (pgo_contacts["departement-population"].UID(), "Département population", "na"),
                (
                    pgo_contacts["departement-population"]["population"].UID(),
                    "Département population - Population",
                    "na",
                ),
                (
                    pgo_contacts["departement-population"]["etat-civil"].UID(),
                    "Département population - État-civil",
                    "na",
                ),
                (pgo_contacts["departement-culturel"].UID(), "Département culturel", "na"),
                (
                    pgo_contacts["departement-culturel"]["enseignement"].UID(),
                    "Département culturel - Enseignement",
                    "na",
                ),
                (
                    pgo_contacts["departement-culturel"]["culture-loisirs"].UID(),
                    "Département culturel - Culture-loisirs",
                    "na",
                ),
                (pgo_contacts["evenements"].UID(), "Événements", "a"),
                (pgo_contacts["college-communal"].UID(), "Collège communal", "a"),
                (pgo_contacts["conseil-communal"].UID(), "Conseil communal", "a"),
            ],
        )

    def test_IdmUtilsMethods_get_im_folder(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.get_im_folder(), self.portal["incoming-mail"])

    def test_IdmUtilsMethods_user_has_review_level(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.user_has_review_level())
        self.assertFalse(view.user_has_review_level("dmsincomingmail"))
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")  # refresh getGroups
        set_dms_config(
            ["review_levels", "dmsincomingmail"],
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"}),
                ]
            ),
        )
        invalidate_users_groups(portal=self.portal, user_id="siteadmin")
        self.assertTrue(view.user_has_review_level("dmsincomingmail"))
        api.group.remove_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")  # refresh getGroups
        self.assertFalse(view.user_has_review_level("dmsincomingmail"))
        api.group.add_user(groupname="dir_general", username="siteadmin")
        self.change_user("siteadmin")  # refresh getGroups
        self.assertTrue(view.user_has_review_level("dmsincomingmail"))

    def test_IdmUtilsMethods_created_col_cond(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.created_col_cond())
        self.change_user("encodeur")
        self.assertTrue(view.created_col_cond())
        self.change_user("agent")
        self.assertFalse(view.created_col_cond())
        api.group.add_user(groupname="abc_group_encoder", username="agent")
        self.change_user("agent")  # refresh getGroups
        self.assertTrue(view.created_col_cond())

    def test_IdmUtilsMethods_proposed_to_manager_col_cond(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_manager_col_cond())
        self.change_user("encodeur")
        self.assertTrue(view.proposed_to_manager_col_cond())
        self.change_user("agent")
        self.assertFalse(view.proposed_to_manager_col_cond())
        api.group.add_user(groupname="abc_group_encoder", username="agent")
        self.change_user("agent")  # refresh getGroups
        self.assertTrue(view.proposed_to_manager_col_cond())
        self.change_user("dirg")
        self.assertTrue(view.proposed_to_manager_col_cond())

    def test_IdmUtilsMethods_proposed_to_premanager_col_cond(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = IdmUtilsMethods(imail, imail.REQUEST)
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        self.change_user("encodeur")
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        self.change_user("agent")
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        api.group.add_user(groupname="abc_group_encoder", username="agent")
        self.change_user("agent")  # refresh getGroups
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        self.change_user("dirg")
        self.assertTrue(view.proposed_to_pre_manager_col_cond())
        self.change_user("agent1")
        self.assertFalse(view.proposed_to_pre_manager_col_cond())
        api.group.create("pre_manager", "Pre manager")
        api.group.add_user(groupname="pre_manager", username="agent1")
        self.change_user("agent1")  # refresh getGroups
        self.assertTrue(view.proposed_to_pre_manager_col_cond())

    def test_IdmUtilsMethods_proposed_to_n_plus_col_cond0(self):
        im_folder = self.portal["incoming-mail"]["mail-searches"]
        self.assertFalse("searchfor_proposed_to_n_plus_1" in im_folder)
        self.assertTrue("See test_wfadaptations_imservicevalidation.py")

    def test_create_period_folder(self):
        dte = datetime.now() - timedelta(days=7)
        foldername = dte.strftime("%Y%U")  # week
        self.assertNotIn(foldername, self.imf)
        folder = create_period_folder(self.imf, dte)
        self.assertIn(foldername, self.imf)
        folder.invokeFactory("dmsincomingmail", id="test-id")
        self.assertIn("test-id", folder)
        folder = create_period_folder(self.imf, dte, subfolder="fixed")
        self.assertIn("fixed", self.imf)

    def test_create_period_folder_max(self):
        dte = datetime.now()
        foldername = dte.strftime("%Y%U")  # week
        self.assertIn(foldername, self.imf)  # we already have example ims
        self.assertEqual(len(self.imf[foldername].objectIds()), 9)
        counter_dic = {}
        create_period_folder_max(self.imf, dte, counter_dic, max_nb=9)
        self.assertIn("{}-1".format(foldername), self.imf)
        for i in range(0, 9):
            create_period_folder_max(self.imf, dte, counter_dic, max_nb=9)
        self.assertIn("{}-2".format(foldername), self.imf)

    def test_create_personnel_content(self):
        pf = self.contacts["personnel-folder"]
        ev_uid = self.contacts["plonegroup-organization"]["evenements"].UID()
        self.portal.portal_registration.addMember(id="newuser", password="TestUser=6")
        self.assertNotIn("newuser", pf)
        # add newuser in ev editeur group
        api.group.add_user(groupname="{}_editeur".format(ev_uid), username="newuser")
        self.assertIn("newuser", pf)
        self.assertEqual(pf.newuser.userid, "newuser")
        self.assertIsNone(pf.newuser.primary_organization)
        self.assertListEqual(pf.newuser.objectIds(), [ev_uid])
        self.assertEqual(pf.newuser[ev_uid].get_organization().UID(), ev_uid)
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "deactivated")
        # add newuser in ev encodeur group
        api.group.add_user(groupname="{}_encodeur".format(ev_uid), username="newuser")
        self.assertListEqual(pf.newuser.objectIds(), [ev_uid])
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "active")
        # add newuser in sc editeur group
        sc_uid = self.contacts["plonegroup-organization"]["direction-generale"]["secretariat"].UID()
        api.group.add_user(groupname="{}_editeur".format(sc_uid), username="newuser")
        self.assertListEqual(pf.newuser.objectIds(), [ev_uid, sc_uid])
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "active")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "deactivated")
        # add newuser in sc encodeur group
        api.group.add_user(groupname="{}_encodeur".format(sc_uid), username="newuser")
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "active")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "active")
        # use primary arg but multiple hps => not set
        create_personnel_content("newuser", ["{}_editeur".format(sc_uid)], primary=True)
        self.assertListEqual(pf.newuser.objectIds(), [ev_uid, sc_uid])
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "active")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "active")
        self.assertIsNone(pf.newuser.primary_organization)
        # remove newuser from sc editeur group
        api.group.remove_user(groupname="{}_editeur".format(sc_uid), username="newuser")
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "active")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "active")
        # remove newuser from ev encodeur group
        api.group.remove_user(groupname="{}_encodeur".format(ev_uid), username="newuser")
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "deactivated")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "active")
        # remove newuser from sc encodeur group
        api.group.remove_user(groupname="{}_encodeur".format(sc_uid), username="newuser")
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "deactivated")
        self.assertEqual(api.content.get_state(pf.newuser[sc_uid]), "deactivated")
        # delete sc hp and use primary arg with one hp => set
        api.content.delete(obj=pf.newuser[sc_uid])
        create_personnel_content("newuser", ["{}_editeur".format(ev_uid)], primary=True)
        self.assertListEqual(pf.newuser.objectIds(), [ev_uid])
        self.assertEqual(api.content.get_state(pf.newuser[ev_uid]), "deactivated")
        self.assertEqual(pf.newuser.primary_organization, ev_uid)

    def test_create_read_cron_task(self):
        annot = IAnnotations(self.portal)
        self.assertNotIn("read_label_cron", annot["imio.dms.mail"])
        ev_uid = self.contacts["plonegroup-organization"]["evenements"].UID()
        end = datetime.now() - timedelta(days=5)
        create_read_label_cron_task("agent", [ev_uid], end, portal=self.portal)
        self.assertIn("read_label_cron", annot["imio.dms.mail"])
        self.assertIn("agent", annot["imio.dms.mail"]["read_label_cron"])
        self.assertEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["end"], end)
        self.assertSetEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["orgs"], {ev_uid})
        # add another org
        dg_uid = self.contacts["plonegroup-organization"]["direction-generale"].UID()
        end2 = end + timedelta(days=1)
        create_read_label_cron_task("agent", [dg_uid], end2, portal=self.portal)
        self.assertEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["end"], end)  # dont change
        self.assertSetEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["orgs"], {ev_uid, dg_uid})
        # add another user
        create_read_label_cron_task("agent1", [dg_uid], end2, portal=self.portal)
        self.assertEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["end"], end)  # dont change
        self.assertSetEqual(annot["imio.dms.mail"]["read_label_cron"]["agent"]["orgs"], {ev_uid, dg_uid})
        self.assertEqual(annot["imio.dms.mail"]["read_label_cron"]["agent1"]["end"], end2)
        self.assertSetEqual(annot["imio.dms.mail"]["read_label_cron"]["agent1"]["orgs"], {dg_uid})
        reset_dms_config()

    def test_update_solr_config(self):
        # Early return when collective.solr is not configured (registry records absent)
        self.assertEqual(api.portal.get_registry_record("collective.solr.host", default="not found"), "not found")
        update_solr_config()  # must not raise
        self.assertEqual(api.portal.get_registry_record("collective.solr.host", default="not found"), "not found")

        # Setup: create the registry records collective.solr would normally provide
        plone_registry = getUtility(IRegistry)
        solr_records = {
            "collective.solr.port": (reg_field.Int(title="port"), 8983),
            "collective.solr.host": (reg_field.TextLine(title="host"), "localhost"),
            "collective.solr.base": (reg_field.TextLine(title="base"), "/solr"),
            "collective.solr.solr_login": (reg_field.TextLine(title="login"), "login"),
            "collective.solr.solr_password": (reg_field.TextLine(title="password"), "pwd"),
            "collective.solr.https_connection": (reg_field.Bool(title="https"), False),
            "collective.solr.ignore_certificate_check": (reg_field.Bool(title="ignore cert"), True),
        }
        for key, (fld, value) in solr_records.items():
            rec = Record(fld)
            rec.value = value
            plone_registry.records[key] = rec

        os.environ["COLLECTIVE_SOLR_HOST"] = "newhost"
        os.environ["COLLECTIVE_SOLR_PORT"] = "9000"
        os.environ["COLLECTIVE_SOLR_HTTPS_CONNECTION"] = "true"
        os.environ["COLLECTIVE_SOLR_IGNORE_CERTIFICATE_CHECK"] = "false"
        update_solr_config()
        self.assertEqual(api.portal.get_registry_record("collective.solr.host"), "newhost")
        self.assertEqual(api.portal.get_registry_record("collective.solr.port"), 9000)
        self.assertEqual(api.portal.get_registry_record("collective.solr.https_connection"), True)
        self.assertEqual(api.portal.get_registry_record("collective.solr.ignore_certificate_check"), False)
        # Absent env vars → unchanged values
        self.assertEqual(api.portal.get_registry_record("collective.solr.base"), "/solr")
        self.assertEqual(api.portal.get_registry_record("collective.solr.solr_login"), "login")
        # os.environ is process-level state, not rolled back by the test layer
        for key in (
            "COLLECTIVE_SOLR_HOST",
            "COLLECTIVE_SOLR_PORT",
            "COLLECTIVE_SOLR_HTTPS_CONNECTION",
            "COLLECTIVE_SOLR_IGNORE_CERTIFICATE_CHECK",
        ):
            del os.environ[key]

    def test_is_hp_used_in_signer_rules(self):
        pf = self.contacts["personnel-folder"]
        bourgmestre_hp = pf["bourgmestre"]["bourgmestre"]
        dirg_hp = pf["dirg"]["directeur-general"]
        rk_rules = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        rk_subs = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_substitutes"
        base_rule = {
            "number": 1,
            "signer": bourgmestre_hp.UID(),
            "esign": True,
            "approvings": ["_empty_"],
            "editor": False,
            "treating_groups": [],
            "mail_types": [],
            "send_modes": [],
            "tal_condition": None,
        }

        # No rules, no substitutes: not referenced
        api.portal.set_registry_record(rk_rules, [])
        api.portal.set_registry_record(rk_subs, [])
        self.assertFalse(is_hp_used_in_signer_rules(bourgmestre_hp, []))

        # Signer in rules, remaining_usages=[]: referenced
        api.portal.set_registry_record(rk_rules, [base_rule])
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, []))
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, ["approving"]))

        # Signer in rules, remaining_usages=["signer"]: not a conflict
        self.assertFalse(is_hp_used_in_signer_rules(bourgmestre_hp, ["signer"]))

        # Signer in substitutes as absent_signer or substitute_signer: referenced
        api.portal.set_registry_record(rk_rules, [])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": None,
                    "valid_until": None,
                }
            ],
        )
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, []))
        self.assertTrue(is_hp_used_in_signer_rules(dirg_hp, []))
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, ["approving"]))
        self.assertTrue(is_hp_used_in_signer_rules(dirg_hp, ["approving"]))

        # Approver in rules (approvings stores person UIDs), remaining_usages=[]: referenced
        api.portal.set_registry_record(rk_subs, [])
        bourgmestre_person = pf["bourgmestre"]
        bourgmestre_hp.usages = ["approving"]
        bourgmestre_hp.reindexObject(idxs=["usages"])
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.SigningApprovingsVocabulary")
        approving_rule = dict(base_rule)
        approving_rule["signer"] = dirg_hp.UID()
        approving_rule["approvings"] = [bourgmestre_person.UID()]
        api.portal.set_registry_record(rk_rules, [approving_rule])
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, []))
        self.assertTrue(is_hp_used_in_signer_rules(bourgmestre_hp, ["signer"]))

        # Approver in rules, remaining_usages=["approving"]: not a conflict
        self.assertFalse(is_hp_used_in_signer_rules(bourgmestre_hp, ["approving"]))

    def test_VariousMethods_check_scan_id(self):
        view = VariousUtilsMethods(self.portal, self.portal.REQUEST)
        self.change_user("agent")
        self.assertIsNone(view.check_scan_id())
        self.change_user("siteadmin")
        imail = sub_create(
            self.imf, "dmsincomingmail", datetime.now(), "my-id", title="Scan", internal_reference_no="E9999"
        )
        createContentInContainer(imail, "dmsmainfile", id="scan", scan_id="010999900001000")
        bad = sub_create(self.imf, "dmsincomingmail", datetime.now(), "bad-id", title="Bad scan")
        createContentInContainer(bad, "dmsmainfile", id="bad", scan_id="010999900AB")
        # one scan id by 1000, by flow
        out = view.check_scan_id()
        self.assertIn("<h1>Courrier entrant</h1>", out)
        self.assertIn('<a href="{}" target="_blank">1000</a>, E9999'.format(imail.absolute_url()), out)
        self.assertIn("Invalid scan_id '010999900AB' for item {}".format(bad["bad"].absolute_url()), out)
        # sorted by internal reference
        out = view.check_scan_id(sort="ref")
        self.assertIn('<a href="{}" target="_blank">E9999</a>, 1000'.format(imail.absolute_url()), out)

    def test_VariousMethods_kofax_orgs(self):
        view = VariousUtilsMethods(self.portal, self.portal.REQUEST)
        self.change_user("agent")
        self.assertIsNone(view.kofax_orgs())
        self.change_user("siteadmin")
        lines = safe_unicode(view.kofax_orgs()).split("\r\n")
        self.assertEqual(lines[0], _tr("Creating groups : to be used in kofax index"))
        self.assertIn(_tr("Treating groups : to be used in kofax index"), lines)
        dg_uid = self.pgof["direction-generale"].UID()
        self.assertIn("Direction générale ___ {}".format(dg_uid), lines)

    def test_VariousMethods_template_infos(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        # a file not generated from a template
        annex = createContentInContainer(omail, "dmsappendixfile", file=NamedBlobFile("pdf", filename="a.pdf"))
        self.assertEqual(VariousUtilsMethods(annex, annex.REQUEST).template_infos(), "No template infos")
        # a document generated from a template
        main = self.portal["templates"]["om"]["main"]
        gen_view = omail.restrictedTraverse("persistent-document-generation")
        gen_view.pod_template = main
        gen_view.output_format = "odt"
        doc = gen_view.generate_persistent_doc(main, "odt")
        out = VariousUtilsMethods(doc, doc.REQUEST).template_infos()
        self.assertTrue(out.startswith("<p>Template: "))
        self.assertIn(main.absolute_url(), out)
        for name in sorted(main.get_templates_to_merge()):
            self.assertIn("<li>{} = ".format(name), out)

    def test_VariousMethods_user_usages(self):
        view = VariousUtilsMethods(self.portal, self.portal.REQUEST)
        self.assertEqual(view.user_usages("chef"), "You must be a zope manager to run this script")
        self.change_user("admin")
        self.assertEqual(view.user_usages(), "You must give a parameter named 'userid'")
        self.assertEqual(view.user_usages("unknown"), "Cannot find a user with userid='unknown'")
        # the report is also printed: stdout is captured (non-ASCII titles break on an ASCII stdout)
        with patch("sys.stdout", StringIO()):
            out = view.user_usages("chef")
        self.assertIn("<h1>Usages of user name 'chef'</h1>", out)
        self.assertIn("Email='chef@macommune.be'", out)
        self.assertIn("<p>=> Found a person ", out)
        # chef is the sender of 3 outgoing mails as "responsable-grh"
        hp = self.contacts["personnel-folder"]["chef"]["responsable-grh"]
        om_url = "{}/outgoing-mail/mail-searches#c1={}&c7={}".format(
            self.portal.absolute_url(), self.omf["mail-searches"]["all_mails"].UID(), hp.UID()
        )
        self.assertIn('<a href="{}" target="_blank">3</a> om sender.'.format(om_url), out)

    def test_manage_fields(self):
        rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields"
        imail = sub_create(self.imf, "dmsincomingmail", datetime.now(), "my-id", title="Test")
        # sender first, mail_type not editable, description not displayed, external reference removed
        config = []
        for dic in api.portal.get_registry_record(rk):
            if dic["field_name"] == "external_reference_no":
                continue
            dic = dict(dic)
            if dic["field_name"] == "mail_type":
                dic["write_tal_condition"] = "python:False"
            elif dic["field_name"] == "IDublinCore.description":
                dic["read_tal_condition"] = "python:False"
            if dic["field_name"] == "sender":
                config.insert(0, dic)
            else:
                config.append(dic)
        api.portal.set_registry_record(rk, config)

        def form_fields(form):
            return list(form.fields.keys()) + [name for group in form.groups for name in group.fields.keys()]

        edit = IMEdit(imail, imail.REQUEST)
        edit.update()
        self.assertEqual(list(edit.fields.keys())[0], "sender")
        self.assertNotIn("mail_type", form_fields(edit))
        self.assertIn("IDublinCore.description", form_fields(edit))
        self.assertNotIn("external_reference_no", form_fields(edit))
        view = IMView(imail, imail.REQUEST)
        view.update()
        self.assertIn("mail_type", form_fields(view))
        self.assertNotIn("IDublinCore.description", form_fields(view))
        self.assertNotIn("external_reference_no", form_fields(view))
        # the signing fieldset is shown only when a signing field is configured
        omail = sub_create(
            self.omf,
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="Test",
            treating_groups=get_registry_organizations()[0],
        )
        edit = OMEdit(omail, omail.REQUEST)
        edit.update()
        self.assertNotIn("signing", [group.__name__ for group in edit.groups])
        rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields"
        config = api.portal.get_registry_record(rk)
        config.append({"field_name": "ISigningBehavior.signers", "read_tal_condition": "", "write_tal_condition": ""})
        api.portal.set_registry_record(rk, config)
        edit = OMEdit(omail, omail.REQUEST)
        edit.update()
        signing = [group for group in edit.groups if group.__name__ == "signing"]
        self.assertEqual(list(signing[0].fields.keys()), ["ISigningBehavior.signers"])

    def _im_in_n_plus_1(self):
        """Return an incoming mail proposed to the n+1 level of its treating group."""
        imail = sub_create(
            self.imf,
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            title="Test",
            treating_groups=get_registry_organizations()[0],
        )
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )
        api.portal.set_registry_record(AUC_RECORD, "no_check")
        api.content.transition(imail, "propose_to_n_plus_1")
        return imail

    def test_is_n_plus_level_obsolete(self):
        imail = sub_create(self.imf, "dmsincomingmail", datetime.now(), "my-id2", title="Test")
        # no treating group
        self.assertEqual(is_n_plus_level_obsolete(imail, "dmsincomingmail"), (False, None, None))
        # not in a validation state
        imail.treating_groups = get_registry_organizations()[0]
        self.assertEqual(is_n_plus_level_obsolete(imail, "dmsincomingmail"), (False, "created", None))
        # in the n+1 validation state, with a n+1 user
        imail = self._im_in_n_plus_1()
        obsolete, state, config = is_n_plus_level_obsolete(imail, "dmsincomingmail")
        self.assertFalse(obsolete)
        self.assertEqual(state, "proposed_to_n_plus_1")
        self.assertEqual(config, get_dms_config(["transitions_levels", "dmsincomingmail"]))
        # the validation state checked is not the current one
        self.assertFalse(is_n_plus_level_obsolete(imail, "dmsincomingmail", state_start="proposed_to_manager")[0])
        # no more n+1 user in the treating group: the level is obsolete
        api.group.remove_user(groupname="{}_n_plus_1".format(imail.treating_groups), username="chef")
        self.assertTrue(is_n_plus_level_obsolete(imail, "dmsincomingmail")[0])

    def test_do_next_transition(self):
        imail = self._im_in_n_plus_1()
        # the n+1 level has no more user: the mail goes to the next level
        api.group.remove_user(groupname="{}_n_plus_1".format(imail.treating_groups), username="chef")
        do_next_transition(imail, "dmsincomingmail")
        self.assertEqual(api.content.get_state(imail), "proposed_to_agent")

    def test_get_context_with_request(self):
        col = self.imf["mail-searches"]["all_mails"]
        request = self.portal.REQUEST
        # a context with a request is kept
        self.assertEqual(get_context_with_request(col).UID(), col.UID())
        # no request (the registry when editing a collection): the published view context is used
        request.set("PUBLISHED", DummyView(col, request))
        self.assertEqual(get_context_with_request(Dummy()).UID(), col.UID())
        # no published view: the collection is found from the referer
        request.set("PUBLISHED", None)
        request.set("HTTP_REFERER", "{}/edit".format(col.absolute_url()))
        self.assertEqual(get_context_with_request(Dummy()).UID(), col.UID())
        # the referer is not a collection
        request.set("HTTP_REFERER", self.imf.absolute_url())
        self.assertIsNone(get_context_with_request(Dummy()))
        # the referer is not found
        request.set("HTTP_REFERER", "{}/unknown/edit".format(self.portal.absolute_url()))
        self.assertIsNone(get_context_with_request(Dummy()))
