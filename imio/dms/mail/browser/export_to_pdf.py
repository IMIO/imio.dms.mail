# -*- coding: utf-8 -*-
"""Export the files to print of an outgoing mail or a signing request as a single PDF."""

from collective.documentgenerator.config import get_oo_port_list
from collective.documentgenerator.config import get_oo_server
from collective.documentgenerator.utils import convert_file
from collective.eeafaceted.collectionwidget.interfaces import NotDashboardContextException
from collective.eeafaceted.collectionwidget.utils import getCurrentCollection
from collective.iconifiedcategory.utils import get_categorized_elements
from imio.annex.browser.views import ConcatenateAnnexesBatchActionForm
from imio.annex.browser.views import ExportPDFForm
from imio.annex.vocabularies import ContainedAnnexesVocabulary
from imio.dms.mail import _
from imio.dms.mail.setuphandlers import OM_PRINT_SIGNED_COLS
from imio.dms.mail.setuphandlers import OM_PRINT_TO_SIGN_COLS
from plone import api
from Products.CMFPlone.utils import safe_unicode
from zope.annotation import IAnnotations
from zope.i18n import translate

import socket


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


def oo_answers(server, port, timeout=1):
    """Is something listening on p_server:p_port?"""
    try:
        socket.create_connection((server, port), timeout).close()
    except (socket.error, socket.timeout):
        return False
    return True


def pdf_content(afile):
    """Odt and docx files are converted to PDF before being concatenated."""
    return convert_file(afile) if afile.contentType in (ODT, DOCX) else afile.data


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
        return {element_id: pdf_content(self.context[element_id].file) for element_id in data["elements"]}


class ExportToPDFBeforeSignatureForm(ExportToPDFForm):

    label = _(u"Export to PDF before signature")
    vocabulary = u"imio.dms.mail.ExportToPDFBeforeSignatureVocabulary"

    def update_not_used(self):
        super(ExportToPDFBeforeSignatureForm, self).update()
        if self.status:
            return
        # odt and docx are converted by LibreOffice: warn when it does not answer
        server, ports = get_oo_server(), get_oo_port_list()
        if ports != [2002]:
            return
        down = [str(port) for port in ports if not oo_answers(server, port)]
        if down:
            self.status = _(u"LibreOffice server ${server} does not answer on port(s) ${ports}: odt and docx files "
                            u"cannot be converted.", mapping={"server": server, "ports": ", ".join(down)})


class ExportToPDFAfterSignatureForm(ExportToPDFForm):

    label = _(u"Export to PDF after signature")
    vocabulary = u"imio.dms.mail.ExportToPDFAfterSignatureVocabulary"


class ExportToPDFBatchActionForm(ConcatenateAnnexesBatchActionForm):
    """Concatenate the files to print of the selected outgoing mails, as the element export preselects them."""

    collections = ()  # ids of the dashboard collections showing the button, None for every collection
    vocabulary = None  # vocabulary class listing the files of a mail
    condition = None  # name of the element method telling if the element export is possible
    condition_msg = None  # exclusion reason when the condition is not met
    button_with_icon = False
    CHECK_ELEMENTS = True

    def available(self):
        if self.request.get("uids") or "form.widgets.uids" in self.request.form:
            # ponytail: the form itself is not checked against the collection, the button is only shown where needed
            return True
        if self.collections is None:
            return True
        try:
            collection = getCurrentCollection(self.context)
        except NotDashboardContextException:
            return False
        return collection is not None and collection.getId() in self.collections

    def _update(self):
        super(ExportToPDFBatchActionForm, self)._update()
        self.fields = self.fields.omit("annex_types")
        self.fields["two_sided"].field.default = True

    def _element_annexes(self, obj, data=None):
        """The files the vocabulary allows to export, data is not used."""
        return [obj[term.token] for term in self.vocabulary()(obj) if not getattr(term, "disabled", False)]

    def _check_element(self, obj):
        if not getattr(obj, self.condition)():
            return self.condition_msg
        # ponytail: vocabulary computed twice per element (check and export), cache it if slow
        if not self._element_annexes(obj):
            return _(u"No file to print")

    def _annex_content(self, annex):
        return pdf_content(annex.file)


class ExportToPDFBeforeSignatureBatchActionForm(ExportToPDFBatchActionForm):

    label = _(u"Export to PDF before signature")
    collections = OM_PRINT_TO_SIGN_COLS
    vocabulary = ExportToPDFBeforeSignatureVocabulary
    condition = "can_do_export_to_pdf_before_signature"
    condition_msg = _(u"E-signature or seal set, or already signed")


class ExportToPDFAfterSignatureBatchActionForm(ExportToPDFBatchActionForm):

    label = _(u"Export to PDF after signature")
    collections = OM_PRINT_SIGNED_COLS
    vocabulary = ExportToPDFAfterSignatureVocabulary
    condition = "can_do_export_to_pdf_after_signature"
    condition_msg = _(u"Not signed")


class ExportToPDFReqAfterSignatureBatchActionForm(ExportToPDFAfterSignatureBatchActionForm):

    collections = None
