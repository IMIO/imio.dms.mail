# -*- coding: utf-8 -*-
"""Test views."""
import unittest
from zope.i18n import translate

from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING


class TestReplyForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_updateFields(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        view = imail1.unrestrictedTraverse('@@reply')
        view.updateFields()
        form = self.portal.REQUEST.form
        expected = ('/plone/incoming-mail/courrier1', )
        self.assertEqual(form['linked_mails'], expected)
        self.assertEqual(form['form.widgets.linked_mails'], expected)
        self.assertEqual(translate(view.label), u'Reply to E0001 - Courrier 1')
