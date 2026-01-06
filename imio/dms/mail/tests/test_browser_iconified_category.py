# -*- coding: utf-8 -*-
from collective.dms.basecontent.browser.listing import CategorizedContent
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.browser.iconified_category import ApprovedChangeView
from imio.dms.mail.browser.iconified_category import ApprovedColumn
from imio.dms.mail.browser.iconified_category import SignedChangeView
from imio.dms.mail.browser.iconified_category import SignedColumn
from imio.dms.mail.Extensions.demo import activate_signing
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.helpers.content import uuidToCatalogBrain
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestBrowserIconifiedCategory(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pw = self.portal.portal_workflow
        self.change_user("siteadmin")
        activate_signing(self.portal)

        # TODO patch workflow to add to_print state
        # sva = OMToPrintAdaptation()
        # sva.patch_workflow("outgoingmail_workflow")

        # Create outgoing mail 1 with one eSign signer and one file to approve
        intids = getUtility(IIntIds)
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "type1",
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
            "signers": [
                {
                    "number": 1,
                    "signer": self.portal["contacts"]["personnel-folder"]["dirg"]["directeur-general"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": True,
                }
            ],
            "esign": True,
        }
        self.omail1 = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om1", **params)
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            self.file1 = createContentInContainer(
                self.omail1,
                "dmsommainfile",
                id="file1",
                scan_id="012999900000600",
                file=file_object,
                content_category=calculate_category_id(ct),
            )

        # Create outgoing mail 2 with two eSign signers and one file to approve
        params["signers"].append(
            {
                "number": 2,
                "signer": self.portal["contacts"]["personnel-folder"]["bourgmestre"]["bourgmestre"].UID(),
                "approvings": [u"_themself_"],
                "editor": False,
            }
        )
        self.omail2 = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om2", **params)
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            self.file2 = createContentInContainer(
                self.omail2,
                "dmsommainfile",
                id="file2",
                scan_id="012999900000601",
                file=file_object,
                content_category=calculate_category_id(ct),
            )

    def test_approved_column(self):
        """Test column rendering"""
        file1_cc = CategorizedContent(self.omail1, uuidToCatalogBrain(self.file1.UID()))
        col = ApprovedColumn(self.omail1, self.portal.REQUEST, None)

        # Test get_url
        # "created"
        self.change_user("agent")
        self.assertEqual(col.get_url(file1_cc), "%s/@@iconified-approved" % self.file1.absolute_url())
        # "to_approve"
        self.pw.doActionFor(self.omail1, "propose_to_approve")
        self.assertEqual(col.get_url(file1_cc), "#")
        self.change_user("dirg")
        self.assertEqual(col.get_url(file1_cc), "%s/@@iconified-approved" % self.file1.absolute_url())
        # FIXME This raises Unauthorized but still passes
        self.assertEqual(
            col.get_action_view(file1_cc)(),
            u'{"msg":"En attente de votre approbation (cliquer pour approuver)","status":1,"reload": true}',
        )
        # TODO "to_print"
        # "to_be_signed"
        self.assertEqual(col.get_url(file1_cc), "#")
        # "signed"
        self.change_user("encodeur")
        self.pw.doActionFor(self.omail1, "mark_as_signed")
        self.assertEqual(col.get_url(file1_cc), "#")
        # "sent"
        self.pw.doActionFor(self.omail1, "mark_as_sent")
        self.assertEqual(col.get_url(file1_cc), "#")

        # Test css_class
        self.change_user("admin")
        file2_cc = CategorizedContent(self.omail2, uuidToCatalogBrain(self.file2.UID()))
        col = ApprovedColumn(self.omail2, self.portal.REQUEST, None)
        # "created", nothing to approve
        col.get_action_view(file2_cc)()  # deactivate approval on file2
        # file2_brain = get_brain(self.file2)
        self.change_user("dirg")
        self.assertEqual(col.css_class(file2_cc), " to-approve ")
        self.assertEqual(col.msg, u"Deactivated for approval")
        self.change_user("agent")
        self.assertEqual(col.css_class(file2_cc), " to-approve editable")
        self.assertEqual(col.msg, u"Deactivated for approval (click to activate)")
        # "created", one file to approve
        col.get_action_view(file2_cc)()  # activate approval on file2
        # file2_brain = get_brain(self.file2)
        self.change_user("dirg")
        self.assertEqual(col.css_class(file2_cc), " active to-approve")
        self.assertEqual(col.msg, u"Activated for approval")
        self.change_user("agent")
        self.assertEqual(col.css_class(file2_cc), " active to-approve editable")
        self.assertEqual(col.msg, u"Activated for approval (click to deactivate)")
        # "to_approve"
        self.pw.doActionFor(self.omail2, "propose_to_approve")
        clean_borg_cache(col.request)
        self.assertEqual(col.css_class(file2_cc), " cant-approve")
        self.assertEqual(col.msg, u"Waiting for the first approval")
        self.change_user("dirg")
        self.assertEqual(col.css_class(file2_cc), " editable")
        self.assertEqual(col.msg, u"Waiting for your approval (click to approve)")
        self.change_user("bourgmestre")
        self.assertEqual(col.css_class(file2_cc), " waiting")
        self.assertEqual(col.msg, u"Waiting for other approval before you can approve")
        self.change_user("dirg")
        col.get_action_view(file2_cc)()  # dirg approves file
        clean_borg_cache(col.request)  # because approval borg roles are changed
        self.assertEqual(col.css_class(file2_cc), " partially-approved")
        self.assertEqual(col.msg, u"Partially approved. Still waiting for other approval(s)")
        self.change_user("agent")
        self.assertEqual(col.css_class(file2_cc), " partially-approved")
        self.assertEqual(col.msg, u"Partially approved. Still waiting for other approval(s)")
        self.change_user("bourgmestre")
        self.assertEqual(col.css_class(file2_cc), " editable")
        self.assertEqual(col.msg, u"Waiting for your approval (click to approve)")
        col.get_action_view(file2_cc)()  # bourgmestre approves file
        clean_borg_cache(col.request)  # because transition was done
        # file2_brain = get_brain(self.file2)
        # "to_be_signed"
        self.assertEqual(col.css_class(file2_cc), " totally-approved")
        self.assertEqual(col.msg, u"Totally approved")
        # "sent", approval deactivated
        self.change_user("agent")
        self.pw.doActionFor(self.omail2, "back_to_creation")
        clean_borg_cache(col.request)
        col.get_action_view(file2_cc)()  # Set as not to approve
        file2_cc = CategorizedContent(self.omail2, uuidToCatalogBrain(self.file2.UID()))  # reload metadata
        self.pw.doActionFor(self.omail2, "mark_as_sent")
        self.assertEqual(col.css_class(file2_cc), " to-approve")
        self.assertEqual(col.msg, u"Deactivated for approval")

    def test_approved_change_view(self):
        """Test ApprovedChangeView"""
        view = ApprovedChangeView(self.file1, self.portal.REQUEST)
        # Test get_next_values
        # "created"
        old_values = {"to_approve": True, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Deactivated for approval (click to activate)")
        old_values = {"to_approve": True, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Deactivated for approval (click to activate)")
        old_values = {"to_approve": False, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (1, {"to_approve": True, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": False, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (1, {"to_approve": True, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        # "to_approve"
        self.pw.doActionFor(self.omail1, "propose_to_approve")
        old_values = {"to_approve": False, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": False, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": True, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": True, "approved": True}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": True, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": True, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        self.change_user("dirg")
        old_values = {"to_approve": False, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": False, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": False, "approved": False}))
        self.assertEqual(view.msg, u"Activated for approval (click to deactivate)")
        old_values = {"to_approve": True, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (1, {"to_approve": True, "approved": True}))
        self.assertEqual(view.msg, u"Waiting for your approval (click to approve)")
        # "to_be_signed"
        self.assertEqual(api.content.get_state(self.omail1), "to_be_signed")
        self.assertTrue(OMApprovalAdapter(self.omail1).is_file_approved(self.file1.UID()))
        old_values = {"to_approve": True, "approved": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": True, "approved": False}))
        self.assertEqual(view.msg, u"Waiting for your approval (click to approve)")
        old_values = {"to_approve": True, "approved": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_approve": True, "approved": True}))
        self.assertEqual(view.msg, u"Waiting for your approval (click to approve)")

    def test_signed_column(self):
        """Test signed column rendering"""
        file1_cc = CategorizedContent(self.omail1, uuidToCatalogBrain(self.file1.UID()))
        col = SignedColumn(self.omail1, self.portal.REQUEST, None)

        # Test get_url
        # "created"
        self.change_user("agent")
        self.assertEqual(col.get_url(file1_cc), "%s/@@iconified-signed" % self.file1.absolute_url())
        # "to_approve"
        self.pw.doActionFor(self.omail1, "propose_to_approve")
        self.assertEqual(col.get_url(file1_cc), "#")
        self.change_user("dirg")
        self.assertEqual(col.get_url(file1_cc), "#")
        # TODO "to_print"
        # "to_be_signed"
        ApprovedChangeView(self.file1, self.portal.REQUEST)()  # transition to_be_signed
        self.assertEqual(col.get_url(file1_cc), "%s/@@iconified-signed" % self.file1.absolute_url())
        # "signed"
        self.change_user("encodeur")
        self.pw.doActionFor(self.omail1, "mark_as_signed")
        self.assertEqual(col.get_url(file1_cc), "#")
        # "sent"
        self.pw.doActionFor(self.omail1, "mark_as_sent")
        self.assertEqual(col.get_url(file1_cc), "#")

        # Test css_class
        self.change_user("admin")
        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            file3 = createContentInContainer(
                self.omail2,
                "dmsommainfile",
                id="file3",
                scan_id="012999900000602",
                file=file_object,
                content_category=calculate_category_id(ct),
            )
        file2_cc = CategorizedContent(self.omail2, uuidToCatalogBrain(self.file2.UID()))
        file3_cc = CategorizedContent(self.omail2, uuidToCatalogBrain(file3.UID()))
        col = SignedColumn(self.omail2, self.portal.REQUEST, None)
        # "created"
        self.change_user("dirg")
        self.assertEqual(col.css_class(file2_cc), "")
        self.change_user("agent")
        self.assertEqual(col.css_class(file2_cc), "")
        ApprovedChangeView(file3, self.portal.REQUEST)()  # Set file3 not to_approve
        self.assertEqual(col.css_class(file3_cc), " editable")
        self.assertEqual(
            col.get_action_view(file3_cc)(),
            u'{"msg":"Cet \xe9l\xe9ment ne doit pas \xeatre sign\xe9","status":-1,"reload": true}',
        )  # Set file3 not to_sign
        self.assertEqual(col.css_class(file3_cc), " deactivated editable")
        self.change_user("dirg")
        self.assertEqual(col.css_class(file3_cc), " deactivated ")
        self.change_user("agent")
        # "to_approve"
        self.pw.doActionFor(self.omail2, "propose_to_approve")
        clean_borg_cache(col.request)
        self.assertEqual(col.css_class(file2_cc), "")
        self.assertEqual(col.css_class(file3_cc), " deactivated")
        self.change_user("bourgmestre")
        self.assertEqual(col.css_class(file2_cc), "")
        self.assertEqual(col.css_class(file3_cc), " deactivated")
        self.change_user("dirg")
        self.assertEqual(col.css_class(file2_cc), "")
        self.assertEqual(col.css_class(file3_cc), " deactivated")
        ApprovedChangeView(self.file2, self.portal.REQUEST)()  # dirg approves file
        clean_borg_cache(col.request)  # because approval borg roles are changed
        self.change_user("bourgmestre")
        ApprovedChangeView(self.file2, self.portal.REQUEST)()  # bourgmestre approves file
        clean_borg_cache(col.request)  # because transition was done
        # "to_be_signed"
        self.change_user("agent")
        self.assertEqual(col.css_class(file2_cc), "")
        self.assertEqual(col.css_class(file3_cc), " deactivated")
        self.assertEqual(
            col.get_action_view(file2_cc)(), u'{"msg":"Cet \xe9l\xe9ment est sign\xe9","status":1}'
        )  # Set file2 as signed
        file2_cc = CategorizedContent(self.omail2, uuidToCatalogBrain(self.file2.UID()))  # reload metadata
        self.assertEqual(col.css_class(file2_cc), " active")
        # "sent"
        self.pw.doActionFor(self.omail2, "mark_as_sent")
        self.assertEqual(col.css_class(file2_cc), " active")
        self.assertEqual(col.css_class(file3_cc), " deactivated")

    def test_signed_change_view(self):
        """Test ApprovedChangeView"""
        view = SignedChangeView(self.file1, self.portal.REQUEST)
        # Test get_next_values
        # "created"
        old_values = {"to_sign": True, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (-1, {"to_sign": False, "signed": False}))
        old_values = {"to_sign": True, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (-1, {"to_sign": False, "signed": False}))
        old_values = {"to_sign": False, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": True, "signed": False}))
        old_values = {"to_sign": False, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": True, "signed": False}))
        # "to_approve"
        self.pw.doActionFor(self.omail1, "propose_to_approve")
        old_values = {"to_sign": False, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": False, "signed": False}))
        old_values = {"to_sign": False, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": False, "signed": True}))
        old_values = {"to_sign": True, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": True, "signed": True}))
        old_values = {"to_sign": True, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": True, "signed": False}))
        self.change_user("dirg")
        ApprovedChangeView(self.file1, self.portal.REQUEST)()  # dirg approves file
        clean_borg_cache(view.request)  # because approval borg roles are changed
        # "to_be_signed"
        self.assertEqual(api.content.get_state(self.omail1), "to_be_signed")
        old_values = {"to_sign": False, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": False, "signed": False}))
        old_values = {"to_sign": False, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": False, "signed": True}))
        old_values = {"to_sign": True, "signed": True}
        self.assertEqual(view._get_next_values(old_values), (0, {"to_sign": True, "signed": False}))
        old_values = {"to_sign": True, "signed": False}
        self.assertEqual(view._get_next_values(old_values), (1, {"to_sign": True, "signed": True}))
