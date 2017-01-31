# -*- coding: utf-8 -*-
""" documentgenerator.py tests for this package."""
import unittest

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.browser.documentgenerator import DocumentGenerationCategoriesHelper


class TestDocumentGenerator(unittest.TestCase):
    """Test installation of imio.project.pst into Plone."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pc = self.portal.portal_catalog
        self.omf = self.portal['outgoing-mail']

    def test_DocumentGenerationOMDashboardHelper(self):
        view = self.omf['mail-searches'].unrestrictedTraverse('@@document_generation_helper_view')
        # for dashboard
        view.request.form['facetedQuery'] = ''
        self.assertTrue(view.is_dashboard())
        brains = self.pc(id=['reponse1', 'reponse2', 'reponse3'])
        view.context_var = lambda x: brains
        objs = [b.getObject() for b in brains]
        # test getting files
        files = view.get_dms_files()
        self.assertListEqual(files, [(objs[0]['1'], True), (objs[1]['1'], False), (objs[2]['1'], False)])
        # test getting num pages
        self.assertEquals(view.get_num_pages(objs[0]['1']), 1)
        self.assertEquals(view.get_num_pages(objs[1]['1']), 2)
        self.assertEquals(view.get_num_pages(objs[2]['1']), 1)
        # test getting images
        images = view.get_dv_images(objs[0]['1'])
        self.assertEqual(len(images), 1)
        self.assertTrue(hasattr(images[0], 'read'))
        images[0].close()
