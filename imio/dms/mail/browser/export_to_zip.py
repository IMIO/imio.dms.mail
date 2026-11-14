# -*- coding: utf-8 -*-
"""Export the files of a mail, a signing request or a folder as a Zip file."""

from Acquisition import aq_inner
from Acquisition import aq_parent
from imio.annex.browser.views import DownloadElementsAnnexesBatchActionForm
from imio.annex.browser.views import ExportZipForm
from imio.dms.mail import _
from imio.dms.mail.browser.export_to_pdf import DmsFilesVocabulary
from imio.dms.mail.browser.export_to_pdf import PreselectElementsMixin
from plone.app.uuid.utils import uuidToObject
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.field import Fields
from zope import schema
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary


def subfolders(folder):
    """The subfolders of a classification folder the current user may see."""
    return folder.listFolderContents(contentFilter={"portal_type": "ClassificationSubfolder"})


class ExportToZipFolderVocabulary(DmsFilesVocabulary):
    """Files of a classification folder, then the files of each of its subfolders (with the subfolder title).

    Tokens are UIDs: ids are only unique in their container.
    """

    def __call__(self, context, token_value="UID", **kwargs):
        terms = list(super(ExportToZipFolderVocabulary, self).__call__(context, token_value=token_value, **kwargs))
        kwargs["include_parent_title"] = True
        for subfolder in subfolders(context):
            terms += list(super(ExportToZipFolderVocabulary, self).__call__(
                subfolder, token_value=token_value, **kwargs))
        return SimpleVocabulary(terms)


class ExportToZipForm(PreselectElementsMixin, ExportZipForm):
    """Zip the selected files of a mail or a signing request."""

    label = _(u"Export to zip")
    vocabulary = u"imio.dms.mail.ExportToZipVocabulary"

    def available(self):
        """Condition of the object action: there is something to export."""
        terms = getUtility(IVocabularyFactory, self.vocabulary)(self.context)
        return any(not getattr(term, "disabled", False) for term in terms)


class ExportToZipFolderForm(ExportToZipForm):
    """Zip the selected files of a folder and of its subfolders.

    Only the folder files are preselected: the user checks the subfolder files to include them.
    When there are subfolders, the user chooses to store their files in a directory by subfolder.
    """

    vocabulary = u"imio.dms.mail.ExportToZipFolderVocabulary"
    by_subfolder = True

    def update(self):
        # not in __init__: the view is created during traversal, before the user is authenticated
        if "by_subfolder" not in self.fields and subfolders(self.context):
            self.fields += Fields(schema.Bool(
                __name__="by_subfolder",
                title=_(u"Subfolder files in a directory by subfolder?"),
                description=_(u"by_subfolder description"),
                default=True,
                required=False))
            self.fields["by_subfolder"].widgetFactory = RadioFieldWidget
        super(ExportToZipFolderForm, self).update()

    def _do_export(self, data):
        self.by_subfolder = data.get("by_subfolder", True)
        return super(ExportToZipFolderForm, self)._do_export(data)

    def _preselect(self, term):
        return (super(ExportToZipFolderForm, self)._preselect(term)
                and term.token in getattr(self.context, "categorized_elements", {}))

    def _element(self, token):
        # token is a selectable term, checked by _check_data
        return uuidToObject(token)

    def _zip_path(self, annex):
        """With by_subfolder, subfolder files are stored in a directory named after the subfolder id."""
        path = super(ExportToZipFolderForm, self)._zip_path(annex)
        parent = aq_parent(aq_inner(annex))
        if self.by_subfolder and parent != self.context:
            path = u"{0}/{1}".format(parent.getId(), path)
        return path


class ExportToZipBatchActionForm(DownloadElementsAnnexesBatchActionForm):
    """Zip the files of the selected mails or signing requests."""

    label = _(u"Export to zip")
    annexes_vocabulary = u"imio.dms.mail.ExportToZipVocabulary"


class ExportToZipFolderBatchActionForm(ExportToZipBatchActionForm):
    """Zip the files of the selected folders and of their subfolders.

    Only the files of the selected elements are preselected, as in the element form.
    """

    annexes_vocabulary = u"imio.dms.mail.ExportToZipFolderVocabulary"

    def _element_terms(self, element, **kwargs):
        """A subfolder selected with its folder: its files are listed once."""
        listed = set(term.token for term in self.annexes_terms)
        terms = super(ExportToZipFolderBatchActionForm, self)._element_terms(element, **kwargs)
        return [term for term in terms if term.token not in listed]

    def _annex_from_term(self, element, term):
        return uuidToObject(term.token)

    def _default_annexes(self):
        selected = set(brain.UID for brain in self.brains)
        return [annex for annex in self.annexes if aq_parent(aq_inner(annex)).UID() in selected]
