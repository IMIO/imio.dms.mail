# -*- coding: utf-8 -*-
""" browser/export_to_zip.py tests for this package."""
from Acquisition import aq_parent
from collective.iconifiedcategory.utils import calculate_category_id
from imio.dms.mail.browser.export_to_pdf import DmsFilesVocabulary
from imio.dms.mail.tests.test_browser_export_to_pdf import ExportToPdfTestCase
from imio.dms.mail.tests.test_browser_export_to_pdf import PDF_PATH
from imio.helpers.content import get_object
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.app.testing import login
from plone.app.testing import logout
from plone.namedfile.file import NamedBlobFile
from zope.annotation import IAnnotations

import io
import zipfile


def zip_names(data):
    return sorted(zipfile.ZipFile(io.BytesIO(data)).namelist())


class TestExportToZipVocabulary(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_pdf.DmsFilesVocabulary used as zip vocabulary."""

    def test___call__(self):
        """Every file is listed, the base versions are dropped."""
        self.assertEqual([term.token for term in DmsFilesVocabulary()(self.omail)],
                         [self.a_odt.getId(), self.b_pdf.getId(), self.appendix.getId()])
        # a_odt converted to pdf, b_pdf source of a mailing: only their derived files are listed
        converted = self._add_file(u"converted", PDF_PATH)
        self._set_infos(converted, conv_from_uid=self.a_odt.UID())
        mailed = self._add_file(u"mailed", PDF_PATH)
        IAnnotations(mailed)["documentgenerator"] = {"mailed": True, "from_doc_uid": self.b_pdf.UID()}
        self._clean_cache()
        self.assertEqual(sorted(term.token for term in DmsFilesVocabulary()(self.omail)),
                         sorted([converted.getId(), mailed.getId(), self.appendix.getId()]))

    def test_incoming_mail(self):
        """The main files of an incoming mail are listed."""
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual([term.token for term in DmsFilesVocabulary()(imail)],
                         [obj.getId() for obj in imail.objectValues() if obj.portal_type == "dmsmainfile"])


class TestExportToZipForm(ExportToPdfTestCase):
    """Test imio.dms.mail.browser.export_to_zip.ExportToZipForm."""

    def test_available(self):
        imail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertTrue(imail.restrictedTraverse("@@export-to-zip").available())
        self.assertTrue(self.omail.restrictedTraverse("@@export-to-zip").available())
        empty = api.content.copy(source=self.omail, target=self.portal["outgoing-mail"], id="om-empty")
        api.content.delete(objects=empty.objectValues())
        self._clean_cache()
        self.assertFalse(empty.restrictedTraverse("@@export-to-zip").available())

    def test_handleApply(self):
        """Every file is preselected and zipped."""
        form = self.omail.restrictedTraverse("@@export-to-zip")
        form.update()
        self.assertEqual(form.widgets["elements"].value,
                         [self.a_odt.getId(), self.b_pdf.getId(), self.appendix.getId()])
        self.request["form.widgets.elements"] = form.widgets["elements"].value
        form.update()
        self.assertEqual(zip_names(form.handleApply(form, None)),
                         [u"in-courrier2-1.pdf", u"in-courrier2.pdf", u"in-courrier3.odt"])


class TestExportToZipFolder(ExportToPdfTestCase):
    """Test the folder export: element form and batch action."""

    def setUp(self):
        super(TestExportToZipFolder, self).setUp()
        self.subfolder = api.content.find(portal_type="ClassificationSubfolder")[0].getObject()
        self.folder = aq_parent(self.subfolder)
        self.f_annex = self._add_annex(self.folder, u"folder annex")
        self.sf_annex = self._add_annex(self.subfolder, u"subfolder annex")
        self._clean_cache()

    def _add_annex(self, container, title):
        with open(PDF_PATH, "rb") as fo:
            return createContentInContainer(
                container, "annex", title=title,
                file=NamedBlobFile(fo.read(), filename=u"%s.pdf" % title.replace(u" ", u"-")),
                content_category=calculate_category_id(self.portal["annexes_types"]["annexes"]["annex"]))

    def test_form(self):
        """Subfolder files are listed but not preselected, they are zipped in a subfolder directory."""
        form = self.folder.restrictedTraverse("@@export-to-zip")
        form.update()
        tokens = [term.token for term in form.widgets["elements"].terms]
        self.assertIn(self.f_annex.UID(), tokens)
        self.assertIn(self.sf_annex.UID(), tokens)
        self.assertIn(self.f_annex.UID(), form.widgets["elements"].value)
        self.assertNotIn(self.sf_annex.UID(), form.widgets["elements"].value)
        self.assertIn("by_subfolder", form.fields)
        res = form._do_export({"elements": [self.f_annex.UID(), self.sf_annex.UID()], "by_subfolder": True})
        self.assertIn(u"folder-annex.pdf", zip_names(res))
        self.assertIn(u"%s/subfolder-annex.pdf" % self.subfolder.getId(), zip_names(res))
        # without directory by subfolder, every file is at the root
        res = form._do_export({"elements": [self.f_annex.UID(), self.sf_annex.UID()], "by_subfolder": False})
        self.assertIn(u"subfolder-annex.pdf", zip_names(res))
        # no subfolder: no option
        form = self.subfolder.restrictedTraverse("@@export-to-zip")
        form.update()
        self.assertNotIn("by_subfolder", form.fields)

    def test_form_created_before_authentication(self):
        """The publisher creates the view while traversing, before authenticating the user."""
        user = api.user.get_current()
        logout()
        form = self.folder.unrestrictedTraverse("@@export-to-zip")
        login(self.portal, user.getId())
        form.update()
        self.assertIn("by_subfolder", form.widgets)

    def test_batch_action(self):
        """A subfolder selected with its folder is listed once, only selected elements files are preselected."""
        self.request["uids"] = u",".join([self.folder.UID(), self.subfolder.UID()])
        form = self.portal["folders"]["folder-searches"].restrictedTraverse("@@export-to-zip-batch-action")
        form.update()
        uids = [annex.UID() for annex in form.annexes]
        self.assertEqual(len(uids), len(set(uids)))
        self.assertIn(self.sf_annex.UID(), uids)
        self.assertIn(self.sf_annex.UID(), form.fields["annexes"].field.default)
        # folder alone: the subfolder file is listed, not preselected
        del self.request.form["form.widgets.uids"]  # set by the previous form update
        self.request["uids"] = self.folder.UID()
        form = self.portal["folders"]["folder-searches"].restrictedTraverse("@@export-to-zip-batch-action")
        form.update()
        self.assertIn(self.sf_annex, form.annexes)
        self.assertIn(self.f_annex.UID(), form.fields["annexes"].field.default)
        self.assertNotIn(self.sf_annex.UID(), form.fields["annexes"].field.default)
        self.assertIn(u"subfolder-annex.pdf", zip_names(form._apply(annexes=[self.sf_annex.UID()])))

    def test_mail_batch_action(self):
        """Mail files are listed by the zip vocabulary."""
        self.request["uids"] = self.omail.UID()
        form = self.portal["outgoing-mail"]["mail-searches"].restrictedTraverse("@@export-to-zip-batch-action")
        form.update()
        self.assertEqual(form.annexes, [self.a_odt, self.b_pdf, self.appendix])
