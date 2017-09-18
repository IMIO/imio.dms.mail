# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from plone import api
from plone.app.uuid.utils import uuidToObject
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import safe_unicode
from collective.contact.core.interfaces import IContactable
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.person import IPerson
from collective.documentgenerator import _ as _dg
from collective.documentgenerator.browser.generation_view import PersistentDocumentGenerationView
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.documentgenerator.utils import update_dict_with_validation
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from imio.dashboard.browser.overrides import IDDocumentGenerationView
from imio.helpers.barcode import generate_barcode
from imio.zamqp.core.utils import next_scan_id


### HELPERS ###

class OMDGHelper(DXDocumentGenerationHelperView):
    """
        Helper methods used for outgoing mail generation
    """

    def fmt(self, val, fmt='%s '):
        if val:
            return fmt % val
        return ''

    def get_ctct_det(self, obj, fallback=True):
        try:
            contactable = IContactable(obj)
            return contactable.get_contact_details(fallback=fallback)
            # {'website': '', 'fax': '', 'phone': '', 'address': {'city': u'Eghez\xe9e', 'country': '', 'region': '',
            # 'additional_address_details': '', 'number': u'8', 'street': u'Grande Ruelle', 'zip_code': u'5310'},
            # 'im_handle': '', 'cell_phone': '', 'email': ''}
        except:
            return {}

    def get_sender(self):
        om = self.real_context
        sender = uuidToObject(om.sender)
        if not sender:
            return {}
        ret = {}
        #ret['label'] = sender.label
        ret['hp'] = sender
        # sender.get_full_title(), sender.get_person_title()
        person = sender.get_person()
        ret['person'] = person
        #ret['person_title'] = person.person_title
        #ret['get_title'] = person.get_title()
        # get contactable informations
        #ret.update(self.get_ctct_det(sender))
        org = sender.get_organization()
        ret['org'] = org
        ret['org_full_title'] = org.get_full_title(separator=' - ', first_index=1)
        return ret

    def get_recipient(self):
        om = self.real_context
        if not om.recipients:
            return None
        relval = om.recipients[0]
        if relval.isBroken():
            return None
        recipient = relval.to_object
        return recipient

    def get_full_title(self, contact, **kwargs):
        if IPerson.providedBy(contact):
            return contact.get_title()
        elif IOrganization.providedBy(contact):
            return contact.get_full_title(**kwargs)
        elif IHeldPosition.providedBy(contact):
            return contact.get_full_title()
        else:
            return ''

    def do_mailing(self):
        return True


class DashboardDGBaseHelper():
    """
        Common methods
    """

    objs = []
    sel_type = ''

    def is_dashboard(self):
        """ Test if template is rendered from a dashboard """
        return 'facetedQuery' in self.request.form

    def uids_to_objs(self, brains):
        """ set objects from brains """
        # can be used like this in normal template:
        # do section- if view.is_dashboard()
        # do text if view.uids_to_objs(brains)
        self.objs = []
        for brain in brains:
            self.objs.append(brain.getObject())
        self.sel_type = len(brains) and self.objs[0].portal_type or ''
        return False


class DocumentGenerationDocsDashboardHelper(ATDocumentGenerationHelperView, DashboardDGBaseHelper):
    """
        Methods used for listing
    """

    def group_by_tg(self, brains):
        results = {'1_no_group': {'mails': [], 'title': translate('listing_no_group', domain="imio.dms.mail",
                                                                  context=self.request)}}
        for brain in brains:
            obj = brain.getObject()
            tg = brain.treating_groups
            if tg:
                if not tg in results:
                    results[tg] = {'mails': []}
                    title = tg
                    tgroup = uuidToObject(tg)
                    if tgroup is not None:
                        title = tgroup.get_full_title(separator=' - ', first_index=1)
                    results[tg]['title'] = title
                results[tg]['mails'].append(obj)
            else:
                results['1_no_group']['mails'].append(obj)
        if not results['1_no_group']['mails']:
            del results['1_no_group']
        return results


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
        #self.uids_to_objs(self.context_var('brains'))
        for brain in self.context_var('brains'):
            brains = catalog(portal_type='dmsommainfile', path=brain.getPath(), sort_on='getObjPositionInParent',
                             sort_order='descending')
            if limit:
                brains = brains[0:limit]
            for bfile in brains:
                obj = bfile.getObject()
                files.append([obj, self.get_num_pages(obj)])
        result = []
        last_i = len(files) - 1
        for i, (afile, pages) in enumerate(files):
            odd = bool(pages % 2)
            if i == 0:
                result.append((afile, False, odd))
            else:
                pbb = False
                if files[i-1][1] == 1:
                    pbb = True
                pba = odd
                if i == last_i:
                    pba = False
                result.append((afile, pbb, pba))
        return result

    def get_num_pages(self, obj):
        annot = IAnnotations(obj).get('collective.documentviewer', '')
        if not annot or not annot['successfully_converted'] or not annot.get('num_pages', None):
            return 0
        return annot['num_pages']

    def get_dv_images(self, obj):
        images = []
        annot = IAnnotations(obj).get('collective.documentviewer', '')
        if not annot or not annot['successfully_converted'] or not annot.get('blob_files', None):
            return []
        files = annot.get('blob_files', {})
        for page in range(1, annot['num_pages']+1):
            img = 'large/dump_%d.%s' % (page, annot['pdf_image_format'])
            blob = files[img]
            images.append(blob.open())
        return images


class DocumentGenerationCategoriesHelper(ATDocumentGenerationHelperView, DashboardDGBaseHelper):
    """
        Helper for categories folder
    """


class DocumentGenerationDirectoryHelper(DXDocumentGenerationHelperView):
    """
        Helper for collective.contact.core directory
    """

    def __init__(self, context, request):
        super(DocumentGenerationDirectoryHelper, self).__init__(context, request)
        self.uids = {}
        self.pers = {}
        self.directory_path = '/'.join(self.context.getPhysicalPath())
        self.dp_len = len(self.directory_path)

    def get_organizations(self):
        """ Return a list of organizations, ordered by path, with parent id """
        lst = []
        id = 0
        paths = {}
        for brain in self.portal.portal_catalog(portal_type='organization', path=self.directory_path, sort_on='path'):
            id += 1
            self.uids[brain.UID] = id
            obj = brain.getObject()
            path = brain.getPath()[self.dp_len:]
            parts = path.split('/')
            p_path = '/'.join(parts[:-1])
            paths[path] = id
            p_id = ''
            if p_path:
                p_id = paths[p_path]
            lst.append((id, p_id, obj))
        return lst

    def get_persons(self):
        """ Return a list of persons """
        lst = []
        id = 0
        for brain in self.portal.portal_catalog(portal_type='person', path=self.directory_path,
                                                sort_on='sortable_title'):
            id += 1
            self.uids[brain.UID] = id
            self.pers[brain.getPath()[self.dp_len:]] = id
            obj = brain.getObject()
            lst.append((id, obj))
        return lst

    def get_held_positions(self):
        """ Return a list of held positions """
        lst = []
        id = 0
        for brain in self.portal.portal_catalog(portal_type='held_position', path=self.directory_path, sort_on='path'):
            id += 1
            self.uids[brain.UID] = id
            obj = brain.getObject()
            # pers id
            path = brain.getPath()[self.dp_len:]
            parts = path.split('/')
            p_path = '/'.join(parts[:-1])
            p_id = self.pers[p_path]
            # org id
            org = obj.get_organization()
            org_id = ''
            if org:
                org_id = self.uids[org.UID()]
            lst.append((id, p_id, org_id, obj))
        return lst


### GENERATION VIEW ###

class DashboardDocumentGenerationView(IDDocumentGenerationView):
    """
    """

    def _get_generation_context(self, helper_view, pod_template):
        """ """
        gen_context = super(DashboardDocumentGenerationView, self)._get_generation_context(helper_view, pod_template)
        if pod_template.getId() == 'd-im-listing':
            gen_context['by_tg'] = helper_view.group_by_tg(gen_context.get('brains', []))
        return gen_context


class OMPDGenerationView(PersistentDocumentGenerationView):

    def generate_persistent_doc(self, pod_template, output_format):
        """ Create a dmsmainfile from the generated document """
        doc, doc_name, gen_context = self._generate_doc(pod_template, output_format)
        file_object = NamedBlobFile(doc, filename=safe_unicode(doc_name))
        scan_id = gen_context['scan_id'][4:]
        scan_params = [param for param in ('PD', 'PC', 'PVS') if gen_context.get(param, False)]
        # Could be stored in annotation
        scan_user = (scan_params and '|'.join(scan_params) or None)
        with api.env.adopt_roles(['Manager']):
            persisted_doc = createContentInContainer(self.context, 'dmsommainfile', title=pod_template.title,
                                                     id=scan_id, scan_id=scan_id, scan_user=scan_user, file=file_object)
        return persisted_doc

    def redirects(self, persisted_doc):
        """
        Redirects after creation.
        """
        self._set_header_response(persisted_doc.file.filename)
        response = self.request.response
        #return response.redirect(self.context.absolute_url())
        return response.redirect(persisted_doc.absolute_url() + '/external_edit')

    def _get_generation_context(self, helper_view, pod_template):
        """
        Return the generation context for the current document.
        """
        generation_context = super(OMPDGenerationView, self)._get_generation_context(helper_view, pod_template)
        recipient = helper_view.get_recipient()
        if recipient:
            update_dict_with_validation(generation_context,
                                        {'mailed_data': recipient},
                                        _dg("Error when merging mailed_data in generation context"))
        scan_id = next_scan_id(file_portal_type='dmsommainfile', scan_type='2')
        scan_id = 'IMIO{0}'.format(scan_id)
        update_dict_with_validation(generation_context,
                                    {'scan_id': scan_id,
                                     'barcode': generate_barcode(scan_id).read()},
                                    _dg("Error when merging helper_view in generation context"))
        return generation_context


class CategoriesDocumentGenerationView(IDDocumentGenerationView):
    """
        UNUSED
        Change context for folder categories => dashboard collections context
    """

    def _get_generation_context(self, helper_view, pod_template):
        """ """
        gen_context = super(CategoriesDocumentGenerationView, self)._get_generation_context(helper_view, pod_template)
        if hasattr(helper_view, 'uids_to_objs'):
            helper_view.uids_to_objs(gen_context.get('brains', []))
            if helper_view.sel_type:
                gen_context['context'] = helper_view.objs[0].aq_parent
                gen_context['view'] = helper_view.getDGHV(gen_context['context'])
        return gen_context

### VIEWLETS ###


class OutgoingMailLinksViewlet(DocumentGeneratorLinksViewlet):
    """This viewlet displays available documents to generate on outgoingmail."""

    def available(self):
        return False

    def get_generation_view_name(self, template, output_format):
        return 'persistent-document-generation'
