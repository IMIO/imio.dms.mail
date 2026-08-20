# -*- coding: utf-8 -*-
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.person import IPerson
from collective.contact.core.interfaces import IContactable
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.documentgenerator import _ as _dg
from collective.documentgenerator import utils
from collective.documentgenerator.browser.generation_view import MailingLoopPersistentDocumentGenerationView
from collective.documentgenerator.browser.generation_view import PersistentDocumentGenerationView
from collective.documentgenerator.browser.overrides import DGDXDocumentViewerView
from collective.documentgenerator.browser.table import TemplatesTable
from collective.documentgenerator.browser.views import EditConfigurablePodTemplate
from collective.documentgenerator.browser.views import TemplatesListing
from collective.documentgenerator.content.pod_template import ConfigurablePODTemplate
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.documentgenerator.utils import update_dict_with_validation
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from collective.documentviewer.convert import Converter
from collective.documentviewer.views import DXDocumentViewerView
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGenerationView
from collective.iconifiedcategory.utils import get_categorized_elements
from imio.annex.utils import get_annexes_to_print
from imio.dms.mail import _
from imio.dms.mail import get_empty_signers_value
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.content.behaviors import ISigningBehavior
from imio.dms.mail.subscribers import apply_signer_rules
from imio.dms.mail.subscribers import apply_substitutes_to_signers
from imio.dms.mail.utils import PREVIEW_CLEANED_DATE
from imio.dms.mail.utils import PREVIEW_EML_DATE
from imio.esign.interfaces import IItemOrderProvider
from imio.helpers.barcode import generate_barcode
from imio.helpers.content import uuidToObject
from imio.zamqp.core import base
from imio.zamqp.core.utils import next_scan_id
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from z3c.table.column import Column
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component import queryAdapter
from zope.i18n import translate
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory

import copy
import operator
import zope.event


# # # HELPERS # # #


def get_template_signers_source(pod_template):
    """Return the template object defining the signers to apply for pod_template.

    Signers are taken from pod_template itself. If it defines none, its merge_templates
    sub-templates are looked up in order and the first one defining signers is returned.
    Returns a tuple:
        - the sub/template or None
        - a bool showing the template contains itself the signers
    """
    if bool(getattr(pod_template, "signers", None)) or bool(getattr(pod_template, "seal", None)):
        return pod_template, True
    for line in getattr(pod_template, "merge_templates", None) or []:
        sub = uuidToObject(line.get("template"), unrestricted=True)
        if sub is not None and (bool(getattr(sub, "signers", None)) or bool(getattr(sub, "seal", None))):
            return sub, False
    return None, True


class BaseDGHelper(DXDocumentGenerationHelperView):
    """
    Helper methods used for mail generation
    """

    def fmt(self, val, fmt="%s "):
        if val:
            return fmt % val
        return ""

    def get_classification_folders(self, sep=u", "):
        obj = self.real_context
        if (not self.has_field("classification_folders") or not hasattr(obj, "classification_folders")
                or not obj.classification_folders):
            return []
        ret = []
        for fld in obj.classification_folders:
            obj = uuidToObject(fld, unrestricted=True)
            ret.append(obj.internal_reference_no or safe_unicode(obj.Title()))
        ret = sep.join(ret)
        return ret

    def get_ctct_det(self, obj, fallback=True):
        try:
            contactable = IContactable(obj)
            return contactable.get_contact_details(fallback=fallback)
            # {'website': '', 'fax': '', 'phone': '', 'address': {'city': u'Eghez\xe9e', 'country': '', 'region': '',
            # 'additional_address_details': '', 'number': u'8', 'street': u'Grande Ruelle', 'zip_code': u'5310'},
            # 'im_handle': '', 'cell_phone': '', 'email': ''}
        except Exception:
            return {}

    def get_full_title(self, contact, **kwargs):
        if IPerson.providedBy(contact):
            return contact.get_title()
        elif IOrganization.providedBy(contact):
            return contact.get_full_title(**kwargs)
        elif IHeldPosition.providedBy(contact):
            return contact.get_full_title()
        else:
            return ""

    def get_separate_contacts(self, contact, **kwargs):
        """Return a list with separate organization and person"""
        ret = {"pers": None, "org": None, "root": None, "chain": None, "levels": False}
        if IPerson.providedBy(contact):
            ret["pers"] = contact
        elif IOrganization.providedBy(contact):
            ret["org"] = contact
        elif IHeldPosition.providedBy(contact):
            if contact.label:
                ret["label"] = contact.label
            ret["pers"] = contact.get_person()
            org = contact.get_organization()
            if org:
                ret["org"] = org
        if ret["org"]:
            ret["chain"] = ret["org"].get_organizations_chain()
            ret["root"] = ret["chain"][0]
            ret["levels"] = len(ret["chain"]) > 1 and True
        return ret

    def get_separate_titles(self, contact, **kwargs):
        """Return a list with separate title for organization and person"""
        ret = [u"", u""]  # org, pers
        if IPerson.providedBy(contact):
            ret[1] = contact.get_title()
        elif IOrganization.providedBy(contact):
            ret[0] = contact.get_full_title(**kwargs)  # separator=u' / ', first_index=0
        elif IHeldPosition.providedBy(contact):
            ret[1] = contact.get_person_title()
            org = contact.get_organization()
            if org:
                ret[0] = org.get_full_title(**kwargs)
        return ret

    def get_treating_groups(self):
        obj = self.real_context
        if not obj.treating_groups:
            return None
        return uuidToObject(obj.treating_groups, unrestricted=True)

    def person_title(
        self, contact, pers_dft=u"Monsieur", org_dft=u"Madame, Monsieur", with_name=False, upper_name=False
    ):
        def pers_title(pers):
            title = contact.person_title
            if not title:
                title = pers_dft
            if with_name and pers.lastname:
                return u"{} {}".format(title, upper_name and pers.lastname.upper() or pers.lastname)
            else:
                return title

        if IPerson.providedBy(contact):
            return pers_title(contact)
        elif IOrganization.providedBy(contact):
            return org_dft
        elif IHeldPosition.providedBy(contact):
            return pers_title(contact.get_person())
        else:
            return u""

    def separate_full_title(self, tg=u"", nb=2, sep=u" - "):
        """Separates a treating group name in different parts.
        Returns always the good number of parts, fulled with empty strings."""
        ret = [u"" for i in range(0, nb)]
        if not tg:
            return ret
        parts = tg.split(sep)
        for i in range(0, nb - 1):
            ret[i] = parts[i]
        if len(parts) >= nb:
            ret[-1] = sep.join(parts[nb - 1:])
        return ret


class IMDGHelper(BaseDGHelper):
    """
    Helper methods used for incoming mail generation
    """


class BasePrintDGHelper(object):
    """Collect the files to print, as documentviewer preview images.

    A container is the outgoing mail or the signing request holding the files.
    """

    print_image_size = (17.0, 25.7)  # Printable area of the print template page, in centimetres
    SIGNED_PRINT_TEMPLATE_IDS = ("d-print-signed", "d-print-request")
    PRINT_HEADER_SETTINGS = {
        "d-print-to-sign": "omail_print_manual_annex_header",
        "d-print-signed": "omail_print_esign_annex_header",
        "d-print-request": "request_print_esign_annex_header",
    }

    def print_containers(self):
        """Return the containers whose files must be printed."""
        raise NotImplementedError

    def is_signed_print(self):
        """Return True when rendering the print template for electronically signed files."""
        # Derive whether the print template is for signed files from the pod_template id
        pod_template = getattr(self, "pod_template", None)
        return pod_template is not None and pod_template.getId() in self.SIGNED_PRINT_TEMPLATE_IDS

    def print_annex_header(self):
        """Return True if the annex header must be printed above each annex page."""
        pod_template = getattr(self, "pod_template", None)
        pod_template_id = pod_template is not None and pod_template.getId() or None
        key = self.PRINT_HEADER_SETTINGS.get(pod_template_id)
        if key is None:
            raise KeyError("No print annex header setting for pod_template id {}".format(pod_template_id))
        return api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(key), default=False
        )

    def _usable_preview(self, fobj):
        """Return True if the file has printable preview images, regenerating them if needed."""
        annot = IAnnotations(fobj).get("collective.documentviewer", "")
        if not annot:
            return False
        if annot.get("last_updated") == PREVIEW_EML_DATE:
            return False
        if annot.get("last_updated") == PREVIEW_CLEANED_DATE:
            Converter(fobj)()
            annot = IAnnotations(fobj).get("collective.documentviewer", "")
        return bool(annot and annot.get("successfully_converted") and annot.get("num_pages"))

    def _superseded_uids(self, container):
        """Return the uids of files replaced by a derived file still present in the container.

        If related files are both marked to_print, keep the derived one :
        * A file converted from ODT to PDF (see ApprovalAdapter): keep the PDF, remove the ODT.
        * A mailing loop template: keep the generated files, remove the template.
        """
        uids = set()
        for obj in get_categorized_elements(container, result_type="objects", caching=False):
            uids.add(getattr(obj, "conv_from_uid", None))
            uids.add(IAnnotations(obj).get("documentgenerator", {}).get("from_doc_uid"))
        uids.discard(None)
        return uids

    def _printable_uids(self, container, portal_type, filters, superseded):
        """Return the uids of the files to print, warning about those without preview."""
        uids = set()
        for fobj in get_categorized_elements(
            container, result_type="objects", portal_type=portal_type, filters=filters, caching=False
        ):
            if fobj.UID() in superseded:
                continue
            if not self._usable_preview(fobj):
                api.portal.show_message(
                    message=translate(
                        _(u"Warning: no preview image found for document '${doc}' of mail '${mail}'. "
                          u"This document will not be included in the printing.",
                          mapping={u"doc": safe_unicode(fobj.Title()),
                                   u"mail": safe_unicode(container.Title())}),
                        context=self.request),
                    request=self.request,
                    type="warning",
                )
                continue
            uids.add(fobj.UID())
        return uids

    def _annexes(self, container, portal_type, filters, superseded):
        """Return the annex dicts to print for one portal_type of one container.

        Each dict comes from imio.annex.utils.get_annexes_to_print: 'title', 'UID',
        'number', 'number_of_images' and 'images', a list of {'number', 'path'}.
        They are ordered by the item order provider of the container, so the printed order
        matches the file table, and renumbered accordingly.
        """
        uids = self._printable_uids(container, portal_type, filters, superseded)
        if not uids:
            return []
        annexes = [dic for dic in get_annexes_to_print(container, portal_type=portal_type,
                                                       filters=filters, caching=False)
                   if dic["UID"] in uids]
        return self._ordered(container, annexes)

    def _ordered(self, container, annexes):
        """Sort annex dicts in the file table order of the container and renumber them."""
        provider = queryAdapter(container, IItemOrderProvider)
        if provider is not None:
            order = provider.get_item_order()
            annexes = sorted(annexes, key=lambda dic: order.get(dic["UID"], len(order)))
        for i, dic in enumerate(annexes):
            dic["number"] = i + 1
        return annexes

    def get_dms_files(self):
        """Return the files to print, grouped by container, as preview images.

                :return: list of dicts {'container': <outgoing mail or signing request>,
            'mainfiles': [...], 'annexes': [...]}, ged files and appendix files kept
            apart so the template prints the annex header above annexes only.
        """
        to_print = {"to_print": True}
        res = []
        for container in self.print_containers():
            ged_type = None
            if container.portal_type != "sign_request":
                ged_type = "dmsommainfile"
            if self.is_signed_print():
                main_type, main_filters = ged_type or "dmsappendixfile", {"esigned": True, "to_print": True}
            else:
                main_type, main_filters = ged_type, to_print
            superseded = self._superseded_uids(container)
            mainfiles = main_type and self._annexes(container, main_type, main_filters, superseded) or []
            # a file already printed as a ged file must not be printed again as an annex
            done = superseded | set(dic["UID"] for dic in mainfiles)
            annexes = self._annexes(container, "dmsappendixfile", to_print, done)
            if ged_type is None:
                # every file of a signing request is an appendix file, so every page it
                # prints is an annex page: only the header setting decides the header
                mainfiles, annexes = [], self._ordered(container, mainfiles + annexes)
            if mainfiles or annexes:
                res.append({"container": container, "mainfiles": mainfiles, "annexes": annexes})
        return res

    def annex_header(self, entry, annex, image):
        """Return the header line printed above one annex page."""
        return _(u"Annex ${nb}/${total} - ${title} - Page ${page}/${pages}",
                 mapping={u"nb": annex["number"],
                          u"total": len(entry["annexes"]),
                          u"title": safe_unicode(annex["title"]),
                          u"page": image["number"],
                          u"pages": annex["number_of_images"]})

    def get_print_pages(self):
        """Return one entry per page to print, in printing order."""
        with_header = self.print_annex_header()
        pages = []
        for entry in self.get_dms_files():
            for kind in ("mainfiles", "annexes"):
                for annex in entry[kind]:
                    for image in annex["images"]:
                        if not image["path"]:
                            continue
                        pages.append({
                            "path": image["path"],
                            "header": (kind == "annexes" and with_header
                                       and translate(self.annex_header(entry, annex, image),
                                                     context=self.request) or u""),
                        })
        return pages

    def image_orientation(self, image):
        """Rotate a landscape image 270 degrees clockwise so it fills the page.

        Used as the appy.pod 'document' convertOptions parameter.
        """
        if image.width > image.height:
            return "-rotate 270"


class OMDGHelper(BaseDGHelper):
    """
    Helper methods used for outgoing mail generation
    """

    def get_sender(self):
        dic = self.real_context.get_sender_info()
        if "org" in dic:
            dic["org_full_title"] = dic["org"].get_full_title(separator=" - ", first_index=1)
        return dic

    def mailing_list(self, gen_context=None):
        """Returns a list of tuples (contact, send_mode) for send_mode starting with post."""
        om = self.real_context
        if not om.recipients:
            return []

        post_modes = []
        if api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_post_mailing",
            default=False,
        ):
            post_modes = [mode for mode in om.send_modes or [] if mode.startswith("post")]

        mailing_list = []
        for relval in om.recipients:
            if relval.isBroken():
                continue
            for mode in post_modes or [None]:
                mailing_list.append((relval.to_object, mode))
        return mailing_list

    def mailed_context(self, mailed_data):
        """Modify context to separate mailing_list tuple."""
        new_context = super(OMDGHelper, self).mailed_context(mailed_data)
        (contact, send_mode) = new_context['mailed_data']
        new_context['mailed_data'] = contact
        new_context['send_mode'] = send_mode
        return new_context

    def is_first_doc(self):
        """in mailing context"""
        ctx = self.appy_renderer.contentParser.env.context
        if "loop" in ctx and hasattr(ctx["loop"], "mailed_data") and not ctx["loop"].mailed_data.first:
            return False
        return True

    def display_send_modes(self, separator=u", ", filter_on=None):
        """Return a list of send modes to display in the template.

        :param separator: separator to join values
        :param filter_on: list of send modes to filter on
        :return: string of send modes titles
        """
        send_modes = []
        if filter_on is None:
            filter_on = []
        if not isinstance(filter_on, (list, tuple)):
            filter_on = [filter_on]
        if self.real_context.send_modes:
            factory = getUtility(IVocabularyFactory, "imio.dms.mail.OMSendModesVocabulary")
            vocab = factory(None)
            for mode in self.real_context.send_modes:
                if mode.startswith("post") and filter_on and mode not in filter_on:
                    continue
                term = vocab.getTerm(mode)
                send_modes.append(term.title)
        return separator.join(send_modes)

    def get_signers(self):
        """Return a list of tuple (position, name, function) containing signers.
        For seal only, returns an ampty list"""
        return OMApprovalAdapter(self.real_context).signers_details


class DashboardDGBaseHelper:  # noqa
    """
    Common methods
    """

    objs = []
    sel_type = ""

    def is_dashboard(self):
        """Test if template is rendered from a dashboard"""
        return "facetedQuery" in self.request.form

    def uids_to_objs(self, brains):
        """set objects from brains"""
        # can be used like this in normal template:
        # do section- if view.is_dashboard()
        # do text if view.uids_to_objs(brains)
        self.objs = []
        for brain in brains:
            self.objs.append(brain.getObject())
        self.sel_type = len(brains) and self.objs[0].portal_type or ""
        return False


class DocumentGenerationDocsDashboardHelper(ATDocumentGenerationHelperView, DashboardDGBaseHelper):
    """
    Methods used for listing
    """

    def group_by_tg(self, brains):
        results = {
            "1_no_group": {
                "mails": [],
                "title": translate("listing_no_group", domain="imio.dms.mail", context=self.request),
            }
        }
        for brain in brains:
            obj = brain.getObject()
            tg = brain.treating_groups
            if tg:
                if tg not in results:
                    results[tg] = {"mails": []}
                    title = tg
                    tgroup = uuidToObject(tg, unrestricted=True)
                    if tgroup is not None:
                        title = tgroup.get_full_title(separator=" - ", first_index=1)
                    results[tg]["title"] = title
                results[tg]["mails"].append(obj)
            else:
                results["1_no_group"]["mails"].append(obj)
        if not results["1_no_group"]["mails"]:
            del results["1_no_group"]
        return results

    def flatten_group_by_tg(self, dic):
        """Flatten dict as a list of list"""
        current_tg = ""
        res = []
        for tg in dic:
            if current_tg != dic[tg]["title"]:
                current_tg = dic[tg]["title"]
            for mail in dic[tg]["mails"]:
                res.append([current_tg, mail])
        res.sort(key=operator.itemgetter(0))
        return res


class DocumentGenerationOMDashboardHelper(BasePrintDGHelper, DocumentGenerationDocsDashboardHelper):
    """
    Methods used in document generation view, for IOMDashboard
    """

    def print_containers(self):
        """The outgoing mails selected on the dashboard, in the selection order."""
        return [brain._unrestrictedGetObject() for brain in self.context_var("brains")]


class DocumentGenerationReqDashboardHelper(DocumentGenerationOMDashboardHelper):
    """
    Methods used in document generation view, for IReqDashboard.

    Same print methods as the outgoing mail dashboard: get_dms_files adapts itself to
    the portal type of every selected item.
    """


class DocumentGenerationCategoriesHelper(ATDocumentGenerationHelperView, DashboardDGBaseHelper):
    """
    Helper for categories folder
    """


class DocumentGenerationDirectoryHelper(ATDocumentGenerationHelperView, DashboardDGBaseHelper):
    """
    Helper for collective.contact.core directory
    """

    def __init__(self, context, request):
        super(DocumentGenerationDirectoryHelper, self).__init__(context, request)
        self.uids = {}
        self.pers = {}
        self.directory_path = "/".join(self.real_context.aq_parent.getPhysicalPath())
        self.dp_len = len(self.directory_path)
        self.pc = self.portal.portal_catalog

    def get_organizations(self):
        """
        Return a list of organizations, ordered by path, with parent id.
        [(id, parent_id, obj)]
        """
        lst = []
        id = 0
        paths = {}
        for brain in self.pc.unrestrictedSearchResults(
            portal_type="organization", path=self.directory_path, sort_on="path"
        ):
            id += 1
            self.uids[brain.UID] = id
            obj = brain._unrestrictedGetObject()
            path = brain.getPath()[self.dp_len:]
            parts = path.split("/")
            p_path = "/".join(parts[:-1])
            paths[path] = id
            p_id = ""
            if p_path:
                p_id = paths[p_path]
            lst.append((id, p_id, obj))
        return lst

    def get_persons(self):
        """
        Return a list of persons.
        [(id, obj)]
        """
        lst = []
        id = 0
        for brain in self.pc.unrestrictedSearchResults(
            portal_type="person", path=self.directory_path, sort_on="sortable_title"
        ):
            id += 1
            self.uids[brain.UID] = id
            self.pers[brain.getPath()[self.dp_len:]] = id
            obj = brain._unrestrictedGetObject()
            lst.append((id, obj))
        return lst

    def get_held_positions(self):
        """
        Return a list of held positions tuples.
        [(id, person_id, org_id, obj)]
        """
        lst = []
        id = 0
        for brain in self.pc.unrestrictedSearchResults(
            portal_type="held_position", path=self.directory_path, sort_on="path"
        ):
            id += 1
            self.uids[brain.UID] = id
            obj = brain._unrestrictedGetObject()
            # pers id
            path = brain.getPath()[self.dp_len:]
            parts = path.split("/")
            p_path = "/".join(parts[:-1])
            p_id = self.pers[p_path]
            # org id
            org = obj.get_organization()
            org_id = ""
            if org:
                org_id = self.uids[org.UID()]
            lst.append((id, p_id, org_id, obj))
        return lst

    def is_internal(self, contact):
        """
        Check if contact is internal (not INotPloneGroupContact => IPloneGroupContact or IPers)
        """
        return not INotPloneGroupContact.providedBy(contact)


# # # GENERATION VIEW # # #


class DbDocumentGenerationView(DashboardDocumentGenerationView):
    """ """

    def _get_generation_context(self, helper_view, pod_template):
        """ """
        gen_context = super(DbDocumentGenerationView, self)._get_generation_context(helper_view, pod_template)
        if pod_template.getId().startswith("d-im-listing"):
            gen_context["by_tg"] = helper_view.group_by_tg(gen_context.get("brains", []))
        return gen_context


class OMPDGenerationView(PersistentDocumentGenerationView):

    """Generation view used on an outgoingmail"""

    def _get_title(self, doc_name, gen_context):
        return self.pod_template.title

    def mailing_related_generation_context(self, helper_view, gen_context):
        mailing_list = helper_view.mailing_list(gen_context)
        if len(mailing_list) == 0:
            utils.update_dict_with_validation(gen_context, {'mailed_data': None},
                                              _dg("Error when merging mailed_data in generation context"))
        elif len(mailing_list) == 1:
            ctx = helper_view.mailed_context(mailing_list[0])
            utils.update_dict_with_validation(gen_context, {'mailed_data': ctx['mailed_data']},
                                              _dg("Error when merging mailed_data in generation context"))
            utils.update_dict_with_validation(gen_context, {'send_mode': ctx['send_mode']},
                                              _dg("Error when merging mailed_data in generation context"))

    def generate_persistent_doc(self, pod_template, output_format):
        """Create a dmsmainfile from the generated document"""
        self._copy_template_signers(pod_template)
        doc, doc_name, gen_context = self._generate_doc(pod_template, output_format)
        need_mailing = not ("mailed_data" in gen_context or "mailing_list" in gen_context)
        file_object = NamedBlobFile(doc, filename=safe_unicode(doc_name))
        scan_id = gen_context["scan_id"][4:]
        scan_params = [param for param in ("PD", "PC", "PVS") if gen_context.get(param, False)]
        # Could be stored in annotation
        scan_user = scan_params and "|".join(scan_params) or None

        if isinstance(pod_template, ConfigurablePODTemplate):
            category = pod_template.default_content_category
        else:  # MailingLoopTemplate
            category = self.document.content_category

        with api.env.adopt_roles(["Manager"]):
            persisted_doc = createContentInContainer(
                self.context,
                "dmsommainfile",
                title=self._get_title(doc_name, gen_context),
                id=scan_id,
                scan_id=scan_id,
                scan_user=scan_user,
                file=file_object,
                content_category=category,
                need_mailing=need_mailing,
            )
        # store informations on persisted doc
        self.add_mailing_infos(persisted_doc, gen_context)
        return persisted_doc

    def _copy_template_signers(self, pod_template):
        """Set outgoing mail signers from the template, depending on the omail_signers_origin mode.

        - "rules": signers come from the signer rules only, nothing is done here.
        - "template_first": copy the template signers; if the template defines none, fall back to
          the signer rules.
        - "rules_first": rules are authoritative; the template is only used as a fallback when the
          rules produced no signer (empty or only the _empty_ placeholder).

        In both non-"rules" modes, when neither the template nor the rules provide any signer, an
        _empty_ placeholder is set so the field is no longer reprocessed on next modification.
        """
        mode = api.portal.get_registry_record("omail_signers_origin", IImioDmsMailConfig, u"rules")
        if mode == u"rules":
            return
        source = pod_template
        if not isinstance(source, ConfigurablePODTemplate) and hasattr(self, "orig_template"):
            source = self.orig_template
        if not isinstance(source, ConfigurablePODTemplate):
            return
        mail = self.context
        mail_has_signers = bool(mail.signers)

        # "rules_first": when the rules already produced signers, the template configuration is ignored.
        if mode == u"rules_first" and mail_has_signers:
            return

        signers_source, _z = get_template_signers_source(source)
        template_signers = getattr(signers_source, "signers", None) if signers_source is not None else None
        if not template_signers:
            if mail_has_signers:
                return
            # we are in rules_first or template_first and mail has not signer
            if mode == u"template_first":
                # fall back to the signer rules to set signers
                apply_signer_rules(mail)
            if not mail.signers:
                # nothing from the template nor the rules: set an _empty_ value
                mail.signers = get_empty_signers_value()
            zope.event.notify(ObjectModifiedEvent(mail, Attributes(ISigningBehavior, "ISigningBehavior.signers")))
            return

        # copy the template signers, applying the active signer substitutes (as the rules do)
        resolved_signers = apply_substitutes_to_signers(copy.deepcopy(template_signers))

        # "template_first": warn (and skip) if the mail already has different signers (manual edit).
        if mail_has_signers:
            if mail.signers != resolved_signers:
                api.portal.show_message(
                    message=translate(
                        _(u"Warning: the mail already has signers configured that differ from the template. "
                          u"The template signers were not applied."),
                        context=self.request),
                    request=self.request,
                    type="warning",
                )
            return
        mail.signers = resolved_signers
        mail.seal = getattr(signers_source, "seal", False) or False
        mail.esign = getattr(signers_source, "esign", False) or False
        zope.event.notify(ObjectModifiedEvent(mail, Attributes(ISigningBehavior, "ISigningBehavior.signers")))

    def redirects(self, persisted_doc):
        """
        Redirects after creation.
        """
        self._set_header_response(persisted_doc.file.filename)
        response = self.request.response
        # return response.redirect(self.context.absolute_url())
        return response.redirect(persisted_doc.absolute_url() + "/external_edit")

    def _get_generation_context(self, helper_view, pod_template):
        """
        Return the generation context for the current document.
        This method is common for OMPDGenerationView and OMMLPDGenerationView
        """
        generation_context = super(OMPDGenerationView, self)._get_generation_context(helper_view, pod_template)

        if base_hasattr(self, "document"):
            # Mailing ! We use the same scan_id
            scan_id = self.document.scan_id
        elif helper_view.real_context.id == "test_creation_modele":
            client_id = base.get_config("client_id")
            scan_id = "%s2%s00000000" % (client_id[0:2], client_id[2:6])
        else:
            scan_id = next_scan_id(file_portal_types=["dmsommainfile", "dmsappendixfile"], scan_type="2")

        scan_id = "IMIO{0}".format(scan_id)
        update_dict_with_validation(
            generation_context,
            {
                "scan_id": scan_id,
                "barcode": generate_barcode(scan_id).read(),
                # for a non esign outgoingmail, the paragraph with the download url barcode will not be rendered
                "render_download_barcode": not (helper_view.real_context.esign or helper_view.real_context.seal),
            },
            _dg("Error when merging 'scan_id' in generation context"),
        )
        return generation_context


class OMMLPDGenerationView(MailingLoopPersistentDocumentGenerationView, OMPDGenerationView):
    """Inherits from 2 classes"""

    def _get_title(self, doc_name, gen_context):
        return u"%s, %s" % (self.pod_template.title, self.document.title)

    def _get_generation_context(self, helper_view, pod_template):
        """
        Return the generation context for the current document.
        """
        generation_context = super(OMMLPDGenerationView, self)._get_generation_context(helper_view, pod_template)

        if helper_view.real_context.esign or helper_view.real_context.seal:
            generation_context["page_break_after"] = False
        else:
            generation_context["page_break_after"] = True

        return generation_context

# # # TEMPLATE FORM OVERRIDES # # #


def _filter_signing_fieldset(form_instance):
    """Remove the signing fieldset from template form groups when signers come from rules only."""
    if api.portal.get_registry_record("omail_signers_origin", IImioDmsMailConfig, u"rules") == u"rules":
        form_instance.groups = [gr for gr in form_instance.groups if gr.__name__ != "signing"]


class DmsEditConfigurablePodTemplate(EditConfigurablePodTemplate):

    def update(self):
        super(DmsEditConfigurablePodTemplate, self).update()
        _filter_signing_fieldset(self)


class DmsViewConfigurablePodTemplate(DGDXDocumentViewerView):

    def update(self):
        super(DmsViewConfigurablePodTemplate, self).update()
        _filter_signing_fieldset(self)


# # # TEMPLATES LISTING SIGNERS COLUMN # # #


class TemplateSignersColumn(Column):
    """Column showing whether a template defines signers (directly or via a merge sub-template)."""

    header = _(u"Signers")
    weight = 55
    cssClasses = {"td": "signers-column"}

    def renderCell(self, item):
        if not base_hasattr(item, "signers"):
            # types without the signing behavior (e.g. style or mailing loop templates)
            return u""
        tmpl, itself = get_template_signers_source(item)
        if tmpl is not None:
            if itself:
                return u"<span class='svg-icon pt_self_signers' title='{0}'></span>".format(
                    translate(_(u"Signers defined"), context=self.request)
                )
            else:
                return u"<span class='svg-icon pt_sub_signers' title='{0}'></span>".format(
                    translate(_(u"Signers defined via sub template"), context=self.request)
                )
            icon = ("++resource++imio.dms.mail/itemIsSignedYes.png",
                    translate(_(u"Signers defined"), context=self.request))
        else:
            return u""
        return u"<img class='svg-icon' title='{0}' src='{1}' />".format(
            safe_unicode(icon[1]).replace("'", "&#39;"),
            u"{0}/{1}".format(self.table.portal_url, icon[0]))


class DmsTemplatesTable(TemplatesTable):
    """TemplatesTable variant hiding the signers column when signers come from rules only."""

    def setUpColumns(self):
        columns = super(DmsTemplatesTable, self).setUpColumns()
        mode = api.portal.get_registry_record("omail_signers_origin", IImioDmsMailConfig, u"rules")
        if mode == u"rules":
            columns = [col for col in columns if col.__name__ != "TemplateSignersColumn"]
        return columns


class DmsTemplatesListing(TemplatesListing):
    """'dg-templates-listing' variant using DmsTemplatesTable to add the signers column."""

    __table__ = DmsTemplatesTable


class DmsAddConfigurablePodTemplateForm(DefaultAddForm):

    portal_type = "ConfigurablePODTemplate"

    def update(self):
        super(DmsAddConfigurablePodTemplateForm, self).update()
        _filter_signing_fieldset(self)


class DmsAddConfigurablePodTemplate(DefaultAddView):

    form = DmsAddConfigurablePodTemplateForm


# SubTemplate form overrides. Plain Dexterity base forms are used here (no children_pod_template
# provider, which only exists on ConfigurablePODTemplate).


class DmsEditSubTemplate(DefaultEditForm):

    def update(self):
        super(DmsEditSubTemplate, self).update()
        _filter_signing_fieldset(self)


class DmsViewSubTemplate(DXDocumentViewerView):

    def update(self):
        super(DmsViewSubTemplate, self).update()
        _filter_signing_fieldset(self)


class DmsAddSubTemplateForm(DefaultAddForm):

    portal_type = "SubTemplate"

    def update(self):
        super(DmsAddSubTemplateForm, self).update()
        _filter_signing_fieldset(self)


class DmsAddSubTemplate(DefaultAddView):

    form = DmsAddSubTemplateForm


# # # VIEWLETS # # #


class OutgoingMailLinksViewlet(DocumentGeneratorLinksViewlet):
    """This viewlet displays available documents to generate on outgoingmail."""

    def available(self):
        return False

    def get_generation_view_name(self, template, output_format):
        return "persistent-document-generation"
