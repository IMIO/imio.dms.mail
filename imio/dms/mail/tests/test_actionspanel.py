# -*- coding: utf-8 -*-
"""Test views."""
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import unittest


class TestDmsIMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        change_user(self.portal)
        self.portal.REQUEST['AUTHENTICATED_USER'] = api.user.get(username='siteadmin')
        self.im2 = get_object(oid='courrier2', ptype='dmsincomingmail')
        self.view = self.im2.unrestrictedTraverse('@@actions_panel')
        self.intids = getUtility(IIntIds)

    def test_mayReply(self):
        self.assertEqual(api.content.get_state(self.im2), 'created')
        self.assertTrue(self.view.mayReply())
        # change state
        api.content.transition(self.im2, 'propose_to_manager')
        self.assertEqual(api.content.get_state(self.im2), 'proposed_to_manager')
        self.assertTrue(self.view.mayReply())
        # change title
        self.im2.title = None
        self.assertFalse(self.view.mayReply())
        self.im2.title = u'title'
        # removed permission
        api.content.transition(self.im2, to_state='proposed_to_agent')
        change_user(self.portal, 'lecteur')
        self.view.request.set('imio.actionspanel_member_cachekey', None)
        self.assertFalse(self.view.mayReply())

    def test_renderReplyButton(self):
        api.content.transition(self.im2, 'propose_to_manager')
        self.view.useIcons = True
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="{}'
                         '/@@reply">\n     \n     <img title="Reply" src=" http://nohost/plone/'
                         '++resource++imio.dms.mail/reply_icon.png" />\n  </a>\n</td>'
                         '\n'.format(self.im2.absolute_url()))
#                         '<td class="noPadding"></td>\n'.format(self.im2.absolute_url()))
        self.view.useIcons = False
        self.assertEqual(self.view.renderReplyButton(),
                         '<td class="noPadding">\n  <a target="_parent" href="{}'
                         '/@@reply">\n     <input type="button" value="Reply" class="apButton apButtonAction '
                         'apButtonAction_reply" />\n     \n  </a>\n</td>'
                         '\n'.format(self.im2.absolute_url()))
#                         '<td class="noPadding"></td>\n'.format(self.im2.absolute_url()))

    def test_renderAssignUser(self):
        self.view.useIcons = False
        self.assertEqual(api.content.get_state(self.view.context), 'created')
        self.assertEqual(self.view.renderAssignUser(), '')
        api.content.transition(self.view.context, 'propose_to_manager')
        # right state
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select name="Assign" onchange="javascript:'
                         u'callViewAndReload(base_url=\'{}\', view_name=\'@@update_item\', params={{\'assigned_user\': '
                         u'this.value}})" class="apButton apButtonSelect apButtonAction apButtonAction_assign">\n'
                         u'        <option style="display:none" value="#">Assign</option>\n        \n        '
                         u'<option value="agent">Fred Agent</option>\n      </select>\n    </form>\n</td>'
                         u'\n'.format(self.im2.absolute_url()))
        self.view.useIcons = True
        self.assertEqual(self.view.renderAssignUser(),
                         u'<td>\n    <form action="">\n      <select name="Assign" onchange="javascript:'
                         u'callViewAndReload(base_url=\'{}\', view_name=\'@@update_item\', params={{\'assigned_user\': '
                         u'this.value}})" class="apButton apButtonSelect apButtonAction apButtonAction_assign '
                         u'apUseIcons">\n        \n        <option style="display:none" value="#"></option>\n        '
                         u'<option value="agent">Fred Agent</option>\n      </select>\n    </form>\n</td>'
                         u'\n'.format(self.im2.absolute_url()))
        # without treating_groups
        new = api.content.create(self.portal['incoming-mail'], 'dmsincomingmail', 'c1')
        view = new.unrestrictedTraverse('@@actions_panel')
        view.useIcons = True
        self.assertEqual(view.renderAssignUser(), '')

    def test_sortTransitions(self):
        self.assertListEqual([t['id'] for t in self.view.getTransitions()],
                             ['propose_to_manager', 'propose_to_agent'])
        api.content.transition(obj=self.im2, to_state='proposed_to_agent')
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
        # we have 5 actions: edit, propose manager, propose agent, reply
        self.assertEqual(ret0.count(u'<td '), 4)
        api.content.transition(self.im2, 'propose_to_agent')
        ret1 = self.view()
        # we have the same transitions because there is a cache on getTransitions
        # we have also assign but it starts with <td>
        self.assertEqual(ret1.count(u'<td '), 4)
        # we add a reply
        om2 = get_object(oid='reponse2', ptype='dmsoutgoingmail')
        om2.reply_to = [RelationValue(self.intids.getId(self.im2))]
        modified(om2)
        ret2 = self.view()
        self.assertEqual(ret2.count(u'<td '), 4)


class TestContactActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        self.portal = self.layer['portal']
        self.swde = self.portal['contacts']['swde']
        self.view = self.swde.unrestrictedTraverse('@@actions_panel')
