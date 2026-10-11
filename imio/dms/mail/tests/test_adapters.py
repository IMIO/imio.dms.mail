# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.classification.folder.interfaces import IServiceInCharge
from collective.classification.folder.interfaces import IServiceInCopy
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_person_from_userid
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.interfaces import IIconifiedInfos
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_category_object
from collective.task.behaviors import ITask
from collective.wfadaptations.api import add_applied_adaptation
from datetime import date
from datetime import datetime
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelJar
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.adapters import ActionsSubMenuItem
from imio.dms.mail.adapters import ApprovalRoleAdapter
from imio.dms.mail.adapters import AssignedUserDataManager
from imio.dms.mail.adapters import ClassificationFolderInCopyGroupCriterion
from imio.dms.mail.adapters import ClassificationFolderInTreatingGroupCriterion
from imio.dms.mail.adapters import common_marker
from imio.dms.mail.adapters import ContactAutocompleteValidator
from imio.dms.mail.adapters import creating_group_index
from imio.dms.mail.adapters import DateDataManager
from imio.dms.mail.adapters import default_criterias
from imio.dms.mail.adapters import DmsCategorizedObjectInfoAdapter
from imio.dms.mail.adapters import FactoriesSubMenuItem
from imio.dms.mail.adapters import fancy_tree_folder_index
from imio.dms.mail.adapters import get_full_title_index
from imio.dms.mail.adapters import get_obj_size
from imio.dms.mail.adapters import get_obj_size_af_index
from imio.dms.mail.adapters import get_obj_size_df_index
from imio.dms.mail.adapters import IdmSearchableExtender
from imio.dms.mail.adapters import im_irn_no_index
from imio.dms.mail.adapters import im_markers
from imio.dms.mail.adapters import im_reception_date_index
from imio.dms.mail.adapters import im_sender_email_index
from imio.dms.mail.adapters import imio_contact_source
from imio.dms.mail.adapters import IMPrettyLinkAdapter
from imio.dms.mail.adapters import in_out_date_index
from imio.dms.mail.adapters import IncomingMailFollowedCriterion
from imio.dms.mail.adapters import IncomingMailHighestValidationCriterion
from imio.dms.mail.adapters import IncomingMailInCopyGroupCriterion
from imio.dms.mail.adapters import IncomingMailInCopyGroupUnreadCriterion
from imio.dms.mail.adapters import IncomingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import IncomingMailValidationCriterion
from imio.dms.mail.adapters import ItemSignersAdapter
from imio.dms.mail.adapters import mail_date_index
from imio.dms.mail.adapters import mail_type_index
from imio.dms.mail.adapters import markers_conversion_error
from imio.dms.mail.adapters import markers_dmaf_index
from imio.dms.mail.adapters import markers_dmf_index
from imio.dms.mail.adapters import markers_im_index
from imio.dms.mail.adapters import markers_om_index
from imio.dms.mail.adapters import OdmSearchableExtender
from imio.dms.mail.adapters import om_in_out_date_index
from imio.dms.mail.adapters import om_irn_no_index
from imio.dms.mail.adapters import om_mail_date_index
from imio.dms.mail.adapters import om_markers
from imio.dms.mail.adapters import om_outgoing_date_index
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.adapters import OMPrettyLinkAdapter
from imio.dms.mail.adapters import org_sortable_title_index
from imio.dms.mail.adapters import OutgoingMailInCopyGroupCriterion
from imio.dms.mail.adapters import OutgoingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import OutgoingMailValidationCriterion
from imio.dms.mail.adapters import person_usages_index
from imio.dms.mail.adapters import ready_for_email_index
from imio.dms.mail.adapters import ScanSearchableExtender
from imio.dms.mail.adapters import send_modes_index
from imio.dms.mail.adapters import SendableAnnexesToPMAdapter
from imio.dms.mail.adapters import ServiceInChargeAdapter
from imio.dms.mail.adapters import ServiceInCopyAdapter
from imio.dms.mail.adapters import signrequest_approvings_index
from imio.dms.mail.adapters import SignRequestApprovalAdapter
from imio.dms.mail.adapters import SignRequestInCopyGroupCriterion
from imio.dms.mail.adapters import SignRequestInTreatingGroupCriterion
from imio.dms.mail.adapters import state_group_index
from imio.dms.mail.adapters import task_enquirer_index
from imio.dms.mail.adapters import TaskInAssignedGroupCriterion
from imio.dms.mail.adapters import TaskInProposingGroupCriterion
from imio.dms.mail.adapters import TaskPrettyLinkAdapter
from imio.dms.mail.adapters import TaskValidationCriterion
from imio.dms.mail.adapters import WorkflowMenu
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.content.behaviors import ISigningBehavior
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import sub_create
from imio.esign.adapters import ISignable
from imio.esign.config import set_esign_registry_file_url
from imio.esign.utils import get_session_annotation
from imio.helpers import EMPTY_DATE
from imio.helpers import EMPTY_STRING
from imio.helpers.content import get_object
from imio.helpers.test_helpers import ImioTestHelpers
from imio.helpers.tests.test_pdf import _pdf_page_count
from imio.pm.wsclient.interfaces import ISendableAnnexesToPM
from imio.prettylink.interfaces import IPrettyLink
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.contentmenu.interfaces import IContentMenuItem
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from plone.indexer.interfaces import IIndexer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import safe_unicode
from z3c.form.interfaces import IDataManager
from z3c.form.interfaces import IValidator
from z3c.relationfield.relation import RelationValue
from zope.annotation import IAnnotations
from zope.browsermenu.interfaces import IBrowserMenu
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.interfaces import RequiredMissing
from zope.security.management import endInteraction
from zope.security.management import newInteraction

import time
import unittest
import zope.event


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

    def test_SignRequestInTreatingGroupCriterion(self):
        crit = SignRequestInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"treating_groups": {"query": []}})
        api.group.create(groupname="111_demand_sign")
        api.group.add_user(groupname="111_demand_sign", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"treating_groups": {"query": ["111"]}})

    def test_SignRequestInCopyGroupCriterion(self):
        crit = SignRequestInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"recipient_groups": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"recipient_groups": {"query": ["111"]}})

    def test_approval_property(self):
        om = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om-disp")
        self.assertIsInstance(om.approval(), OMApprovalAdapter)
        request, files = create_sign_request(self.portal, oid="sr-disp", signers=[], nb_files=0)
        self.assertIsInstance(request.approval(), SignRequestApprovalAdapter)

    def test_signrequest_approvings_index(self):
        request, files = create_sign_request(self.portal, oid="sr-idx", nb_files=1)
        self.assertEqual(signrequest_approvings_index(request)(), [])
        self.portal.portal_workflow.doActionFor(request, "propose_to_approve")
        self.assertEqual(signrequest_approvings_index(request)(), ["dirg"])

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
            createContentInContainer(omail, "dmsommainfile", file=NamedBlobFile(fo.read(), filename=filename),
                                     signed=True)
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
        # a binary file is converted to text by portal_transforms
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            obj = createContentInContainer(
                imail, "dmsmainfile", id="testid3", title="title", file=NamedBlobFile(fo.read(), filename=filename)
            )
        text = ScanSearchableExtender(obj)()
        # a native string (utf8 bytes on Python 2)
        self.assertIsInstance(text, str)
        text = safe_unicode(text)
        self.assertTrue(text.startswith(u"testid3 title Commune de Belleville\n"))
        self.assertIn(u"Concerne : Votre demande de réservation de salle\n", text)
        # no transformation to text for an image
        filename = u"in-Fiche IMIO urbanisme.jpg"
        with open("%s/batchimport/toprocess/incoming-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            obj = createContentInContainer(
                imail, "dmsmainfile", id="testid4", title="title", file=NamedBlobFile(fo.read(), filename=filename)
            )
        self.assertEqual(ScanSearchableExtender(obj)(), u"testid4 title")

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
            createContentInContainer(omail, "dmsommainfile", id="testid1", scan_id="011999900000690",
                                     file=NamedBlobFile(fo.read(), filename=filename))
        self.assertEqual(ext(), u"011999900000690 IMIO011999900000690 690")
        pc = omail.portal_catalog
        rid = pc(id="my-id")[0].getRID()
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(
            index_value, ["s0010", "my", "title", "description", u"011999900000690", "imio011999900000690", u"690"]
        )
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            createContentInContainer(omail, "dmsommainfile", id="testid2", scan_id="011999900000700",
                                     file=NamedBlobFile(fo.read(), filename=filename))
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
            mail_type="courrier",
        )
        view = omail.restrictedTraverse("@@view")
        view.update()
        # the title from the vocabulary is well rendered
        self.assertIn("Courrier", view.widgets["mail_type"].render())
        # We deactivate the courrier mail type, the missing value is managed
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.omail_types
        mail_types[0]["active"] = False
        settings.omail_types = mail_types
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.OMActiveMailTypesVocabulary")
        self.assertNotIn("courrier", [t.value for t in voc_inst(omail)])
        view.updateWidgets()
        self.assertIn("Courrier", view.widgets["mail_type"].render())
        # We remove the courrier mail type, the missing value cannot be managed anymore
        settings.omail_types = settings.omail_types[1:]
        view.updateWidgets()
        self.assertNotIn("Courrier", view.widgets["mail_type"].render())
        self.assertIn("Missing", view.widgets["mail_type"].render())

    def test_IncomingMailInCopyGroupUnreadCriterion(self):
        crit = IncomingMailInCopyGroupUnreadCriterion(self.portal)
        self.assertEqual(crit.query, {"recipient_groups": {"query": []}, "labels": {"not": ["siteadmin:lu"]}})
        api.group.create(groupname="111_lecteur")
        api.group.add_user(groupname="111_lecteur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"recipient_groups": {"query": ["111"]}, "labels": {"not": ["siteadmin:lu"]}})
        # the dashboard query: a mail in copy of the agent's service, until the agent reads it
        org_uid = get_person_from_userid("agent").primary_organization
        imail = sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id", recipient_groups=[org_uid]
        )
        self.change_user("agent")
        pc = self.portal.portal_catalog
        self.assertIn(imail.UID(), [b.UID for b in pc.unrestrictedSearchResults(**crit.query)])
        ILabeling(imail).pers_update(["lu"], True)
        imail.reindexObject(idxs=["labels"])
        self.assertNotIn(imail.UID(), [b.UID for b in pc.unrestrictedSearchResults(**crit.query)])

    def test_IncomingMailFollowedCriterion(self):
        crit = IncomingMailFollowedCriterion(self.portal)
        self.assertEqual(crit.query, {"labels": {"query": "siteadmin:suivi"}})
        # the dashboard query: the mails the agent follows
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.change_user("agent")
        pc = self.portal.portal_catalog
        self.assertEqual(len(pc.unrestrictedSearchResults(**crit.query)), 0)
        ILabeling(imail).pers_update(["suivi"], True)
        imail.reindexObject(idxs=["labels"])
        self.assertEqual([b.UID for b in pc.unrestrictedSearchResults(**crit.query)], [imail.UID()])

    def test_ClassificationFolderInCopyGroupCriterion(self):
        crit = ClassificationFolderInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"recipient_groups": {"query": []}})
        api.group.create(groupname="111_editeur")
        api.group.add_user(groupname="111_editeur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"recipient_groups": {"query": ["111"]}})

    def test_ClassificationFolderInTreatingGroupCriterion(self):
        crit = ClassificationFolderInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {"treating_groups": {"query": []}})
        api.group.create(groupname="111_lecteur")
        api.group.add_user(groupname="111_lecteur", username="siteadmin")
        self.change_user("siteadmin")
        self.assertEqual(crit.query, {"treating_groups": {"query": ["111"]}})

    def test_ActionsSubMenuItem(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        item = getMultiAdapter((imail, self.portal.REQUEST), IContentMenuItem, name="plone.contentmenu.actions")
        self.assertIsInstance(item, ActionsSubMenuItem)
        self.assertTrue(item.available())
        # only shown to users with "Manage portal"
        self.change_user("agent")
        item = getMultiAdapter((imail, self.portal.REQUEST), IContentMenuItem, name="plone.contentmenu.actions")
        self.assertFalse(item.available())

    def test_FactoriesSubMenuItem(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        item = getMultiAdapter((imail, self.portal.REQUEST), IContentMenuItem, name="plone.contentmenu.factories")
        self.assertIsInstance(item, FactoriesSubMenuItem)
        self.assertTrue(item.available())
        # only shown to users with "Manage portal"
        self.change_user("agent")
        item = getMultiAdapter((imail, self.portal.REQUEST), IContentMenuItem, name="plone.contentmenu.factories")
        self.assertFalse(item.available())

    def test_WorkflowMenu(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        menu = getUtility(IBrowserMenu, name="plone_contentmenu_workflow")
        self.assertIsInstance(menu, WorkflowMenu)
        self.assertEqual(
            [item["extra"]["id"] for item in menu.getMenuItems(imail, self.portal.REQUEST)],
            [
                "workflow-transition-propose_to_agent",
                "workflow-transition-propose_to_manager",
                "workflow-transition-advanced",
            ],
        )
        # only shown to users with "Manage portal"
        self.change_user("dirg")
        self.assertEqual(menu.getMenuItems(imail, self.portal.REQUEST), [])

    def test_IMPrettyLinkAdapter(self):
        dguid = self.pgof["direction-generale"].UID()
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            title=u"My title",
            treating_groups=dguid,
            assigned_user=u"chef",
        )
        adapter = IPrettyLink(imail)
        self.assertIsInstance(adapter, IMPrettyLinkAdapter)
        self.assertEqual(adapter._leadingIcons(), [])
        # a remark is only shown in the configured states (proposed_to_agent)
        imail.task_description = RichTextValue(u"<p>Remarque</p>", "text/html", "text/x-html-safe")
        self.assertEqual(adapter._leadingIcons(), [])
        api.content.transition(obj=imail, to_state="proposed_to_manager")
        api.content.transition(obj=imail, to_state="proposed_to_agent")
        self.assertEqual([icon for icon, title in adapter._leadingIcons()], ["++resource++imio.dms.mail/remark.gif"])
        # a back transition
        api.content.transition(obj=imail, transition="back_to_manager")
        self.assertEqual([icon for icon, title in adapter._leadingIcons()], ["++resource++imio.dms.mail/wf_back.png"])
        # an outgoing mail replies to it
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail.reply_to = [RelationValue(getUtility(IIntIds).getId(imail))]
        modified(omail)
        self.assertEqual(
            [icon for icon, title in adapter._leadingIcons()],
            ["++resource++imio.dms.mail/wf_back.png", "++resource++imio.dms.mail/replied_icon.png"],
        )

    def test_OMPrettyLinkAdapter(self):
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title=u"My title",
            treating_groups=self.pgof["direction-generale"]["secretariat"].UID(),
        )
        adapter = IPrettyLink(omail)
        self.assertIsInstance(adapter, OMPrettyLinkAdapter)
        self.assertEqual(adapter._leadingIcons(), [])
        omail.task_description = RichTextValue(u"<p>Remarque</p>", "text/html", "text/x-html-safe")
        self.assertEqual(adapter._leadingIcons(), [])
        # a remark is only shown in the configured states
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states",
                                       ["created"])
        self.assertEqual([icon for icon, title in adapter._leadingIcons()], ["++resource++imio.dms.mail/remark.gif"])
        # a back transition
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=omail, transition="mark_as_sent")
            api.content.transition(obj=omail, transition="back_to_creation")
        self.assertEqual(
            [icon for icon, title in adapter._leadingIcons()],
            ["++resource++imio.dms.mail/remark.gif", "++resource++imio.dms.mail/wf_back.png"],
        )

    def test_TaskPrettyLinkAdapter(self):
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        adapter = IPrettyLink(task)
        self.assertIsInstance(adapter, TaskPrettyLinkAdapter)
        self.assertEqual(adapter._leadingIcons(), [])
        api.content.transition(obj=task, transition="do_to_assign")  # automatically to to_do
        self.assertEqual(api.content.get_state(task), "to_do")
        self.assertEqual(adapter._leadingIcons(), [])
        api.content.transition(obj=task, transition="back_in_created2")
        self.assertEqual([icon for icon, title in adapter._leadingIcons()], ["++resource++imio.dms.mail/wf_back.png"])
        # to_do again
        api.content.transition(obj=task, transition="do_to_assign")
        self.assertEqual([icon for icon, title in adapter._leadingIcons()], ["++resource++imio.dms.mail/wf_again.png"])

    def test_person_usages_index(self):
        pf = self.portal["contacts"]["personnel-folder"]
        self.assertEqual(person_usages_index(pf["dirg"])(), ["signer"])
        self.assertEqual(person_usages_index(pf["chef"])(), ["approving"])
        self.assertIs(person_usages_index(pf["agent"])(), common_marker)
        pc = self.portal.portal_catalog
        self.assertEqual(
            sorted(b.id for b in pc.unrestrictedSearchResults(portal_type="person", usages="signer")),
            ["bourgmestre", "dirg"],
        )

    def test_creating_group_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertIs(creating_group_index(imail)(), common_marker)
        org_uid = self.pgof["direction-generale"].UID()
        imail.creating_group = org_uid
        self.assertEqual(creating_group_index(imail)(), org_uid)

    def test_om_sender_email_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail.orig_sender_email = u'"Dexter Morgan" <dexter.morgan@mpd.am>'
        omail.reindexObject(idxs=["email"])
        pc = self.portal.portal_catalog
        self.assertEqual(
            [b.UID for b in pc.unrestrictedSearchResults(portal_type="dmsoutgoingmail", email="dexter.morgan@mpd.am")],
            [omail.UID()],
        )

    def test_fancy_tree_folder_index(self):
        om_folder = self.portal["templates"]["om"]
        folder_uid = self.pgof["direction-generale"]["secretariat"].UID()
        self.assertFalse(fancy_tree_folder_index(om_folder)())
        self.assertTrue(fancy_tree_folder_index(om_folder[folder_uid])())
        self.assertFalse(fancy_tree_folder_index(self.portal["Members"])())
        pc = self.portal.portal_catalog
        self.assertIn(
            om_folder[folder_uid].UID(),
            [b.UID for b in pc.unrestrictedSearchResults(path="/".join(om_folder.getPhysicalPath()), enabled=True)],
        )

    def test_get_full_title_index(self):
        imail = sub_create(
            self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id", title=u"Réponse à l'été"
        )
        value = get_full_title_index(imail)()
        # a native string (utf8 bytes on Python 2), json serialized by the classification folder autocomplete
        self.assertIsInstance(value, str)
        self.assertEqual(safe_unicode(value), u"Réponse à l'été")
        brain = self.portal.portal_catalog.unrestrictedSearchResults(UID=imail.UID())[0]
        self.assertEqual(safe_unicode(brain.get_full_title), u"Réponse à l'été")
        imail.title = u""
        self.assertIs(get_full_title_index(imail)(), common_marker)

    def test_get_obj_size(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        for i, (size, expected) in enumerate(
            ((10, "1 KB"), (1024, "1.0 KB"), (5000, "4.9 KB"), (2 * 1048576 + 300000, "2.3 MB"))
        ):
            dfile = createContentInContainer(
                imail, "dmsmainfile", id="f%d" % i, file=NamedBlobFile(b"x" * size, filename=u"f.bin")
            )
            self.assertEqual(get_obj_size(dfile), expected)

    def test_get_obj_size_af_index(self):
        request, files = create_sign_request(self.portal, oid="sr-size", nb_files=1)
        self.assertEqual(get_obj_size_af_index(files[0])(), "108.4 KB")
        brain = self.portal.portal_catalog.unrestrictedSearchResults(UID=files[0].UID())[0]
        self.assertEqual(brain.getObjSize, "108.4 KB")

    def test_get_obj_size_df_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        dfile = [obj for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"][0]
        self.assertEqual(get_obj_size_df_index(dfile)(), "275.4 KB")
        brain = self.portal.portal_catalog.unrestrictedSearchResults(UID=dfile.UID())[0]
        self.assertEqual(brain.getObjSize, "275.4 KB")

    def test_in_out_date_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(in_out_date_index(imail)(), imail.reception_date)
        imail.reception_date = None
        self.assertEqual(in_out_date_index(imail)(), EMPTY_DATE)

    def test_om_in_out_date_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertEqual(om_in_out_date_index(omail)(), EMPTY_DATE)
        omail.outgoing_date = datetime(2024, 1, 2, 10, 20)
        self.assertEqual(om_in_out_date_index(omail)(), datetime(2024, 1, 2, 10, 20))

    def test_im_irn_no_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertTrue(imail.internal_reference_no)
        self.assertIs(im_irn_no_index(imail)(), common_marker)

    def test_om_irn_no_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertTrue(omail.internal_reference_no)
        self.assertIs(om_irn_no_index(omail)(), common_marker)

    def test_mail_date_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(mail_date_index(imail)(), EMPTY_DATE)
        imail.original_mail_date = date(2024, 1, 2)
        self.assertEqual(mail_date_index(imail)(), date(2024, 1, 2))

    def test_om_mail_date_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertEqual(om_mail_date_index(omail)(), omail.mail_date)
        self.assertTrue(omail.mail_date)
        omail.mail_date = None
        self.assertEqual(om_mail_date_index(omail)(), EMPTY_DATE)

    def test_mail_type_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(mail_type_index(imail)(), "courrier")
        self.assertIs(mail_type_index(self.portal["Members"])(), common_marker)
        pc = self.portal.portal_catalog
        brains = pc.unrestrictedSearchResults(portal_type="dmsincomingmail", mail_type="courrier")
        self.assertIn(imail.UID(), [b.UID for b in brains])

    def test_task_enquirer_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        task = imail["tache1"]
        self.assertEqual(task_enquirer_index(task)(), imail.treating_groups)
        task.enquirer = None
        self.assertIs(task_enquirer_index(task)(), common_marker)

    def test_im_markers(self):
        intids = getUtility(IIntIds)
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(im_markers(imail), [])
        self.assertEqual(IAnnotations(imail)["dmsmail.markers"], [])
        # an incoming mail linked to it is not a response
        imail2 = get_object(oid="courrier2", ptype="dmsincomingmail")
        imail2.reply_to = [RelationValue(intids.getId(imail))]
        modified(imail2)
        self.assertEqual(im_markers(imail), [])
        # an outgoing mail replying to it
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail.reply_to = [RelationValue(intids.getId(imail))]
        modified(omail)
        self.assertEqual(im_markers(imail), ["hasResponse"])
        self.assertEqual(IAnnotations(imail)["dmsmail.markers"], ["hasResponse"])

    def test_markers_im_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(markers_im_index(imail)(), [])
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail.reply_to = [RelationValue(getUtility(IIntIds).getId(imail))]
        modified(omail)
        self.assertEqual(markers_im_index(imail)(), ["hasResponse"])
        pc = self.portal.portal_catalog
        self.assertEqual([b.UID for b in pc.unrestrictedSearchResults(markers="hasResponse")], [imail.UID()])

    def test_om_markers(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertEqual(om_markers(omail), ["lastDmsFileIsOdt"])
        self.assertEqual(IAnnotations(omail)["dmsmail.markers"], ["lastDmsFileIsOdt"])
        omail.email_status = u"sent"
        self.assertEqual(om_markers(omail), ["lastDmsFileIsOdt", "emailSent"])
        # the last main file is not an odt
        createContentInContainer(omail, "dmsommainfile", id="2", file=NamedBlobFile(b"text", filename=u"scan.txt"))
        self.assertEqual(om_markers(omail), ["emailSent"])
        new_omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "my-id")
        self.assertEqual(om_markers(new_omail), [])

    def test_markers_om_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertEqual(markers_om_index(omail)(), ["lastDmsFileIsOdt"])
        pc = self.portal.portal_catalog
        self.assertIn(omail.UID(), [b.UID for b in pc.unrestrictedSearchResults(markers="lastDmsFileIsOdt")])

    def test_markers_conversion_error(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        dfile = [obj for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"][0]
        self.assertEqual(markers_conversion_error(dfile), [])
        self.assertEqual(IAnnotations(dfile)["dmsmail.markers"], [])
        # documentviewer conversion error
        IAnnotations(dfile)["collective.documentviewer"] = PersistentMapping({"last_updated": "2050-01-01T00:00:00"})
        self.assertEqual(markers_conversion_error(dfile), ["dvConvError"])
        self.assertEqual(IAnnotations(dfile)["dmsmail.markers"], ["dvConvError"])
        # an eml file cannot be converted
        eml = createContentInContainer(
            imail, "dmsappendixfile", id="eml", file=NamedBlobFile(b"Subject: test", filename=u"message.eml")
        )
        self.assertEqual(markers_conversion_error(eml), ["dvConvError"])

    def test_markers_dmf_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        dfile = [obj for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"][0]
        self.assertEqual(markers_dmf_index(dfile)(), [])
        eml = createContentInContainer(
            imail, "dmsmainfile", id="eml", file=NamedBlobFile(b"Subject: test", filename=u"message.eml")
        )
        self.assertEqual(markers_dmf_index(eml)(), ["dvConvError"])
        pc = self.portal.portal_catalog
        self.assertEqual([b.UID for b in pc.unrestrictedSearchResults(markers="dvConvError")], [eml.UID()])

    def test_markers_dmaf_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        eml = createContentInContainer(
            imail, "dmsappendixfile", id="eml", file=NamedBlobFile(b"Subject: test", filename=u"message.eml")
        )
        self.assertEqual(markers_dmaf_index(eml)(), ["dvConvError"])
        pc = self.portal.portal_catalog
        self.assertEqual([b.UID for b in pc.unrestrictedSearchResults(markers="dvConvError")], [eml.UID()])

    def test_im_reception_date_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        imail.reception_date = datetime(2024, 1, 2, 10, 20)
        self.assertEqual(im_reception_date_index(imail)(), int(time.mktime((2024, 1, 2, 10, 20, 0, 1, 2, -1))))
        imail.reception_date = None
        self.assertEqual(im_reception_date_index(imail)(), 0)

    def test_om_outgoing_date_index(self):
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertEqual(om_outgoing_date_index(omail)(), 0)
        omail.outgoing_date = datetime(2024, 1, 2, 10, 20)
        self.assertEqual(om_outgoing_date_index(omail)(), int(time.mktime((2024, 1, 2, 10, 20, 0, 1, 2, -1))))

    def test_task_state_group_index(self):
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        pc = self.portal.portal_catalog
        # task_state_group_index returns the state_group_index indexer, called by the catalog
        self.assertEqual(len(pc.unrestrictedSearchResults(UID=task.UID(), state_group="created")), 1)
        api.content.transition(obj=task, transition="do_to_assign")  # automatically to to_do
        task.reindexObject(idxs=["state_group"])
        self.assertEqual(len(pc.unrestrictedSearchResults(UID=task.UID(), state_group="to_do")), 1)
        # validation at service level
        dguid = self.pgof["direction-generale"].UID()
        task.assigned_group = dguid
        set_dms_config(
            ["review_states", "task"], OrderedDict([("to_do", {"group": "_n_plus_1", "org": "assigned_group"})])
        )
        task.reindexObject(idxs=["state_group"])
        self.assertEqual(len(pc.unrestrictedSearchResults(UID=task.UID(), state_group="to_do,%s" % dguid)), 1)

    def test_send_modes_index(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(send_modes_index(imail)(), ["post"])
        pc = self.portal.portal_catalog
        self.assertIn(imail.UID(), [b.UID for b in pc.unrestrictedSearchResults(Subject="post")])
        imail.send_modes = []
        self.assertIs(send_modes_index(imail)(), common_marker)

    def test_imio_contact_source(self):
        pc = self.portal.portal_catalog
        # the registered metadata indexer
        indexer = getMultiAdapter((self.portal["contacts"]["electrabel"], pc), IIndexer, name="contact_source")
        self.assertEqual(indexer(), u"Electrabel ⏺ 1, Rue de l'électron, 0020, E-ville ⏺ contak@electrabel.eb")
        # empty address parts are cleaned
        org = api.content.create(container=self.portal["contacts"], type="organization", id="org", title=u"Org")
        self.assertEqual(imio_contact_source(org)(), u"Org ⏺  ⏺")
        org.email = u"org@macommune.be"
        self.assertEqual(imio_contact_source(org)(), u"Org ⏺  ⏺ org@macommune.be")

    def test_labels(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        pc = self.portal.portal_catalog
        indexer = getMultiAdapter((imail, pc), IIndexer, name="labels")
        self.assertEqual(indexer(), ["_", EMPTY_STRING])
        # a personal label
        self.change_user("agent")
        ILabeling(imail).pers_update(["lu"], True)
        self.assertEqual(indexer(), ["lu", "agent:lu", EMPTY_STRING])
        # a global label
        ILabelJar(self.portal["incoming-mail"]).add("Urgent", "red", False)
        ILabeling(imail).update(["urgent"])
        self.assertEqual(sorted(indexer()), ["agent:lu", "lu", "urgent"])
        imail.reindexObject(idxs=["labels"])
        self.assertEqual([b.UID for b in pc.unrestrictedSearchResults(labels="agent:lu")], [imail.UID()])

    def test_ContactAutocompleteValidator(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        # the contact widget checks the View permission of the selected contacts, as in a published request
        newInteraction()
        self.addCleanup(endInteraction)
        view = imail.restrictedTraverse("@@edit")
        view.update()
        form = view.form_instance
        widget = form.widgets["sender"]
        validator = getMultiAdapter((imail, self.portal.REQUEST, form, widget.field, widget), IValidator)
        self.assertIsInstance(validator, ContactAutocompleteValidator)
        # a contact is accepted
        self.assertIsNone(validator.validate([rel.to_object for rel in imail.sender]))
        # an empty value is always validated: the required sender is enforced
        self.assertRaises(RequiredMissing, validator.validate, None)
        self.assertRaises(RequiredMissing, validator.validate, [])

    def test_DateDataManager(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        dm = getMultiAdapter((imail, IImioDmsIncomingMail["reception_date"]), IDataManager)
        self.assertIsInstance(dm, DateDataManager)
        dm.set(None)
        self.assertIsNone(imail.reception_date)
        dm.set(datetime(2024, 1, 2, 10, 20, 33))
        self.assertEqual(imail.reception_date, datetime(2024, 1, 2, 10, 20, 33))
        # the form gives minutes: the stored value is kept if the minute is the same
        dm.set(datetime(2024, 1, 2, 10, 20))
        self.assertEqual(imail.reception_date, datetime(2024, 1, 2, 10, 20, 33))
        # the stored seconds are kept on a new value
        dm.set(datetime(2024, 1, 2, 11, 5))
        self.assertEqual(imail.reception_date, datetime(2024, 1, 2, 11, 5, 33))

    def test_AssignedUserDataManager(self):
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        dm = getMultiAdapter((imail, ITask["assigned_user"]), IDataManager)
        self.assertIsInstance(dm, AssignedUserDataManager)
        self.assertIsNone(dm.query())
        # the default assigned user given by the treating group master select
        self.portal.REQUEST.set("_default_assigned_user_", "agent")
        self.addCleanup(self.portal.REQUEST.other.pop, "_default_assigned_user_", None)
        self.assertEqual(dm.query(), "agent")
        imail.assigned_user = "chef"
        self.assertEqual(dm.query(), "chef")

    def test_ServiceInChargeAdapter(self):
        adapter = IServiceInCharge(self.portal["folders"])
        self.assertIsInstance(adapter, ServiceInChargeAdapter)
        self.assertEqual(sorted(t.value for t in adapter()), sorted(get_registry_organizations()))

    def test_ServiceInCopyAdapter(self):
        adapter = IServiceInCopy(self.portal["folders"])
        self.assertIsInstance(adapter, ServiceInCopyAdapter)
        self.assertEqual(sorted(t.value for t in adapter()), sorted(get_registry_organizations()))

    def test_SendableAnnexesToPMAdapter(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        dfile = [obj for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"][0]
        annex = createContentInContainer(
            imail, "dmsappendixfile", id="annex", title=u"Annexe é", file=NamedBlobFile(b"text", filename=u"a.txt")
        )
        adapter = ISendableAnnexesToPM(imail)
        self.assertIsInstance(adapter, SendableAnnexesToPMAdapter)
        # tasks are not sent
        self.assertEqual(
            list(adapter.get()),
            [{"title": dfile.title, "UID": dfile.UID()}, {"title": u"Annexe é", "UID": annex.UID()}],
        )

    def test_DmsCategorizedObjectInfoAdapter(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        dfile = [obj for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"][0]
        adapter = IIconifiedInfos(dfile)
        self.assertIsInstance(adapter, DmsCategorizedObjectInfoAdapter)
        infos = adapter.get_infos(get_category_object(dfile, dfile.content_category))
        self.assertEqual(infos["scan_id"], "010999900000001")
        self.assertIsNone(infos["conv_from_uid"])
        self.assertFalse(infos["esigned"])
        # infos stored on the mail, used by the files table
        self.assertEqual(imail.categorized_elements[dfile.UID()]["scan_id"], "010999900000001")


class TestOMApprovalAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pw = self.portal.portal_workflow
        self.change_user("admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        # Create outgoing mail with two eSign signers and two files to approve
        intids = getUtility(IIntIds)
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.pf = self.portal["contacts"]["personnel-folder"]
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "courrier",
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [],
                "current_nb": None,
                "approvers": [],
                "session_ids": [],
                "pdf_files": [],
                "approval": [],
                "editors": [],
                "signers": [],
            },
        )

    def test_files_uids(self):
        self.assertEqual(self.approval.files_uids, [self.files[0].UID(), self.files[1].UID()])

    def test_signers(self):
        self.assertEqual(self.approval.signers, ["dirg", "bourgmestre"])

    def test_signers_details(self):
        self.assertEqual(
            self.approval.signers_details, [(0, u"Maxime DG", u"Directeur Général"), (1, u"Paul BM", u"Bourgmestre")]
        )

    def test_approvers(self):
        # built from a set: no order
        self.assertEqual(sorted(self.approval.approvers), ["bourgmestre", "chef", "dirg"])

    def test_calculate_current_nb(self):
        # None, no approval session started
        self.assertIsNone(self.approval.calculate_current_nb())
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.calculate_current_nb(), 0)
        self.approval.approve_file(self.files[0], "dirg")
        self.approval.approve_file(self.files[1], "dirg")
        self.assertEqual(self.approval.calculate_current_nb(), 1)
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.approval.approve_file(self.files[1], "bourgmestre")
        # -1, all approvers have approved
        self.assertEqual(self.approval.calculate_current_nb(), -1)
        # None, no file to approve
        self.approval.reset()
        self.assertIsNone(self.approval.calculate_current_nb())

    def test_is_state_before_approve(self):
        self.assertTrue(self.approval.is_state_before_approve())  # created
        self.assertFalse(self.approval.is_state_before_approve("to_approve"))
        self.assertFalse(self.approval.is_state_before_approve("to_print"))
        self.assertFalse(self.approval.is_state_before_approve("sent"))

    def test_is_state_before_or_approve(self):
        self.assertTrue(self.approval.is_state_before_or_approve())  # created
        self.assertTrue(self.approval.is_state_before_or_approve("to_approve"))
        self.assertFalse(self.approval.is_state_before_or_approve("to_be_signed"))
        self.assertFalse(self.approval.is_state_before_or_approve("sent"))

    def test_is_state_after_approve(self):
        self.assertFalse(self.approval.is_state_after_approve())  # created
        self.assertFalse(self.approval.is_state_after_approve("to_approve"))
        self.assertTrue(self.approval.is_state_after_approve("to_print"))
        self.assertTrue(self.approval.is_state_after_approve("signed"))

    def test_is_state_after_or_approve(self):
        self.assertFalse(self.approval.is_state_after_or_approve())  # created
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertTrue(self.approval.is_state_after_or_approve())  # to_approve
        self.assertTrue(self.approval.is_state_after_or_approve("sent"))

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
        self.approval.start_approval_process()
        self.assertEqual(self.approval.roles, {})
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.roles, {"dirg": ("Reader", "Reviewer", "Editor")})
        self.approval.approve_file(self.files[0], "dirg")
        self.approval.approve_file(self.files[1], "dirg")

        # Second approvers
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader", "Reviewer"), "chef": ("Reader", "Reviewer"),
                                  "dirg": ("Reader",)}
        )
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.approval.approve_file(self.files[1], "bourgmestre")

        # Approval process finished
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader",), "chef": ("Reader",), "dirg": ("Reader",)}
        )

    def test_roles2(self):
        self.omail.signers = [
            {
                "number": 1,
                "signer": self.pf["bourgmestre"]["bourgmestre"].UID(),
                "approvings": [u"_themself_"],
                "editor": True,
            },
            {
                "number": 2,
                "signer": self.pf["dirg"]["directeur-general"].UID(),
                "approvings": [self.pf["chef"].UID()],
                "editor": False,
            },
        ]
        zope.event.notify(ObjectModifiedEvent(self.omail, Attributes(ISigningBehavior, "ISigningBehavior.signers")))

        # Empty, no approval session started
        self.assertEqual(self.approval.roles, {})

        # First approver
        self.approval.start_approval_process()
        self.assertEqual(self.approval.roles, {})
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.roles, {"bourgmestre": ("Reader", "Reviewer", "Editor")})
        self.approval.approve_file(self.files[0], "bourgmestre")
        self.approval.approve_file(self.files[1], "bourgmestre")

        # Second approvers and signer
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader",), "chef": ("Reader", "Reviewer"),
                                  "dirg": ("Reader", "Reviewer")}
        )
        self.approval.approve_file(self.files[0], "chef")
        self.approval.approve_file(self.files[1], "chef")

        # Approval process finished
        self.assertEqual(
            self.approval.roles, {"bourgmestre": ("Reader",), "chef": ("Reader",), "dirg": ("Reader",)}
        )

    def test_start_approval_process(self):
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
        self.approval.start_approval_process()
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
        self.approval.start_approval_process()
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
        self.approval.start_approval_process()
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
        self.approval.start_approval_process()
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
        self.approval.start_approval_process()
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[]],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[]],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID(), self.files[0].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[1].UID(), self.files[0].UID()],
                "current_nb": None,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.approval.start_approval_process()
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": 1,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [],
                "pdf_files": [[], []],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID(), self.files[1].UID()],
                "current_nb": -1,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [0],
                "pdf_files": [[self.omail["file0"].UID()], [self.omail["file1"].UID()]],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "current_nb": -1,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [0],
                "pdf_files": [[self.files[0].UID()]],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [0],
                "pdf_files": [[self.files[0].UID()]],
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
        self.assertEqual(self.approval.annot["current_nb"], self.approval.calculate_current_nb())
        self.assertEqual(
            self.approval.annot,
            {
                "files": [self.files[0].UID()],
                "current_nb": 0,
                "approvers": [["dirg"], ["bourgmestre", "chef"]],
                "session_ids": [0],
                "pdf_files": [[self.files[0].UID()]],
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

        # generate from model
        view = self.omail.restrictedTraverse("persistent-document-generation")
        view.pod_template = self.portal["templates"]["om"]["main"]
        view.output_format = "odt"
        doc = view.generate_persistent_doc(view.pod_template, view.output_format)

        # Not all files approved
        self.approval.add_file_to_approval(doc.UID())
        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.assertEqual(self.approval.add_mail_files_to_session(), (False, "Not all files approved"))

        self.approval.annot["approval"][0][0]["status"] = "a"
        self.approval.annot["approval"][1][0]["status"] = "a"

        orig_scanid = doc.scan_id
        # Bad scan_id
        doc.scan_id = "wrong"
        self.assertEqual(
            self.approval.add_mail_files_to_session(),
            (False, "Bad scan_id for file uid ${uid}"),
        )
        doc.scan_id = orig_scanid

        # Good case
        self.assertEqual(len(self.omail.values()), 3)
        self.assertIn(orig_scanid, self.omail)
        self.assertEqual(
            get_session_annotation(),
            {
                "numbering": 0,
                "sessions": {},
                "uids": {},
                "c_uids": {},
            },
        )
        self.assertEqual(self.approval.add_mail_files_to_session(),
                         (True, "${count} file(s) added to session(s) ${session_ids}"))
        self.assertEqual(len(self.omail.values()), 4)
        self.assertIn("modele-de-base-s0010-courrier-sortant-test.pdf", self.omail)
        pdf_file = self.omail["modele-de-base-s0010-courrier-sortant-test.pdf"]
        self.assertEqual(self.approval.annot["pdf_files"], [[pdf_file.UID()]])
        self.assertEqual(pdf_file.title, u"Modele de base S0010 Courrier sortant test.pdf")
        self.assertTrue(pdf_file.to_sign)
        self.assertFalse(pdf_file.to_approve)
        self.assertFalse(pdf_file.approved)
        self.assertEqual(pdf_file.scan_id, orig_scanid)
        self.assertIsNone(pdf_file.scan_user)
        self.assertEqual(pdf_file.content_category, "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file")
        self.assertEqual(pdf_file.conv_from_uid, doc.UID())
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
                                "scan_id": orig_scanid,
                                "uid": pdf_file.UID(),
                                "title": u"Modele de base S0010 Courrier sortant test.pdf",
                                "filename": u"Modele de base S0010 Courrier sortant test__{}.pdf".format(
                                    pdf_file.UID()),
                            }
                        ],
                        "discriminators": ("dmsoutgoingmail",),
                        "watchers": [],
                        "title": u'[iA.Docs] Courrier sortant - 012999900000',
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
                        "sign_id": "012999900000",
                        "size": pdf_file.file.size,
                        "acroform": True,
                    }
                },
                "numbering": 1,
                "uids": {pdf_file.UID(): 0},
                "c_uids": {self.omail.UID(): [pdf_file.UID()]},
            },
        )
        self.assertEqual(len(self.approval.session_ids), 1)
        self.assertEqual(self.approval.session_ids[0], 0)

        # Already done
        self.assertEqual(self.approval.add_mail_files_to_session(),
                         (True, "${count} file(s) added to session(s) ${session_ids}"))
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
                                "scan_id": orig_scanid,
                                "uid": pdf_file.UID(),
                                "title": u"Modele de base S0010 Courrier sortant test.pdf",
                                "filename": u"Modele de base S0010 Courrier sortant test__{}.pdf".format(
                                    pdf_file.UID()),
                            }
                        ],
                        "discriminators": ("dmsoutgoingmail",),
                        "watchers": [],
                        "title": u'[iA.Docs] Courrier sortant - 012999900000',
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
                        "sign_id": "012999900000",
                        "size": pdf_file.file.size,
                        "acroform": True,
                    }
                },
                "numbering": 1,
                "uids": {pdf_file.UID(): 0},
                "c_uids": {self.omail.UID(): [pdf_file.UID()]},
            },
        )

    def test_create_pdf_file_from_pdf(self):
        """Through the esignature process, a PDF file gets a QR barcode page appended."""

        # Replace existing ODT files with a PDF file in the approval process
        self.approval.remove_file_from_approval(self.files[0].UID())
        self.approval.remove_file_from_approval(self.files[1].UID())
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/tests/files/example.pdf" % PRODUCT_DIR, "rb") as fo:
            pdf_data = fo.read()
        pdf_fobj = createContentInContainer(
            self.omail,
            "dmsommainfile",
            id="pdffile",
            scan_id="012999900000601",
            file=NamedBlobFile(pdf_data, filename=u"example.pdf"),
            content_category=calculate_category_id(ct),
        )

        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.approval.approve_file(pdf_fobj, "dirg")
        self.approval.approve_file(pdf_fobj, "bourgmestre")

        # 2 ODT originals + 1 PDF original and merged PDF
        self.assertEqual(len(list(self.omail.objectIds())), 3)

        # Locate the created PDF via the approval annotation
        new_uid = self.approval.annot["pdf_files"][0][0]
        self.assertEqual(new_uid, pdf_fobj.UID())  # PDF original != merged PDF

        pdf_file = pdf_fobj
        # Check page count: 6 pages (example.pdf) + 1 barcode page = 7
        page_count = _pdf_page_count(pdf_file.file.data)
        self.assertEqual(page_count, 7)

        # Check all required attributes
        self.assertTrue(pdf_file.to_sign)
        self.assertFalse(pdf_file.signed)
        self.assertTrue(pdf_file.to_approve)
        self.assertTrue(pdf_file.approved)
        self.assertFalse(pdf_file.to_print)
        self.assertEqual(pdf_file.content_category, "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file")
        self.assertFalse(hasattr(pdf_file, "conv_from_uid"))

    def test_create_pdf_file_from_odt(self):
        """Through the esignature process, a real ODT file is embedded
        with the download code bar template then converted to PDF."""

        # Keep self.files[0] (ODT) in approval; remove file1
        self.approval.remove_file_from_approval(self.files[1].UID())

        self.pw.doActionFor(self.omail, "propose_to_approve")
        self.approval.approve_file(self.files[0], "dirg")
        self.approval.approve_file(self.files[0], "bourgmestre")

        # 2 ODT originals but the first one has been converted
        self.assertEqual(len(list(self.omail.objectIds())), 2)
        self.assertTrue(self.files[0].file.filename.endswith(u".pdf"))
        self.assertTrue(self.files[1].file.filename.endswith(u".odt"))
        pdf_file = self.files[0]

        # Check page count: at least one page produced by the conversion
        page_count = _pdf_page_count(pdf_file.file.data)
        self.assertGreaterEqual(page_count, 1)

        # Check all required attributes
        self.assertTrue(pdf_file.to_sign)
        self.assertFalse(pdf_file.signed)
        self.assertTrue(pdf_file.to_approve)
        self.assertTrue(pdf_file.approved)
        self.assertFalse(pdf_file.to_print)
        self.assertFalse(self.files[1].to_print)
        self.assertEqual(pdf_file.content_category, "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file")
        self.assertFalse(hasattr(pdf_file, "conv_from_uid"))

    def test_create_pdf_file_from_doc(self):
        """Through the esignature process, a DOC file is converted to PDF
        with a QR barcode page appended."""

        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_esign_formats",
            ["odt", "pdf", "doc"],
        )

        try:
            # Remove existing ODT files from approval, then add a DOC file
            self.approval.remove_file_from_approval(self.files[0].UID())
            self.approval.remove_file_from_approval(self.files[1].UID())
            ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
            with open("%s/batchimport/toprocess/incoming-mail/in-courrier4.doc" % PRODUCT_DIR, "rb") as fo:
                doc_data = fo.read()
            doc_fobj = createContentInContainer(
                self.omail,
                "dmsommainfile",
                id="docfile",
                scan_id="012999900000601",
                file=NamedBlobFile(doc_data, contentType="application/msword", filename=u"in-courrier4.doc"),
                content_category=calculate_category_id(ct),
            )

            self.pw.doActionFor(self.omail, "propose_to_approve")
            # Signer 0 (dirg) approves — no session creation yet
            self.approval.approve_file(doc_fobj, "dirg")
            # Signer 1 (bourgmestre) approves — triggers add_mail_files_to_session()
            self.approval.approve_file(doc_fobj, "bourgmestre")
        finally:
            api.portal.set_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_esign_formats",
                ["odt", "pdf"],
            )

        # 2 ODT originals + 1 converted PDF tahts replaces doc
        self.assertEqual(len(list(self.omail.objectIds())), 3)

        # At least 1 converted content page + 1 barcode page
        pdf_file = self.omail.values()[-1]
        self.assertTrue(pdf_file.file.filename.endswith(".pdf"))
        page_count = _pdf_page_count(pdf_file.file.data)
        self.assertGreaterEqual(page_count, 2)

        # Check all required attributes
        self.assertTrue(pdf_file.to_sign)
        self.assertFalse(pdf_file.signed)
        self.assertTrue(pdf_file.to_approve)
        self.assertTrue(pdf_file.approved)
        self.assertFalse(pdf_file.to_print)
        self.assertEqual(pdf_file.content_category, "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file")
        self.assertFalse(hasattr(pdf_file, "conv_from_uid"))


class TestSignRequestApprovalAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pw = self.portal.portal_workflow
        self.change_user("admin")
        # sign_request with two signers (dirg then bourgmestre) and two files to approve
        self.request, self.files = create_sign_request(self.portal, oid="sr", nb_files=2)
        self.approval = SignRequestApprovalAdapter(self.request)

    def test_after_approval_states(self):
        self.assertEqual(self.approval.after_approval_states, ("to_be_signed", "signed", "closed"))

    def test_is_state_after_or_approve(self):
        self.assertFalse(self.approval.is_state_after_or_approve())  # created
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertTrue(self.approval.is_state_after_or_approve())  # to_approve

    def test_start_approval_process(self):
        self.assertIsNone(self.approval.current_nb)
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(self.approval.current_nb, 0)
        self.assertEqual([level[0]["status"] for level in self.approval.annot["approval"]], ["p", "w"])

    def test_approve_file(self):
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(self.approval.current_nb, 0)
        for afile in self.files:
            self.approval.approve_file(afile, "dirg")
        self.assertEqual(self.approval.current_nb, 1)
        for afile in self.files:
            self.approval.approve_file(afile, "bourgmestre")
        self.assertEqual(self.approval.current_nb, -1)

    def test_roles(self):
        self.assertEqual(self.approval.roles, {})
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(self.approval.roles, {"dirg": ("Reader", "Reviewer", "Editor")})


class TestApprovalRoleAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pw = self.portal.portal_workflow
        self.change_user("admin")
        # sign_request with two signers (dirg then bourgmestre) and one file to approve
        self.request, self.files = create_sign_request(self.portal, oid="sr", nb_files=1)
        self.adapter = ApprovalRoleAdapter(self.request)

    def test_getRoles(self):
        self.assertEqual(self.adapter.getRoles("dirg"), ())
        self.assertNotIn("Reviewer", api.user.get_roles(username="bourgmestre", obj=self.request))
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(self.adapter.getRoles("dirg"), ("Reader", "Reviewer", "Editor"))
        self.assertEqual(self.adapter.getRoles("bourgmestre"), ())
        self.request.approval().approve_file(self.files[0], "dirg")
        self.assertEqual(self.adapter.getRoles("dirg"), ("Reader",))
        self.assertEqual(self.adapter.getRoles("bourgmestre"), ("Reader", "Reviewer"))
        # the local roles the user gets
        self.assertIn("Reviewer", api.user.get_roles(username="bourgmestre", obj=self.request))

    def test_getAllRoles(self):
        self.assertEqual(list(self.adapter.getAllRoles()), [("", ("",))])
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(list(self.adapter.getAllRoles()), [("dirg", ("Reader", "Reviewer", "Editor"))])

    def test_config(self):
        self.assertEqual(self.adapter.config, {})
        self.pw.doActionFor(self.request, "propose_to_approve")
        self.assertEqual(self.adapter.config, {"dirg": ("Reader", "Reviewer", "Editor")})
        self.assertEqual(self.adapter.config, self.request.approval().roles)


class TestItemSignersAdapter(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        pf = self.portal["contacts"]["personnel-folder"]
        self.dg = pf["dirg"]["directeur-general"]
        self.bm = pf["bourgmestre"]["bourgmestre"]
        signers = [
            {"number": 1, "signer": self.dg.UID(), "approvings": [u"_themself_"], "editor": True},
            {"number": 2, "signer": u"_empty_", "approvings": [], "editor": False},
            {"number": 3, "signer": self.bm.UID(), "approvings": [u"_themself_"], "editor": False},
        ]
        self.omail = sub_create(
            self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om", title=u"Test", signers=signers
        )
        self.adapter = ISignable(self.omail)

    def test_get_signers(self):
        self.assertIsInstance(self.adapter, ItemSignersAdapter)
        self.assertEqual(
            [(s["held_position"].UID(), s["name"], s["function"]) for s in self.adapter.get_signers()],
            [(self.dg.UID(), u"Maxime DG", u"Directeur Général"), (self.bm.UID(), u"Paul BM", u"Bourgmestre")],
        )

    def test_get_files_uids(self):
        # the files are added to the session by the approval mechanism
        self.assertEqual(self.adapter.get_files_uids(), [])
