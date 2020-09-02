# -*- coding: utf-8 -*-
"""Test views."""
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class BatchActions(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pc = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.msf = self.imf['mail-searches']
        self.imdb = self.imf['mail-searches']['all_mails']
        self.im1 = self.imf['courrier1']
        self.im2 = self.imf['courrier2']
        self.im3 = self.imf['courrier3']
        self.im4 = self.imf['courrier4']
        self.tsf = self.portal['tasks']['task-searches']
        self.ta1 = self.im1['tache1']
        self.ta2 = self.im1['tache2']
        self.ta3 = self.im1['tache3']
        self.pgof = self.portal['contacts']['plonegroup-organization']

    def test_TransitionBatchActionForm(self):
        self.assertEqual('created', api.content.get_state(self.im1))
        view = self.msf.unrestrictedTraverse('@@transition-batch-action')
        view.request.form['form.widgets.uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        # override z3c.form.field.FieldWidgets.extract
        view.widgets.extract = lambda *a, **kw: ({'transition': u'propose_to_manager', 'comment': u''}, [])
        view.handleApply(view, 'apply')
        self.assertEqual('proposed_to_manager', api.content.get_state(self.im1))
        self.assertEqual('proposed_to_manager', api.content.get_state(self.im2))

    def test_TreatingGroupBatchActionForm(self):
        self.assertEqual(self.im1.treating_groups, self.pgof['direction-generale'].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof['direction-generale']['secretariat'].UID())
        api.group.add_user(groupname='{}_editeur'.format(self.pgof['direction-financiere'].UID()), username='chef')
        self.im2.assigned_user = 'agent'
        self.im2.reindexObject()
        # assigned user blocking
        view = self.msf.unrestrictedTraverse('@@treatinggroup-batch-action')
        view.request['uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'treating_group': self.pgof['direction-financiere'].UID()}, [])
        view.handleApply(view, 'apply')
        self.assertEqual(self.im1.treating_groups, self.pgof['direction-generale'].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof['direction-generale']['secretariat'].UID())
        # assigned_user not blocking
        self.im2.assigned_user = 'chef'
        self.im2.reindexObject()
        view = self.msf.unrestrictedTraverse('@@treatinggroup-batch-action')
        view.request['uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'treating_group': self.pgof['direction-financiere'].UID()}, [])
        view.handleApply(view, 'apply')
        self.assertEqual(self.im1.treating_groups, self.pgof['direction-financiere'].UID())
        self.assertEqual(self.im2.treating_groups, self.pgof['direction-financiere'].UID())

    def test_RecipientGroupBatchActionForm(self):
        self.im1.recipient_groups = [self.pgof['direction-generale'].UID(),
                                     self.pgof['direction-financiere']['budgets'].UID()]
        self.im2.recipient_groups = [self.pgof['direction-generale'].UID(),
                                     self.pgof['direction-generale']['secretariat'].UID()]
        view = self.msf.unrestrictedTraverse('@@recipientgroup-batch-action')
        view.request['uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        # test remove action
        view.widgets.extract = lambda *a, **kw: ({'action_choice': 'remove', 'removed_values':
                                                  [self.pgof['direction-generale'].UID()]}, [])
        view.handleApply(view, 'apply')
        self.assertListEqual(self.im1.recipient_groups, [self.pgof['direction-financiere']['budgets'].UID()])
        self.assertListEqual(self.im2.recipient_groups, [self.pgof['direction-generale']['secretariat'].UID()])
        # test add action
        view.widgets.extract = lambda *a, **kw: ({'action_choice': 'add', 'added_values':
                                                  [self.pgof['direction-financiere'].UID()]}, [])
        view.handleApply(view, 'apply')
        self.assertSetEqual(set(self.im1.recipient_groups), {self.pgof['direction-financiere']['budgets'].UID(),
                                                             self.pgof['direction-financiere'].UID()})
        self.assertSetEqual(set(self.im2.recipient_groups), {self.pgof['direction-generale']['secretariat'].UID(),
                                                             self.pgof['direction-financiere'].UID()})
        # test replace action
        view.widgets.extract = lambda *a, **kw: ({'action_choice': 'replace', 'removed_values':
                                                  [self.pgof['direction-financiere'].UID(),
                                                   self.pgof['direction-financiere']['budgets'].UID()],
                                                  'added_values': [self.pgof['direction-generale'].UID(),
                                                  self.pgof['direction-generale']['secretariat'].UID()]}, [])
        view.handleApply(view, 'apply')
        self.assertSetEqual(set(self.im1.recipient_groups), {self.pgof['direction-generale'].UID(),
                                                             self.pgof['direction-generale']['secretariat'].UID()})
        self.assertSetEqual(set(self.im2.recipient_groups), {self.pgof['direction-generale'].UID(),
                                                             self.pgof['direction-generale']['secretariat'].UID()})
        # test overwrite action
        view.widgets.extract = lambda *a, **kw: ({'action_choice': 'replace', 'removed_values':
                                                  [self.pgof['direction-financiere'].UID(),
                                                   self.pgof['direction-financiere']['budgets'].UID()],
                                                  'added_values': [self.pgof['direction-generale'].UID(),
                                                  self.pgof['direction-generale']['secretariat'].UID()]}, [])
        view.handleApply(view, 'apply')
        self.assertSetEqual(set(self.im1.recipient_groups), {self.pgof['direction-generale'].UID(),
                                                             self.pgof['direction-generale']['secretariat'].UID()})
        self.assertSetEqual(set(self.im2.recipient_groups), {self.pgof['direction-generale'].UID(),
                                                             self.pgof['direction-generale']['secretariat'].UID()})

    def test_AssignedUserBatchActionForm(self):
        self.assertIsNone(self.im1.assigned_user)
        self.assertIsNone(self.im2.assigned_user)
        view = self.msf.unrestrictedTraverse('@@assigneduser-batch-action')
        view.request['uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'assigned_user': 'agent'}, [])
        view.handleApply(view, 'apply')
        self.assertEqual(self.im1.assigned_user, 'agent')
        self.assertEqual(self.im2.assigned_user, 'agent')
        view = self.msf.unrestrictedTraverse('@@assigneduser-batch-action')
        view.request['uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'assigned_user': '__none__'}, [])
        view.handleApply(view, 'apply')
        self.assertIsNone(self.im1.assigned_user)
        self.assertIsNone(self.im2.assigned_user)

    def test_TransitionBatchActionFormOnTasks(self):
        self.assertEqual('created', api.content.get_state(self.ta1))
        self.assertEqual('created', api.content.get_state(self.ta2))
        view = self.tsf.unrestrictedTraverse('@@transition-batch-action')
        view.request.form['form.widgets.uids'] = ','.join([self.ta1.UID(), self.ta2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'transition': u'do_to_assign', 'comment': u''}, [])
        view.handleApply(view, 'apply')
        # to_do due to automatic transition
        self.assertEqual('to_do', api.content.get_state(self.ta1))
        self.assertEqual('to_do', api.content.get_state(self.ta2))

    def test_AssignedGroupBatchActionForm(self):
        self.assertEqual(self.ta1.assigned_group, self.pgof['direction-generale'].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof['direction-financiere'].UID())
        view = self.tsf.unrestrictedTraverse('@@assignedgroup-batch-action')
        view.request['uids'] = ','.join([self.ta1.UID(), self.ta3.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'assigned_group':
                                                  self.pgof['direction-financiere']['budgets'].UID()}, [])
        view.handleApply(view, 'apply')
        self.assertEqual(self.ta1.assigned_group, self.pgof['direction-financiere']['budgets'].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof['direction-financiere']['budgets'].UID())
        # assigned user blocking
        self.ta1.assigned_user = 'agent'
        self.ta1.reindexObject()
        view = self.tsf.unrestrictedTraverse('@@assignedgroup-batch-action')
        view.request['uids'] = ','.join([self.ta1.UID(), self.ta3.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'assigned_group':
                                                  self.pgof['direction-generale'].UID()}, [])
        view.handleApply(view, 'apply')
        # Not changed !
        self.assertEqual(self.ta1.assigned_group, self.pgof['direction-financiere']['budgets'].UID())
        self.assertEqual(self.ta3.assigned_group, self.pgof['direction-financiere']['budgets'].UID())

    def test_TaskAssignedUserBatchActionForm(self):
        self.assertIsNone(self.ta1.assigned_user)
        self.assertIsNone(self.ta2.assigned_user)
        view = self.msf.unrestrictedTraverse('@@assigneduser-batch-action')
        view.request['uids'] = ','.join([self.ta1.UID(), self.ta2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'assigned_user': 'chef'}, [])
        view.handleApply(view, 'apply')
        self.assertEqual(self.ta1.assigned_user, 'chef')
        self.assertEqual(self.ta2.assigned_user, 'chef')
