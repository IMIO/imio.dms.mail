# -*- coding: utf-8 -*-
"""Export the files to print of an outgoing mail or a signing request as a single PDF."""

from collective.documentgenerator.utils import convert_file
from collective.iconifiedcategory.utils import get_categorized_elements
from imio.annex.browser.views import ExportPDFForm
from imio.annex.vocabularies import ContainedAnnexesVocabulary
from imio.dms.mail import _
from plone import api
from Products.CMFPlone.utils import safe_unicode
from zope.annotation import IAnnotations
from zope.i18n import translate


GED = "dmsommainfile"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ODT = "application/vnd.oasis.opendocument.text"
PDF = "application/pdf"


def superseded_uids(context):
    """Return the (mailed, converted) UIDs of files replaced by a derived file of p_context.

    * mailed: source document of an existing mailing (`from_doc_uid` annotation)
    * converted: odt converted to pdf when added to a sign session (`conv_from_uid`)
    """
    mailed, converted = set(), set()
    for infos in get_categorized_elements(context):
        if infos.get("conv_from_uid"):
            converted.add(infos["conv_from_uid"])
        from_doc_uid = IAnnotations(context[infos["id"]]).get("documentgenerator", {}).get("from_doc_uid")
        if from_doc_uid:
            mailed.add(from_doc_uid)
    return mailed, converted


class ExportToPDFElementsVocabulary(ContainedAnnexesVocabulary):
    """Files of an outgoing mail or a signing request that may be exported to PDF.

    GED files are listed first, then the appendix files, each group alphabetically.
    Files superseded by their mailing are dropped, the others are disabled when they
    are not to be printed, when a PDF was generated from them or when they cannot be
    concatenated.
    """

    after_signature = False

    def __call__(
            self,
            context,
            portal_type=None,
            token_value='id',
            include_portal_type=True,
            include_parent_title=False,
            filters={}):

        return super(ExportToPDFElementsVocabulary, self).__call__(
            context, portal_type=None, include_portal_type=True)

    def _prepare_annex_infos(self, context, annex_infos):
        mailed = superseded_uids(context)[0]
        return sorted(
            [infos for infos in annex_infos if infos["UID"] not in mailed],
            key=lambda infos: (infos["portal_type"] != GED, safe_unicode(infos["title"]).lower()))

    def _portal_type_title(self, context, annex_info):
        """Tell ged files and appendix files apart, the FTI titles are not readable."""
        return u"%s - " % translate(
            api.portal.get().portal_types[annex_info['portal_type']].title,
            domain="plone",
            context=context.REQUEST)

    def _to_print(self, annex_info):
        """Is this file part of what has to be printed?"""
        if self.after_signature:
            # main files to_print is off as soon as the mail is esigned
            return annex_info.get("esigned", False) or annex_info["to_print"]
        return annex_info["to_print"]

    def _selectable_content_types(self, annex_info):
        """Only PDF, plus the GED odt and docx before signature: they are converted when exporting."""
        if not self.after_signature and annex_info["portal_type"] == GED:
            return (PDF, ODT, DOCX)
        return (PDF,)

    def _check_disable_term(self, context, annex_info, categories_vocab, term):
        super(ExportToPDFElementsVocabulary, self)._check_disable_term(
            context, annex_info, categories_vocab, term)
        if term.disabled:
            return
        if annex_info["UID"] in superseded_uids(context)[1]:
            reason = " [converted to pdf]"
        elif not self._to_print(annex_info):
            reason = " [not to print]"
        elif annex_info["contentType"] not in self._selectable_content_types(annex_info):
            reason = " [pdf required]"
        else:
            return
        term.disabled = True
        term.title += translate(reason, domain="imio.dms.mail", context=context.REQUEST)


class ExportToPDFBeforeSignatureVocabulary(ExportToPDFElementsVocabulary):
    after_signature = False


class ExportToPDFAfterSignatureVocabulary(ExportToPDFElementsVocabulary):
    after_signature = True


class ExportToPDFForm(ExportPDFForm):
    """Concatenate the selected files of an outgoing mail or a signing request."""

    def updateWidgets(self):
        super(ExportToPDFForm, self).updateWidgets()
        widget = self.widgets["elements"]
        if "%s-empty-marker" % widget.name not in self.request.form:
            # first display: preselect everything that may be exported
            widget.value = [term.token for term in widget.terms if not getattr(term, "disabled", False)]

    def _elements_content(self, data):
        """Odt and docx files are converted to PDF before being concatenated."""
        content = {}
        for element_id in data["elements"]:
            afile = self.context[element_id].file
            content[element_id] = convert_file(afile) if afile.contentType in (ODT, DOCX) else afile.data
        return content


class ExportToPDFBeforeSignatureForm(ExportToPDFForm):

    label = _(u"Export to PDF before signature")
    vocabulary = u"imio.dms.mail.ExportToPDFBeforeSignatureVocabulary"


class ExportToPDFAfterSignatureForm(ExportToPDFForm):

    label = _(u"Export to PDF after signature")
    vocabulary = u"imio.dms.mail.ExportToPDFAfterSignatureVocabulary"
