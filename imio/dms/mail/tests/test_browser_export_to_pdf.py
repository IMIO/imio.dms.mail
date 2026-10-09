# -*- coding: utf-8 -*-
""" browser/export_to_pdf.py tests for this package."""
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import update_categorized_elements
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser import export_to_pdf
from imio.dms.mail.browser.export_to_pdf import ExportToPDFAfterSignatureVocabulary
from imio.dms.mail.browser.export_to_pdf import ExportToPDFBeforeSignatureVocabulary
from imio.dms.mail.browser.export_to_pdf import superseded_uids
from imio.dms.mail.interfaces import IReqDashboardBatchActions
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.helpers.test_helpers import ImioTestHelpers
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


ODT_PATH = u"%s/batchimport/toprocess/incoming-mail/in-courrier3.odt" % PRODUCT_DIR
PDF_PATH = u"%s/batchimport/toprocess/incoming-mail/in-courrier2.pdf" % PRODUCT_DIR
DOCX_PATH = u"%s/batchimport/toprocess/incoming-mail/in-courrier4.docx" % PRODUCT_DIR


class ExportToPdfTestCase(unittest.TestCase, ImioTestHelpers):
    """Common fixture: an outgoing mail holding ged files and an appendix."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.change_user("siteadmin")
        intids = getUtility(IIntIds)
        self.omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "om-export",
            title=u"Courrier sortant export",
            internal_reference_no=internalReferenceOutgoingMailDefaultValue(DummyView(self.portal, self.request)),
            mail_type="courrier",
            treating_groups=self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
            recipients=[RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            sender=self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            send_modes=u"post",
        )
        self.ged_ct = calculate_category_id(
            self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"])
        self.app_ct = calculate_category_id(
            self.portal["annexes_types"]["outgoing_appendix_files"]["outgoing-appendix-file"])
        # b_pdf and a_odt are ged files, appendix is an appendix file
        self.b_pdf = self._add_file(u"b pdf", PDF_PATH)
        self.a_odt = self._add_file(u"a odt", ODT_PATH)
        self.appendix = self._add_file(u"appendix", PDF_PATH, portal_type="dmsappendixfile")
        for obj in (self.b_pdf, self.a_odt, self.appendix):
            self._set_infos(obj, to_print=True)

    def _add_file(self, title, path, portal_type="dmsommainfile", **kwargs):
        with open(path, "rb") as fo:
            return createContentInContainer(
                self.omail,
                portal_type,
                title=title,
                file=NamedBlobFile(fo.read(), filename=path.split("/")[-1]),
                content_category=portal_type == "dmsommainfile" and self.ged_ct or self.app_ct,
                **kwargs)

    def _set_infos(self, obj, **kwargs):
        """Set attributes on a file and mirror them in the parent categorized_elements."""
        for key, value in kwargs.items():
            setattr(obj, key, value)
        category = get_category_object(obj, obj.content_category)
        update_categorized_elements(self.omail, obj, category)
        self.omail.categorized_elements[obj.UID()].update(kwargs)
        self.omail._p_changed = True

    def _clean_cache(self):
        """get_categorized_elements is cached on the request, files were added since."""
        annotations = IAnnotations(self.request)
        for key in list(annotations.keys()):
            if key.startswith("collective.iconifiedcategory.get_categorized_elements"):
                del annotations[key]


class TestExportToPdf(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_pdf module level functions."""

    def test_superseded_uids(self):
        self.assertEqual(superseded_uids(self.omail), (set(), set()))
        # a pdf generated from a_odt supersedes it
        pdf = self._add_file(u"converted", PDF_PATH, conv_from_uid=self.a_odt.UID())
        self._clean_cache()
        self.assertEqual(superseded_uids(self.omail), (set(), {self.a_odt.UID()}))
        # a mailing generated from b_pdf supersedes it
        mailed = self._add_file(u"mailed", PDF_PATH)
        IAnnotations(mailed)["documentgenerator"] = {"mailed": True, "from_doc_uid": self.b_pdf.UID()}
        self._clean_cache()
        self.assertEqual(superseded_uids(self.omail), ({self.b_pdf.UID()}, {self.a_odt.UID()}))
        self.assertTrue(pdf)


class TestExportToPDFElementsVocabulary(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_pdf.ExportToPDFElementsVocabulary."""

    def test___call__(self):
        """Ged files first, then appendix files, each group alphabetically."""
        vocab = ExportToPDFBeforeSignatureVocabulary()(self.omail)
        self.assertEqual([term.token for term in vocab._terms],
                         [self.a_odt.getId(), self.b_pdf.getId(), self.appendix.getId()])
        # terms are numbered in that order
        self.assertIn(u"1. a odt", vocab._terms[0].title)
        self.assertIn(u"3. appendix", vocab._terms[2].title)
        # a file superseded by its mailing is not listed at all
        mailed = self._add_file(u"mailed", PDF_PATH)
        IAnnotations(mailed)["documentgenerator"] = {"mailed": True, "from_doc_uid": self.b_pdf.UID()}
        self._set_infos(mailed, to_print=True)
        self._clean_cache()
        vocab = ExportToPDFBeforeSignatureVocabulary()(self.omail)
        self.assertEqual([term.token for term in vocab._terms],
                         [self.a_odt.getId(), mailed.getId(), self.appendix.getId()])

    def test__prepare_annex_infos(self):
        """Only ordering and the mailing exclusion, see test___call__."""
        infos = [{"UID": "1", "portal_type": "dmsappendixfile", "title": u"a"},
                 {"UID": "2", "portal_type": "dmsommainfile", "title": u"z"},
                 {"UID": "3", "portal_type": "dmsommainfile", "title": u"B"}]
        res = ExportToPDFBeforeSignatureVocabulary()._prepare_annex_infos(self.omail, infos)
        self.assertEqual([i["UID"] for i in res], ["3", "2", "1"])

    def test__to_print(self):
        before = ExportToPDFBeforeSignatureVocabulary()
        after = ExportToPDFAfterSignatureVocabulary()
        ged = {"portal_type": "dmsommainfile", "to_print": True, "esigned": False}
        self.assertTrue(before._to_print(ged))
        self.assertTrue(after._to_print(ged))
        # to_print is off on main files once esigned: after signature, an e-signed file still counts
        ged["to_print"] = False
        self.assertFalse(before._to_print(ged))
        self.assertFalse(after._to_print(ged))
        ged["esigned"] = True
        self.assertFalse(before._to_print(ged))
        self.assertTrue(after._to_print(ged))
        app = {"portal_type": "dmsappendixfile", "to_print": True, "esigned": False}
        self.assertTrue(before._to_print(app))
        self.assertTrue(after._to_print(app))
        app["to_print"] = False
        self.assertFalse(before._to_print(app))
        self.assertFalse(after._to_print(app))

    def test__selectable_content_types(self):
        before = ExportToPDFBeforeSignatureVocabulary()
        after = ExportToPDFAfterSignatureVocabulary()
        ged = {"portal_type": "dmsommainfile"}
        app = {"portal_type": "dmsappendixfile"}
        self.assertEqual(before._selectable_content_types(ged),
                         (export_to_pdf.PDF, export_to_pdf.ODT, export_to_pdf.DOCX))
        self.assertEqual(before._selectable_content_types(app), (export_to_pdf.PDF,))
        self.assertEqual(after._selectable_content_types(ged), (export_to_pdf.PDF,))
        self.assertEqual(after._selectable_content_types(app), (export_to_pdf.PDF,))

    def test__check_disable_term(self):
        """Nothing to print, no pdf and superseded odt are disabled."""
        # before signature: everything is to_print, the ged odt stays selectable
        vocab = ExportToPDFBeforeSignatureVocabulary()(self.omail)
        self.assertEqual([term.disabled for term in vocab._terms], [False, False, False])
        # after signature: the ged odt is not concatenable anymore
        self._clean_cache()
        vocab = ExportToPDFAfterSignatureVocabulary()(self.omail)
        self.assertEqual([term.disabled for term in vocab._terms], [True, False, False])
        self.assertIn(u"[pdf required]", vocab._terms[0].title)
        # ged files not to print and not e-signed are disabled
        self._set_infos(self.a_odt, to_print=False)
        self._set_infos(self.b_pdf, to_print=False)
        self._clean_cache()
        vocab = ExportToPDFAfterSignatureVocabulary()(self.omail)
        self.assertEqual([term.disabled for term in vocab._terms], [True, True, False])
        self.assertIn(u"[not to print]", vocab._terms[0].title)
        # e-signed ged files are to print, but an odt is still not concatenable
        self._set_infos(self.a_odt, esigned=True)
        self._set_infos(self.b_pdf, esigned=True)
        self._clean_cache()
        vocab = ExportToPDFAfterSignatureVocabulary()(self.omail)
        self.assertEqual([term.disabled for term in vocab._terms], [True, False, False])
        self.assertIn(u"[pdf required]", vocab._terms[0].title)
        # an odt converted to pdf is disabled, whatever the mode
        self._add_file(u"converted", PDF_PATH, conv_from_uid=self.a_odt.UID())
        self._clean_cache()
        vocab = ExportToPDFBeforeSignatureVocabulary()(self.omail)
        self.assertEqual(vocab.getTermByToken(self.a_odt.getId()).disabled, True)
        self.assertIn(u"[converted to pdf]", vocab.getTermByToken(self.a_odt.getId()).title)


class TestExportToPDFForm(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_pdf.ExportToPDFForm."""

    def test_updateWidgets(self):
        """Everything that may be exported is preselected."""
        form = self.omail.restrictedTraverse("@@export-to-pdf-before-signature")
        form.update()
        self.assertEqual(form.widgets["elements"].value,
                         [self.a_odt.getId(), self.b_pdf.getId(), self.appendix.getId()])
        self.assertTrue(form.widgets["elements"].sortable)
        # after signature, the ged odt cannot be concatenated anymore
        self._clean_cache()
        form = self.omail.restrictedTraverse("@@export-to-pdf-after-signature")
        form.update()
        self.assertEqual(form.widgets["elements"].value, [self.b_pdf.getId(), self.appendix.getId()])
        # ged files not to print and not e-signed are not preselected
        self._set_infos(self.b_pdf, to_print=False)
        self._clean_cache()
        form = self.omail.restrictedTraverse("@@export-to-pdf-after-signature")
        form.update()
        self.assertEqual(form.widgets["elements"].value, [self.appendix.getId()])

    @unittest.skip("Skipping test_update_oo_warning")
    def test_update_oo_warning(self):
        """A warning is shown when LibreOffice does not answer."""
        original = export_to_pdf.oo_answers
        try:
            export_to_pdf.oo_answers = lambda server, port: False
            form = self.omail.restrictedTraverse("@@export-to-pdf-before-signature")
            form.update()
            self.assertIn(u"does not answer", form.status)
            export_to_pdf.oo_answers = lambda server, port: True
            form = self.omail.restrictedTraverse("@@export-to-pdf-before-signature")
            form.update()
            self.assertFalse(form.status)
        finally:
            export_to_pdf.oo_answers = original
        # nothing listens on port 1
        self.assertFalse(export_to_pdf.oo_answers("localhost", 1))

    def test__elements_content(self):
        """Odt and docx files are converted to pdf, the others are taken as is."""
        docx = self._add_file(u"c docx", DOCX_PATH)
        original = export_to_pdf.convert_file
        export_to_pdf.convert_file = lambda afile, **kwargs: "%PDF-converted"
        try:
            form = self.omail.restrictedTraverse("@@export-to-pdf-before-signature")
            content = form._elements_content({"elements": [self.a_odt.getId(), docx.getId(), self.b_pdf.getId()]})
        finally:
            export_to_pdf.convert_file = original
        self.assertEqual(content[self.a_odt.getId()], "%PDF-converted")
        self.assertEqual(content[docx.getId()], "%PDF-converted")
        self.assertEqual(content[self.b_pdf.getId()], self.b_pdf.file.data)


class TestExportToPDFBatchActionForm(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_pdf.ExportToPDFBatchActionForm."""

    def _form(self, name):
        return self.portal["outgoing-mail"]["mail-searches"].restrictedTraverse("@@%s" % name)

    def test_available(self):
        """The buttons depend on the dashboard collection, the form itself is available."""
        searches = self.portal["outgoing-mail"]["mail-searches"]
        original = export_to_pdf.getCurrentCollection
        try:
            export_to_pdf.getCurrentCollection = lambda context: searches["to_treat"]
            self.assertTrue(self._form("export-to-pdf-before-signature-batch-action").available())
            self.assertFalse(self._form("export-to-pdf-after-signature-batch-action").available())
            export_to_pdf.getCurrentCollection = lambda context: searches["searchfor_signed"]
            self.assertFalse(self._form("export-to-pdf-before-signature-batch-action").available())
            self.assertTrue(self._form("export-to-pdf-after-signature-batch-action").available())
            export_to_pdf.getCurrentCollection = lambda context: searches["all_mails"]
            self.assertFalse(self._form("export-to-pdf-before-signature-batch-action").available())
            self.assertFalse(self._form("export-to-pdf-after-signature-batch-action").available())
            self.request["uids"] = self.omail.UID()
            self.assertTrue(self._form("export-to-pdf-after-signature-batch-action").available())
        finally:
            export_to_pdf.getCurrentCollection = original

    def test__get_annexes(self):
        """The files preselected by the element export are taken, ged files first."""
        self.request["uids"] = self.omail.UID()
        form = self._form("export-to-pdf-before-signature-batch-action")
        form.update()
        self.assertNotIn("annex_types", form.fields)
        self.assertEqual(form.widgets["two_sided"].value, ["true"])
        self.assertEqual(form._get_annexes({}), [self.a_odt, self.b_pdf, self.appendix])
        self._clean_cache()
        self.omail.can_do_export_to_pdf_after_signature = lambda: True  # signed
        form = self._form("export-to-pdf-after-signature-batch-action")
        form.update()
        self.assertEqual(form._get_annexes({}), [self.b_pdf, self.appendix])

    def test__excluded_elements(self):
        """Elements not concerned by the export are listed in the description and not exported."""
        self.request["uids"] = self.omail.UID()
        form = self._form("export-to-pdf-after-signature-batch-action")
        form.update()
        self.assertEqual(form._excluded_elements(), [(self.omail, u"Not signed")])
        self.assertEqual(form._get_annexes({}), [])
        self.assertIn(self.omail.absolute_url(), form.description)
        self.omail.can_do_export_to_pdf_after_signature = lambda: True
        for obj in (self.b_pdf, self.appendix):
            self._set_infos(obj, to_print=False)
        self._clean_cache()
        form = self._form("export-to-pdf-after-signature-batch-action")
        form.update()
        self.assertEqual(form._excluded_elements(), [(self.omail, u"No file to print")])
        # nothing excluded: no warning
        self._clean_cache()
        form = self._form("export-to-pdf-before-signature-batch-action")
        form.update()
        self.assertEqual(form._excluded_elements(), [])
        self.assertEqual(form._get_annexes({}), [self.a_odt])
        self.assertNotIn("portalMessage", form.description)

    def test_req_dashboard(self):
        """Only the after signature export is on the requests dashboard, whatever the collection."""
        searches = self.portal["requests"]["requests-searches"]
        self.assertTrue(IReqDashboardBatchActions.providedBy(searches))
        self.assertIn(u"select_row", searches["all_requests"].customViewFields)
        form = searches.restrictedTraverse("@@export-to-pdf-after-signature-batch-action")
        self.assertTrue(form.available())
        actions = [action["name"] for action in BatchActionsViewlet(searches, self.request, None, None)
                   .get_batch_actions()]
        self.assertIn("export-to-pdf-after-signature-batch-action", actions)
        self.assertNotIn("export-to-pdf-before-signature-batch-action", actions)
