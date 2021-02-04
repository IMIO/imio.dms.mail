# -*- coding: utf-8 -*-
"""Test views."""
from imio.dms.mail.browser.views import parse_query
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.i18n import translate

import json
import unittest


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
        self.assertEqual(form['form.widgets.reply_to'], expected_linked_mails)
        self.assertEqual(translate(view.label), u'Reply to E0001 - Courrier 1')
        expected_recipients = ('/plone/contacts/electrabel', )
        self.assertEqual(form['form.widgets.recipients'], expected_recipients)

    def test_add(self):
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Manager'])
        imail1 = self.portal['incoming-mail']['courrier1']
        omail1 = api.content.create(container=self.portal, type='dmsoutgoingmail', id='newo1', title='TEST')
        view = imail1.unrestrictedTraverse('@@reply')
        view.add(omail1)
        self.assertIn('newo1', self.portal['outgoing-mail'])


class TestPloneView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_showEditableBorder(self):
        view = self.portal['incoming-mail']['courrier1'].unrestrictedTraverse('@@plone')
        self.assertEqual(view.showEditableBorder(), False)
        view = self.portal['front-page'].unrestrictedTraverse('@@plone')
        self.assertEqual(view.showEditableBorder(), True)


class TestContactSuggest(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.ctct = self.portal['contacts']
        self.elec = self.ctct['electrabel']
        self.pf = self.ctct['personnel-folder']
        self.pgo = self.portal['contacts']['plonegroup-organization']

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
                         {"text": "Monsieur Jean Courant, Agent (Electrabel)",
                          "id": self.ctct['jeancourant']['agent-electrabel'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Monsieur Jean Courant", "id": self.ctct['jeancourant'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel [TOUT]", "id": 'l:%s' % self.elec.UID()})
        self.assertEqual(ret.pop(0),
                         {"text": "Electrabel / Travaux 1 [TOUT]", "id": 'l:%s' % self.elec['travaux'].UID()})

    def test_call_SenderSuggest(self):
        omail1 = self.portal['incoming-mail']['courrier1']
        view = omail1.unrestrictedTraverse('@@sender-autocomplete-suggest')
        # no term
        self.assertEqual(view(), '[]')
        # search held position
        view.request['term'] = 'directeur'
        ret = json.loads(view())
        self.assertEqual(ret.pop(0),
                         {'text': u'Monsieur Maxime DG, Directeur du personnel (Mon organisation / Direction générale '
                                  u'/ GRH)',
                          'id': self.pf['dirg']['directeur-du-personnel'].UID()})
        self.assertEqual(ret.pop(0),
                         {'text': u'Monsieur Maxime DG, Directeur général (Mon organisation / Direction générale)',
                          'id': self.pf['dirg']['directeur-general'].UID()})
        # search organization
        view.request['term'] = 'direction générale grh'
        ret = json.loads(view())
        self.assertEqual(ret.pop(0),
                         {'text': u'Mon organisation / Direction générale / GRH',
                          u'id': self.pgo['direction-generale']['grh'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": u"Monsieur Fred Agent, Agent GRH (Mon organisation / Direction générale / GRH)",
                          "id": self.pf['agent']['agent-grh'].UID()})
        self.assertEqual(ret.pop(0),
                         {"text": u"Monsieur Michel Chef, Responsable GRH (Mon organisation / Direction générale "
                                  u"/ GRH)",
                          "id": self.pf['chef']['responsable-grh'].UID()})
        self.assertEqual(ret.pop(0),
                         {'text': u'Monsieur Maxime DG, Directeur du personnel (Mon organisation / Direction générale '
                                  u'/ GRH)',
                          'id': self.pf['dirg']['directeur-du-personnel'].UID()})
        self.assertEqual(ret.pop(0),
                         {'text': u'Mon organisation / Direction générale / GRH [TOUT]',
                          u'id': 'l:%s' % self.pgo['direction-generale']['grh'].UID()})


class TestServerSentEvents(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Manager'])

    def test_call(self):
        omail1 = self.portal['outgoing-mail']['reponse1']
        omf = omail1['1']
        sse_vw = omail1.restrictedTraverse('server_sent_events')
        eee_vw = omf.restrictedTraverse('@@externalEditorEnabled')

        # a dmsommainfile has been added manually and we go back on the dmsoutgoingmail
        self.assertEqual(omf.conversion_finished, True)
        self.assertFalse(hasattr(omf, 'generated'))
        self.assertEqual(sse_vw(), u'')  # no refresh

        # a dmsommainfile has been generated
        omf.generated = 1
        omf.conversion_finished = True
        self.assertEqual(sse_vw(), u'')  # no refresh
        self.assertEqual(omf.generated, 2)  # waiting external edition
        # we lock like zopeedit
        omf.restrictedTraverse('lock-unlock')()
        self.assertTrue(eee_vw.isObjectLocked())
        self.assertEqual(sse_vw(), u'')  # no refresh
        self.assertEqual(omf.generated, 3)  # was always waiting but will end
        self.assertEqual(sse_vw(), u'')  # no refresh
        self.assertEqual(omf.generated, 3)  # no more waiting but locked
        # we unlock
        omf.restrictedTraverse('lock-unlock')(unlock=1)
        self.assertFalse(eee_vw.isObjectLocked())
        res = sse_vw()
        # u'data: {"path": "/plone/outgoing-mail/reponse1/1", "id": "1", "refresh": true}\n\n'
        self.assertIn('"id": "1", "refresh": true', res)  # we refresh

        # a dmsommainfile is edited with zopeedit
        self.assertFalse(hasattr(omf, 'generated'))
        self.assertFalse(hasattr(omf, 'conversion_finished'))
        self.assertEqual(sse_vw(), u'')  # no refresh
        # we lock like zopeedit
        omf.restrictedTraverse('lock-unlock')()
        self.assertTrue(eee_vw.isObjectLocked())
        self.assertEqual(sse_vw(), u'')  # no refresh
        # we save the file in the editor but dont close it
        omf.conversion_finished = True
        self.assertEqual(sse_vw(), u'')  # no refresh
        self.assertEqual(omf.generated, 3)  # set as no more waiting
        # we unlock
        omf.restrictedTraverse('lock-unlock')(unlock=1)
        self.assertFalse(eee_vw.isObjectLocked())
        res = sse_vw()
        # u'data: {"path": "/plone/outgoing-mail/reponse1/1", "id": "1", "refresh": true}\n\n'
        self.assertIn('"id": "1", "refresh": true', res)  # we refresh


class TestUpdateItem(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_call(self):
        imail1 = self.portal['incoming-mail']['courrier1']
        self.assertIsNone(imail1.assigned_user)
        view = imail1.unrestrictedTraverse('@@update_item')
        # called without form value
        view()
        self.assertIsNone(imail1.assigned_user)
        # called with form value
        form = self.portal.REQUEST.form
        form['assigned_user'] = 'chef'
        view()
        self.assertEqual(imail1.assigned_user, 'chef')
