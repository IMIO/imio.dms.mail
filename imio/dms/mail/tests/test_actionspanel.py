# -*- coding: utf-8 -*-
"""Test views."""
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestDmsIMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.REQUEST['AUTHENTICATED_USER'] = api.user.get(username=TEST_USER_ID)
        self.im1 = self.portal['incoming-mail']['courrier1']
        self.view = self.im1.unrestrictedTraverse('@@actions_panel')

    def test_renderReplyButton(self):
        self.view.useIcons = True
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="http://nohost/plone/incoming-mail/'
                         'courrier1/@@reply">\n     \n     <img title="Reply" src=" http://nohost/plone/'
                         '++resource++imio.dms.mail/reply_icon.png" />\n  </a>\n</td>\n<td class="noPadding"></td>\n')
        self.view.useIcons = False
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="http://nohost/plone/incoming-mail/'
                         'courrier1/@@reply">\n     <input type="button" value="Reply" class="apButton apButtonAction '
                         'apButtonAction_reply" />\n     \n  </a>\n</td>\n<td class="noPadding"></td>\n')

    def test_renderAssignUser(self):
        self.view.useIcons = False
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select class="apButton apButtonAction '
                         u'apButtonAction_assign" name="Assign" onchange="javascript:window.location=this.value;">'
                         u'\n        <option style="display:none" value="#">Assign</option>\n        \n        <option '
                         u'value="http://nohost/plone/incoming-mail/courrier1/@@update_item?assigned_user=chef">'
                         u'Michel Chef</option>\n      </select>\n    </form>\n</td>\n')
        self.view.useIcons = True
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select class="apButton apButtonAction '
                         u'apButtonAction_assign" name="Assign" onchange="javascript:window.location=this.value;">'
                         u'\n        \n        <option style="display:none" value="#"></option>\n        <option '
                         u'value="http://nohost/plone/incoming-mail/courrier1/@@update_item?assigned_user=chef">'
                         u'Michel Chef</option>\n      </select>\n    </form>\n</td>\n')
        new = api.content.create(self.portal['incoming-mail'], 'dmsincomingmail', 'c1')
        view = new.unrestrictedTraverse('@@actions_panel')
        view.useIcons = True
        self.assertEqual(view.renderAssignUser(), '')

    def test_sortTransitions(self):
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_service_chief'])
        api.content.transition(obj=self.im1, to_state='proposed_to_agent')
        # with caching
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_service_chief'])
        # without caching
        self.assertListEqual([t['id'] for t in self.view.getTransitions(caching=False)],
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
