# -*- coding: utf-8 -*-
"""Test views."""
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import unittest


class TestDmsIMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.REQUEST['AUTHENTICATED_USER'] = api.user.get(username=TEST_USER_ID)
        self.im1 = self.portal['incoming-mail']['courrier2']
        self.view = self.im1.unrestrictedTraverse('@@actions_panel')
        self.intids = getUtility(IIntIds)

    def test_mayReply(self):
        self.assertEqual(api.content.get_state(self.im1), 'created')
        self.assertFalse(self.view.mayReply())
        # change state
        api.content.transition(self.im1, 'propose_to_manager')
        self.assertEqual(api.content.get_state(self.im1), 'proposed_to_manager')
        self.assertTrue(self.view.mayReply())
        # change title
        self.im1.title = None
        self.assertFalse(self.view.mayReply())
        self.im1.title = u'title'
        # removed permission
        api.content.transition(self.im1, to_state='proposed_to_agent')
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        logout()
        login(self.portal, 'lecteur')
        self.view.request.set('imio.actionspanel_member_cachekey', None)
        self.assertFalse(self.view.mayReply())

    def test_renderReplyButton(self):
        api.content.transition(self.im1, 'propose_to_manager')
        self.view.useIcons = True
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="http://nohost/plone/incoming-mail/'
                         'courrier2/@@reply">\n     \n     <img title="Reply" src=" http://nohost/plone/'
                         '++resource++imio.dms.mail/reply_icon.png" />\n  </a>\n</td>\n<td class="noPadding"></td>\n')
        self.view.useIcons = False
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="http://nohost/plone/incoming-mail/'
                         'courrier2/@@reply">\n     <input type="button" value="Reply" class="apButton apButtonAction '
                         'apButtonAction_reply" />\n     \n  </a>\n</td>\n<td class="noPadding"></td>\n')

    def test_renderAssignUser(self):
        self.view.useIcons = False
        self.assertEqual(api.content.get_state(self.view.context), 'created')
        self.assertEqual(self.view.renderAssignUser(), '')
        api.content.transition(self.view.context, 'propose_to_manager')
        # right state
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select class="apButton apButtonSelect apButtonAction '
                         u'apButtonAction_assign" name="Assign" onchange="javascript:callViewAndReload(base_url='
                         u'\'http://nohost/plone/incoming-mail/courrier2\', view_name=\'@@update_item\', params='
                         u'{\'assigned_user\': this.value})">\n        <option style="display:none" value="#">Assign'
                         u'</option>\n        \n        <option value="agent">Fred Agent</option>\n      </select>'
                         u'\n    </form>\n</td>\n')
        self.view.useIcons = True
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select class="apButton apButtonSelect apButtonAction '
                         u'apButtonAction_assign" name="Assign" onchange="javascript:callViewAndReload(base_url='
                         u'\'http://nohost/plone/incoming-mail/courrier2\', view_name=\'@@update_item\', params='
                         u'{\'assigned_user\': this.value})">\n        \n        <option style="display:none" value='
                         u'"#"></option>\n        <option value="agent">Fred Agent</option>\n      </select>\n    '
                         u'</form>\n</td>\n')
        # without treating_groups
        new = api.content.create(self.portal['incoming-mail'], 'dmsincomingmail', 'c1')
        view = new.unrestrictedTraverse('@@actions_panel')
        view.useIcons = True
        self.assertEqual(view.renderAssignUser(), '')

    def test_sortTransitions(self):
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_agent'])
        api.content.transition(obj=self.im1, to_state='proposed_to_agent')
        # with caching
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_agent'])
        # without caching
        self.assertListEqual([t['id'] for t in self.view.getTransitions(caching=False)],
                             ['back_to_creation', 'back_to_manager', 'treat', 'close'])
        to_sort = [{'id': 'close'}, {'id': 'back_to_creation'}, {'id': 'treat'}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{'id': 'back_to_creation'}, {'id': 'treat'}, {'id': 'close'}])
        to_sort = [{'id': 'unknown'}, {'id': 'close'}, {'id': 'back_to_creation'}, {'id': 'treat'}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{'id': 'back_to_creation'}, {'id': 'treat'}, {'id': 'close'}, {'id': 'unknown'}])

    def test_im_actionspanel_cache(self):
        # TODO update this irrelevant test
        ret0 = self.view()
        # we have 3 actions: edit, propose manager, propose agent
        self.assertEqual(ret0.count(u'<td '), 3)
        api.content.transition(self.im1, 'propose_to_agent')
        ret1 = self.view()
        # we have the same transitions because there is a cache on getTransitions
        self.assertEqual(ret1.count(u'<td '), 5)
        # we add a reply
        om2 = self.portal['outgoing-mail']['reponse2']
        om2.reply_to = [RelationValue(self.intids.getId(self.im1))]
        modified(om2)
        ret2 = self.view()
        self.assertEqual(ret2.count(u'<td '), 5)


class TestContactActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        self.portal = self.layer['portal']
        self.swde = self.portal['contacts']['swde']
        self.view = self.swde.unrestrictedTraverse('@@actions_panel')
