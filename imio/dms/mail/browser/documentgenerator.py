# -*- coding: utf-8 -*-
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.person import IPerson
from collective.contact.core.interfaces import IContactable
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.documentgenerator import _ as _dg
from collective.documentgenerator.browser.generation_view import MailingLoopPersistentDocumentGenerationView
from collective.documentgenerator.browser.generation_view import PersistentDocumentGenerationView
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.documentgenerator.utils import update_dict_with_validation
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGenerationView
from imio.helpers.barcode import generate_barcode
from imio.helpers.content import uuidToObject
from imio.zamqp.core import base
from imio.zamqp.core.utils import next_scan_id
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate

import operator


# # # HELPERS # # #


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
        if not obj.classification_folders:
            return []
        ret = []
        for fld in obj.classification_folders:
            obj = uuidToObject(fld, unrestricted=True)
            if hasattr(obj, "internal_reference_no") and obj.internal_reference_no is not None:
                ret.append(obj.internal_reference_no)
            else:
                ret.append(obj.Title())
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
            ret[-1] = sep.join(parts[nb - 1 :])
        return ret


class IMDGHelper(BaseDGHelper):
    """
    Helper methods used for incoming mail generation
    """


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
        om = self.real_context
        if not om.recipients:
            return []
        ml = []
        for relval in om.recipients:
            if relval.isBroken():
                continue
            ml.append(relval.to_object)
        return ml

    def is_first_doc(self):
        """in mailing context"""
        ctx = self.appy_renderer.contentParser.env.context
        if "loop" in ctx and hasattr(ctx["loop"], "mailed_data") and not ctx["loop"].mailed_data.first:
            return False
        return True


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


class DocumentGenerationOMDashboardHelper(DocumentGenerationDocsDashboardHelper):
    """
    Methods used in document generation view, for IOMDashboard
    """

    def get_dms_files(self, limit=None):
        """
        Return a list of tuples containing the file obj, a pageBreakBefore boolean, a pageBreakAfter boolean
        """
        files = []
        if not self.is_dashboard():
            return files
        catalog = self.portal.portal_catalog
        # self.uids_to_objs(self.context_var('brains'))
        limit = 1  # needed to be coherent with dashboard info following lastDmsFileIsOdt
        for brain in self.context_var("brains"):
            brains = catalog.unrestrictedSearchResults(
                portal_type="dmsommainfile",
                path=brain.getPath(),
                sort_on="getObjPositionInParent",
                sort_order="descending",
                sort_limit=limit,
            )
            if limit:
                brains = brains[0:limit]
            for bfile in brains:
                doc = bfile._unrestrictedGetObject()
                # if brain.markers is not Missing.Value and 'lastDmsFileIsOdt' in brain.markers
                if doc.is_odt():
                    files.append(doc)
        return files

    def get_num_pages(self, obj):
        annot = IAnnotations(obj).get("collective.documentviewer", "")
        if not annot or not annot["successfully_converted"] or not annot.get("num_pages", None):
            return 0
        return annot["num_pages"]

    def get_dv_images(self, obj):
        images = []
        annot = IAnnotations(obj).get("collective.documentviewer", "")
        if not annot or not annot["successfully_converted"] or not annot.get("blob_files", None):
            return []
        files = annot.get("blob_files", {})
        for page in range(1, annot["num_pages"] + 1):
            img = "large/dump_%d.%s" % (page, annot["pdf_image_format"])
            blob = files[img]
            images.append(blob.open())
        return images


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
            path = brain.getPath()[self.dp_len :]
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
            self.pers[brain.getPath()[self.dp_len :]] = id
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
            path = brain.getPath()[self.dp_len :]
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

    def generate_persistent_doc(self, pod_template, output_format):
        """Create a dmsmainfile from the generated document"""
        doc, doc_name, gen_context = self._generate_doc(pod_template, output_format)
        file_object = NamedBlobFile(doc, filename=safe_unicode(doc_name))
        scan_id = gen_context["scan_id"][4:]
        scan_params = [param for param in ("PD", "PC", "PVS") if gen_context.get(param, False)]
        # Could be stored in annotation
        scan_user = scan_params and "|".join(scan_params) or None
        with api.env.adopt_roles(["Manager"]):
            persisted_doc = createContentInContainer(
                self.context,
                "dmsommainfile",
                title=self._get_title(doc_name, gen_context),
                id=scan_id,
                scan_id=scan_id,
                scan_user=scan_user,
                file=file_object,
            )
        # store informations on persisted doc
        self.add_mailing_infos(persisted_doc, gen_context)

        return persisted_doc

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
            scan_id = next_scan_id(file_portal_types=["dmsommainfile"], scan_type="2")

        scan_id = "IMIO{0}".format(scan_id)
        update_dict_with_validation(
            generation_context,
            {"scan_id": scan_id, "barcode": generate_barcode(scan_id).read()},
            _dg("Error when merging 'scan_id' in generation context"),
        )
        return generation_context


class OMMLPDGenerationView(MailingLoopPersistentDocumentGenerationView, OMPDGenerationView):
    """Inherits from 2 classes"""

    def _get_title(self, doc_name, gen_context):
        return u"%s, %s" % (self.pod_template.title, self.document.title)


# # # VIEWLETS # # #


class OutgoingMailLinksViewlet(DocumentGeneratorLinksViewlet):
    """This viewlet displays available documents to generate on outgoingmail."""

    def available(self):
        return False

    def get_generation_view_name(self, template, output_format):
        return "persistent-document-generation"
