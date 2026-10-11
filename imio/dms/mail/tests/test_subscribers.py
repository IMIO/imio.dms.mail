# -*- coding: utf-8 -*-
from App.config import getConfiguration
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_organizations
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.iconifiedcategory.utils import calculate_category_id
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.wfadaptations.api import add_applied_adaptation
from datetime import datetime
from DateTime import DateTime
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.content.behaviors import ISignRequestSigningBehavior
from imio.dms.mail.content.behaviors import IUsagesBehavior
from imio.dms.mail.interfaces import IActionsPanelFolderOnlyAdd
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.interfaces import ISignRequestApproval
from imio.dms.mail.subscribers import dmsoutgoingmail_transition
from imio.dms.mail.subscribers import i_annex_removed
from imio.dms.mail.subscribers import reindex_person_usages
from imio.dms.mail.subscribers import zope_ready
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import sub_create
from imio.dms.mail.vocabularies import AssignedUsersWithDeactivatedVocabulary
from imio.dms.mail.vocabularies import OMActiveSenderVocabulary
from imio.dms.mail.vocabularies import OMSenderVocabulary
from imio.esign.config import set_esign_registry_file_url
from imio.esign.utils import get_session_annotation
from imio.helpers import EMPTY_STRING
from imio.helpers import EMPTY_TITLE
from imio.helpers.content import get_object
from imio.helpers.content import uuidToObject
from imio.helpers.ram import IMIORAMCache
from imio.helpers.test_helpers import ImioTestHelpers
from mock import Mock
from mock import patch
from plone import api
from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.linkintegrity.exceptions import LinkIntegrityNotificationException
from plone.app.testing import TEST_USER_ID
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.dexterity.events import EditFinishedEvent
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield import RelationValue
from zExceptions import Redirect
from zope.annotation import IAnnotations
from zope.component import getSiteManager
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import Invalid
from zope.intid import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from zope.ramcache.interfaces.ram import IRAMCache
from zope.ramcache.ram import RAMCache

import unittest
import zope.event


class TestSubscribers(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        self.intids = getUtility(IIntIds)
        self.imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "c1",
            **{
                "sender": [RelationValue(self.intids.getId(self.portal.contacts["electrabel"]))],
                "mail_type": u"courrier",
                "title": u"title",
            }
        )
        self.omf = self.portal["outgoing-mail"]
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.pf = self.portal["contacts"]["personnel-folder"]

    def test_i_annex_created(self):
        # an annex left without a title takes the file name, without its extension (DMS-1217, DMS-605)
        annex = createContentInContainer(self.imail, "dmsappendixfile",
                                         file=NamedBlobFile("pdf", filename=u"Ma pièce.pdf"))
        self.assertEqual(annex.title, u"Ma pièce")
        # a title given by the user is kept
        titled = createContentInContainer(self.imail, "dmsappendixfile", title=u"CV",
                                          file=NamedBlobFile("pdf", filename=u"Ma pièce.pdf"))
        self.assertEqual(titled.title, u"CV")
        # a file name without extension is kept as is
        noext = createContentInContainer(self.imail, "dmsappendixfile",
                                         file=NamedBlobFile("pdf", filename=u"README"))
        self.assertEqual(noext.title, u"README")
        # an annex without file does not break
        nofile = createContentInContainer(self.imail, "dmsappendixfile", title=u"No file")
        self.assertEqual(nofile.title, u"No file")

    def test_item_copied(self):
        # check if protection markers are removed from copied item
        source = self.portal["templates"]["om"]["main"]
        self.assertFalse(source.restrictedTraverse("@@various-utils").is_unprotected())
        copied = api.content.copy(source, self.portal["templates"]["om"], "copied_id")
        self.assertIn("copied_id", self.portal["templates"]["om"])
        self.assertTrue(copied.restrictedTraverse("@@various-utils").is_unprotected())
        # check if om folder cannot be pasted
        self.assertRaises(Redirect, api.content.copy, self.portal["templates"]["om"], self.portal["templates"], "new")

    def test_item_moved(self):
        source = self.portal["templates"]["om"]["main"]
        copied = api.content.copy(source, self.portal["templates"]["om"], "copied_id")
        self.assertIn("copied_id", self.portal["templates"]["om"])
        # cannot move or delete a protected object
        self.assertRaises(Redirect, api.content.delete, obj=source, check_linkintegrity=False)
        self.assertRaises(Redirect, api.content.move, source, self.portal["templates"]["om"]["common"])
        # cannot rename a protected object
        self.assertRaises(Redirect, api.content.rename, source, "new_id")
        # can rename an unprotected
        copied = api.content.rename(copied, "new_id")
        self.assertEqual(copied.id, "new_id")
        # can delete an unprotected
        api.content.delete(obj=copied, check_linkintegrity=False)
        self.assertNotIn("new_id", self.portal["templates"]["om"])

    def test_dmsdocument_added(self):
        # we add an im with contact list
        orgs = get_registry_organizations()
        cl = self.portal.contacts["contact-lists-folder"]["common"]["list-agents-swde"]
        imail1 = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "id1",
            **{"title": u"IMail1", "treating_groups": orgs[0], "sender": [RelationValue(self.intids.getId(cl))]}
        )
        self.assertEqual(len(imail1.sender), 2)
        self.assertFalse(hasattr(imail1, "creating_group"))
        # we activate imail group encoder
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder", True)
        functions = get_registry_functions()
        functions[-1]["fct_orgs"] = [orgs[0], orgs[2]]
        set_registry_functions(functions)  # set contributor local roles
        api.group.add_user(groupname="{}_{}".format(orgs[0], CREATING_GROUP_SUFFIX), username="chef")  # dg
        api.group.add_user(groupname="{}_{}".format(orgs[2], CREATING_GROUP_SUFFIX), username="agent")  # dg/grh
        imail2 = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "id2")
        self.assertEqual(imail2.creating_group, orgs[0])  # user not in groups, take the first value
        self.change_user("agent")
        imail3 = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "id3")
        self.assertEqual(imail3.creating_group, orgs[2])
        self.change_user("chef")
        imail4 = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "id4")
        self.assertEqual(imail4.creating_group, orgs[0])

    def test_dmsdocument_modified(self):
        # owner changing test
        orgs = get_registry_organizations()
        with api.env.adopt_user(username="scanner"):
            imail = sub_create(
                self.portal["incoming-mail"],
                "dmsincomingmail",
                datetime.now(),
                "my-id",
                **{"title": u"IMail created by scanner", "treating_groups": orgs[0]}
            )
            dfile = createContentInContainer(imail, "dmsmainfile", **{"title": "File created by scanner"})
        self.assertEquals(imail.Creator(), "scanner")
        self.assertEquals(imail.owner_info()["id"], "scanner")
        self.assertEquals(imail.get_local_roles_for_userid("scanner"), ("Owner",))
        self.assertEquals(dfile.Creator(), "scanner")
        self.assertEquals(dfile.owner_info()["id"], "scanner")
        self.assertEquals(dfile.get_local_roles_for_userid("scanner"), ("Owner",))
        with api.env.adopt_user(username="encodeur"):
            imail.setTitle("IMail modified by encodeur")
            zope.event.notify(ObjectModifiedEvent(imail))
        self.assertEquals(imail.Creator(), "encodeur")
        self.assertEquals(imail.owner_info()["id"], "encodeur")
        self.assertEquals(imail.get_local_roles_for_userid("encodeur"), ("Owner",))
        self.assertEquals(imail.get_local_roles_for_userid("scanner"), ())
        self.assertEquals(dfile.Creator(), "encodeur")
        self.assertEquals(dfile.owner_info()["id"], "encodeur")
        self.assertEquals(dfile.get_local_roles_for_userid("encodeur"), ("Owner",))
        self.assertEquals(dfile.get_local_roles_for_userid("scanner"), ())
        # tasks update test
        task1 = api.content.create(container=imail, type="task", title="task1", id="t1", assigned_group=orgs[1])
        self.assertListEqual(task1.parents_assigned_groups, [orgs[0]])
        task2 = api.content.create(container=task1, type="task", title="task2", id="t2", assigned_group=orgs[2])
        self.assertListEqual(task2.parents_assigned_groups, [orgs[0], orgs[1]])
        imail.treating_groups = orgs[4]
        zope.event.notify(ObjectModifiedEvent(imail, Attributes(Interface, "treating_groups")))
        self.assertListEqual(task1.parents_assigned_groups, [orgs[4]])
        self.assertListEqual(task2.parents_assigned_groups, [orgs[4], orgs[1]])
        # treating_groups change on service validation state is tested in test_wfadaptations_imservicevalidation...

    def test_dmsincomingmail_transition(self):
        self.assertEqual(api.content.get_state(self.imail), "created")
        self.imail.treating_groups = get_registry_organizations()[1]  # direction-generale secretariat
        api.content.transition(self.imail, "propose_to_agent")
        self.change_user("agent")
        self.assertIsNone(self.imail.assigned_user)
        api.content.transition(self.imail, "close")
        self.assertEqual(self.imail.assigned_user, "agent")

    def test_correct_to_print(self):
        """to_print is auto-derived: main files follow (not esign), appendix always False."""
        omail = sub_create(
            self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(),
            "omail-tp-test",
            title=u"To print test",
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type=u"courrier",
        )
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        filename = u"Réponse salle.odt"

        def _add(portal_type, oid, esign):
            omail.esign = esign
            with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
                file_obj = NamedBlobFile(fo.read(), filename=filename)
            return createContentInContainer(
                omail, portal_type, id=oid, file=file_obj,
                content_category=calculate_category_id(ct),
            )

        # GED main, esign off -> to_print True
        main_off = _add("dmsommainfile", "main-off", False)
        self.assertTrue(main_off.to_print)
        # GED main, esign on -> to_print False
        main_on = _add("dmsommainfile", "main-on", True)
        self.assertFalse(main_on.to_print)
        # appendix, esign off -> always False
        app_off = _add("dmsappendixfile", "app-off", False)
        self.assertFalse(app_off.to_print)
        # appendix, esign on -> always False
        app_on = _add("dmsappendixfile", "app-on", True)
        self.assertFalse(app_on.to_print)
        # 'to_be_printed_activated' gate: a main that would be to_print (esign off)
        # stays False when its category group has printing deactivated
        group = self.portal["annexes_types"]["outgoing_dms_files"]
        group.to_be_printed_activated = False
        try:
            gated_main = _add("dmsommainfile", "main-gated", False)
            self.assertFalse(gated_main.to_print)
        finally:
            group.to_be_printed_activated = True

    def test_dmsoutgoingmail_transition(self):
        def make_event(transition_id=None):
            event = Mock()
            if transition_id is None:
                event.transition = None
            else:
                event.transition = Mock()
                event.transition.id = transition_id
            return event

        omail = sub_create(
            self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(),
            "omail-tr-test",
            title=u"Transition test",
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type=u"courrier",
        )
        request = self.portal.REQUEST

        # Branch A: mark_as_sent sets outgoing_date
        # A1: no transition → no effect
        dmsoutgoingmail_transition(omail, make_event())
        self.assertIsNone(omail.outgoing_date)

        # A2: unrelated transition → no effect
        dmsoutgoingmail_transition(omail, make_event("set_scanned"))
        self.assertIsNone(omail.outgoing_date)

        # A3: mark_as_sent with outgoing_date=None → sets it
        dmsoutgoingmail_transition(omail, make_event("mark_as_sent"))
        self.assertIsNotNone(omail.outgoing_date)

        # A4: mark_as_sent with outgoing_date already set → no overwrite
        orig_date = datetime(2020, 1, 1)
        omail.outgoing_date = orig_date
        dmsoutgoingmail_transition(omail, make_event("mark_as_sent"))
        self.assertEqual(omail.outgoing_date, orig_date)

        # Branch B: propose_to_approve → calls start_approval_process
        with patch.object(OMApprovalAdapter, "start_approval_process") as mock_start:
            dmsoutgoingmail_transition(omail, make_event("propose_to_approve"))
            mock_start.assert_called_once_with()

        # a dmsommainfile inside omail, used by the seal branch below
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_obj = NamedBlobFile(fo.read(), filename=filename)
        afile = createContentInContainer(
            omail, "dmsommainfile", id="test-odt",
            file=file_obj,
            content_category=calculate_category_id(ct),
        )

        # Branch D: seal handling (seal without signers, due to constraints)

        # D0: esign=True → seal block skipped, OMApprovalAdapter never instantiated
        omail.esign = True
        omail.seal = True
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
            MockAdapter.assert_not_called()
        omail.esign = False

        # D1: seal=False → OMApprovalAdapter never instantiated
        omail.seal = False
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
            MockAdapter.assert_not_called()
        omail.seal = True

        # D2: file filter — to_sign=True files are added, to_sign=False are not
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_obj2 = NamedBlobFile(fo.read(), filename=filename)
        afile2 = createContentInContainer(
            omail, "dmsommainfile", id="test-odt2",
            file=file_obj2,
            content_category=calculate_category_id(ct),
        )
        afile2.to_sign = True
        afile.to_sign = False  # category defaults to True; explicitly disable

        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (False, u"No files")
            dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
            self.assertEqual(mock_approval.add_file_to_approval.call_count, 1)
            self.assertEqual(mock_approval.add_file_to_approval.call_args[0][0], afile2.UID())
            IStatusMessage(request).show()  # consume messages

        # D3: (False, msg) → exactly 1 error message with correct content, no second message
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (False, u"No files")
            dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
            msgs = IStatusMessage(request).show()
            self.assertEqual(len(msgs), 1)
            self.assertEqual(msgs[0].type, u"error")
            self.assertEqual(msgs[0].message, u"No files")

        # D4: (True, msg), no seal code only → info + "Seal code" error, ExternalSessionCreateView not called
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (True, u"1 file added")
            with patch("imio.dms.mail.subscribers.get_esign_registry_seal_code", return_value=None):
                with patch("imio.dms.mail.subscribers.get_esign_registry_seal_email", return_value=u"sign@example.com"):
                    with patch("imio.dms.mail.subscribers.ExternalSessionCreateView") as MockESV:
                        dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
                        MockESV.assert_not_called()
            msgs = IStatusMessage(request).show()
            self.assertEqual(len(msgs), 2)
            self.assertEqual(msgs[0].type, u"info")
            self.assertEqual(msgs[0].message, u"1 file added")
            self.assertEqual(msgs[1].type, u"error")
            self.assertIn(u"cachet", msgs[1].message)  # French: "Le code du cachet électronique..."

        # D5: both seal code and email missing → info + 2 errors
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (True, u"1 file added")
            with patch("imio.dms.mail.subscribers.get_esign_registry_seal_code", return_value=None):
                with patch("imio.dms.mail.subscribers.get_esign_registry_seal_email", return_value=None):
                    with patch("imio.dms.mail.subscribers.ExternalSessionCreateView") as MockESV:
                        dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
                        MockESV.assert_not_called()
            msgs = IStatusMessage(request).show()
            self.assertEqual(len(msgs), 3)
            self.assertEqual(msgs[0].type, u"info")
            self.assertEqual(msgs[1].type, u"error")
            self.assertIn(u"cachet", msgs[1].message)
            self.assertEqual(msgs[2].type, u"error")
            self.assertIn(u"email", msgs[2].message.lower())

        # D6: (True, msg), seal code present but no seal email → info + "Seal email" error
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (True, u"1 file added")
            with patch("imio.dms.mail.subscribers.get_esign_registry_seal_code", return_value=u"1234"):
                with patch("imio.dms.mail.subscribers.get_esign_registry_seal_email", return_value=None):
                    with patch("imio.dms.mail.subscribers.ExternalSessionCreateView") as MockESV:
                        dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
                        MockESV.assert_not_called()
            msgs = IStatusMessage(request).show()
            self.assertEqual(len(msgs), 2)
            self.assertEqual(msgs[0].type, u"info")
            self.assertEqual(msgs[1].type, u"error")
            self.assertIn(u"email", msgs[1].message.lower())  # "Seal email must be defined..."

        # D7: (True, msg), both seal code and email present → ExternalSessionCreateView called, 1 info message
        with patch("imio.dms.mail.subscribers.OMApprovalAdapter") as MockAdapter:
            mock_approval = Mock()
            MockAdapter.return_value = mock_approval
            mock_approval.add_mail_files_to_session.return_value = (True, u"1 file added")
            mock_approval.session_ids = [u"session-abc"]
            with patch("imio.dms.mail.subscribers.get_esign_registry_seal_code", return_value=u"1234"):
                with patch("imio.dms.mail.subscribers.get_esign_registry_seal_email", return_value=u"sign@example.com"):
                    with patch("imio.dms.mail.subscribers.ExternalSessionCreateView") as MockESV:
                        mock_esv_instance = Mock()
                        MockESV.return_value = mock_esv_instance
                        dmsoutgoingmail_transition(omail, make_event("propose_to_be_signed"))
                        MockESV.assert_called_once_with(omail, omail.REQUEST)
                        mock_esv_instance.assert_called_once_with(session_id=u"session-abc")
            msgs = IStatusMessage(request).show()
            self.assertEqual(len(msgs), 1)
            self.assertEqual(msgs[0].type, u"info")
            self.assertEqual(msgs[0].message, u"1 file added")

    def test_dmsoutgoingmail_modified_signer_rules(self):
        dirg = self.pf["dirg"]
        dirg_hp = dirg["directeur-general"]
        bourgmestre = self.pf["bourgmestre"]
        bourgmestre_hp = bourgmestre["bourgmestre"]
        rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )

        # Test no rules
        omail.signers = None
        api.portal.set_registry_record(rk, [])
        modified(omail)
        self.assertListEqual(
            omail.signers, [{"signer": u"_empty_", "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test treating groups
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [self.pgof["direction-generale"].UID()],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [self.pgof["direction-financiere"].UID()],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": True,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": u"_empty_", "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test mail types
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": ["courrier"],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        omail.signers = None
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types",
            [
                {"dtitle": u"Courrier", "active": True, "value": u"courrier"},
                {"dtitle": u"Type 2", "active": True, "value": u"type2"},
            ],
        )
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": ["type2"],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": u"_empty_", "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test TAL condition
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": u"python:True",
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": u"python:False",
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": u"_empty_", "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test skip number if already present
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": dirg_hp.UID(),
                    "editor": True,
                },
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test seal (number 0)
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": False,
                    "number": 0,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": u"_seal_",
                    "editor": False,
                },
            ],
        )
        self.assertIsNone(omail.seal)
        modified(omail)
        self.assertTrue(omail.seal)
        self.assertEqual(
            omail.signers, [{"signer": u"_empty_", "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test sort signers
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 2,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": dirg_hp.UID(),
                    "editor": True,
                },
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers,
            [
                {"signer": dirg_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": True},
                {"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 2, "editor": False},
            ],
        )

        # Test duplicate signer
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 2,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        with self.assertRaises(Invalid) as cm:
            modified(omail)
        self.assertEqual(
            cm.exception.message,
            u"You cannot have the same signer (${signer_title}) multiple times ! " u"You have to adapt the rules !",
        )

        params = {
            "position": RelationValue(
                self.intids.getId(self.portal["contacts"]["plonegroup-organization"]["college-communal"])
            ),
            "usages": ["signer"],
        }
        bourgmestre_hp2 = bourgmestre.invokeFactory("held_position", "directeur-general-college-communal-2", **params)
        bourgmestre_hp2 = bourgmestre[bourgmestre_hp2]
        modified(bourgmestre_hp2, Attributes(Interface, "usages"))  # interface behavior
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 2,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp2.UID(),
                    "editor": False,
                },
            ],
        )
        with self.assertRaises(Invalid) as cm:
            modified(omail)
        self.assertEqual(
            cm.exception.message,
            u"You cannot have the same signer (${signer_title}) multiple times ! " u"You have to adapt the rules !",
        )

        # Test missing number
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": dirg_hp.UID(),
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 3,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )

        # Test seal + esign
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 0,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": u"_seal_",
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        modified(omail)
        self.assertTrue(omail.esign)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        omail.signers = None
        omail.seal = None
        omail.esign = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": False,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        modified(omail)
        self.assertFalse(omail.esign)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        omail.signers = None
        omail.seal = None
        omail.esign = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 0,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": u"_seal_",
                    "editor": False,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": False,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        with self.assertRaises(Invalid) as cm:
            modified(omail)
        self.assertEqual(
            cm.exception.message, u"You cannot have a seal without electronic signature ! You have to adapt the rules !"
        )

        # Test mail already has signers
        omail.signers = [
            {
                "signer": dirg_hp.UID(),
                "approvings": [u"_themself_", bourgmestre_hp.UID()],
                "number": 1,
                "editor": True,
            }
        ]
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": False,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers,
            [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_", bourgmestre_hp.UID()],
                    "number": 1,
                    "editor": True,
                }
            ],
        )

        # Test duplicate approvings userids
        chef = self.pf["chef"]
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [chef.UID()],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": dirg_hp.UID(),
                    "editor": True,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [chef.UID()],
                    "esign": True,
                    "number": 2,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        with self.assertRaises(Invalid) as cm:
            modified(omail)
        self.assertEqual(
            cm.exception.message, u"The chef already exists in the approvings with another order 1 <=> 2"
        )

        # Test signers have same email
        api.user.get("bourgmestre").setMemberProperties({"email": "duplicate@belleville.eb"})
        api.user.get("dirg").setMemberProperties({"email": "duplicate@belleville.eb"})
        omail.signers = None
        api.portal.set_registry_record(
            rk,
            [
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 1,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": dirg_hp.UID(),
                    "editor": True,
                },
                {
                    "tal_condition": None,
                    "mail_types": [],
                    "approvings": [u"_empty_"],
                    "esign": True,
                    "number": 2,
                    "treating_groups": [],
                    "send_modes": [],
                    "signer": bourgmestre_hp.UID(),
                    "editor": False,
                },
            ],
        )
        with self.assertRaises(Invalid) as cm:
            modified(omail)
        self.assertEqual(cm.exception.message, u"You cannot have the same email (duplicate@belleville.eb) "
                                               u"for multiple signers !")
        api.user.get("dirg").setMemberProperties({"email": "deduplicate@belleville.eb"})

        # Test mail in sent or to_be_signed states
        filepath = "%s/batchimport/toprocess/outgoing-mail/Réponse salle.odt" % PRODUCT_DIR
        with open(filepath, "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=u"example.odt")
            createContentInContainer(omail, "dmsommainfile", id="1", title="Example", file=file_object)
        api.content.transition(omail, to_state="to_be_signed")
        omail.signers = None
        modified(omail)
        self.assertIsNone(omail.signers)

        api.content.transition(omail, to_state="sent")
        omail.signers = None
        modified(omail)
        self.assertIsNone(omail.signers)

    def test_dmsoutgoingmail_modified_signers_origin(self):
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        dirg_hp = self.pf["dirg"]["directeur-general"]
        bourgmestre_hp = self.pf["bourgmestre"]["bourgmestre"]
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-ts-id",
            title="Template Signers Test",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )

        # Baseline: "rules" mode (default), default signer rules apply on creation
        self.assertEqual(len(omail.signers), 2)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(omail.signers[1]["signer"], bourgmestre_hp.UID())

        # "template_first": signer rules are skipped and no value is set.
        api.portal.set_registry_record(rk_so, u"template_first")
        omail.signers = None
        modified(omail)
        self.assertIsNone(omail.signers)

        # Existing signers are preserved
        omail.signers = [{"number": 1, "signer": dirg_hp.UID(), "editor": True, "approvings": [u"_empty_"]}]
        modified(omail)
        self.assertEqual(len(omail.signers), 1)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())

        # "rules_first": rules apply on creation (template is only a fallback at generation time)
        api.portal.set_registry_record(rk_so, u"rules_first")
        omail.signers = None
        modified(omail)
        self.assertEqual(len(omail.signers), 2)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(omail.signers[1]["signer"], bourgmestre_hp.UID())

        # "rules" mode: rules apply again
        api.portal.set_registry_record(rk_so, u"rules")
        omail.signers = None
        modified(omail)
        self.assertEqual(len(omail.signers), 2)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(omail.signers[1]["signer"], bourgmestre_hp.UID())
        # empty rules
        rk_osr = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        api.portal.set_registry_record(rk_osr, [])
        omail.signers = None
        modified(omail)
        self.assertEqual(len(omail.signers), 1)
        self.assertEqual(omail.signers[0]["signer"], u"_empty_")

        # "rules_first": rules apply on creation (template is only a fallback at generation time)
        api.portal.set_registry_record(rk_so, u"rules_first")
        omail.signers = None
        modified(omail)
        self.assertFalse(omail.signers)

    def test_i_annex_added_signers_template_first(self):
        # In "template_first" mode, signers stay empty until the first template generation. When an
        # appendix (dmsappendixfile) is added before any template, the signer rules are applied here.
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        rk_osr = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        dirg_hp = self.pf["dirg"]["directeur-general"]
        bourgmestre_hp = self.pf["bourgmestre"]["bourgmestre"]
        api.portal.set_registry_record(rk_so, u"template_first")
        omail = sub_create(
            self.omf,
            "dmsoutgoingmail",
            datetime.now(),
            "appendix-tf-id",
            title="Appendix First Test",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )
        # template_first: no signer set yet
        self.assertFalse(omail.signers)

        # adding an appendix first applies the signer rules
        createContentInContainer(omail, "dmsappendixfile", id="appendix1", title="Appendix 1")
        self.assertEqual(len(omail.signers), 2)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(omail.signers[1]["signer"], bourgmestre_hp.UID())

        # adding another appendix does not reset/recompute signers
        omail.signers = [{"number": 1, "signer": dirg_hp.UID(), "editor": True, "approvings": [u"_empty_"]}]
        createContentInContainer(omail, "dmsappendixfile", id="appendix2", title="Appendix 2")
        self.assertEqual(len(omail.signers), 1)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())

        # when the rules produce nothing, an _empty_ placeholder is set (like _copy_template_signers does).
        api.portal.set_registry_record(rk_osr, [])
        omail2 = sub_create(
            self.omf,
            "dmsoutgoingmail",
            datetime.now(),
            "appendix-tf-id2",
            title="Appendix First Test 2",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )
        createContentInContainer(omail2, "dmsappendixfile", id="appendix1", title="Appendix 1")
        self.assertEqual(omail2.signers, [{"number": 1, "signer": u"_empty_", "editor": False,
                                           "approvings": [u"_empty_"]}])

    def test_dmsoutgoingmail_modified_signer_substitutes(self):
        dirg = self.pf["dirg"]
        dirg_hp = dirg["directeur-general"]
        bourgmestre = self.pf["bourgmestre"]
        bourgmestre_hp = bourgmestre["bourgmestre"]
        rk_rules = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        rk_subs = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_substitutes"
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-sub-id",
            title="Substitute Test",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )
        base_rule = {
            "number": 1,
            "signer": bourgmestre_hp.UID(),
            "esign": True,
            "approvings": [u"_empty_"],
            "editor": False,
            "treating_groups": [],
            "mail_types": [],
            "send_modes": [],
            "tal_condition": None,
        }

        # Test no substitutes -> original signer used
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(rk_subs, [])
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test substitute match -> substitute signer used (bourgmestre_hp -> dirg_hp)
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
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
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": dirg_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # First-match-wins: two substitutes for same absent_signer — first one applies
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": None,
                    "valid_until": None,
                },
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": bourgmestre_hp.UID(),  # different target, should be ignored
                    "valid_from": None,
                    "valid_until": None,
                },
            ],
        )
        modified(omail)
        self.assertEqual(omail.signers[0]["signer"], dirg_hp.UID())

        # Test no match (different absent_signer) -> original signer kept
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": dirg_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": None,
                    "valid_until": None,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test substitute expired (valid_until in past) -> original signer
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": u"2000/01/01",
                    "valid_until": u"2001/01/01",
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test substitute not yet active (valid_from in future) -> original signer
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": u"2099/01/01",
                    "valid_until": None,
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": bourgmestre_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

        # Test substitute within valid date range -> substitute used
        omail.signers = None
        api.portal.set_registry_record(rk_rules, [base_rule])
        api.portal.set_registry_record(
            rk_subs,
            [
                {
                    "absent_signer": bourgmestre_hp.UID(),
                    "substitute_signer": dirg_hp.UID(),
                    "valid_from": u"2000/01/01",
                    "valid_until": u"2100/01/01",
                }
            ],
        )
        modified(omail)
        self.assertEqual(
            omail.signers, [{"signer": dirg_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": False}]
        )

    def test_dmsoutgoingmail_modified_approval_annot(self):
        dirg = self.pf["dirg"]
        dirg_hp = dirg["directeur-general"]
        bourg = self.pf["bourgmestre"]
        bourg_hp = bourg["bourgmestre"]
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="courrier",
        )
        self.assertEqual(
            omail.signers,
            [
                {"signer": dirg_hp.UID(), "approvings": [u"_empty_"], "number": 1, "editor": True},
                {"signer": bourg_hp.UID(), "approvings": [u"_empty_"], "number": 2, "editor": False},
            ],
        )
        self.assertFalse(omail.esign)
        annot = OMApprovalAdapter(omail).annot
        # after creation, default rules are applied
        self.assertEqual(
            annot,
            {
                "files": [],
                "current_nb": None,
                "approvers": [[], []],
                "session_ids": [],
                "pdf_files": [],
                "approval": [[], []],
                "editors": [True, False],
                "signers": [
                    ("dirg", u"Maxime DG", u"Directeur G\xe9n\xe9ral"),
                    ("bourgmestre", u"Paul BM", u"Bourgmestre"),
                ],
            },
        )
        # we remove a signer

    def _setup_omail_with_esign(self):
        """Helper to create an outgoing mail with esign approval and files."""
        self.change_user("admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        set_esign_registry_file_url("https://downloads.files.com")
        intids = getUtility(IIntIds)
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
        omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om", **params)
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        files = []
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            files.append(
                createContentInContainer(
                    omail,
                    "dmsommainfile",
                    id="file0",
                    scan_id="012999900000601",
                    file=file_object,
                    content_category=calculate_category_id(ct),
                )
            )
        view = omail.restrictedTraverse("persistent-document-generation")
        view.pod_template = self.portal["templates"]["om"]["main"]
        view.output_format = "odt"
        files.append(view.generate_persistent_doc(view.pod_template, view.output_format))

        return omail, files, IOMApproval(omail)

    def _approve_all_files(self, omail, files, approval):
        """Helper to transition omail through full approval to to_be_signed state."""
        pw = self.portal.portal_workflow
        pw.doActionFor(omail, "propose_to_approve")
        approval.start_approval_process()
        # Both signers must approve both files to reach to_be_signed
        approval.approve_file(files[0], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "dirg", transition="propose_to_be_signed")
        approval.approve_file(files[1], "bourgmestre", transition="propose_to_be_signed")
        approval.approve_file(files[0], "bourgmestre", transition="propose_to_be_signed")

    def test_i_annex_removed_pdf_file(self):
        """Test i_annex_removed Case 1: removing a generated PDF removes it from approval."""
        omail, files, approval = self._setup_omail_with_esign()
        self._approve_all_files(omail, files, approval)
        self.assertEqual(api.content.get_state(omail), "to_be_signed")
        # Get the generated PDF for files[1]
        pdf_uid = approval.pdf_files_uids[1][0]
        pdf_obj = uuidToObject(pdf_uid)
        self.assertIsNotNone(pdf_obj)
        # The PDF should have conv_from_uid pointing to the source
        self.assertEqual(pdf_obj.conv_from_uid, files[1].UID())
        session_annot = get_session_annotation()
        self.assertIn(pdf_uid, session_annot["uids"])
        self.assertEqual(session_annot["uids"][pdf_uid], 0)
        self.assertIn(pdf_uid, [dic["uid"] for dic in session_annot["sessions"][0]["files"]])

        # Call the subscriber directly to remove the PDF
        event = ObjectRemovedEvent(pdf_obj, omail, pdf_obj.getId())
        i_annex_removed(pdf_obj, event)
        # PDF is removed from session annotation
        self.assertNotIn(pdf_uid, session_annot["uids"])
        self.assertNotIn(pdf_uid, [dic["uid"] for dic in session_annot["sessions"][0]["files"]])
        # PDF is removed from pdf_files_uids annotation
        self.assertNotIn(pdf_uid, [uid for lst in approval.pdf_files_uids for uid in lst])
        # Source file stays in approval (Case 1 only removes the PDF, not the source)
        self.assertIn(files[0].UID(), approval.files_uids)
        self.assertIn(files[1].UID(), approval.files_uids)

    def test_i_annex_removed_pdf_file_not_draft(self):
        """Test i_annex_removed Case 1: removing a PDF when its esign session is not in draft state
        raises Redirect. The PDF stays in the session (deletion is blocked)."""
        omail, files, approval = self._setup_omail_with_esign()
        self._approve_all_files(omail, files, approval)
        self.assertEqual(api.content.get_state(omail), "to_be_signed")
        pdf_uid = approval.pdf_files_uids[1][0]
        pdf_obj = uuidToObject(pdf_uid)
        self.assertIsNotNone(pdf_obj)

        # Simulate the session having been sent to the signing service (no longer draft)
        session_annot = get_session_annotation()
        session_id = session_annot["uids"][pdf_uid]
        session_annot["sessions"][session_id]["state"] = "sent"

        event = ObjectRemovedEvent(pdf_obj, omail, pdf_obj.getId())
        with self.assertRaises(Redirect):
            i_annex_removed(pdf_obj, event)

        # PDF is still registered in the session (deletion was blocked)
        self.assertIn(pdf_uid, session_annot["uids"])
        self.assertIn(pdf_uid, [uid for lst in approval.pdf_files_uids for uid in lst])

    def test_i_annex_removed_source_file(self):
        """Test i_annex_removed Case 2: removing a source file that has linked PDFs raises Redirect.
        The source file and its PDFs are left untouched (deletion is blocked)."""
        omail, files, approval = self._setup_omail_with_esign()
        self._approve_all_files(omail, files, approval)
        self.assertEqual(api.content.get_state(omail), "to_be_signed")
        # We should have PDF files generated
        self.assertTrue(approval.pdf_files_uids[1])
        pdf_uid_1 = approval.pdf_files_uids[1][0]
        self.assertIsNotNone(uuidToObject(pdf_uid_1))

        # Attempting to delete a source file with linked PDFs must be blocked
        event = ObjectRemovedEvent(files[1], omail, files[1].getId())
        with self.assertRaises(Redirect):
            i_annex_removed(files[1], event)

        # Source file and its PDF remain in approval (deletion was blocked)
        self.assertIn(files[1].UID(), approval.files_uids)
        self.assertIsNotNone(uuidToObject(pdf_uid_1))

    def test_i_annex_removed_source_file_no_pdfs(self):
        """Test i_annex_removed Case 2: source file with no linked PDFs is removed from approval."""
        omail, files, approval = self._setup_omail_with_esign()
        # files[0] has no conv_from_uid (it's a source file, not a generated PDF)
        self.assertIsNone(getattr(files[0], "conv_from_uid", None))
        self.assertIn(files[0].UID(), approval.files_uids)
        initial_files_count = len(approval.files_uids)
        # Directly call the subscriber with a removal event
        event = ObjectRemovedEvent(files[0], omail, files[0].getId())
        i_annex_removed(files[0], event)
        # The file should be removed from approval
        self.assertEqual(len(approval.files_uids), initial_files_count - 1)

    def test_task_transition(self):
        # task = createContentInContainer(self.imail, 'task', id='t1')
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        # no assigned_user and no TaskServiceValidation
        self.assertIsNone(task.assigned_user)
        api.content.transition(task, transition="do_to_assign")
        self.assertEqual(api.content.get_state(task), "to_do")
        # assigned_user and no TaskServiceValidation
        api.content.transition(task, transition="back_in_created2")
        task.assigned_user = "chef"
        api.content.transition(task, transition="do_to_assign")
        self.assertEqual(api.content.get_state(task), "to_do")
        # no assigned_user but TaskServiceValidation but no user in groups
        api.content.transition(task, transition="back_in_created2")
        task.assigned_user = None
        add_applied_adaptation("imio.dms.mail.wfadaptations.TaskServiceValidation", "task_workflow", False)
        api.content.transition(task, transition="do_to_assign")
        self.assertEqual(api.content.get_state(task), "to_do")
        # no assigned_user but TaskServiceValidation and user in groups
        api.content.transition(task, transition="back_in_created2")
        api.group.create(groupname="{}_n_plus_1".format(task.assigned_group), groups=["chef"])
        api.content.transition(task, transition="do_to_assign")
        self.assertEqual(api.content.get_state(task), "to_assign")

    def test_dmsmainfile_modified(self):
        pc = self.portal.portal_catalog
        rid = pc(id="c1")[0].getRID()
        # before mainfile creation
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ["e0010", "title"])
        # after mainfile creation
        f1 = createContentInContainer(self.imail, "dmsmainfile", id="f1", scan_id="010999900000690")
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ["e0010", "title", u"010999900000690", "imio010999900000690", u"690"])
        # after mainfile modification
        f1.scan_id = "010999900000691"
        zope.event.notify(ObjectModifiedEvent(f1, Attributes(IScanFields, "IScanFields.scan_id")))
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ["e0010", "title", u"010999900000691", "imio010999900000691", u"691"])
        # event without scan_id attribute
        zope.event.notify(ObjectModifiedEvent(f1))

    def test_user_related_modification(self):
        voc_inst = AssignedUsersWithDeactivatedVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )
        # we change a user property
        member = api.user.get(userid="chef")
        member.setMemberProperties({"fullname": "Michel Chef 2"})
        # we simulate the user form change event
        zope.event.notify(ConfigurationChangedEvent(UserDataConfiglet(self.portal, self.portal.REQUEST), {}))
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef 2"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )
        # we change the activated services
        set_registry_organizations(get_registry_organizations()[0:1])  # only keep Direction générale
        api.group.remove_user(groupname="createurs_dossier", username="agent")  # remove agent from global group
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("encodeur", u"Jean Encodeur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef 2"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent", u"Fred Agent (Désactivé)"),
                ("lecteur", u"Jef Lecteur (Désactivé)"),
                ("agent1", u"Stef Agent (Désactivé)"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )
        # wrong configuration change
        zope.event.notify(ConfigurationChangedEvent(self.portal, {}))

    def test_user_deleted(self):
        request = self.portal.REQUEST
        # protected user
        self.assertRaises(Redirect, api.user.delete, username="scanner")
        smi = IStatusMessage(request)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'scanner'.")
        # having group
        self.assertRaises(Redirect, api.user.delete, "lecteur")
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'lecteur', used in following groups.")
        # is used in content
        self.assertRaises(Redirect, api.user.delete, username=TEST_USER_ID)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'test_user_1_', used in 'Creator' index.")
        # is used as person user_id
        api.user.create("test@test.be", "testuser", "Password#1")
        agent = self.portal.contacts["personnel-folder"]["agent"]
        agent.userid = "testuser"
        agent.reindexObject()
        self.assertRaises(Redirect, api.user.delete, username="testuser")
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'testuser', used in 'userid' index.")

    def test_group_deleted(self):
        request = self.portal.REQUEST
        # protected group
        self.assertRaises(Redirect, api.group.delete, groupname="expedition")
        smi = IStatusMessage(request)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the group 'expedition'.")
        # is used in content
        group = "%s_editeur" % get_registry_organizations()[0]
        # we remove this organization to escape plonegroup subscriber
        set_registry_organizations(get_registry_organizations()[1:])
        self.assertRaises(Redirect, api.group.delete, groupname=group)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the group '%s', used in 'Assigned group' index." % group)

    def test_group_assignment(self):
        self.portal.ok = True
        self.portal.acl_users.source_groups.addPrincipalToGroup("agent", "encodeurs")
        self.assertRaises(Redirect, self.portal.acl_users.source_groups.addPrincipalToGroup, "Reviewers", "encodeurs")

    def test_organization_modified(self):
        pc = self.portal.portal_catalog
        self.elec = self.portal["contacts"]["electrabel"]
        rid = pc(id="travaux")[0].getRID()
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, "electrabel|travaux 0001|")
        self.elec.title = "Electrabel 1"
        zope.event.notify(ObjectModifiedEvent(self.elec, Attributes(IBasic, "IBasic.title")))
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, "electrabel 0001|travaux 0001|")
        rid = pc(id="electrabel")[0].getRID()
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, "electrabel 0001|")

    def test_contact_plonegroup_change(self):
        e_groups = [("%s_encodeur" % uid, ("Contributor",)) for uid in get_registry_organizations()]
        e_groups.append(("admin", ("Owner",)))
        e_groups.append(("expedition", ("Contributor",)))
        e_groups.append(("dir_general", ("Contributor",)))
        self.assertSetEqual(set(self.omf.get_local_roles()), set(e_groups))
        self.assertEqual(len(self.omf.get_local_roles()), 15)
        set_registry_organizations(get_registry_organizations()[:3])
        self.assertEqual(len(self.omf.get_local_roles()), 6)
        # TODO tests other changes !!

    def test_cktemplate_moved(self):
        oemf = self.portal["templates"]["oem"]
        srvf = self.portal["contacts"]["plonegroup-organization"]
        org1 = srvf["direction-generale"]
        org2 = srvf["direction-generale"]["secretariat"]
        self.assertIn(org1.UID(), oemf)
        self.assertIn(org2.UID(), oemf)
        mod1 = api.content.create(container=oemf, type="cktemplate", id="mod1", title="Modèle 1")
        annot = IAnnotations(mod1)
        self.assertEqual(annot["dmsmail.cke_tpl_tit"], u"")
        mod1 = api.content.move(mod1, oemf[org1.UID()])
        annot = IAnnotations(mod1)
        self.assertEqual(annot["dmsmail.cke_tpl_tit"], u"Direction générale")
        mod2 = api.content.copy(mod1, oemf[org2.UID()], id="mod2")
        annot = IAnnotations(mod2)
        self.assertEqual(annot["dmsmail.cke_tpl_tit"], u"Direction générale - Secrétariat")
        folder = api.content.create(container=oemf, type="Folder", id="fold1", title="héhéhé")
        mod2 = api.content.move(mod2, folder)
        annot = IAnnotations(mod2)
        self.assertEqual(annot["dmsmail.cke_tpl_tit"], u"héhéhé")
        mod2 = api.content.rename(mod2, "mod-nextgen")
        annot = IAnnotations(mod2)
        self.assertEqual(annot["dmsmail.cke_tpl_tit"], u"héhéhé")

    def _person_usages(self, person):
        """Return the value stored in the 'usages' catalog index for the given person."""
        pc = self.portal.portal_catalog
        rid = pc(UID=person.UID())[0].getRID()
        return pc._catalog.getIndex("usages").getEntryForObject(rid, default=[])

    def test_reindex_person_usages(self):
        # the person's 'usages' index aggregates its held positions' usages
        person = api.content.create(container=self.pf, type="person", id="tester", lastname=u"Tester")
        person.invokeFactory(
            "held_position",
            "hp1",
            position=RelationValue(self.intids.getId(self.pgof["direction-generale"])),
        )
        hp = person["hp1"]
        hp.usages = ["signer", "approving"]
        reindex_person_usages(hp)
        self.assertListEqual(sorted(self._person_usages(person)), ["approving", "signer"])

    def test_held_position_added(self):
        # a fresh person without held positions is not present in the 'usages' index
        person = api.content.create(container=self.pf, type="person", id="tester", lastname=u"Tester")
        self.assertListEqual(self._person_usages(person), [])
        # adding a held position with a usage reindexes the person (held_position_added subscriber)
        person.invokeFactory(
            "held_position",
            "hp1",
            position=RelationValue(self.intids.getId(self.pgof["direction-generale"])),
            usages=["signer"],
        )
        self.assertListEqual(self._person_usages(person), ["signer"])

    def test_held_position_modified(self):
        person = api.content.create(container=self.pf, type="person", id="tester", lastname=u"Tester")
        person.invokeFactory(
            "held_position",
            "hp1",
            position=RelationValue(self.intids.getId(self.pgof["direction-generale"])),
        )
        hp = person["hp1"]
        self.assertListEqual(self._person_usages(person), [])
        # modifying the usages reindexes the person (held_position_modified subscriber)
        hp.usages = ["approving"]
        modified(hp, Attributes(IUsagesBehavior, "IUsagesBehavior.usages"))
        self.assertListEqual(self._person_usages(person), ["approving"])
        # a modification not touching usages leaves the index untouched
        hp.usages = ["signer"]
        modified(hp, Attributes(IBasic, "IBasic.title"))
        self.assertListEqual(self._person_usages(person), ["approving"])

    def test_held_position_removed(self):
        person = api.content.create(container=self.pf, type="person", id="tester", lastname=u"Tester")
        person.invokeFactory(
            "held_position",
            "hp1",
            position=RelationValue(self.intids.getId(self.pgof["direction-generale"])),
            usages=["signer"],
        )
        self.assertListEqual(self._person_usages(person), ["signer"])
        # removing the held position reindexes the person (held_position_removed subscriber)
        api.content.delete(person["hp1"])
        self.assertListEqual(self._person_usages(person), [])

    def _answered(self, imail):
        """Return True if the incoming mail is found as answered (hasResponse marker) in the catalog."""
        return len(self.portal.portal_catalog(UID=imail.UID(), markers="hasResponse")) == 1

    def test_update_relations(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.assertFalse(self._answered(imail))
        # an outgoing mail replying to an incoming mail marks the latter as answered
        omail.reply_to = [RelationValue(self.intids.getId(imail))]
        modified(omail)
        self.assertTrue(self._answered(imail))
        # the reply link is removed: the incoming mail is no more answered
        omail.reply_to = []
        modified(omail)
        self.assertFalse(self._answered(imail))

    def test_remove_relations(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        omail.reply_to = [RelationValue(self.intids.getId(imail))]
        modified(omail)
        self.assertTrue(self._answered(imail))
        # the reply is deleted: the incoming mail is no more answered
        api.content.delete(obj=omail, check_linkintegrity=False)
        self.assertFalse(self._answered(imail))

    def test_im_edit_finished(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        request = imail.REQUEST
        # the editor can still view the mail: no redirection
        zope.event.notify(EditFinishedEvent(imail))
        self.assertIsNone(request.response.getHeader("location"))
        # the editor cannot view the mail anymore: redirected to the incoming mails dashboard with a message
        self.change_user("agent1")
        self.assertFalse(api.user.has_permission("View", obj=imail))
        zope.event.notify(EditFinishedEvent(imail))
        all_mails = self.portal["incoming-mail"]["mail-searches"]["all_mails"]
        self.assertEqual(
            request.response.getHeader("location"),
            "{}/incoming-mail/mail-searches#c1={}".format(self.portal.absolute_url(), all_mails.UID()),
        )
        msgs = IStatusMessage(request).show()
        self.assertEqual(msgs[-1].type, u"warning")
        self.assertEqual(
            msgs[-1].message,
            u"You have been redirected here because you do not have access anymore to the element you just edited.",
        )

    def test_dexterity_transition(self):
        task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        old = DateTime("2020/01/01")
        task.setModificationDate(old)
        task.reindexObject(idxs=["modified"])
        recently_modified = {"UID": task.UID(), "modified": {"query": DateTime("2020/01/02"), "range": "min"}}
        self.assertEqual(len(self.portal.portal_catalog(**recently_modified)), 0)
        # a transition is a modification: the modification date is updated and reindexed
        api.content.transition(task, transition="do_to_assign")
        self.assertGreater(task.modified(), old)
        self.assertEqual(len(self.portal.portal_catalog(**recently_modified)), 1)

    def test_group_unassignment(self):
        self.addCleanup(reset_dms_config)
        grh_uid = self.pgof["direction-generale"]["grh"].UID()
        # an agent removed from the encoders of a service: his held position (as OM sender) is deactivated
        hp = self.pf["agent"]["agent-grh"]
        self.assertEqual(api.content.get_state(hp), "active")
        api.group.remove_user(groupname="{}_encodeur".format(grh_uid), username="agent")
        self.assertEqual(api.content.get_state(hp), "deactivated")
        # the last n+1 validator removed from a service: the service has no more validation level
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertTrue(config["proposed_to_n_plus_1"][grh_uid][2])
        self.assertEqual(config["proposed_to_manager"][grh_uid][0], "propose_to_n_plus_1")
        api.group.remove_user(groupname="{}_n_plus_1".format(grh_uid), username="chef")
        config = get_dms_config(["transitions_levels", "dmsincomingmail"])
        self.assertFalse(config["proposed_to_n_plus_1"][grh_uid][2])
        self.assertEqual(config["proposed_to_manager"][grh_uid][0], "propose_to_agent")

    def test_plonegroup_contact_changed(self):
        pc = self.portal.portal_catalog
        dg = self.pgof["direction-generale"]
        secr = dg["secretariat"]
        folders = (self.portal["templates"]["om"], self.portal["contacts"]["contact-lists-folder"])
        for folder in folders:
            self.assertEqual(folder[secr.UID()].title, u"Direction générale - Secrétariat")
        # renaming a service renames its templates and contact lists folders, and the sub-services ones
        dg.title = u"Direction générale bis"
        modified(dg)
        for folder in folders:
            self.assertEqual(folder[dg.UID()].title, u"Direction générale bis")
            self.assertEqual(folder[secr.UID()].title, u"Direction générale bis - Secrétariat")
            self.assertEqual(len(pc(UID=folder[secr.UID()].UID(), Title=u"bis")), 1)
        # an organization outside the own organization is not concerned
        elec = self.portal["contacts"]["electrabel"]
        elec.title = u"Electrabel bis"
        modified(elec)
        self.assertNotIn(elec.UID(), folders[0])

    def test_mark_contact(self):
        def provided(obj, iface):
            return len(self.portal.portal_catalog(UID=obj.UID(), object_provides=iface.__identifier__)) == 1

        contacts = self.portal["contacts"]
        # a service added in the own organization
        org = api.content.create(container=self.pgof, type="organization", id="new-service", title=u"Nouveau")
        self.assertTrue(provided(org, IPloneGroupContact))
        self.assertFalse(provided(org, INotPloneGroupContact))
        # a person added in the personnel folder
        person = api.content.create(container=self.pf, type="person", id="tester", lastname=u"Tester")
        self.assertTrue(provided(person, IPersonnelContact))
        self.assertFalse(provided(person, INotPloneGroupContact))
        # an external person
        ext = api.content.create(container=contacts, type="person", id="external", lastname=u"External")
        self.assertTrue(provided(ext, INotPloneGroupContact))
        self.assertFalse(provided(ext, IPersonnelContact))
        # the external person is moved in the personnel folder
        ext = api.content.move(source=ext, target=self.pf)
        self.assertTrue(provided(ext, IPersonnelContact))
        self.assertFalse(provided(ext, INotPloneGroupContact))
        # and moved out again
        ext = api.content.move(source=ext, target=contacts)
        self.assertTrue(provided(ext, INotPloneGroupContact))
        self.assertFalse(provided(ext, IPersonnelContact))

    def test_contact_added(self):
        contacts = self.portal["contacts"]
        # contact group encoder not activated: no creating group
        org = api.content.create(container=contacts, type="organization", id="org1", title=u"Organisation 1")
        self.assertIsNone(getattr(org, "creating_group", None))
        # contact group encoder activated: the creating group of the creator is stored
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder", True)
        org0, org1 = get_registry_organizations()[:2]
        api.group.add_user(groupname="{}_{}".format(org0, CREATING_GROUP_SUFFIX), username="chef")
        api.group.add_user(groupname="{}_{}".format(org1, CREATING_GROUP_SUFFIX), username="encodeur")
        self.change_user("encodeur")
        org = api.content.create(container=contacts, type="organization", id="org2", title=u"Organisation 2")
        self.assertEqual(org.creating_group, org1)
        # the stored value doesn't depend on the user reading it (the field default is the user creating group)
        self.change_user("siteadmin")
        self.assertEqual(org.creating_group, org1)

    def test_contact_modified(self):
        hp = self.pf["chef"]["responsable-grh"]
        voc = OMSenderVocabulary()
        self.assertNotIn(u"Chefbis", voc(self.portal).getTerm(hp.UID()).title)
        # a personnel person is renamed: the senders vocabulary shows the new name
        chef = self.pf["chef"]
        chef.lastname = u"Chefbis"
        modified(chef)
        self.assertIn(u"Chefbis", voc(self.portal).getTerm(hp.UID()).title)
        # a personnel held position is deactivated: it's no more an active sender
        active_voc = OMActiveSenderVocabulary()
        self.assertIn(hp.UID(), active_voc(self.portal).by_value)
        api.content.transition(hp, "deactivate")
        self.assertNotIn(hp.UID(), active_voc(self.portal).by_value)
        self.assertIn(hp.UID(), voc(self.portal).by_value)

    def test_personnel_contact_removed(self):
        # a held position not used as outgoing mail sender can be deleted
        api.content.delete(obj=self.pf["chef"]["responsable-batiments"])
        self.assertNotIn("responsable-batiments", self.pf["chef"])
        # a held position used as outgoing mail sender (reponse1): its deletion is refused
        hp = self.pf["chef"]["responsable-grh"]
        self.assertEqual(get_object(oid="reponse1", ptype="dmsoutgoingmail").sender, hp.UID())
        self.assertRaises(LinkIntegrityNotificationException, api.content.delete, obj=hp)

    def test_personnel_contact_will_be_removed(self):
        rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        hp = self.pf["bourgmestre"]["bourgmestre"]
        # a held position not used in signer rules can be deleted
        api.content.delete(obj=self.pf["agent1"]["agent-evenements"])
        self.assertNotIn("agent-evenements", self.pf["agent1"])
        # a held position used as signer in the signer rules: its deletion is refused
        self.assertIn(hp.UID(), [rule["signer"] for rule in api.portal.get_registry_record(rk)])
        self.assertRaises(LinkIntegrityNotificationException, api.content.delete, obj=hp)

    def test_i_annex_will_be_removed(self):
        # approval started: a file to approve cannot be deleted
        request, files = create_sign_request(self.portal, oid="sr-started")
        self.portal.portal_workflow.doActionFor(request, "propose_to_approve")
        self.assertRaises(Redirect, api.content.delete, obj=files[0])
        self.assertIn(files[0].getId(), request)
        msgs = IStatusMessage(request.REQUEST).show()
        self.assertEqual(msgs[-1].type, u"error")
        self.assertEqual(
            msgs[-1].message,
            translate(
                _(u"You cannot delete a file '${title}' part of already started esign process !",
                  mapping={"title": u"3-degradation-voirie"}),
                context=request.REQUEST,
            ),
        )
        # approval not started: deleting a file to approve must be confirmed (link integrity breach)
        request, files = create_sign_request(self.portal, oid="sr-created")
        self.assertIn(files[0].UID(), ISignRequestApproval(request).files_uids)
        self.assertRaises(LinkIntegrityNotificationException, api.content.delete, obj=files[0])

    def test_member_area_added(self):
        mtool = self.portal.portal_membership
        mtool.memberareaCreationFlag = 1
        mtool.createMemberArea("agent")
        area = self.portal["Members"]["agent"]
        self.assertEqual(area.portal_type, "member_area")
        # nothing can be added directly in the personal folder
        self.assertEqual(area.getConstrainTypesMode(), 1)
        self.assertEqual(list(area.getLocallyAllowedTypes()), [])
        # a personal contact lists folder is created, owned by the user
        self.assertIn("contact-lists", area)
        folder = area["contact-lists"]
        self.assertEqual(folder.getConstrainTypesMode(), 1)
        self.assertEqual(list(folder.getLocallyAllowedTypes()), ["contact_list"])
        self.assertEqual(list(folder.getImmediatelyAddableTypes()), ["contact_list"])
        self.assertEqual(sorted(folder.get_local_roles_for_userid("agent")), ["Contributor", "Editor", "Reader"])

    def test_folder_added(self):
        # folders added in om templates, email templates or contact lists are only "add" folders
        for container in (
            self.portal["templates"]["om"],
            self.portal["templates"]["oem"],
            self.portal["contacts"]["contact-lists-folder"],
        ):
            folder = api.content.create(container=container, type="Folder", id="new-folder", title=u"Nouveau")
            self.assertTrue(IActionsPanelFolderOnlyAdd.providedBy(folder), container.getId())
            self.assertTrue(INextPrevNotNavigable.providedBy(folder), container.getId())
        # elsewhere, a folder is a "normal" folder
        folder = api.content.create(container=self.portal, type="Folder", id="new-folder", title=u"Nouveau")
        self.assertFalse(IActionsPanelFolderOnlyAdd.providedBy(folder))
        self.assertFalse(INextPrevNotNavigable.providedBy(folder))

    def test_wsclient_configuration_changed(self):
        record = getUtility(IRegistry).records[
            "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"
        ]
        actions = self.portal.portal_actions
        self.assertNotIn("plonemeeting_wsclient_action_1", actions.object_buttons)
        self.assertListEqual(actions.object_portlet.objectIds(), ["batchimport", "im-listing"])
        # the "send to PloneMeeting" actions are generated and also shown in the actions portlet, before im-listing
        zope.event.notify(RecordModifiedEvent(record, record.value, record.value))
        self.assertIn("plonemeeting_wsclient_action_1", actions.object_buttons)
        self.assertListEqual(
            actions.object_portlet.objectIds(), ["batchimport", "plonemeeting_wsclient_action_1", "im-listing"]
        )
        # regenerated actions are not duplicated
        zope.event.notify(RecordModifiedEvent(record, record.value, record.value))
        self.assertListEqual(
            actions.object_portlet.objectIds(), ["batchimport", "plonemeeting_wsclient_action_1", "im-listing"]
        )

    def test_record_modified(self):
        action = self.portal.portal_actions.user["audit-contacts"]
        self.assertFalse(action.visible)
        # activating the contacts access audit shows the audit user action
        record = "collective.contact.core.interfaces.IContactCoreParameters.audit_contact_access"
        api.portal.set_registry_record(record, True)
        self.assertTrue(action.visible)
        api.portal.set_registry_record(record, False)
        self.assertFalse(action.visible)

    def test_zope_ready(self):
        sml = getSiteManager(self.portal)
        sml.unregisterUtility(provided=IRAMCache)
        sml.registerUtility(component=RAMCache(), provided=IRAMCache)
        # the process-start hook opens its own ZODB connection and commits: both are patched here
        with patch("imio.dms.mail.subscribers.get_zope_root", return_value=self.layer["app"]):
            with patch("imio.dms.mail.subscribers.transaction.commit") as commit:
                # no plone-path configured for imio.dms.mail: nothing is done
                zope_ready(None)
                self.assertNotIsInstance(getUtility(IRAMCache), IMIORAMCache)
                self.assertFalse(commit.called)
                # plone-path configured: the site uses the imio.helpers ram cache
                config = getConfiguration().product_config
                config["imio.dms.mail"] = {"plone-path": self.portal.getId()}
                self.addCleanup(config.pop, "imio.dms.mail")
                zope_ready(None)
                self.assertIsInstance(getUtility(IRAMCache), IMIORAMCache)
                self.assertTrue(commit.called)


class TestSignRequestSubscribers(unittest.TestCase, ImioTestHelpers):
    """Integration tests (no mock) for the sign_request event subscribers."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        self.pf = self.portal["contacts"]["personnel-folder"]

    def test_sign_request_added(self):
        # a titled request computes signers/approvers on add (added -> modified -> update_signers)
        request, _files = create_sign_request(self.portal, oid="sr-add", nb_files=0)
        self.assertEqual(ISignRequestApproval(request).annot["approvers"], [["dirg"], ["bourgmestre"]])

    def test_sign_request_transition(self):
        request, _files = create_sign_request(self.portal, oid="sr-tr", nb_files=1)
        self.assertIsNone(ISignRequestApproval(request).current_nb)
        self.portal.portal_workflow.doActionFor(request, "propose_to_approve")
        self.assertEqual(ISignRequestApproval(request).current_nb, 0)

    def test_sign_request_modified(self):
        request, _files = create_sign_request(self.portal, oid="sr-mod", nb_files=0)
        request.signers = [{"number": 1, "signer": self.pf["bourgmestre"]["bourgmestre"].UID(),
                            "approvings": [u"_themself_"], "editor": True}]
        modified(request, Attributes(ISignRequestSigningBehavior, "ISignRequestSigningBehavior.signers"))
        self.assertEqual(ISignRequestApproval(request).annot["approvers"], [["bourgmestre"]])

    def test_sign_request_modified_duplicate_email(self):
        request, _files = create_sign_request(self.portal, oid="sr-dup", nb_files=0)
        # two signers resolving to the same person => update_signers raises, surfaced as Invalid
        request.signers = [
            {"number": 1, "signer": self.pf["dirg"]["directeur-general"].UID(),
             "approvings": [u"_themself_"], "editor": True},
            {"number": 2, "signer": self.pf["dirg"]["directeur-general"].UID(),
             "approvings": [u"_themself_"], "editor": False},
        ]
        with self.assertRaises(Invalid):
            modified(request, Attributes(ISignRequestSigningBehavior, "ISignRequestSigningBehavior.signers"))

    def test_i_annex_added(self):
        request, _files = create_sign_request(self.portal, oid="sr-annex", nb_files=0)
        approval = ISignRequestApproval(request)
        self.assertEqual(approval.annot["files"], [])
        ct = self.portal["annexes_types"]["sign_request_appendix_files"]["sign-request-appendix-file"]
        filename = u"3-degradation-voirie.odt"
        with open("%s/batchimport/toprocess/requests/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            afile = createContentInContainer(
                request, "dmsappendixfile", id="f1", scan_id="012999900000601",
                file=NamedBlobFile(fo.read(), filename=filename), content_category=calculate_category_id(ct),
            )
        self.assertIn(afile.UID(), approval.annot["files"])
