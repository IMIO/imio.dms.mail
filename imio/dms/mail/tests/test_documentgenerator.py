# -*- coding: utf-8 -*-
""" documentgenerator.py tests for this package."""
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.documentgenerator import OutgoingMailLinksViewlet
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import mocker  # must be replaced in Plone 5 with python 3 unittest.mock
import unittest


class TestDocumentGenerator(unittest.TestCase):
    """Test installation of imio.project.pst into Plone."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pc = self.portal.portal_catalog
        self.intids = getUtility(IIntIds)
        self.omf = self.portal["outgoing-mail"]
        self.ctct = self.portal["contacts"]
        self.electrabel = self.ctct["electrabel"]
        self.jc = self.ctct["jeancourant"]
        self.agent = self.jc["agent-electrabel"]
        self.grh = self.ctct["plonegroup-organization"]["direction-generale"]["grh"]
        self.chef = self.ctct["personnel-folder"]["chef"]
        self.resp_grh = self.chef["responsable-grh"]

    def test_OMDGHelper(self):
        """
        Test all methods of OMDGHelper view
        """
        view1 = get_object(oid="reponse1", ptype="dmsoutgoingmail").unrestrictedTraverse(
            "@@document_generation_helper_view"
        )

        # Test fmt method
        self.assertEqual(view1.fmt(None), "")
        self.assertEqual(view1.fmt("Test"), "Test ")
        self.assertEqual(view1.fmt("Test", fmt="(%s)"), "(Test)")

        # Test get_ctct_det method
        self.assertDictEqual(view1.get_ctct_det(""), {})
        det = {"address": {}, "website": "", "fax": "", "phone": "", "im_handle": "", "cell_phone": "", "email": ""}
        self.assertDictEqual(view1.get_ctct_det(self.jc), det)
        # get address from linked organization
        det = {
            "address": {
                "city": u"E-ville",
                "country": "",
                "region": "",
                "additional_address_details": "",
                "number": u"1",
                "street": u"Rue de l'électron",
                "zip_code": u"0020",
            },
            "im_handle": "",
            "cell_phone": "",
            "email": u"jean.courant@electrabel.eb",
            "website": "",
            "fax": "",
            "phone": u"012345678",
        }
        self.assertDictEqual(view1.get_ctct_det(self.jc["agent-electrabel"]), det)

        # Test get_sender method
        sender = {
            "person": self.chef,
            "hp": self.resp_grh,
            "org_full_title": u"Direction générale - GRH",
            "org": self.grh,
        }
        self.assertDictEqual(view1.get_sender(), sender)
        backup = view1.real_context.sender
        view1.real_context.sender = ""
        self.assertDictEqual(view1.get_sender(), {})
        view1.real_context.sender = backup

        # Test mailing_list method
        self.assertListEqual(view1.real_context.send_modes, [u"post"])
        self.assertListEqual(view1.mailing_list(), [(self.electrabel, u"post")])
        view1.real_context.send_modes = [u"post", u"post_registered"]
        self.assertListEqual(
            view1.mailing_list(),
            [(self.electrabel, u"post"), (self.electrabel, u"post_registered")],
        )
        view1.real_context.recipients.append(RelationValue(self.intids.getId(self.jc)))
        self.assertListEqual(
            view1.mailing_list(),
            [(self.electrabel, u"post"), (self.electrabel, u"post_registered"),
             (self.jc, u"post"), (self.jc, u"post_registered")],
        )
        backup = view1.real_context.recipients[0]
        view1.real_context.recipients = None
        self.assertListEqual(view1.mailing_list(), [])
        view1.real_context.recipients = [backup]

        # Test get_full_title method
        self.assertEqual(view1.get_full_title(None), "")
        self.assertEqual(view1.get_full_title(self.electrabel), u"Electrabel")
        self.assertEqual(view1.get_full_title(self.grh), u"Mon organisation / Direction générale / GRH")
        self.assertEqual(view1.get_full_title(self.grh, separator=" - ", first_index=1), u"Direction générale - GRH")
        self.assertEqual(view1.get_full_title(self.jc), u"Monsieur Jean Courant")
        self.assertEqual(view1.get_full_title(self.agent), u"Monsieur Jean Courant, Agent (Electrabel)")

        # Test get_separate_titles method
        self.assertListEqual(view1.get_separate_titles(None), [u"", u""])
        self.assertListEqual(view1.get_separate_titles(self.electrabel), [u"Electrabel", u""])
        self.assertListEqual(view1.get_separate_titles(self.grh), [u"Mon organisation / Direction générale / GRH", ""])
        self.assertListEqual(
            view1.get_separate_titles(self.grh, separator=" - ", first_index=1), [u"Direction générale - GRH", ""]
        )
        self.assertListEqual(view1.get_separate_titles(self.jc), ["", u"Monsieur Jean Courant"])
        self.assertListEqual(view1.get_separate_titles(self.agent), [u"Electrabel", u"Monsieur Jean Courant"])
        self.assertListEqual(
            view1.get_separate_titles(self.resp_grh),
            [u"Mon organisation / Direction générale / GRH", u"Monsieur Michel Chef"],
        )

        # Test person_title
        self.assertEqual(view1.person_title(None), "")
        self.assertEqual(view1.person_title(self.jc), u"Monsieur")
        self.assertEqual(view1.person_title(self.jc, with_name=True), u"Monsieur Courant")
        self.assertEqual(view1.person_title(self.jc, with_name=True, upper_name=True), u"Monsieur COURANT")
        self.jc.person_title = None
        self.assertEqual(view1.person_title(self.jc), u"Monsieur")
        self.assertEqual(view1.person_title(self.jc, pers_dft=u"Madame"), u"Madame")
        self.assertEqual(view1.person_title(self.jc, pers_dft=u"Madame", with_name=True), u"Madame Courant")
        self.assertEqual(
            view1.person_title(self.jc, pers_dft=u"Madame", with_name=True, upper_name=True), u"Madame COURANT"
        )
        self.assertEqual(view1.person_title(self.electrabel), u"Madame, Monsieur")
        self.assertEqual(view1.person_title(self.electrabel, org_dft=u"Messieurs"), u"Messieurs")
        self.assertEqual(view1.person_title(self.agent), u"Monsieur")
        self.assertEqual(view1.person_title(self.agent, with_name=True), u"Monsieur Courant")
        self.assertEqual(view1.person_title(self.agent, with_name=True, upper_name=True), u"Monsieur COURANT")

        # Test is_first_doc
        mock = mocker.Mocker()
        res = {}
        view1.appy_renderer = mock.mock()
        mocker.expect(view1.appy_renderer.contentParser.env.context).result(res).replay()
        self.assertTrue(view1.is_first_doc())
        mock2 = mocker.Mocker()
        res["loop"] = mock2.mock()
        mocker.expect(res["loop"].mailed_data.first).result(False).replay()
        mock.replay()
        self.assertFalse(view1.is_first_doc())

        # Test separate_full_title
        self.assertListEqual(view1.separate_full_title(None), [u"", u""])
        self.assertListEqual(view1.separate_full_title(u""), [u"", u""])
        self.assertListEqual(view1.separate_full_title(u"Direction générale"), [u"Direction générale", u""])
        self.assertListEqual(
            view1.separate_full_title(u"Direction générale - Secrétariat"), [u"Direction générale", u"Secrétariat"]
        )
        self.assertListEqual(
            view1.separate_full_title(u"Direction générale - Secrétariat - Michèle"),
            [u"Direction générale", u"Secrétariat - Michèle"],
        )
        self.assertListEqual(
            view1.separate_full_title(u"Direction générale - Secrétariat - Michèle", nb=3),
            [u"Direction générale", u"Secrétariat", u"Michèle"],
        )
        self.assertRaises(IndexError, view1.separate_full_title, u"Direction", nb=0)

        # Test mailed_context
        view1.appy_renderer = mocker.Mocker().mock()
        mocker.expect(view1.appy_renderer.contentParser.env.context).result({}).replay()
        ctx = (self.electrabel, u"post")
        ctx = view1.mailed_context(ctx)
        self.assertEqual(ctx["mailed_data"], self.electrabel)
        self.assertEqual(ctx["send_mode"], u"post")

        view1.appy_renderer = mocker.Mocker().mock()
        mocker.expect(view1.appy_renderer.contentParser.env.context).result({}).replay()
        ctx = (self.electrabel, None)
        ctx = view1.mailed_context(ctx)
        self.assertEqual(ctx["mailed_data"], self.electrabel)
        self.assertEqual(ctx["send_mode"], None)

        # Test display_send_modes
        self.assertEqual(view1.display_send_modes(), u'Lettre, Lettre recommand\xe9e')
        self.assertEqual(view1.display_send_modes(filter_on=u'post'), u'Lettre')
        self.assertEqual(view1.display_send_modes(filter_on=u'wrong_mode'), u'')
        self.assertEqual(view1.display_send_modes(separator=' & '), u'Lettre & Lettre recommand\xe9e')
        view1.real_context.send_modes = [u"post", u"post_registered", u"email"]
        self.assertEqual(view1.display_send_modes(filter_on=u'post'), u'Lettre, Email')
        self.assertEqual(view1.display_send_modes(filter_on=u'post_registered'), u'Lettre recommand\xe9e, Email')
        self.assertEqual(view1.display_send_modes(filter_on=[u'post', u'post_registered']), u'Lettre, Lettre recommand\xe9e, Email')
        self.assertEqual(view1.display_send_modes(filter_on=u'wrong_mode'), u'Email')


    def test_DocumentGenerationOMDashboardHelper(self):
        """
        Test all methods of DocumentGenerationOMDashboardHelper view
        """
        view = self.omf["mail-searches"].unrestrictedTraverse("@@document_generation_helper_view")

        # Test is_dashboard
        view.request.form["facetedQuery"] = ""
        self.assertTrue(view.is_dashboard())

        # Test uids_to_objs
        brains = self.pc(id=["reponse1", "reponse2", "reponse3"], sort_on="id")
        self.assertEqual(len(view.objs), 0)
        view.uids_to_objs(brains)
        self.assertEqual(len(view.objs), 3)

        # Test group_by_tg
        tg1 = self.ctct["plonegroup-organization"]["direction-generale"]
        tg2 = tg1[u"secretariat"]
        res = {
            tg1.UID(): {"mails": [view.objs[0]], "title": u"Direction générale"},
            tg2.UID(): {"mails": [view.objs[1]], "title": u"Direction générale - Secrétariat"},
        }
        self.assertDictEqual(view.group_by_tg(brains[:2]), res)
        res = [[u"Direction générale", view.objs[0]], [u"Direction générale - Secrétariat", view.objs[1]]]
        self.assertListEqual(view.flatten_group_by_tg(view.group_by_tg(brains[:2])), res)
        backup = brains[1].treating_groups
        brains[1].treating_groups = None
        res = {
            tg1.UID(): {"mails": [view.objs[0]], "title": u"Direction générale"},
            "1_no_group": {"mails": [view.objs[1]], "title": u"No treating group"},
        }
        self.assertDictEqual(view.group_by_tg(brains[:2]), res)
        res = [[u"Direction générale", view.objs[0]], [u"No treating group", view.objs[1]]]
        self.assertListEqual(view.flatten_group_by_tg(view.group_by_tg(brains[:2])), res)
        brains[1].treating_groups = backup
        brains2 = self.pc(portal_type="dmsoutgoingmail", sort_on="id")
        res = [
            [u"Direction financière", brains2[4 - 1].getObject()],
            [u"Direction financière - Budgets", brains2[5 - 1].getObject()],
            [u"Direction financière - Comptabilité", brains2[6 - 1].getObject()],
            [u"Direction générale", brains2[1 - 1].getObject()],
            [u"Direction générale", brains2[7 - 1].getObject()],
            [u"Direction générale - GRH", brains2[3 - 1].getObject()],
            [u"Direction générale - GRH", brains2[9 - 1].getObject()],
            [u"Direction générale - Secrétariat", brains2[2 - 1].getObject()],
            [u"Direction générale - Secrétariat", brains2[8 - 1].getObject()],
        ]
        self.assertListEqual(view.flatten_group_by_tg(view.group_by_tg(brains2)), res)

        # Test get_dms_files
        view.context_var = lambda x: brains
        files = view.get_dms_files()
        self.assertListEqual(files, [view.objs[0]["1"], view.objs[1]["1"], view.objs[2]["1"]])
        filespath = u"%s/batchimport/toprocess/incoming-mail" % PRODUCT_DIR
        filename = u"in-courrier2.pdf"
        with open(u"%s/%s" % (filespath, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            createContentInContainer(view.objs[0], "dmsommainfile", id="2", title="", file=file_object)
        self.assertListEqual(view.get_dms_files(), [view.objs[1]["1"], view.objs[2]["1"]])
        del view.request.form["facetedQuery"]
        self.assertListEqual(view.get_dms_files(), [])

        # Test get_num_pages
        self.assertEquals(view.get_num_pages(view.objs[0]["1"]), 1)
        self.assertEquals(view.get_num_pages(view.objs[1]["1"]), 2)
        self.assertEquals(view.get_num_pages(view.objs[2]["1"]), 1)
        self.assertEquals(view.get_num_pages(self.portal["incoming-mail"]), 0)

        # Test get_dv_images
        images = view.get_dv_images(view.objs[0]["1"])
        self.assertEqual(len(images), 1)
        self.assertTrue(hasattr(images[0], "read"))
        images[0].close()

    def test_DocumentGenerationDirectoryHelper(self):
        """
        Test all methods of DocumentGenerationDirectoryHelper view
        """
        view = self.ctct["orgs-searches"].unrestrictedTraverse("@@document_generation_helper_view")
        # Test get_organisations
        res = [
            (1, "", self.electrabel),
            (2, 1, self.electrabel["travaux"]),
            (3, "", self.ctct["plonegroup-organization"]),
            (4, 3, self.ctct["plonegroup-organization"]["college-communal"]),
        ]
        self.assertListEqual(view.get_organizations()[:4], res)

        # Test get_persons
        res = [
            (1, self.ctct["personnel-folder"]["agent"]),
            (2, self.ctct["personnel-folder"]["agent1"]),
            (3, self.chef),
            (4, self.ctct["jeancourant"]),
            (5, self.ctct["personnel-folder"]["encodeur"]),
            (6, self.ctct["personnel-folder"]["lecteur"]),
            (7, self.ctct["bernardlermitte"]),
            (8, self.ctct["notencoded"]),
            (9, self.ctct["sergerobinet"]),
        ]
        self.assertListEqual(view.get_persons(), res)

        # Test get_held_positions
        res = [
            (1, 7, 27, self.ctct["bernardlermitte"]["agent-swde"]),
            (2, 4, 1, self.ctct["jeancourant"]["agent-electrabel"]),
        ]
        self.assertListEqual(view.get_held_positions()[:2], res)

    def test_DashboardDocumentGenerationView(self):
        """
        Test all methods of DashboardDocumentGenerationView view
        """
        view = self.portal["incoming-mail"]["mail-searches"].restrictedTraverse("document-generation")
        template = self.portal["templates"]["d-im-listing"]
        # make template conditions are right
        # view.request.form['output_format'] = 'odt'
        # view.request.form['c1[]'] = self.portal['incoming-mail']['mail-searches']['all_mails'].UID()
        # template.can_be_generated(view.context)
        # doc = view(template_uid=template.UID(), output_format='odt')
        hview = self.portal["incoming-mail"]["mail-searches"].restrictedTraverse("document_generation_helper_view")
        self.assertIn("by_tg", view._get_generation_context(hview, template))

    def test_OMPDGenerationView(self):
        """
        Test all methods of OMPDGenerationView view
        """
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = rep1.restrictedTraverse("persistent-document-generation")
        hview = rep1.restrictedTraverse("document_generation_helper_view")
        view.pod_template = self.portal["templates"]["om"]["main"]
        # view(template_uid=template.UID(), output_format='odt')

        # Test title
        self.assertEqual(view._get_title("", ""), u"Modèle de base")

        # Test generate_persistent_doc
        doc = view.generate_persistent_doc(view.pod_template, "odt")
        self.assertEqual(doc.portal_type, "dmsommainfile")
        self.assertIsNone(doc.scan_user)

        # Test redirects
        # redirects has be monkey patched in tests !!
        # self.assertEqual(view.redirects(doc),
        #                 'http://nohost/plone/outgoing-mail/reponse1/012999900000001/external_edit')

        # Test generation context
        gen_con = view._get_generation_context(hview, view.pod_template)
        self.assertEqual(gen_con["scan_id"], "IMIO012999900000002")
        get_object(oid="reponse1", ptype="dmsoutgoingmail").id = "test_creation_modele"
        gen_con = view._get_generation_context(hview, view.pod_template)
        self.assertEqual(gen_con["scan_id"], "IMIO012999900000000")

    def test_OMMLPDGenerationView(self):
        """
        Test all methods of OMMLPDGenerationView view
        """
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = rep1.restrictedTraverse("mailing-loop-persistent-document-generation")
        view.pod_template = self.portal["templates"]["om"]["mailing"]
        view.document = rep1["1"]
        view.document.title = u"Modèle de base"
        # Test title
        self.assertEqual(view._get_title("", ""), u"Publipostage, Modèle de base")

    def test_OutgoingMailLinksViewlet(self):
        """
        Test viewlet
        """
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        viewlet = OutgoingMailLinksViewlet(rep1, rep1.REQUEST, None)
        self.assertFalse(viewlet.available())
        self.assertEqual(viewlet.get_generation_view_name("", ""), "persistent-document-generation")
