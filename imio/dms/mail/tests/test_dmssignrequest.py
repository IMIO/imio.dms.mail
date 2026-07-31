# -*- coding: utf-8 -*-
"""Test the sign_request content type (dmssignrequest.py)."""
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail import get_empty_signers_value
from imio.dms.mail.dmssignrequest import filter_signrequest_assigned_users
from imio.dms.mail.dmssignrequest import IImioDmsSignRequest
from imio.dms.mail.dmssignrequest import incrementSignRequestNumber
from imio.dms.mail.dmssignrequest import signrequest_internal_reference_number_indexer
from imio.dms.mail.dmssignrequest import SignRequestWfConditionsAdapter
from imio.dms.mail.interfaces import ISignRequestApproval
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.autoform.interfaces import OMITTED_KEY
from Products.PluginIndexes.common.UnIndex import _marker

import unittest


SIGNREQUEST_NUMBER = "collective.dms.mailcontent.browser.settings.IDmsMailConfig.signrequest_number"


class TestDmsSignRequest(unittest.TestCase, ImioTestHelpers):
    """Test dmssignrequest.py (mirror of test_dmsmail.py for the sign_request type)."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def _approve_all(self, request, files):
        """Approve every file at both signer levels (dirg then bourgmestre)."""
        self.portal.portal_workflow.doActionFor(request, "propose_to_approve")
        approval = ISignRequestApproval(request)
        for userid in ("dirg", "bourgmestre"):
            for afile in files:
                approval.approve_file(afile, userid, transition="propose_to_be_signed")

    def test_get_mainfiles(self):
        request, files = create_sign_request(self.portal, oid="sr-main")
        self.assertEqual(request.get_mainfiles(), [])

    def test_wf_conditions(self):
        request, files = create_sign_request(self.portal, oid="sr-wfc", signers=[])
        self.assertIsInstance(request.wf_conditions(), SignRequestWfConditionsAdapter)

    def test_SignRequestWfConditionsAdapter_can_be_approved(self):
        # empty signers placeholder => no approver => cannot be approved
        request, files = create_sign_request(self.portal, oid="sr-cba1", signers=get_empty_signers_value())
        self.assertFalse(request.wf_conditions().can_be_approved())
        # signers + file to approve => can be approved
        request, files = create_sign_request(self.portal, oid="sr-cba2")
        self.assertTrue(request.wf_conditions().can_be_approved())

    def test_SignRequestWfConditionsAdapter_can_be_signed(self):
        # no approvings => can be signed
        request, files = create_sign_request(self.portal, oid="sr-cbs1", signers=get_empty_signers_value())
        self.assertTrue(request.wf_conditions().can_be_signed())
        # approvings pending => cannot be signed
        request, files = create_sign_request(self.portal, oid="sr-cbs2")
        self.portal.portal_workflow.doActionFor(request, "propose_to_approve")
        self.assertFalse(request.wf_conditions().can_be_signed())
        # all approvings done => can be signed
        approval = ISignRequestApproval(request)
        for userid in ("dirg", "bourgmestre"):
            approval.approve_file(files[0], userid, transition="propose_to_be_signed")
        self.assertTrue(request.wf_conditions().can_be_signed())

    def test_SignRequestWfConditionsAdapter_can_mark_as_signed(self):
        request, files = create_sign_request(self.portal, oid="sr-cms", signers=[])
        self.assertTrue(request.wf_conditions().can_mark_as_signed())

    def test_SignRequestWfConditionsAdapter_can_close(self):
        request, files = create_sign_request(self.portal, oid="sr-cc", signers=[])
        self.assertTrue(request.wf_conditions().can_close())

    def test_has_approvings(self):
        # no approvers, no files
        request, files = create_sign_request(self.portal, oid="sr-ha1", signers=get_empty_signers_value(), nb_files=0)
        self.assertFalse(request.has_approvings())
        # approvers but no files
        request, files = create_sign_request(self.portal, oid="sr-ha2", nb_files=0)
        self.assertFalse(request.has_approvings())
        # approvers and file, not done
        request, files = create_sign_request(self.portal, oid="sr-ha3")
        self.assertTrue(request.has_approvings())
        self.assertFalse(request.has_approvings(all_done=True))
        # all done
        self._approve_all(request, files)
        self.assertTrue(request.has_approvings(all_done=True))

    def test_filter_signrequest_assigned_users(self):
        # the demand_sign groups (chef + dirg on the three "Direction" orgs) are set up by the step
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-sign-request", run_dependencies=False
        )
        self.assertEqual(len(filter_signrequest_assigned_users(None)), 0)
        selected_orgs = get_registry_organizations()
        self.change_user("chef")
        voc = filter_signrequest_assigned_users(selected_orgs[0])  # direction generale
        self.assertEqual(set(t.value for t in voc._terms), {"chef", "dirg"})

    def test_internal_reference_numbering(self):
        number = api.portal.get_registry_record(SIGNREQUEST_NUMBER)
        request, files = create_sign_request(self.portal, oid="sr-num", signers=[], nb_files=0)
        # reference computed from the tal expression and counter incremented
        self.assertEqual(request.internal_reference_no, u"D%04d" % number)
        self.assertEqual(api.portal.get_registry_record(SIGNREQUEST_NUMBER), number + 1)
        # _auto_ref False => reference still (re)set but counter left untouched
        request._auto_ref = False
        request.internal_reference_no = u""
        incrementSignRequestNumber(request, None)
        self.assertEqual(request.internal_reference_no, u"D%04d" % (number + 1))
        self.assertEqual(api.portal.get_registry_record(SIGNREQUEST_NUMBER), number + 1)

    def test_signrequest_internal_reference_number_indexer(self):
        request, files = create_sign_request(self.portal, oid="sr-idx", signers=[], nb_files=0)
        indexer = signrequest_internal_reference_number_indexer(request)
        self.assertEqual(indexer(), request.internal_reference_no)
        # empty reference is not indexed
        request.internal_reference_no = u""
        self.assertEqual(signrequest_internal_reference_number_indexer(request)(), _marker)

    def test_schema(self):
        self.assertTrue(IImioDmsSignRequest["treating_groups"].required)
        self.assertFalse(IImioDmsSignRequest["recipient_groups"].required)
        omitted = [entry[1] for entry in IImioDmsSignRequest.queryTaggedValue(OMITTED_KEY, [])]
        self.assertIn("notes", omitted)
        self.assertIn("related_docs", omitted)
