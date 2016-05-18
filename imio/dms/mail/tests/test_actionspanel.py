# -*- coding: utf-8 -*-
"""Test views."""
import unittest
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID

from ..testing import DMSMAIL_INTEGRATION_TESTING


class TestDmsIMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.im1 = self.portal['incoming-mail']['courrier1']
        self.view = self.im1.unrestrictedTraverse('@@actions_panel')

    def test_renderReplyButton(self):
        self.assertEqual(self.view.renderReplyButton(), "")

    def test_sortTransitions(self):
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_service_chief'])
        api.content.transition(obj=self.im1, to_state='proposed_to_agent')
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['back_to_service_chief', 'treat', 'close'])
        to_sort = [{'id': 'close'}, {'id': 'back_to_creation'}, {'id': 'treat'}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{'id': 'back_to_creation'}, {'id': 'treat'}, {'id': 'close'}])
        to_sort = [{'id': 'unknown'}, {'id': 'close'}, {'id': 'back_to_creation'}, {'id': 'treat'}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{'id': 'back_to_creation'}, {'id': 'treat'}, {'id': 'close'}, {'id': 'unknown'}])


class TestContactActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        self.portal = self.layer['portal']
        self.swde = self.portal['contacts']['swde']
        self.view = self.swde.unrestrictedTraverse('@@actions_panel')
