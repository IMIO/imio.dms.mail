# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from plone import api
from plone.app.uuid.utils import uuidToObject
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from collective.documentgenerator.browser.generation_view import PersistentDocumentGenerationView
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from imio.dashboard.browser.overrides import IDDocumentGenerationView


### HELPERS ###

class DocumentGenerationBaseHelper():
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


class DocumentGenerationDocsDashboardHelper(ATDocumentGenerationHelperView, DocumentGenerationBaseHelper):
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

    def get_dms_files(self):
        files = []
        if not self.is_dashboard():
            return files
        catalog = self.portal.portal_catalog
        #self.uids_to_objs(self.context_var('brains'))
        for brain in self.context_var('brains'):
            for bfile in catalog(portal_type='dmsmainfile', path=brain.getPath()):
                obj = bfile.getObject()
                files.append((obj, bool(self.get_num_pages(obj) % 2)))
        last = files.pop()
        files.append((last[0], False))
        return files

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


class DocumentGenerationCategoriesHelper(ATDocumentGenerationHelperView, DocumentGenerationBaseHelper):
    """
        Helper for categories folder
    """


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

        doc, doc_name = self._generate_doc(pod_template, output_format)
        splitted_name = doc_name.split('.')
        title = '.'.join(splitted_name[:-1])

        file_object = NamedBlobFile(doc, filename=doc_name)
        with api.env.adopt_roles(['Manager']):
            persisted_doc = createContentInContainer(self.context, 'dmsmainfile', title=title,
                                                     file=file_object)
        return persisted_doc

    def redirects(self, persisted_doc):
        """
        Redirects after creation.
        """
        self._set_header_response(persisted_doc.file.filename)
        response = self.request.response
        #return response.redirect(self.context.absolute_url())
        return response.redirect(persisted_doc.absolute_url() + '/external_edit')


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

    def get_generation_view_name(self, template, output_format):
        return 'persistent-document-generation'
