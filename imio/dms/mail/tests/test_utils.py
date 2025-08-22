# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_organizations
from collective.documentviewer.convert import Converter
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from ftw.labels.interfaces import ILabeling
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import create_period_folder
from imio.dms.mail.utils import create_period_folder_max
from imio.dms.mail.utils import create_personnel_content
from imio.dms.mail.utils import create_read_label_cron_task
from imio.dms.mail.utils import current_user_groups_ids
from imio.dms.mail.utils import dv_clean
from imio.dms.mail.utils import eml_preview
from imio.dms.mail.utils import ensure_set_field
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import group_has_user
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import IdmUtilsMethods
from imio.dms.mail.utils import invalidate_users_groups
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import OdmUtilsMethods
from imio.dms.mail.utils import PREVIEW_DIR
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import sub_create
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.dms.mail.utils import UtilsMethods
from imio.dms.mail.utils import VariousUtilsMethods
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.test_helpers import ImioTestHelpers
from mock import Mock
from mock import patch
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import base_hasattr
from z3c.relationfield.relation import RelationValue
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

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
        api.portal.set_registry_record(AUC_RECORD, u"no_check")
        # no check
        config = get_dms_config(["transitions_auc", "dmsincomingmail"])
        self.assertSetEqual(set(config.keys()), {"close", "propose_to_agent"})
        self.assertTrue(all(config["propose_to_agent"].values()))  # can always do transition
        self.assertTrue(all(config["close"].values()))  # can always do transition
        # n_plus_1
        api.portal.set_registry_record(AUC_RECORD, u"n_plus_1")
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
        self.assertEquals(highest_review_level("dmsincomingmail", "['dir_general']"), "dir_general")
        set_dms_config(
            ["review_levels", "dmsincomingmail"],
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"}),
                ]
            ),
        )
        self.assertEquals(highest_review_level("dmsincomingmail", "['111_n_plus_1']"), "_n_plus_1")

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
                "assigned_user": u"agent",
                "title": u"test",
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
        obj = createContentInContainer(imail, "dmsmainfile", id="testid1.pdf", scan_id=u"010999900000690")
        self.assertListEqual(get_scan_id(obj), [u"010999900000690", u"IMIO010999900000690", u"690"])

    def test_UtilsMethods_current_user_groups_ids(self):
        self.change_user("dirg")
        self.assertSetEqual(
            set(current_user_groups_ids(api.user.get_current())),
            {"AuthenticatedUsers", "audit_contacts", "createurs_dossier", "dir_general"},
        )

    def test_UtilsMethods_highest_scan_id(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        view = UtilsMethods(imail, imail.REQUEST)
        self.assertEqual(view.highest_scan_id(), "dmsmainfiles: '9', highest scan_id: '050999900000009'")

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
            {"AuthenticatedUsers", "audit_contacts", "createurs_dossier", "dir_general"},
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
            self.portal["templates"]["oem"],
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
                (pgo_contacts["direction-generale"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Secr\xc3\xa9tariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financi\xc3\xa8re", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financi\xc3\xa8re - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financi\xc3\xa8re - Comptabilit\xc3\xa9",
                    "a",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - B\xc3\xa2timents", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["evenements"].UID(), "\xc3\x89v\xc3\xa9nements", "a"),
            ],
        )

        # pg_orgs in csv
        pgo = view.pg_organizations()
        self.assertEqual(
            pgo,
            """{};Direction générale
{};Direction g\xc3\xa9n\xc3\xa9rale - Secr\xc3\xa9tariat
{};Direction g\xc3\xa9n\xc3\xa9rale - GRH
{};Direction g\xc3\xa9n\xc3\xa9rale - Communication
{};Direction financi\xc3\xa8re
{};Direction financi\xc3\xa8re - Budgets
{};Direction financi\xc3\xa8re - Comptabilit\xc3\xa9
{};Direction technique
{};Direction technique - B\xc3\xa2timents
{};Direction technique - Voiries
{};\xc3\x89v\xc3\xa9nements""".format(
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
            ),
        )

        # pg_orgs in csv with status
        pgo = view.pg_organizations(with_status=True)
        self.assertEqual(
            pgo,
            """{};Direction générale;a
{};Direction g\xc3\xa9n\xc3\xa9rale - Secr\xc3\xa9tariat;a
{};Direction g\xc3\xa9n\xc3\xa9rale - GRH;a
{};Direction g\xc3\xa9n\xc3\xa9rale - Communication;a
{};Direction financi\xc3\xa8re;a
{};Direction financi\xc3\xa8re - Budgets;a
{};Direction financi\xc3\xa8re - Comptabilit\xc3\xa9;a
{};Direction technique;a
{};Direction technique - B\xc3\xa2timents;a
{};Direction technique - Voiries;a
{};\xc3\x89v\xc3\xa9nements;a""".format(
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
            ),
        )

        # After activating one organisation
        from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY

        org_uids = api.portal.get_registry_record(ORGANIZATIONS_REGISTRY) or []
        org_uids.append(pgo_contacts["college-communal"].UID())
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, org_uids)
        pgo = view.pg_organizations(output="dict")
        self.assertEqual(
            pgo,
            [
                (pgo_contacts["direction-generale"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Secr\xc3\xa9tariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financi\xc3\xa8re", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financi\xc3\xa8re - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financi\xc3\xa8re - Comptabilit\xc3\xa9",
                    "a",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - B\xc3\xa2timents", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["evenements"].UID(), "\xc3\x89v\xc3\xa9nements", "a"),
                (pgo_contacts["college-communal"].UID(), "Coll\xc3\xa8ge communal", "a"),
            ],
        )

        # With both activated and not activated organizations
        pgo = view.pg_organizations(output="dict", only_activated="0")
        self.assertEqual(
            pgo,
            [
                (pgo_contacts["direction-generale"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale", "a"),
                (
                    pgo_contacts["direction-generale"]["secretariat"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Secr\xc3\xa9tariat",
                    "a",
                ),
                (pgo_contacts["direction-generale"]["grh"].UID(), "Direction g\xc3\xa9n\xc3\xa9rale - GRH", "a"),
                (
                    pgo_contacts["direction-generale"]["informatique"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Informatique",
                    "na",
                ),
                (
                    pgo_contacts["direction-generale"]["communication"].UID(),
                    "Direction g\xc3\xa9n\xc3\xa9rale - Communication",
                    "a",
                ),
                (pgo_contacts["direction-financiere"].UID(), "Direction financi\xc3\xa8re", "a"),
                (pgo_contacts["direction-financiere"]["budgets"].UID(), "Direction financi\xc3\xa8re - Budgets", "a"),
                (
                    pgo_contacts["direction-financiere"]["comptabilite"].UID(),
                    "Direction financi\xc3\xa8re - Comptabilit\xc3\xa9",
                    "a",
                ),
                (pgo_contacts["direction-financiere"]["taxes"].UID(), "Direction financi\xc3\xa8re - Taxes", "na"),
                (
                    pgo_contacts["direction-financiere"]["marches-publics"].UID(),
                    "Direction financi\xc3\xa8re - March\xc3\xa9s publics",
                    "na",
                ),
                (pgo_contacts["direction-technique"].UID(), "Direction technique", "a"),
                (pgo_contacts["direction-technique"]["batiments"].UID(), "Direction technique - B\xc3\xa2timents", "a"),
                (pgo_contacts["direction-technique"]["voiries"].UID(), "Direction technique - Voiries", "a"),
                (pgo_contacts["direction-technique"]["urbanisme"].UID(), "Direction technique - Urbanisme", "na"),
                (pgo_contacts["departement-population"].UID(), "D\xc3\xa9partement population", "na"),
                (
                    pgo_contacts["departement-population"]["population"].UID(),
                    "D\xc3\xa9partement population - Population",
                    "na",
                ),
                (
                    pgo_contacts["departement-population"]["etat-civil"].UID(),
                    "D\xc3\xa9partement population - \xc3\x89tat-civil",
                    "na",
                ),
                (pgo_contacts["departement-culturel"].UID(), "D\xc3\xa9partement culturel", "na"),
                (
                    pgo_contacts["departement-culturel"]["enseignement"].UID(),
                    "D\xc3\xa9partement culturel - Enseignement",
                    "na",
                ),
                (
                    pgo_contacts["departement-culturel"]["culture-loisirs"].UID(),
                    "D\xc3\xa9partement culturel - Culture-loisirs",
                    "na",
                ),
                (pgo_contacts["evenements"].UID(), "\xc3\x89v\xc3\xa9nements", "a"),
                (pgo_contacts["college-communal"].UID(), "Coll\xc3\xa8ge communal", "a"),
                (pgo_contacts["conseil-communal"].UID(), "Conseil communal", "na"),
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

    def test_OdmUtilsMethods_duplicate(self):
        intids = getUtility(IIntIds)

        omail2 = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id2",
            title="My title",
            description="Description",
            send_modes=["post"],
            classification_folders=[self.portal.folders['ordre-public-reglement-general-de-police'].UID()],
            classification_categories=self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories,
        )

        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            treating_groups=self.pgof["direction-generale"]["secretariat"].UID(),
            send_modes=["post"],
            classification_folders=[self.portal.folders['ordre-public-reglement-general-de-police'].UID()],
            classification_categories=self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories,
            reply_to=[RelationValue(intids.getId(omail2))],
        )
        createContentInContainer(omail, "dmsommainfile", title=u"D001", file=NamedBlobFile(filename=u"scanned.pdf"))
        createContentInContainer(
            omail, "dmsappendixfile", title=u"A001", file=NamedBlobFile(filename=u"appendix.odt")
        )
        view = OdmUtilsMethods(omail, omail.REQUEST)

        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertEqual(duplicated_mail.title, u"My title")
        self.assertEqual(duplicated_mail.description, u"Description")
        self.assertEqual(duplicated_mail.send_modes, ["post"])
        self.assertGreater(duplicated_mail.creation_date, omail.creation_date)
        self.assertNotEqual(duplicated_mail.internal_reference_no, omail.internal_reference_no)
        self.assertIsNone(duplicated_mail.mail_date)
        self.assertIsNone(duplicated_mail.due_date)
        self.assertIsNone(duplicated_mail.outgoing_date)

        # Test keep_category
        self.assertEqual(duplicated_mail.classification_categories, self.portal.folders['ordre-public-reglement-general-de-police'].classification_categories)
        # Test keep_folder
        self.assertEqual(duplicated_mail.classification_folders, [self.portal.folders['ordre-public-reglement-general-de-police'].UID()])
        # Test keep_linked_mails
        self.assertEqual(len(duplicated_mail.reply_to), 2)
        self.assertEqual(omail2, duplicated_mail.reply_to[0].to_object)
        # Test keep_dms_files
        self.assertNotIn("d001", duplicated_mail)  # By default, we never keep not generated main files
        # Test keep_annexes
        self.assertIn("a001", duplicated_mail)
        # Test link_to_original
        self.assertEqual(omail, duplicated_mail.reply_to[1].to_object)

        # Test not keeping categories
        duplicated_mail = view.duplicate(
            keep_category=False,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertIsNone(duplicated_mail.classification_categories)

        # Test not keeping folders
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=False,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertIsNone(duplicated_mail.classification_folders)

        # Test not keeping linked mails
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=False,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertEqual(len(duplicated_mail.reply_to), 1)
        self.assertNotEqual(omail2, duplicated_mail.reply_to[0].to_object)

        # Test not keeping dms files
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=False,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertNotIn("d001", duplicated_mail)

        # Test not keeping annexes
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=False,
            link_to_duplicated=True,
        )
        self.assertNotIn("a001", duplicated_mail)

        # Test not linking to original
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=False,
        )
        self.assertEqual(len(duplicated_mail.reply_to), 1)
        self.assertNotEqual(omail, duplicated_mail.reply_to[0].to_object)

        # Test with generated main files
        generation_view = getMultiAdapter((omail, omail.REQUEST), name="persistent-document-generation")
        pod_template = self.portal.templates["om"]["main"]
        generation_view.pod_template = pod_template
        generation_view.output_format = 'odt'
        generation_view.generate_persistent_doc(pod_template, 'odt')
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertIn('012999900000002', duplicated_mail)
        dms_file = duplicated_mail['012999900000002']
        annot = IAnnotations(dms_file)['documentgenerator']
        self.assertEqual(annot['template_uid'], pod_template.UID())

        # Test with mailings (publipostage)
        omail.recipients = [RelationValue(intids.getId(self.contacts["jeancourant"]["agent-electrabel"])), RelationValue(intids.getId(self.contacts["sergerobinet"]["agent-swde"]))]
        generation_view.generate_persistent_doc(pod_template, 'odt')
        mailing_loop_generation_view = getMultiAdapter((omail, omail.REQUEST), name="mailing-loop-persistent-document-generation")
        mailing_loop_pod_template = self.portal.templates["om"]["mailing"]
        mailing_loop_generation_view.orig_template = pod_template
        mailing_loop_generation_view.pod_template = mailing_loop_pod_template
        mailing_loop_generation_view.output_format = 'odt'
        mailing_loop_generation_view.document = omail['012999900000001']
        mailing_loop_generation_view.generate_persistent_doc(mailing_loop_pod_template, 'odt')
        duplicated_mail = view.duplicate(
            keep_category=True,
            keep_folder=True,
            keep_reply_to=True,
            keep_dms_files=True,
            keep_annexes=True,
            link_to_duplicated=True,
        )
        self.assertEqual(duplicated_mail.keys(), ['a001', '012999900000004'])
        dms_file = duplicated_mail['012999900000004']
        annot = IAnnotations(dms_file)['documentgenerator']
        self.assertEqual(annot['template_uid'], pod_template.UID())
        self.assertTrue(annot['need_mailing'])

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

    def test_dv_clean(self):
        # Test wrong user
        self.change_user("agent")
        self.assertEqual(dv_clean(self.portal), "You must be a zope manager to run this script")

        self.change_user("admin")
        # Test invalid date
        self.assertIsNone(dv_clean(self.portal, date_back="invalid"))

        # Create incoming mail with file
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "courrier",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "description": "Ceci est la description du courrier",
            "mail_date": datetime.today(),
        }
        imail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)
        pdf_example_filename = os.path.join(os.path.dirname(__file__), "files", "example.pdf")
        with open(pdf_example_filename, "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=u"example.pdf")
            createContentInContainer(
                imail,
                "dmsmainfile",
                title="",
                file=file_object,
                scan_id="050999900000010",
                scan_date=datetime.today(),
            )
        file = imail["example.pdf"]

        # Assert base scenario
        annot = IAnnotations(file)["collective.documentviewer"]
        self.assertEqual(annot["num_pages"], 6)
        self.assertNotEqual(annot["last_updated"], "2010-01-01T00:00:00")
        self.assertEqual(
            [k for k in annot["blob_files"].keys()],
            [
                "large/dump_1.jpg",
                "large/dump_2.jpg",
                "large/dump_3.jpg",
                "large/dump_4.jpg",
                "large/dump_5.jpg",
                "large/dump_6.jpg",
                "normal/dump_1.jpg",
                "normal/dump_2.jpg",
                "normal/dump_3.jpg",
                "normal/dump_4.jpg",
                "normal/dump_5.jpg",
                "normal/dump_6.jpg",
                "small/dump_1.jpg",
                "small/dump_2.jpg",
                "small/dump_3.jpg",
                "small/dump_4.jpg",
                "small/dump_5.jpg",
                "small/dump_6.jpg",
                "text/dump_1.txt",
                "text/dump_2.txt",
                "text/dump_3.txt",
                "text/dump_4.txt",
                "text/dump_5.txt",
                "text/dump_6.txt",
            ],
        )

        # Mail is not closed yet
        self.assertTrue(
            dv_clean(self.portal, days_back=0).endswith("Files: '0', Pages: '0', Deleted: '0', Size: '0.0k'")
        )

        api.content.transition(imail, "propose_to_agent")
        api.content.transition(imail, "treat")
        api.content.transition(imail, "close")

        # Mail is closed but recent
        self.assertTrue(dv_clean(self.portal).endswith("Files: '0', Pages: '0', Deleted: '0', Size: '0.0k'"))

        # Mail is closed and old
        new_date = datetime.today() - timedelta(days=366)
        new_date = DateTime(datetime.strftime(new_date, "%Y/%m/%d")).ISO8601()
        imail.setModificationDate(new_date)
        imail._p_changed = True
        imail.reindexObject(idxs=['modified'])
        self.assertTrue(
            dv_clean(self.portal).endswith("Files: '1', Pages: '6', Deleted: '24', Size: '2.0M'")
        )
        annot = IAnnotations(file)["collective.documentviewer"]
        self.assertEqual(annot["num_pages"], 1)
        self.assertEqual(annot["last_updated"], "2010-01-01T00:00:00")
        self.assertEqual(
            [k for k in annot["blob_files"].keys()],
            ["large/dump_1.jpg", "normal/dump_1.jpg", "small/dump_1.jpg"],
        )

        # Test date_back
        converter = Converter(file)
        converter()
        new_date = datetime.today() - timedelta(days=366)
        new_date = DateTime(datetime.strftime(new_date, "%Y/%m/%d")).ISO8601()
        imail.setModificationDate(new_date)
        imail._p_changed = True
        imail.reindexObject(idxs=['modified'])
        annot = IAnnotations(file)["collective.documentviewer"]
        self.assertEqual(annot["num_pages"], 6)
        self.assertNotEqual(annot["last_updated"], "2010-01-01T00:00:00")
        self.assertTrue(
            dv_clean(self.portal, date_back=(datetime.today() - timedelta(days=367)).strftime("%Y%m%d")).endswith(
                "Files: '0', Pages: '0', Deleted: '0', Size: '0.0k'"
            )
        )
        self.assertTrue(
            dv_clean(self.portal, date_back=(datetime.today() - timedelta(days=365)).strftime("%Y%m%d")).endswith(
                "Files: '1', Pages: '6', Deleted: '24', Size: '2.0M'"
            )
        )

    def test_eml_preview(self):
        # Create incoming mail with file
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "courrier",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "description": "Ceci est la description du courrier",
            "mail_date": datetime.today(),
        }
        iemail = sub_create(self.imf, "dmsincoming_email", datetime.today(), "my-id", **params)
        pdf_example_filename = os.path.join(os.path.dirname(__file__), "files", "example.eml")
        with open(pdf_example_filename, "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=u"example.eml")
            # This prevents the subscriber from executing eml_preview too early in the test
            with patch("imio.dms.mail.subscribers.eml_preview", new=Mock(return_value=None)):
                dmsmainfile = createContentInContainer(
                    iemail,
                    "dmsmainfile",
                    title="",
                    file=file_object,
                    scan_id="050999900000010",
                    scan_date=datetime.today(),
                )
        annot = IAnnotations(dmsmainfile)
        self.assertNotIn("successfully_converted", annot)
        eml_preview(dmsmainfile)
        annot = IAnnotations(dmsmainfile)["collective.documentviewer"]
        self.assertEqual(annot["num_pages"], 1)
        self.assertEqual(annot["successfully_converted"], True)
        self.assertEqual(
            [k for k in annot["blob_files"].keys()],
            ["large/dump_1.jpg", "normal/dump_1.jpg", "small/dump_1.jpg"],
        )
        blobs = [bl for bl in annot["blob_files"].values()]
        self.assertEqual(blobs[0], blobs[1])
        with open(os.path.join(PREVIEW_DIR, "previsualisation_eml_normal.jpg"), 'rb') as f1, \
                open(blobs[0]._p_blob_uncommitted, 'rb') as f2:
            self.assertEqual(f1.read(), f2.read())
