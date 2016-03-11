# -*- coding: utf-8 -*-
"""Test views."""
import json
import unittest
from zope.i18n import translate

from ..browser.views import parse_query
from ..testing import DMSMAIL_INTEGRATION_TESTING


class TestReplyForm(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_updateFields(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        view = imail1.unrestrictedTraverse('@@reply')
        view.updateFields()
        form = self.portal.REQUEST.form
        expected_linked_mails = ('/plone/incoming-mail/courrier1', )
        self.assertEqual(form['form.widgets.linked_mails'], expected_linked_mails)
        self.assertEqual(translate(view.label), u'Reply to E0001 - Courrier 1')
        expected_recipients = ('/plone/contacts/electrabel', )
        self.assertEqual(form['form.widgets.recipients'], expected_recipients)


class TestPloneView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_showEditableBorder(self):
        view = self.portal['incoming-mail']['courrier1'].unrestrictedTraverse('@@plone')
        self.assertEqual(view.showEditableBorder(), True)


class TestContactSuggest(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.ctct = self.portal['contacts']
        self.elec = self.ctct['electrabel']

    def test_parse_query(self):
        self.assertEqual(parse_query('dir*'),
                         {'SearchableText': 'dir*'})
        self.assertEqual(parse_query('director(organization)'),
                         {'SearchableText': 'director* AND organization*'})

    def test_call_ContactSuggest(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        view = imail1.unrestrictedTraverse('@@contact-autocomplete-suggest')
        # no term
        self.assertEqual(view(), '[]')
        # term electra
        view.request['term'] = 'electra'
        ret = json.loads(view())
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel", "id": self.elec.UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel / Travaux 1", "id": self.elec['travaux'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Monsieur Jean Courant (Electrabel - Agent)",
                          "id": self.ctct['jeancourant']['agent-electrabel'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Monsieur Jean Courant", "id": self.ctct['jeancourant'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel [All under]", "id": 'l:%s' % self.elec.UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel / Travaux 1 [All under]", "id": 'l:%s' % self.elec['travaux'].UID()})
