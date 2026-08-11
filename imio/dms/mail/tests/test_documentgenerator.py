# -*- coding: utf-8 -*-
""" documentgenerator.py tests for this package."""
from collective.documentviewer.convert import Converter
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import update_categorized_elements
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.documentgenerator import DmsTemplatesListing
from imio.dms.mail.browser.documentgenerator import OutgoingMailLinksViewlet
from imio.dms.mail.content.behaviors import ISigningBehavior
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield.relation import RelationValue
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import mocker  # must be replaced in Plone 5 with python 3 unittest.mock
import unittest
import zope.event


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
        self.assertEqual(view1.display_send_modes(), u'Courrier postal, Courrier recommand\xe9')
        self.assertEqual(view1.display_send_modes(filter_on=u'post'), u'Courrier postal')
        self.assertEqual(view1.display_send_modes(filter_on=u'wrong_mode'), u'')
        self.assertEqual(view1.display_send_modes(separator=' & '), u'Courrier postal & Courrier recommand\xe9')
        view1.real_context.send_modes = [u"post", u"post_registered", u"email"]
        self.assertEqual(view1.display_send_modes(filter_on=u'post'), u'Courrier postal, Email')
        self.assertEqual(view1.display_send_modes(filter_on=u'post_registered'), u'Courrier recommand\xe9, Email')
        self.assertEqual(view1.display_send_modes(filter_on=[u'post', u'post_registered']),
                         u'Courrier postal, Courrier recommand\xe9, Email')
        self.assertEqual(view1.display_send_modes(filter_on=u'wrong_mode'), u'Email')

        # Test get_signers
        self.assertEqual(view1.get_signers(), [(0, u'Maxime DG', u'Directeur Général'),
                                               (1, u'Paul BM', u'Bourgmestre')])
        view1.real_context.signers.append({'signer': self.resp_grh.UID(), 'approvings': [u'_empty_'], 'number': 3,
                                           "editor": False})
        zope.event.notify(ObjectModifiedEvent(view1.real_context,
                                              Attributes(ISigningBehavior, "ISigningBehavior.signers")))
        self.assertEqual(view1.get_signers(), [(0, u'Maxime DG', u'Directeur Général'), (1, u'Paul BM', u'Bourgmestre'),
                                               (2, u'Michel Chef', u'Responsable GRH')])
        view1.real_context.signers = []
        # rules will be reapplied
        zope.event.notify(ObjectModifiedEvent(view1.real_context,
                                              Attributes(ISigningBehavior, "ISigningBehavior.signers")))
        self.assertEqual(view1.get_signers(), [(0, u'Maxime DG', u'Directeur Général'),
                                               (1, u'Paul BM', u'Bourgmestre')])

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
        def set_to_print(fobj, value):
            fobj.to_print = value
            parent = fobj.aq_parent
            elements = getattr(parent, "categorized_elements", None)
            if elements is None or fobj.UID() not in elements:
                category = get_category_object(fobj, fobj.content_category)
                update_categorized_elements(parent, fobj, category)
                elements = parent.categorized_elements
            elements[fobj.UID()]["to_print"] = value
            parent._p_changed = True

        view.context_var = lambda x: brains
        m0, m1, m2 = view.objs[0], view.objs[1], view.objs[2]
        # by default nothing is marked to_print -> nothing is returned
        for mail in (m0, m1, m2):
            set_to_print(mail["1"], False)
        self.assertListEqual(view.get_dms_files(), [])
        # add a (non-odt) appendix to the first mail, reusing the main file category
        filespath = u"%s/batchimport/toprocess/incoming-mail" % PRODUCT_DIR
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            appendix = createContentInContainer(
                m0, "dmsappendixfile", id="app1", title=u"appendix",
                file=NamedBlobFile(fo.read(), filename=u"in-courrier2.pdf"),
                content_category=m0["1"].content_category,
            )
        # mark to_print on m0 main + its appendix and m1 main; m2 main stays False
        set_to_print(m0["1"], True)
        set_to_print(appendix, True)
        set_to_print(m1["1"], True)
        # main file before appendix within m0, then m1 main; m2 (not to_print) excluded
        self.assertListEqual(view.get_dms_files(), [m0["1"], appendix, m1["1"]])
        # limit caps the total number of returned files
        self.assertListEqual(view.get_dms_files(limit=2), [m0["1"], appendix])
        # signed=True: e-signed files + appendix files to_print, whatever the main files to_print
        self.assertListEqual(view.get_dms_files(signed=True), [appendix])
        m1["1"].esigned = True
        m2["1"].esigned = True
        self.assertListEqual(view.get_dms_files(signed=True), [appendix, m1["1"], m2["1"]])
        # m0 main file converted to pdf when added to a sign session: only the pdf is considered
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            pdf = createContentInContainer(
                m0, "dmsommainfile", id="pdf1", title=u"converted",
                file=NamedBlobFile(fo.read(), filename=u"converted.pdf"),
                content_category=m0["1"].content_category, conv_from_uid=m0["1"].UID(),
            )
        set_to_print(pdf, True)
        pdf.esigned = True
        self.assertListEqual(view.get_dms_files(), [pdf, appendix, m1["1"]])
        self.assertListEqual(view.get_dms_files(signed=True), [pdf, appendix, m1["1"], m2["1"]])
        # m1 main file mailed: only the mailed version is considered, even if it's not e-signed
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            mailed = createContentInContainer(
                m1, "dmsommainfile", id="mailed1", title=u"mailed",
                file=NamedBlobFile(fo.read(), filename=u"mailed.pdf"),
                content_category=m1["1"].content_category,
            )
        set_to_print(mailed, True)
        IAnnotations(mailed)["documentgenerator"] = {"mailed": True, "from_doc_uid": m1["1"].UID()}
        self.assertListEqual(view.get_dms_files(), [pdf, appendix, mailed])
        self.assertListEqual(view.get_dms_files(signed=True), [pdf, appendix, m2["1"]])
        # not rendered from a dashboard -> empty
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

        # Test is_odt
        self.assertTrue(view.is_odt(m0["1"]))
        self.assertFalse(view.is_odt(appendix))

        # add an image appendix (a logo)
        png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
               b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
               b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        img_appendix = createContentInContainer(
            m0, "dmsappendixfile", id="logo", title=u"logo",
            file=NamedBlobFile(png, filename=u"logo.png", contentType="image/png"),
            content_category=m0["1"].content_category,
        )
        # Test is_image
        self.assertTrue(view.is_image(img_appendix))
        self.assertFalse(view.is_image(m0["1"]))
        self.assertFalse(view.is_image(appendix))
        # Test img_format
        self.assertEqual(view.img_format(img_appendix), "png")
        img_appendix.file.contentType = "image/jpeg"
        self.assertEqual(view.img_format(img_appendix), "jpg")
        img_appendix.file.contentType = "image/png"

        # Test get_print_pages
        self.assertListEqual(view.get_print_pages(m0["1"]), [])
        self.assertListEqual(view.get_print_pages(img_appendix), [])
        # borrow a real (converted) documentviewer annotation for the pdf appendix
        dv_annot = IAnnotations(m0["1"])["collective.documentviewer"]
        IAnnotations(appendix)["collective.documentviewer"] = dv_annot
        pages = view.get_print_pages(appendix)
        self.assertEqual(len(pages), dv_annot["num_pages"])
        self.assertEqual(sorted(pages[0].keys()), ["data", "format"])
        self.assertTrue(isinstance(pages[0]["data"], (bytes, str)))

        # get_print_pages regenerates an expired (dv_clean) preview before printing.
        del IAnnotations(appendix)["collective.documentviewer"]
        Converter(appendix)()
        appendix_annot = IAnnotations(appendix)["collective.documentviewer"]
        real_num_pages = appendix_annot["num_pages"]
        self.assertGreaterEqual(real_num_pages, 1)
        # simulate the dv_clean placeholder (single page, old sentinel date)
        appendix_annot["num_pages"] = 1
        appendix_annot["last_updated"] = "2010-01-01T00:00:00"
        pages = view.get_print_pages(appendix)
        # the real preview was regenerated: full page count restored and sentinel cleared
        self.assertEqual(len(pages), real_num_pages)
        self.assertNotEqual(
            IAnnotations(appendix)["collective.documentviewer"]["last_updated"], "2010-01-01T00:00:00"
        )
        # no usable preview -> warning message and the file is left out of the printing
        IAnnotations(appendix)["collective.documentviewer"] = {"successfully_converted": False}
        self.assertListEqual(view.get_print_pages(appendix), [])
        msgs = IStatusMessage(view.request).show()
        self.assertEqual(len(msgs), 1)
        self.assertIn(u"no preview image found", msgs[0].message)
        # restore the borrowed annotation for the following assertions
        IAnnotations(appendix)["collective.documentviewer"] = dv_annot

        # Test print_page_count / needs_blank_after
        self.assertEqual(view.print_page_count(img_appendix), 1)
        self.assertTrue(view.needs_blank_after(img_appendix))
        # a non-odt file occupies its documentviewer preview pages -> blank if odd
        self.assertEqual(view.print_page_count(appendix), dv_annot["num_pages"])
        self.assertEqual(view.needs_blank_after(appendix), dv_annot["num_pages"] % 2 == 1)
        # odt files manage their own duplex page break, so they never need one here
        self.assertFalse(view.needs_blank_after(m0["1"]))

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
            (3, self.ctct["personnel-folder"]["bourgmestre"]),
            (4, self.chef),
            (5, self.ctct["jeancourant"]),
            (6, self.ctct["personnel-folder"]["dirg"]),
            (7, self.ctct["personnel-folder"]["encodeur"]),
            (8, self.ctct["personnel-folder"]["lecteur"]),
            (9, self.ctct["bernardlermitte"]),
            (10, self.ctct["notencoded"]),
            (11, self.ctct["sergerobinet"]),
        ]
        self.assertListEqual(view.get_persons(), res)

        # Test get_held_positions
        res = [
            (1, 9, 27, self.ctct["bernardlermitte"]["agent-swde"]),
            (2, 5, 1, self.ctct["jeancourant"]["agent-electrabel"]),
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
        view.output_format = "odt"
        doc = view.generate_persistent_doc(view.pod_template, view.output_format)
        self.assertEqual(doc.portal_type, "dmsommainfile")
        self.assertIsNone(doc.scan_user)

        # Test redirects
        # redirects has be monkey patched in tests !!
        # self.assertEqual(view.redirects(doc),
        #                 'http://nohost/plone/outgoing-mail/reponse1/012999900000001/external_edit')

        # Test generation context
        gen_con = view._get_generation_context(hview, view.pod_template)
        self.assertEqual(gen_con["scan_id"], "IMIO012999900000011")
        self.assertTrue(gen_con["render_download_barcode"])
        hview.real_context.seal = True
        self.assertFalse(view._get_generation_context(hview, view.pod_template)["render_download_barcode"])
        hview.real_context.seal = False
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

    def test_copy_template_signers(self):
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        rk_rules = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = rep1.restrictedTraverse("persistent-document-generation")
        template = self.portal["templates"]["om"]["main"]
        view.pod_template = template
        pf = self.portal["contacts"]["personnel-folder"]
        dirg_hp = pf["dirg"]["directeur-general"]
        bourgmestre_hp = pf["bourgmestre"]["bourgmestre"]
        request = self.portal.REQUEST

        template_signers = [
            {"number": 1, "signer": dirg_hp.UID(), "editor": True, "approvings": [u"_empty_"]}
        ]
        empty_value = [{"number": 1, "signer": u"_empty_", "editor": False, "approvings": [u"_empty_"]}]
        original_mail_signers = rep1.signers
        original_rules = api.portal.get_registry_record(rk_rules, default=[])
        different_signers = [
            {"number": 1, "signer": bourgmestre_hp.UID(), "editor": False, "approvings": [u"_empty_"]}
        ]

        # "rules" mode (default): no copy from template
        template.signers = template_signers
        template.seal = True
        template.esign = True
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertIsNone(rep1.signers)

        # "template_first", template has signers, mail empty: copy
        api.portal.set_registry_record(rk_so, u"template_first")
        rep1.signers = None
        rep1.seal = False
        rep1.esign = False
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, template_signers)
        self.assertTrue(rep1.seal)
        self.assertTrue(rep1.esign)
        self.assertIsNot(rep1.signers, template.signers)

        # "template_first", mail holds the _empty_ placeholder: considered as a defined value,
        # so the template is not applied (warning).
        IStatusMessage(request).show()  # consume existing messages
        rep1.signers = list(empty_value)
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, empty_value)
        msgs = IStatusMessage(request).show()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].type, u"warning")

        # "template_first", template has no signers
        template.signers = None
        # fall back to signer rules if mail has no signers
        rep1.signers = different_signers
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, different_signers)
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(len(rep1.signers), 2)  # rules applied
        # With empty rules, nothing is found anywhere: an _empty_ value is set.
        api.portal.set_registry_record(rk_rules, [])
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, empty_value)
        api.portal.set_registry_record(rk_rules, original_rules)
        template.signers = template_signers

        # "template_first", conflict: mail has different real signers: warning, no copy
        IStatusMessage(request).show()  # consume existing messages
        rep1.signers = different_signers
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, different_signers)
        msgs = IStatusMessage(request).show()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].type, u"warning")

        # "template_first", same signers as template: no warning, no change
        rep1.signers = list(template_signers)
        rep1.esign = False
        view._copy_template_signers(template)
        msgs = IStatusMessage(request).show()
        self.assertEqual(len(msgs), 0)
        self.assertFalse(rep1.esign)  # no change at all

        # "rules_first", mail already has real signers (from rules): template ignored, no warning
        api.portal.set_registry_record(rk_so, u"rules_first")
        IStatusMessage(request).show()  # consume existing messages
        rep1.signers = different_signers
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, different_signers)
        msgs = IStatusMessage(request).show()
        self.assertEqual(len(msgs), 0)

        # "rules_first", mail empty (rules produced nothing): fall back to the template
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, template_signers)

        # "rules_first", mail is an empty list (rules produced nothing): fall back to the template
        rep1.signers = []
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, template_signers)

        # "rules_first", mail holds the _empty_ placeholder: considered as a defined value,
        # template is ignored (no copy, no warning).
        IStatusMessage(request).show()  # consume existing messages
        rep1.signers = list(empty_value)
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, empty_value)
        self.assertEqual(len(IStatusMessage(request).show()), 0)

        # "rules_first", neither rules nor template provide signers: _empty_ value is set
        # (consistent with template_first)
        template.signers = None
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, empty_value)
        template.signers = template_signers

        # MailingLoopTemplate: uses orig_template
        api.portal.set_registry_record(rk_so, u"template_first")
        mailing_view = rep1.restrictedTraverse("mailing-loop-persistent-document-generation")
        mailing_tpl = self.portal["templates"]["om"]["mailing"]
        mailing_view.orig_template = template
        rep1.signers = None
        mailing_view._copy_template_signers(mailing_tpl)
        self.assertEqual(rep1.signers, template_signers)

        # Cleanup
        api.portal.set_registry_record(rk_so, u"rules")
        api.portal.set_registry_record(rk_rules, original_rules)
        template.signers = None
        template.seal = None
        template.esign = None
        rep1.signers = original_mail_signers

    def test_get_template_signers_source(self):
        from imio.dms.mail.browser.documentgenerator import get_template_signers_source

        templates = self.portal["templates"]["om"]
        template = templates["main"]
        pf = self.portal["contacts"]["personnel-folder"]
        dirg_hp = pf["dirg"]["directeur-general"]
        bourgmestre_hp = pf["bourgmestre"]["bourgmestre"]
        tpl_signers = [{"number": 1, "signer": dirg_hp.UID(), "editor": True, "approvings": [u"_empty_"]}]
        sub_signers = [{"number": 1, "signer": bourgmestre_hp.UID(), "editor": False, "approvings": [u"_empty_"]}]
        empty_value = [{"number": 1, "signer": u"_empty_", "editor": False, "approvings": [u"_empty_"]}]
        original_signers = template.signers
        original_merge = list(template.merge_templates or [])

        sub = templates["ending"]
        sub.signers = sub_signers

        # get_template_signers_source returns a tuple (source_template_or_None, defined_on_template_itself)

        # template defines its own signers: returned directly, itself=True
        template.signers = tpl_signers
        template.merge_templates = [{"template": sub.UID(), "pod_context_name": u"sub", "do_rendering": False}]
        source, itself = get_template_signers_source(template)
        self.assertEqual(source.UID(), template.UID())
        self.assertTrue(itself)
        template.signers = None
        template.seal = True
        template.merge_templates = [{"template": sub.UID(), "pod_context_name": u"sub", "do_rendering": False}]
        source, itself = get_template_signers_source(template)
        self.assertEqual(source.UID(), template.UID())
        self.assertTrue(itself)

        # template has no signers but a merge sub-template defines them: sub-template returned, itself=False
        template.signers = None
        template.seal = False
        source, itself = get_template_signers_source(template)
        self.assertEqual(source.UID(), sub.UID())
        self.assertFalse(itself)
        sub.signers = None
        sub.seal = True
        source, itself = get_template_signers_source(template)
        self.assertEqual(source.UID(), sub.UID())
        self.assertFalse(itself)
        sub.signers = sub_signers
        sub.seal = False

        # an _empty_ placeholder on the template counts as a defined value: template returned, itself=True
        template.signers = empty_value
        source, itself = get_template_signers_source(template)
        self.assertEqual(source.UID(), template.UID())
        self.assertTrue(itself)

        # neither template nor sub-template define signers: (None, True)
        template.signers = None
        sub.signers = None
        self.assertEqual(get_template_signers_source(template), (None, True))

        # no merge_templates at all: (None, True)
        template.merge_templates = []
        self.assertEqual(get_template_signers_source(template), (None, True))

        # end-to-end: template_first, template empty, sub-template provides signers/seal/esign
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = rep1.restrictedTraverse("persistent-document-generation")
        original_rep1_signers = rep1.signers
        sub.signers = sub_signers
        sub.seal = False
        sub.esign = True
        template.signers = None
        template.merge_templates = [{"template": sub.UID(), "pod_context_name": u"sub", "do_rendering": False}]
        api.portal.set_registry_record(rk_so, u"template_first")
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers, sub_signers)
        self.assertTrue(rep1.esign)
        self.assertFalse(rep1.seal)

        # Cleanup
        api.portal.set_registry_record(rk_so, u"rules")
        template.signers = original_signers
        template.merge_templates = original_merge
        rep1.signers = original_rep1_signers

    def test_dg_templates_listing_signers_column(self):
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        folder = self.portal["templates"]["om"]
        template = folder["main"]
        pf = self.portal["contacts"]["personnel-folder"]
        dirg_hp = pf["dirg"]["directeur-general"]
        original_signers = template.signers
        request = self.portal.REQUEST

        def column_names():
            view = DmsTemplatesListing(folder, request)
            view.update()
            return view, [col.__name__ for col in view.table.columns]

        # "rules" mode (default): the signers column is hidden
        api.portal.set_registry_record(rk_so, u"rules")
        view, names = column_names()
        self.assertNotIn("TemplateSignersColumn", names)

        # "template_first": the signers column is shown
        api.portal.set_registry_record(rk_so, u"template_first")
        view, names = column_names()
        self.assertIn("TemplateSignersColumn", names)

        # "rules_first": the signers column is shown too
        api.portal.set_registry_record(rk_so, u"rules_first")
        view, names = column_names()
        self.assertIn("TemplateSignersColumn", names)
        column = [col for col in view.table.columns if col.__name__ == "TemplateSignersColumn"][0]

        # renderCell reflects whether the template defines signers
        bourgmestre_hp = pf["bourgmestre"]["bourgmestre"]
        sub = folder["ending"]
        original_merge = list(template.merge_templates or [])
        original_sub_signers = sub.signers

        # no signers anywhere: empty cell
        template.signers = None
        template.merge_templates = []
        sub.signers = None
        self.assertEqual(column.renderCell(template), u"")

        # signers defined on the template itself
        template.signers = [{"number": 1, "signer": dirg_hp.UID(), "editor": True, "approvings": [u"_empty_"]}]
        self.assertIn("pt_self_signers", column.renderCell(template))

        # signers defined via a merge sub-template
        template.signers = None
        sub.signers = [{"number": 1, "signer": bourgmestre_hp.UID(), "editor": False, "approvings": [u"_empty_"]}]
        template.merge_templates = [{"template": sub.UID(), "pod_context_name": u"sub", "do_rendering": False}]
        self.assertIn("pt_sub_signers", column.renderCell(template))

        # the overridden page is resolved when the imio.dms.mail browser layer is active
        alsoProvides(request, IImioDmsMailLayer)
        try:
            self.assertIsInstance(folder.restrictedTraverse("dg-templates-listing"), DmsTemplatesListing)
        finally:
            noLongerProvides(request, IImioDmsMailLayer)

        # Cleanup
        api.portal.set_registry_record(rk_so, u"rules")
        template.signers = original_signers
        template.merge_templates = original_merge
        sub.signers = original_sub_signers

    def test_copy_template_signers_substitutes(self):
        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"
        rk_subs = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_substitutes"
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        view = rep1.restrictedTraverse("persistent-document-generation")
        template = self.portal["templates"]["om"]["main"]
        view.pod_template = template
        pf = self.portal["contacts"]["personnel-folder"]
        dirg_hp = pf["dirg"]["directeur-general"]
        bourgmestre_hp = pf["bourgmestre"]["bourgmestre"]
        original_signers = template.signers
        original_subs = api.portal.get_registry_record(rk_subs, default=[])
        original_rep1_signers = rep1.signers

        template.signers = [
            {"number": 1, "signer": bourgmestre_hp.UID(), "editor": True, "approvings": [u"_empty_"]}
        ]
        api.portal.set_registry_record(rk_so, u"template_first")

        # An active substitute replaces the template signer when copied to the mail
        api.portal.set_registry_record(
            rk_subs,
            [{"absent_signer": bourgmestre_hp.UID(), "substitute_signer": dirg_hp.UID(),
              "valid_from": None, "valid_until": None}],
        )
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(rep1.signers[0]["editor"], True)

        # Re-generating with the mail already holding the substituted signers: no warning, idempotent
        request = self.portal.REQUEST
        IStatusMessage(request).show()  # consume existing messages
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers[0]["signer"], dirg_hp.UID())
        self.assertEqual(len(IStatusMessage(request).show()), 0)

        # No active substitute: the template signer is kept as-is
        api.portal.set_registry_record(rk_subs, [])
        rep1.signers = None
        view._copy_template_signers(template)
        self.assertEqual(rep1.signers[0]["signer"], bourgmestre_hp.UID())

        # Cleanup
        api.portal.set_registry_record(rk_so, u"rules")
        api.portal.set_registry_record(rk_subs, original_subs)
        template.signers = original_signers
        rep1.signers = original_rep1_signers

    def test_filter_signing_fieldset(self):
        from imio.dms.mail.browser.documentgenerator import _filter_signing_fieldset

        rk_so = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signers_origin"

        class _Group(object):
            def __init__(self, name):
                self.__name__ = name

        class _Form(object):
            def __init__(self):
                self.groups = [_Group("default"), _Group("signing")]

        # "rules" mode: the signing fieldset is removed
        api.portal.set_registry_record(rk_so, u"rules")
        form = _Form()
        _filter_signing_fieldset(form)
        self.assertEqual([gr.__name__ for gr in form.groups], ["default"])

        # other modes: the signing fieldset is kept
        for mode in (u"template_first", u"rules_first"):
            api.portal.set_registry_record(rk_so, mode)
            form = _Form()
            _filter_signing_fieldset(form)
            self.assertEqual([gr.__name__ for gr in form.groups], ["default", "signing"])

        api.portal.set_registry_record(rk_so, u"rules")

    def test_OutgoingMailLinksViewlet(self):
        """
        Test viewlet
        """
        rep1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        viewlet = OutgoingMailLinksViewlet(rep1, rep1.REQUEST, None)
        self.assertFalse(viewlet.available())
        self.assertEqual(viewlet.get_generation_view_name("", ""), "persistent-document-generation")
