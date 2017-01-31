# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from plone import api
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from imio.dashboard.browser.overrides import IDDocumentGenerationView


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


class DocumentGenerationOMDashboardHelper(ATDocumentGenerationHelperView, DocumentGenerationBaseHelper):
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


class CategoriesDocumentGenerationView(IDDocumentGenerationView):
    """
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
