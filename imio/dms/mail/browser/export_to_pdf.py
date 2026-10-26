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
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.setuphandlers import OM_PRINT_SIGNED_COLS
from imio.dms.mail.setuphandlers import OM_PRINT_TO_SIGN_COLS
from imio.helpers.workflow import get_transitions
from plone import api
from plone.app.uuid.utils import uuidToObject
from Products.CMFPlone.utils import safe_unicode
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.field import Fields
from zope import schema
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.i18n import translate
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified
from zope.schema.interfaces import IVocabularyFactory

import datetime
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
            context, portal_type=portal_type, token_value=token_value, include_portal_type=include_portal_type,
            include_parent_title=include_parent_title, filters=filters
        )

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
            # main files to_print is off as soon as the mail is esigned, a signed ged file is printed too
            return (annex_info.get("esigned", False) or annex_info["to_print"]
                    or (annex_info["portal_type"] == GED and annex_info.get("signed", False)))
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
        elif context.portal_type != "sign_request" and not self._to_print(annex_info):
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

    condition = None  # name of the context method telling if the export is possible

    def available(self):
        """Condition of the object action: only computed on the object view, it is hidden in dashboards."""
        import ipdb; ipdb.set_trace()  # noqa
        if not getattr(self.context, self.condition)():
            return False
        terms = getUtility(IVocabularyFactory, self.vocabulary)(self.context)
        return len([term for term in terms if not getattr(term, "disabled", False)]) > 1

    def __init__(self, context, request):
        super(ExportToPDFForm, self).__init__(context, request)
        self.fields["two_sided"].field.default = True

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
    condition = "can_do_export_to_pdf_before_signature"

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
    condition = "can_do_export_to_pdf_after_signature"


class ExportToPDFBatchActionForm(ConcatenateAnnexesBatchActionForm):
    """Concatenate the files to print of the selected outgoing mails, as the element export preselects them."""

    collections = ()  # ids of the dashboard collections showing the button, None for every collection
    vocabulary = None  # vocabulary class listing the files of a mail
    condition = None  # name of the element method telling if the element export is possible
    condition_msg = None  # exclusion reason when the condition is not met
    mailing_appendices = None  # default of the field repeating the appendix files by mailed version, None to omit it
    close_transition = None  # transition to the final state, done after the export when close_content is True
    close_with_date = False  # the outgoing date is set when closing
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
        if self.mailing_appendices is not None:
            self.fields += Fields(schema.Bool(
                __name__="mailing_appendices",
                title=_(u"Appendix files for each mailed version?"),
                description=_(u"mailing_appendices description after signature") if self.mailing_appendices
                else _(u"mailing_appendices description before signature"),
                default=self.mailing_appendices,
                required=False))
            self.fields["mailing_appendices"].widgetFactory = RadioFieldWidget
        if self.close_transition:
            self.fields += Fields(schema.Bool(
                __name__="close_content",
                title=_(u"Close the exported elements?"),
                description=_(u"Will made transition to final state and set an outgoing date"),
                default=True,
                required=False))
            self.fields["close_content"].widgetFactory = RadioFieldWidget
        if self.close_with_date:
            self.fields += Fields(schema.Datetime(
                __name__="outgoing_date",
                title=_(u"Outgoing Date"),
                default=datetime.datetime.now(),
                required=False))

    def _apply(self, **data):
        pdf_file_content = super(ExportToPDFBatchActionForm, self)._apply(**data)
        if pdf_file_content and data.get("close_content"):
            self._close_elements(data)
        return pdf_file_content

    def _close_elements(self, data):
        """Do the final transition on the exported elements that can do it."""
        excluded = [obj for obj, reason in self._excluded_elements()]
        for brain in self.brains:
            obj = brain.getObject()
            if obj in excluded or self.close_transition not in get_transitions(obj):
                continue
            if data.get("outgoing_date"):
                obj.outgoing_date = data["outgoing_date"]
                modified(obj, Attributes(IImioDmsOutgoingMail, "outgoing_date"))
            api.content.transition(obj=obj, transition=self.close_transition)
            # the dashboard showing the batch action is refreshed after the download
            self.request.response.setHeader("X-Refresh-Faceted", "1")

    def _element_annexes(self, obj, data=None):
        """The files the vocabulary allows to export, ged files first.

        With mailing_appendices, the appendix files follow each mailed version of a ged file instead.
        """
        files = [obj[term.token] for term in self.vocabulary()(obj) if not getattr(term, "disabled", False)]
        if not (data or {}).get("mailing_appendices"):
            return files
        appendices = [afile for afile in files if afile.portal_type != GED]
        result, repeated = [], False
        for ged in [afile for afile in files if afile.portal_type == GED]:
            versions = self._mailed_versions(obj, ged)
            result += [ged] + appendices * versions
            repeated = repeated or versions
        return result if repeated else files

    def _mailed_versions(self, obj, ged):
        """Number of mailed versions in p_ged: one by recipient in the mailed odt, one in each pdf split from it."""
        if IAnnotations(ged).get("documentgenerator", {}).get("mailed"):
            return len(api.content.get_view("document_generation_helper_view", obj, self.request).mailing_list())
        source = getattr(ged, "conv_from_uid", None) and uuidToObject(ged.conv_from_uid)
        return int(bool(source and IAnnotations(source).get("documentgenerator", {}).get("mailed")))

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
    mailing_appendices = False  # the mailed odt holds every version


class ExportToPDFAfterSignatureBatchActionForm(ExportToPDFBatchActionForm):

    label = _(u"Export to PDF after signature")
    collections = OM_PRINT_SIGNED_COLS
    vocabulary = ExportToPDFAfterSignatureVocabulary
    condition = "can_do_export_to_pdf_after_signature"
    condition_msg = _(u"Not signed")
    mailing_appendices = True  # each mailed version is a separate pdf
    close_transition = "mark_as_sent"
    close_with_date = True

    def _check_element(self, obj):
        # a mail only sent by email has nothing to print
        if obj.send_modes and all(mode.startswith("email") for mode in obj.send_modes):
            return _(u"Only sent by email")
        return super(ExportToPDFAfterSignatureBatchActionForm, self)._check_element(obj)


class ExportToPDFReqAfterSignatureBatchActionForm(ExportToPDFAfterSignatureBatchActionForm):

    collections = None
    mailing_appendices = None  # sign requests are not mailed
    close_transition = "close"
    close_with_date = False

    def _check_element(self, obj):
        """Sign requests have no send modes."""
        return ExportToPDFBatchActionForm._check_element(self, obj)
