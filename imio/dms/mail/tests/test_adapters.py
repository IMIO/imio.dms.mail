# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.utils import calculate_category_id
from collective.wfadaptations.api import add_applied_adaptation
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.adapters import default_criterias
from imio.dms.mail.adapters import IdmSearchableExtender
from imio.dms.mail.adapters import im_sender_email_index
from imio.dms.mail.adapters import IncomingMailHighestValidationCriterion
from imio.dms.mail.adapters import IncomingMailInCopyGroupCriterion
from imio.dms.mail.adapters import IncomingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import IncomingMailValidationCriterion
from imio.dms.mail.adapters import OdmSearchableExtender
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.adapters import org_sortable_title_index
from imio.dms.mail.adapters import OutgoingMailInCopyGroupCriterion
from imio.dms.mail.adapters import OutgoingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import OutgoingMailValidationCriterion
from imio.dms.mail.adapters import ready_for_email_index
from imio.dms.mail.adapters import ScanSearchableExtender
from imio.dms.mail.adapters import state_group_index
from imio.dms.mail.adapters import TaskInAssignedGroupCriterion
from imio.dms.mail.adapters import TaskInProposingGroupCriterion
from imio.dms.mail.adapters import TaskValidationCriterion
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import sub_create
from imio.esign.utils import get_session_annotation
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestAdapters(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_IncomingMailHighestValidationCriterion(self):
        crit = IncomingMailHighestValidationCriterion(self.portal)
        # no groups, => default criterias
        self.assertEqual(crit.query, default_criterias["dmsincomingmail"])
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(
            ["review_levels", "dmsincomingmail"],
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"}),
                ]
            ),
        )
        # in a group _n_plus_1
        self.assertEqual(
            crit.query, {"review_state": {"query": ["proposed_to_n_plus_1"]}, "treating_groups": {"query": ["111"]}}
        )
        api.group.add_user(groupname="dir_general", username="siteadmin")
        self.change_user("siteadmin")
        # in a group dir_general
        self.assertEqual(crit.query, {"review_state": {"query": ["proposed_to_manager"]}})

    def test_IncomingMailValidationCriterion(self):
        crit = IncomingMailValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {"state_group": {"query": []}})
        # in a group _n_plus_1
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(
            ["review_levels", "dmsincomingmail"],
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"}),
                ]
            ),
        )
        self.assertEqual(crit.query, {"state_group": {"query": ["proposed_to_n_plus_1,111"]}})
        # in a group dir_general
        api.group.add_user(groupname="dir_general", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"state_group": {"query": ["proposed_to_manager", "proposed_to_n_plus_1,111"]}})

    def test_OutgoingMailValidationCriterion(self):
        crit = OutgoingMailValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {"state_group": {"query": []}})
        # in a group _n_plus_1
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(
            ["review_levels", "dmsoutgoingmail"],
            OrderedDict([("_n_plus_1", {"st": ["proposed_to_n_plus_1"], "org": "treating_groups"})]),
        )
        self.assertEqual(crit.query, {"state_group": {"query": ["proposed_to_n_plus_1,111"]}})
        # in a group dir_general
        api.group.add_user(groupname="dir_general", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"state_group": {"query": ["proposed_to_n_plus_1,111"]}})

    def test_TaskValidationCriterion(self):
        crit = TaskValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {"state_group": {"query": []}})
        # in a group _n_plus_1
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        set_dms_config(
            ["review_levels", "task"],
            OrderedDict([("_n_plus_1", {"st": ["to_assign", "realized"], "org": "assigned_group"})]),
        )
        self.assertEqual(crit.query, {"state_group": {"query": ["to_assign,111", "realized,111"]}})
        # in a group dir_general, but no effect for task criterion
        api.group.add_user(groupname="dir_general", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"state_group": {"query": ["to_assign,111", "realized,111"]}})

    def test_IncomingMailInTreatingGroupCriterion(self):
        crit = IncomingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"treating_groups": {"query": []}})
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"treating_groups": {"query": ["111"]}})

    def test_OutgoingMailInTreatingGroupCriterion(self):
        crit = OutgoingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"treating_groups": {"query": []}})
        api.group.create(groupname="111_n_plus_1")
        api.group.add_user(groupname="111_n_plus_1", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"treating_groups": {"query": ["111"]}})

    def test_IncomingMailInCopyGroupCriterion(self):
        crit = IncomingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"recipient_groups": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"recipient_groups": {"query": ["111"]}})

    def test_OutgoingMailInCopyGroupCriterion(self):
        crit = OutgoingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"recipient_groups": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"recipient_groups": {"query": ["111"]}})

    def test_TaskInAssignedGroupCriterion(self):
        crit = TaskInAssignedGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"assigned_group": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"assigned_group": {"query": ["111"]}})

    def test_TaskInProposingGroupCriterion(self):
        crit = TaskInProposingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"mail_type": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"mail_type": {"query": ["111"]}})

    def test_im_sender_email_index(self):
        dguid = self.pgof["direction-generale"].UID()
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "id1",
            **{
                "title": u"test",
                "treating_groups": dguid,
                "assigned_user": u"chef",
                "orig_sender_email": u'"Dexter Morgan" <dexter.morgan@mpd.am>',
            }
        )
        indexer = im_sender_email_index(imail)
        self.assertEqual(indexer(), u"dexter.morgan@mpd.am")

    def test_ready_for_email_index(self):
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            send_modes=["post"],
        )
        indexer = ready_for_email_index(omail)
        # not an email
        self.assertFalse(indexer())
        # email without docs
        omail.send_modes = ["email"]
        self.assertTrue(indexer())
        # email with a doc not signed
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(omail, "dmsommainfile", file=NamedBlobFile(fo.read(), filename=filename))
        self.assertFalse(indexer())
        # email with another doc signed
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(omail, "dmsommainfile", file=NamedBlobFile(fo.read(), filename=filename), signed=True)
        self.assertTrue(indexer())

    def test_state_group_index(self):
        dguid = self.pgof["direction-generale"].UID()
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "id1",
            **{"title": u"test", "treating_groups": dguid, "assigned_user": u"chef"}
        )
        indexer = state_group_index(imail)
        self.assertEqual(indexer(), "created")
        api.content.transition(obj=imail, to_state="proposed_to_manager")
        self.assertEqual(indexer(), "proposed_to_manager")
        api.content.transition(obj=imail, to_state="proposed_to_agent")
        self.assertEqual(indexer(), "proposed_to_agent")

        task = createContentInContainer(imail, "task", assigned_group=dguid)
        indexer = state_group_index(task)
        self.assertEqual(indexer(), "created")
        # simulate adaptation
        add_applied_adaptation("imio.dms.mail.wfadaptations.TaskServiceValidation", "task_workflow", False)
        api.group.create(groupname="{}_n_plus_1".format(dguid), groups=["chef"])
        api.content.transition(obj=task, transition="do_to_assign")
        self.assertEqual(indexer(), "to_assign")
        set_dms_config(
            ["review_states", "task"], OrderedDict([("to_assign", {"group": "_n_plus_1", "org": "assigned_group"})])
        )
        self.assertEqual(indexer(), "to_assign,%s" % dguid)

    def test_ScanSearchableExtender(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "id1")
        obj = createContentInContainer(imail, "dmsmainfile", id="testid1.pdf", title="title", description="description")
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "testid1 title description")
        obj = createContentInContainer(imail, "dmsmainfile", id="testid1", title="title.pdf", description="description")
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "testid1 title description")
        obj = createContentInContainer(
            imail, "dmsmainfile", id="testid2.pdf", title="testid2.PDF", description="description"
        )
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "testid2 description")
        obj = createContentInContainer(
            imail,
            "dmsmainfile",
            id="010999900000690.pdf",
            title="010999900000690.pdf",
            description="description",
            scan_id="010999900000690",
        )
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "010999900000690 IMIO010999900000690 description")
        obj = createContentInContainer(
            imail,
            "dmsmainfile",
            id="010999900001691.pdf",
            title="title",
            description="description",
            scan_id="010999900001691",
        )
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "010999900001691 title IMIO010999900001691 1691 description")
        fh = open("testfile.txt", "w+")
        fh.write("One word\n")
        fh.seek(0)
        file_object = NamedBlobFile(fh.read(), filename=u"testfile.txt")
        obj = createContentInContainer(
            imail,
            "dmsmainfile",
            id="testid2",
            title="title",
            description="description",
            file=file_object,
            scan_id="010999900000690",
        )
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), "testid2 title 010999900000690 IMIO010999900000690 description One word\n")

    def test_IdmSearchableExtender(self):
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            **{"title": u"My title", "description": u"Description"}
        )
        ext = IdmSearchableExtender(imail)
        self.assertEqual(ext(), None)
        createContentInContainer(imail, "dmsmainfile", id="testid1", scan_id="010999900000690")
        self.assertEqual(ext(), u"010999900000690 IMIO010999900000690 690")
        pc = imail.portal_catalog
        rid = pc(id="my-id")[0].getRID()
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(
            index_value, ["e0010", "my", "title", "description", u"010999900000690", "imio010999900000690", u"690"]
        )
        createContentInContainer(imail, "dmsmainfile", id="testid2", scan_id="010999900000700")
        self.assertEqual(ext(), u"010999900000690 IMIO010999900000690 690 010999900000700 IMIO010999900000700 700")
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(
            index_value,
            [
                "e0010",
                "my",
                "title",
                "description",
                u"010999900000690",
                "imio010999900000690",
                u"690",
                u"010999900000700",
                "imio010999900000700",
                u"700",
            ],
        )

    def test_OdmSearchableExtender(self):
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
        )
        ext = OdmSearchableExtender(omail)
        self.assertEqual(ext(), None)
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(omail, "dmsommainfile", id="testid1", scan_id="011999900000690", file=NamedBlobFile(fo.read(), filename=filename))
        self.assertEqual(ext(), u"011999900000690 IMIO011999900000690 690")
        pc = omail.portal_catalog
        rid = pc(id="my-id")[0].getRID()
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(
            index_value, ["s0010", "my", "title", "description", u"011999900000690", "imio011999900000690", u"690"]
        )
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(omail, "dmsommainfile", id="testid2", scan_id="011999900000700", file=NamedBlobFile(fo.read(), filename=filename))
        self.assertEqual(ext(), u"011999900000690 IMIO011999900000690 690 011999900000700 IMIO011999900000700 700")
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(
            index_value,
            [
                "s0010",
                "my",
                "title",
                "description",
                u"011999900000690",
                "imio011999900000690",
                u"690",
                u"011999900000700",
                "imio011999900000700",
                u"700",
            ],
        )

    def test_org_sortable_title_index(self):
        elec = self.portal["contacts"]["electrabel"]
        trav = elec["travaux"]
        self.assertEqual(org_sortable_title_index(elec)(), "electrabel|")
        self.assertEqual(org_sortable_title_index(trav)(), "electrabel|travaux 0001|")

    def test_IMMCTV(self):
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            **{"title": u"My title", "mail_type": u"courrier", "assigned_user": u"agent"}
        )
        view = imail.restrictedTraverse("@@view")
        view.update()
        # the title from the vocabulary is well rendered
        self.assertIn("Courrier", view.widgets["mail_type"].render())
        # We deactivate the courrier mail type, the missing value is managed
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]["active"] = False
        settings.mail_types = mail_types
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.IMActiveMailTypesVocabulary")
        self.assertNotIn("courrier", [t.value for t in voc_inst(imail)])
        view.updateWidgets()
        self.assertIn("Courrier", view.widgets["mail_type"].render())
        # We remove the courrier mail type, the missing value cannot be managed anymore
        settings.mail_types = settings.mail_types[1:]
        view.updateWidgets()
        self.assertNotIn("Courrier", view.widgets["mail_type"].render())
        self.assertIn("Missing", view.widgets["mail_type"].render())

    def test_OMMCTV(self):
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            mail_type="type1",
        )
        view = omail.restrictedTraverse("@@view")
        view.update()
        # the title from the vocabulary is well rendered
        self.assertIn("Type 1", view.widgets["mail_type"].render())
        # We deactivate the courrier mail type, the missing value is managed
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.omail_types
        mail_types[0]["active"] = False
        settings.omail_types = mail_types
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.OMActiveMailTypesVocabulary")
        self.assertNotIn("type1", [t.value for t in voc_inst(omail)])
        view.updateWidgets()
        self.assertIn("Type 1", view.widgets["mail_type"].render())
        # We remove the courrier mail type, the missing value cannot be managed anymore
        settings.omail_types = settings.omail_types[1:]
        view.updateWidgets()
        self.assertNotIn("Type 1", view.widgets["mail_type"].render())
        self.assertIn("Missing", view.widgets["mail_type"].render())


class TestOMApprovalAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pw = self.portal.portal_workflow
        self.change_user("admin")
        self.portal.restrictedTraverse("idm_activate_signing")()

        # Create outgoing mail with two eSign signers and two files to approve
        intids = getUtility(IIntIds)
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.pf = self.portal["contacts"]["personnel-folder"]
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "type1",
            "treating_groups": self.pgof["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
            "signers": [
                {
                    "number": 1,
                    "signer": self.pf["dirg"]["directeur-general"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": True,
                },
                {
                    "number": 2,
                    "signer": self.pf["bourgmestre"]["bourgmestre"].UID(),
                    "approvings": [u"_themself_", self.pf["chef"].UID()],
                    "editor": False,
                },
            ],
            "esign": True,
        }
        self.omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om", **params)

        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        self.files = []
        for i in range(2):
            with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                self.files.append(
                    createContentInContainer(
                        self.omail,
                        "dmsommainfile",
                        id="file%s" % i,
                        scan_id="012999900000601",
                        file=file_object,
                        content_category=calculate_category_id(ct),
                    )
                )

        self.approval = OMApprovalAdapter(self.omail)

    def test_reset(self):
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        self.approval.reset()
        self.assertEqual(
            self.approval.annot,
            {
                "files": [],
                "approvers": [],
                "session_id": None,
                "pdf_files": [],
                "approval": [],
                "editors": [],
                "signers": [],
            },
        )

    def test_current_nb(self):
        # None, no approval session started
        self.assertIsNone(self.approval.current_nb)

        # 0, first approver
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.current_nb, 0)
        self.approval.approve_file(self.files[0], "dirg")
        self.assertEqual(self.approval.current_nb, 0)
        self.approval.approve_file(self.files[1], "dirg")

        # 1, second approver
        self.assertEqual(self.approval.current_nb, 1)
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.assertEqual(self.approval.current_nb, 1)
        self.approval.approve_file(self.files[1], "bourgmestre")

        # -1, all approvers have approved
        self.assertEqual(self.approval.current_nb, -1)

    def test_current_approvers(self):
        # Empty, no approval session started
        self.assertEqual(self.approval.current_approvers, [])

        # First approver
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.current_approvers, ["dirg"])
        self.approval.approve_file(self.files[0], "dirg")
        self.assertEqual(self.approval.current_approvers, ["dirg"])
        self.approval.approve_file(self.files[1], "dirg")

        # Second approvers
        self.assertEqual(self.approval.current_approvers, ["bourgmestre", "chef"])
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.assertEqual(self.approval.current_approvers, ["bourgmestre", "chef"])
        self.approval.approve_file(self.files[1], "chef")

        # Empty, Approval process finished
        self.assertEqual(self.approval.current_approvers, [])

    def test_get_approver_nb(self):
        self.assertEqual(self.approval.get_approver_nb("dirg"), 0)
        self.assertEqual(self.approval.get_approver_nb("bourgmestre"), 1)
        self.assertEqual(self.approval.get_approver_nb("chef"), 1)
        self.assertIsNone(self.approval.get_approver_nb("agent"))
        self.assertIsNone(self.approval.get_approver_nb("unknown"))

    def test_roles(self):
        # Empty, no approval session started
        self.assertEqual(self.approval.roles, {})

        # First approver
        self.approval.propose_to_approve()
        self.assertEqual(self.approval.roles, {})
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.roles, {"dirg": ("Reader", "Editor")})
        self.approval.approve_file(self.files[0], "dirg")
        self.approval.approve_file(self.files[1], "dirg")

        # Second approvers
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader",), "chef": ("Reader",), "dirg": ("Reader", "Editor")}
        )
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.approval.approve_file(self.files[1], "bourgmestre")

        # Approval process finished
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader",), "chef": ("Reader",), "dirg": ("Reader", "Editor")}
        )

    def test_propose_to_approve(self):
        # Initial state
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
            ],
        )
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "p", "approved_on": None, "approved_by": None},
                    {"status": "p", "approved_on": None, "approved_by": None},
                ],
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
            ],
        )

        # One file was already approved
        now = datetime.now()
        self.approval.annot["approval"] = [
            [
                {"status": "a", "approved_on": now, "approved_by": "dirg"},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
            [
                {"status": "w", "approved_on": None, "approved_by": None},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
        ]
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "a", "approved_on": now, "approved_by": "dirg"},
                    {"status": "p", "approved_on": None, "approved_by": None},
                ],
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
            ],
        )

        # First approver had already approved all files
        self.approval.annot["approval"] = [
            [
                {"status": "a", "approved_on": now, "approved_by": "dirg"},
                {"status": "a", "approved_on": now, "approved_by": "dirg"},
            ],
            [
                {"status": "w", "approved_on": None, "approved_by": None},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
        ]
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "a", "approved_on": now, "approved_by": "dirg"},
                    {"status": "a", "approved_on": now, "approved_by": "dirg"},
                ],
                [
                    {"status": "p", "approved_on": None, "approved_by": None},
                    {"status": "p", "approved_on": None, "approved_by": None},
                ],
            ],
        )

        # A file was edited after approval
        self.approval.annot["approval"] = [
            [
                {"status": "a", "approved_on": now, "approved_by": "dirg"},
                {"status": "a", "approved_on": datetime(1900, 1, 1), "approved_by": "dirg"},
            ],
            [
                {"status": "w", "approved_on": None, "approved_by": None},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
        ]
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "a", "approved_on": now, "approved_by": "dirg"},
                    {"status": "p", "approved_on": None, "approved_by": None},
                ],
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
            ],
        )

        # One file for second approvers is pending but it should not
        self.approval.annot["approval"] = [
            [
                {"status": "a", "approved_on": now, "approved_by": "dirg"},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
            [
                {"status": "p", "approved_on": None, "approved_by": None},
                {"status": "w", "approved_on": None, "approved_by": None},
            ],
        ]
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot["approval"],
            [
                [
                    {"status": "a", "approved_on": now, "approved_by": "dirg"},
                    {"status": "p", "approved_on": None, "approved_by": None},
                ],
                [
                    {"status": "w", "approved_on": None, "approved_by": None},
                    {"status": "w", "approved_on": None, "approved_by": None},
                ],
            ],
        )

    def test_update_signers(self):
        self.approval.update_signers()
        # The annotation was reset and rebuilt by the method, Nothing changes
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # Approval has started, signers are reset but approvals are left unchanged
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.approval.approve_file(self.files[0], "dirg")
        approval_datetime = self.approval.annot["approval"][0][0]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {
                            "status": "a",
                            "approved_on": approval_datetime,
                            "approved_by": "dirg",
                        },
                        {"status": "p", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        self.approval.update_signers()
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {
                            "status": "a",
                            "approved_on": approval_datetime,
                            "approved_by": "dirg",
                        },
                        {"status": "p", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # A signer does not exist
        self.omail.signers[0]["signer"] = "wrong-uid"
        self.approval.reset()
        self.assertRaises(ValueError, self.approval.update_signers)
        self.omail.signers[0]["signer"] = self.pf["dirg"]["directeur-general"].UID()

        # Duplicate approvers
        self.omail.signers[0]["approvings"].append(self.pf["chef"].UID())
        self.approval.reset()
        self.assertRaises(ValueError, self.approval.update_signers)
        self.omail.signers[0]["approvings"] = [u"_themself_"]

        # Duplicate emails for approvers
        api.user.get("bourgmestre").setMemberProperties({"email": "duplicate@belleville.eb"})
        api.user.get("dirg").setMemberProperties({"email": "duplicate@belleville.eb"})
        self.approval.reset()
        self.assertRaises(ValueError, self.approval.update_signers)

    def test_add_remove_file_to_approval(self):
        self.approval.remove_file_from_approval(self.files[0].UID())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None],
                "approval": [
                    [{"status": "w", "approved_on": None, "approved_by": None}],
                    [{"status": "w", "approved_on": None, "approved_by": None}],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # File is already removed, nothing changes
        self.approval.remove_file_from_approval(self.files[0].UID())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None],
                "approval": [
                    [{"status": "w", "approved_on": None, "approved_by": None}],
                    [{"status": "w", "approved_on": None, "approved_by": None}],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # Add a new file
        self.approval.add_file_to_approval(self.files[0].UID())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID(), self.files[0].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # File is already added, nothing changes
        self.approval.add_file_to_approval(self.files[0].UID())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID(), self.files[0].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

    def test_is_file_approved(self):
        # Test unknown file
        self.assertFalse(self.approval.is_file_approved("unknown-file-uid", "dirg"))

        # Test partially approved file
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.approval.approve_file(self.files[0], "dirg")
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), totally=False))
        self.assertFalse(self.approval.is_file_approved(self.files[0].UID(), totally=True))

        # Test fully approved file
        self.approval.approve_file(self.files[1], "dirg")
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), totally=False))
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), totally=True))
        self.assertTrue(self.approval.is_file_approved(self.files[1].UID(), totally=False))
        self.assertFalse(self.approval.is_file_approved(self.files[1].UID(), totally=True))

        # Test userid
        self.assertFalse(self.approval.is_file_approved(self.files[1].UID(), userid="unknown-user"))
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), userid="dirg"))
        self.assertTrue(self.approval.is_file_approved(self.files[1].UID(), userid="dirg"))
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), userid="bourgmestre"))
        self.assertFalse(self.approval.is_file_approved(self.files[1].UID(), userid="bourgmestre"))

        # Test nb
        self.assertFalse(self.approval.is_file_approved(self.files[0].UID(), nb=999))
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), nb=0))
        self.assertTrue(self.approval.is_file_approved(self.files[0].UID(), nb=1))
        self.assertTrue(self.approval.is_file_approved(self.files[1].UID(), nb=0))
        self.assertFalse(self.approval.is_file_approved(self.files[1].UID(), nb=1))

    def test_can_approve(self):
        # Test too early
        self.assertFalse(self.approval.can_approve("dirg", self.files[0].UID()))
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertTrue(self.approval.can_approve("dirg", self.files[0].UID()))

        # Test cannot approve now
        self.assertFalse(self.approval.can_approve("chef", self.files[0].UID()))
        self.assertFalse(self.approval.can_approve("bourgmestre", self.files[0].UID()))

        # Test user is not an approver
        self.assertFalse(self.approval.can_approve("agent", self.files[0].UID()))

        # Test file is not to be approved
        self.assertFalse(self.approval.can_approve("dirg", "other-file-uid"))

        # Test already approved file
        self.approval.approve_file(self.files[0], "dirg")
        self.assertTrue(self.approval.can_approve("dirg", self.files[0].UID()))

        # Test second approvers
        self.approval.approve_file(self.files[1], "dirg")
        self.assertTrue(self.approval.can_approve("bourgmestre", self.files[0].UID()))
        self.assertTrue(self.approval.can_approve("bourgmestre", self.files[1].UID()))

    def test_approve_file(self):
        # Approval not started yet
        self.assertRaises(ValueError, self.approval.approve_file, self.files[0], "dirg")

        # Test file is not to be approved
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.approval.remove_file_from_approval(self.files[1].UID())
        self.assertRaises(ValueError, self.approval.approve_file, self.files[1], "dirg")

        # dirg approves files
        self.approval.add_file_to_approval(self.files[1].UID())
        self.approval.propose_to_approve()
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "p", "approved_on": None, "approved_by": None},
                        {"status": "p", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        values = {}
        self.assertEqual(
            self.approval.approve_file(self.files[0], "dirg", values=values, transition="propose_to_be_signed"),
            (True, True),
        )
        self.assertEqual(values, {})
        dirg_approval_datetime_1 = self.approval.annot["approval"][0][0]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "a", "approved_on": dirg_approval_datetime_1, "approved_by": "dirg"},
                        {"status": "p", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "w", "approved_on": None, "approved_by": None},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # Test admin somehow approving a file one step ahead (test c_a)
        self.assertEqual(
            self.approval.approve_file(self.files[1], "admin", values=values, transition="propose_to_be_signed", c_a=1),
            (True, True),
        )
        bourgmestre_approval_datetime_2 = self.approval.annot["approval"][1][1]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "a", "approved_on": dirg_approval_datetime_1, "approved_by": "dirg"},
                        {"status": "p", "approved_on": None, "approved_by": None},
                    ],
                    [
                        {"status": "w", "approved_on": None, "approved_by": None},
                        {"status": "a", "approved_on": bourgmestre_approval_datetime_2, "approved_by": "admin"},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        self.assertEqual(
            self.approval.approve_file(self.files[1], "dirg", values=values, transition="propose_to_be_signed"),
            (True, True),
        )
        self.assertEqual(values, {"approved": True})
        dirg_approval_datetime_2 = self.approval.annot["approval"][0][1]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": None,
                "pdf_files": [None, None],
                "approval": [
                    [
                        {"status": "a", "approved_on": dirg_approval_datetime_1, "approved_by": "dirg"},
                        {"status": "a", "approved_on": dirg_approval_datetime_2, "approved_by": "dirg"},
                    ],
                    [
                        {"status": "p", "approved_on": None, "approved_by": None},
                        {"status": "a", "approved_on": bourgmestre_approval_datetime_2, "approved_by": "admin"},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # bourgmestre approves files
        self.assertEqual(api.content.get_state(self.omail), "to_approve")
        values = {}
        self.assertEqual(
            self.approval.approve_file(self.files[0], "bourgmestre", values=values, transition="propose_to_be_signed"),
            (True, True),
        )
        self.assertEqual(values, {"approved": True})
        bourgmestre_approval_datetime_1 = self.approval.annot["approval"][1][0]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": 0,
                "pdf_files": [self.omail["reponse-salle.pdf"].UID(), self.omail["reponse-salle-1.pdf"].UID()],
                "approval": [
                    [
                        {"status": "a", "approved_on": dirg_approval_datetime_1, "approved_by": "dirg"},
                        {"status": "a", "approved_on": dirg_approval_datetime_2, "approved_by": "dirg"},
                    ],
                    [
                        {"status": "a", "approved_on": bourgmestre_approval_datetime_1, "approved_by": "bourgmestre"},
                        {"status": "a", "approved_on": bourgmestre_approval_datetime_2, "approved_by": "admin"},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        self.assertEqual(api.content.get_state(self.omail), "to_be_signed")

    def test_unapprove_file(self):
        self.pw.doActionFor(self.omail, "propose_to_approve")

        # Cannot unapprove file that is not to approved
        self.approval.remove_file_from_approval(self.files[1].UID())
        self.assertRaises(ValueError, self.approval.unapprove_file, self.files[1], "dirg")

        # Cannot unapprove file with wrong signer
        self.assertRaises(ValueError, self.approval.unapprove_file, self.files[0], "agent")
        self.approval.approve_file(self.files[0], "dirg")
        dirg_approval_datetime = self.approval.annot["approval"][0][0]["approved_on"]
        self.approval.approve_file(self.files[0], "bourgmestre")
        bourgmestre_approval_datetime = self.approval.annot["approval"][1][0]["approved_on"]
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": 0,
                "pdf_files": [self.omail["reponse-salle.pdf"].UID()],
                "approval": [
                    [
                        {"status": "a", "approved_on": dirg_approval_datetime, "approved_by": "dirg"},
                    ],
                    [
                        {"status": "a", "approved_on": bourgmestre_approval_datetime, "approved_by": "bourgmestre"},
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )

        # Unapprove first approver
        self.approval.unapprove_file(self.files[0], "dirg")
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": 0,
                "pdf_files": [self.omail["reponse-salle.pdf"].UID()],
                "approval": [
                    [{"status": "p", "approved_on": None, "approved_by": None}],
                    [
                        {
                            "status": "a",
                            "approved_on": bourgmestre_approval_datetime,
                            "approved_by": "bourgmestre",
                        }
                    ],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        self.assertEqual(self.approval.current_nb, 0)

        # Unapprove second approver
        self.approval.unapprove_file(self.files[0], "bourgmestre")
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_id": 0,
                "pdf_files": [self.omail["reponse-salle.pdf"].UID()],
                "approval": [
                    [{"status": "p", "approved_on": None, "approved_by": None}],
                    [{"status": "w", "approved_on": None, "approved_by": None}],
                ],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        self.assertEqual(self.approval.current_nb, 0)

    def test_add_mail_files_to_session(self):
        # No files
        self.approval.remove_file_from_approval(self.files[0].UID())
        self.approval.remove_file_from_approval(self.files[1].UID())
        self.assertEqual(self.approval.add_mail_files_to_session(), (False, "No files"))

        # Not all files approved
        self.approval.add_file_to_approval(self.files[0].UID())
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.add_mail_files_to_session(), (False, "Not all files approved"))

        self.approval.annot["approval"][0][0]["status"] = "a"
        self.approval.annot["approval"][1][0]["status"] = "a"

        # Bad scan_id
        self.files[0].scan_id = "wrong"
        self.assertEqual(
            self.approval.add_mail_files_to_session(),
            (False, "Bad scan_id for file uid {}".format(self.files[0].UID())),
        )
        self.files[0].scan_id = "012999900000601"

        # Good case
        self.assertEqual(len(self.omail.values()), 2)
        self.assertNotIn("reponse-salle.pdf", self.omail)
        self.assertEqual(
            get_session_annotation(),
            {
                "numbering": 0,
                "sessions": {},
                "uids": {},
                "c_uids": {},
            },
        )
        self.assertEqual(self.approval.add_mail_files_to_session(), (True, "1 files added to session number 0"))
        self.assertEqual(len(self.omail.values()), 3)
        self.assertIn("reponse-salle.pdf", self.omail)
        pdf_file = self.omail["reponse-salle.pdf"]
        self.assertEqual(self.approval.annot["pdf_files"], [pdf_file.UID()])
        self.assertEqual(pdf_file.title, u"R\xe9ponse salle.pdf")
        self.assertTrue(pdf_file.to_sign)
        self.assertFalse(pdf_file.to_approve)
        self.assertFalse(pdf_file.approved)
        self.assertEqual(pdf_file.scan_id, "012999900000601")
        self.assertIsNone(pdf_file.scan_user)
        self.assertEqual(pdf_file.content_category, "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file")
        last_update = get_session_annotation()["sessions"][0]["last_update"]
        self.assertEqual(
            get_session_annotation(),
            {
                "sessions": {
                    0: {
                        "files": [
                            {
                                "status": "",
                                "context_uid": self.omail.UID(),
                                "scan_id": "012999900000601",
                                "uid": pdf_file.UID(),
                                "title": u"R\xe9ponse salle.pdf",
                                "filename": u"R\xe9ponse salle__{}.pdf".format(pdf_file.UID()),
                            }
                        ],
                        "discriminators": (),
                        "watchers": ["dirg@macommune.be"],
                        "title": "",
                        "state": "draft",
                        "signers": [
                            {
                                "status": "",
                                "position": u"Directeur G\xe9n\xe9ral",
                                "fullname": u"Maxime DG",
                                "userid": "dirg",
                                "email": "dirg@macommune.be",
                            },
                            {
                                "status": "",
                                "position": u"Bourgmestre",
                                "fullname": u"Paul BM",
                                "userid": "bourgmestre",
                                "email": "bourgmestre@macommune.be",
                            },
                        ],
                        "last_update": last_update,
                        "returns": [],
                        "client_id": "0129999",
                        "seal": False,
                        "sign_url": None,
                        "sign_id": None,
                        "acroform": True,
                    }
                },
                "numbering": 1,
                "uids": {pdf_file.UID(): 0},
                "c_uids": {self.omail.UID(): [pdf_file.UID()]},
            },
        )

        # Already done
        self.assertEqual(self.approval.add_mail_files_to_session(), (True, "0 files added to session number 0"))
        last_update = get_session_annotation()["sessions"][0]["last_update"]
        self.assertEqual(
            get_session_annotation(),
            {
                "sessions": {
                    0: {
                        "files": [
                            {
                                "status": "",
                                "context_uid": self.omail.UID(),
                                "scan_id": "012999900000601",
                                "uid": pdf_file.UID(),
                                "title": u"R\xe9ponse salle.pdf",
                                "filename": u"R\xe9ponse salle__{}.pdf".format(pdf_file.UID()),
                            }
                        ],
                        "discriminators": (),
                        "watchers": ["dirg@macommune.be"],
                        "title": "",
                        "state": "draft",
                        "signers": [
                            {
                                "status": "",
                                "position": u"Directeur G\xe9n\xe9ral",
                                "fullname": u"Maxime DG",
                                "userid": "dirg",
                                "email": "dirg@macommune.be",
                            },
                            {
                                "status": "",
                                "position": u"Bourgmestre",
                                "fullname": u"Paul BM",
                                "userid": "bourgmestre",
                                "email": "bourgmestre@macommune.be",
                            },
                        ],
                        "last_update": last_update,
                        "returns": [],
                        "client_id": "0129999",
                        "seal": False,
                        "sign_url": None,
                        "sign_id": None,
                        "acroform": True,
                    }
                },
                "numbering": 1,
                "uids": {pdf_file.UID(): 0},
                "c_uids": {self.omail.UID(): [pdf_file.UID()]},
            },
        )
