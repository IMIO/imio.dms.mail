# -*- coding: utf-8 -*-
""" documentgenerator.py tests for this package."""
import mocker
import unittest

from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class TestDocumentGenerator(unittest.TestCase):
    """Test installation of imio.project.pst into Plone."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pc = self.portal.portal_catalog
        self.intids = getUtility(IIntIds)
        self.omf = self.portal['outgoing-mail']
        self.ctct = self.portal['contacts']
        self.electrabel = self.ctct['electrabel']
        self.jc = self.ctct['jeancourant']
        self.agent = self.jc['agent-electrabel']
        self.grh = self.ctct['plonegroup-organization']['direction-generale']['grh']
        self.chef = self.ctct['personnel-folder']['chef']
        self.resp_grh = self.chef['responsable-grh']

    def test_OMDGHelper(self):
        view1 = self.omf.reponse1.unrestrictedTraverse('@@document_generation_helper_view')

        # Test fmt method
        self.assertEqual(view1.fmt(None), '')
        self.assertEqual(view1.fmt('Test'), 'Test ')
        self.assertEqual(view1.fmt('Test', fmt='(%s)'), '(Test)')

        # Test get_ctct_det method
        self.assertDictEqual(view1.get_ctct_det(''), {})
        det = {'address': {'city': u'E-ville', 'country': '', 'region': '',
                           'additional_address_details': '', 'number': u'1',
                           'street': u"Rue de l'électron", 'zip_code': u'0020'},
               'website': '', 'fax': '', 'phone': u'012/345.678', 'im_handle': '',
               'cell_phone': '', 'email': u'jean.courant@electrabel.be'}
        self.assertDictEqual(view1.get_ctct_det(self.jc), det)

        # Test get_sender method
        sender = {'person': self.chef, 'hp': self.resp_grh, 'org_full_title': u'Direction générale - GRH',
                  'org': self.grh}
        self.assertDictEqual(view1.get_sender(), sender)
        backup = view1.real_context.sender
        view1.real_context.sender = ''
        self.assertDictEqual(view1.get_sender(), {})
        view1.real_context.sender = backup

        # Test mailing_list method
        self.assertListEqual(view1.mailing_list(), [self.ctct['electrabel']])
        view1.real_context.recipients.append(RelationValue(self.intids.getId(self.electrabel)))
        self.assertListEqual(view1.mailing_list(), [self.ctct['electrabel'], self.electrabel])
        backup = view1.real_context.recipients[0]
        view1.real_context.recipients = None
        self.assertListEqual(view1.mailing_list(), [])
        view1.real_context.recipients = [backup]

        # Test get_full_title method
        self.assertEqual(view1.get_full_title(None), '')
        self.assertEqual(view1.get_full_title(self.electrabel), u'Electrabel')
        self.assertEqual(view1.get_full_title(self.grh), u'Mon organisation / Direction générale / GRH')
        self.assertEqual(view1.get_full_title(self.grh, separator=' - ', first_index=1), u'Direction générale - GRH')
        self.assertEqual(view1.get_full_title(self.jc), u'Monsieur Jean Courant')
        self.assertEqual(view1.get_full_title(self.agent), u'Monsieur Jean Courant (Electrabel - Agent)')

        # Test get_separate_titles method
        self.assertListEqual(view1.get_separate_titles(None), [u'', u''])
        self.assertListEqual(view1.get_separate_titles(self.electrabel), [u'Electrabel', u''])
        self.assertListEqual(view1.get_separate_titles(self.grh), [u'Mon organisation / Direction générale / GRH', ''])
        self.assertListEqual(view1.get_separate_titles(self.grh, separator=' - ', first_index=1),
                             [u'Direction générale - GRH', ''])
        self.assertListEqual(view1.get_separate_titles(self.jc), ['', u'Monsieur Jean Courant'])
        self.assertListEqual(view1.get_separate_titles(self.agent), [u'Electrabel', u'Monsieur Jean Courant'])
        self.assertListEqual(view1.get_separate_titles(self.resp_grh),
                             [u'Mon organisation / Direction générale / GRH', u'Monsieur Michel Chef'])

        # Test person_title
        self.assertEqual(view1.person_title(None), '')
        self.assertEqual(view1.person_title(self.jc), u'Monsieur')
        self.jc.person_title = None
        self.assertEqual(view1.person_title(self.jc), u'Monsieur')
        self.assertEqual(view1.person_title(self.jc, pers_dft=u'Madame'), u'Madame')
        self.assertEqual(view1.person_title(self.electrabel), u'Madame, Monsieur')
        self.assertEqual(view1.person_title(self.electrabel, org_dft=u'Messieurs'), u'Messieurs')
        self.assertEqual(view1.person_title(self.agent), u'Monsieur')

        # Test is_first_doc
        mock = mocker.Mocker()
        res = {}
        view1.appy_renderer = mock.mock()
        mocker.expect(view1.appy_renderer.contentParser.env.context).result(res).replay()
        self.assertTrue(view1.is_first_doc())
        mock2 = mocker.Mocker()
        res['loop'] = mock2.mock()
        mocker.expect(res['loop'].mailed_data.first).result(False).replay()
        mock.replay()
        self.assertFalse(view1.is_first_doc())

    def test_DocumentGenerationOMDashboardHelper(self):
        view = self.omf['mail-searches'].unrestrictedTraverse('@@document_generation_helper_view')

        # Test is_dashboard
        view.request.form['facetedQuery'] = ''
        self.assertTrue(view.is_dashboard())

        # Test uids_to_objs
        brains = self.pc(id=['reponse1', 'reponse2', 'reponse3'], sort_on='id')
        self.assertEqual(len(view.objs), 0)
        view.uids_to_objs(brains)
        self.assertEqual(len(view.objs), 3)

        # Test group_by_tg
        tg1 = self.ctct['plonegroup-organization']['direction-generale']
        tg2 = tg1[u'secretariat']
        res = {tg1.UID(): {'mails': [view.objs[0]], 'title': u'Direction générale'},
               tg2.UID(): {'mails': [view.objs[1]], 'title': u'Direction générale - Secrétariat'}}
        self.assertDictEqual(view.group_by_tg(brains[:2]), res)
        backup = brains[1].treating_groups
        brains[1].treating_groups = None
        res = {tg1.UID(): {'mails': [view.objs[0]], 'title': u'Direction générale'},
               '1_no_group': {'mails': [view.objs[1]], 'title': u'No treating group'}}
        self.assertDictEqual(view.group_by_tg(brains[:2]), res)
        brains[1].treating_groups = backup

        # Test get_dms_files
        view.context_var = lambda x: brains
        files = view.get_dms_files(limit=1)
        self.assertListEqual(files, [view.objs[0]['1'], view.objs[1]['1'], view.objs[2]['1']])
        del view.request.form['facetedQuery']
        self.assertListEqual(view.get_dms_files(), [])

        # Test get_num_pages
        self.assertEquals(view.get_num_pages(view.objs[0]['1']), 1)
        self.assertEquals(view.get_num_pages(view.objs[1]['1']), 2)
        self.assertEquals(view.get_num_pages(view.objs[2]['1']), 1)
        self.assertEquals(view.get_num_pages(self.portal['incoming-mail']), 0)

        # Test get_dv_images
        images = view.get_dv_images(view.objs[0]['1'])
        self.assertEqual(len(images), 1)
        self.assertTrue(hasattr(images[0], 'read'))
        images[0].close()

    def test_DocumentGenerationDirectoryHelper(self):
        view = self.ctct.unrestrictedTraverse('@@document_generation_helper_view')
        # Test get_organisations
        res = [
            (1, '', self.ctct['electrabel']),
            (2, 1, self.ctct['electrabel']['travaux']),
            (3, '', self.ctct['plonegroup-organization']),
            (4, 3, self.ctct['plonegroup-organization']['college-communal'])]
        self.assertListEqual(view.get_organizations()[:4], res)

        # Test get_persons
        res = [
            (1, self.ctct['personnel-folder']['agent']), (2, self.chef),
            (3, self.ctct['jeancourant']), (4, self.ctct['personnel-folder']['dirg']),
            (5, self.ctct['bernardlermitte']), (6, self.ctct['notencoded']),
            (7, self.ctct['sergerobinet'])]
        self.assertListEqual(view.get_persons(), res)

        # Test get_held_positions
        res = [
            (1, 5, 27, self.ctct['bernardlermitte']['agent-swde']),
            (2, 3, 1, self.ctct['jeancourant']['agent-electrabel']),
            (3, 1, 19, self.ctct['personnel-folder']['agent']['agent-grh'])]
        self.assertListEqual(view.get_held_positions()[:3], res)








