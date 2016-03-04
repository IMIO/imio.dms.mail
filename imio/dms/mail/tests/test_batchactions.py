# -*- coding: utf-8 -*-
"""Test views."""
import unittest
from zope.i18n import translate
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID

from ..browser.batchactions import getAvailableTransitionsVoc
from ..testing import DMSMAIL_INTEGRATION_TESTING


class BatchActions(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pc = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.msf = self.imf['mail-searches']
        self.im1 = self.imf['courrier1']
        self.im2 = self.imf['courrier2']
        self.im3 = self.imf['courrier3']
        self.im4 = self.imf['courrier4']
        self.ta1 = self.im1['tache1']

    def test_getAvailableTransitionsVoc(self):
        api.content.transition(obj=self.im3, to_state='proposed_to_manager')
        api.content.transition(obj=self.im4, to_state='proposed_to_agent')
        brains = self.pc(UID=[self.im1.UID()])
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc(brains)]),
                            set(['propose_to_manager', 'propose_to_service_chief']))
        brains = self.pc(UID=[self.im1.UID(), self.im2.UID()])
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc(brains)]),
                            set(['propose_to_manager', 'propose_to_service_chief']))
        brains = self.pc(UID=[self.im1.UID(), self.im3.UID()])
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc(brains)]),
                            set(['propose_to_service_chief']))
        brains = self.pc(UID=[self.im1.UID(), self.im3.UID(), self.im4.UID()])
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc(brains)]),
                            set([]))
        brains = self.pc(UID=[self.im1.UID(), self.ta1.UID()])
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc(brains)]),
                            set([]))
        self.assertSetEqual(set([t.value for t in getAvailableTransitionsVoc([])]),
                            set([]))

    def test_TransitionBatchActionForm(self):
        self.assertEqual('created', api.content.get_state(self.im1))
        view = self.msf.unrestrictedTraverse('@@transition-batch-action')
        form = view.request.form
        form['form.widgets.uids'] = ','.join([self.im1.UID(), self.im2.UID()])
        view.update()
        view.widgets.extract = lambda *a, **kw: ({'transition': u'propose_to_manager'}, [])
        view.handleApply(view, 'apply')
        self.assertEqual('proposed_to_manager', api.content.get_state(self.im1))
        self.assertEqual('proposed_to_manager', api.content.get_state(self.im2))
