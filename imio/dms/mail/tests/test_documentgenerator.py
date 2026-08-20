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
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import PREVIEW_CLEANED_DATE
from imio.dms.mail.utils import PREVIEW_EML_DATE
from imio.helpers.content import get_object
from mock import Mock
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield.relation import RelationValue
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import mocker  # must be replaced in Plone 5 with python 3 unittest.mock
import unittest
import zipfile
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
            """Mark a file to_print and refresh its stored categorized infos."""
            fobj.to_print = value
            parent = fobj.aq_parent
            category = get_category_object(fobj, fobj.content_category)
            update_categorized_elements(parent, fobj, category)
            parent.categorized_elements[fobj.UID()]["to_print"] = value
            parent._p_changed = True

        def printed(entries):
            """Return [(container, [mainfile titles], [annex titles]), ...] of get_dms_files."""
            return [
                (e["container"],
                 [d["title"] for d in e["mainfiles"]],
                 [d["title"] for d in e["annexes"]])
                for e in entries
            ]

        view.context_var = lambda x: brains
        m0, m1, m2 = view.objs[0], view.objs[1], view.objs[2]
        # by default nothing is marked to_print -> nothing is returned
        for mail in (m0, m1, m2):
            set_to_print(mail["1"], False)
        self.assertListEqual(view.get_dms_files(), [])
        # a converted documentviewer annotation, borrowed from a main file of the fixture
        dv_annot = IAnnotations(m0["1"])["collective.documentviewer"]
        # add a (non-odt) appendix to the first mail, reusing the main file category
        filespath = u"%s/batchimport/toprocess/incoming-mail" % PRODUCT_DIR
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            appendix = createContentInContainer(
                m0, "dmsappendixfile", id="app1", title=u"appendix",
                file=NamedBlobFile(fo.read(), filename=u"in-courrier2.pdf"),
                content_category=m0["1"].content_category,
            )
        IAnnotations(appendix)["collective.documentviewer"] = dv_annot
        # mark to_print on m0 main + its appendix and m1 main; m2 main stays False
        set_to_print(m0["1"], True)
        set_to_print(appendix, True)
        set_to_print(m1["1"], True)
        # files are grouped by mail, ged files and annexes kept apart, m2 (not to_print) excluded
        self.assertListEqual(
            printed(view.get_dms_files()),
            [(m0, [m0["1"].Title()], [u"appendix"]), (m1, [m1["1"].Title()], [])],
        )
        # each file carries its preview pages, numbered from 1 inside its own group
        entry = view.get_dms_files()[0]
        self.assertEqual(entry["mainfiles"][0]["number"], 1)
        self.assertEqual(entry["annexes"][0]["number"], 1)
        self.assertEqual(entry["annexes"][0]["number_of_images"], dv_annot["num_pages"])
        self.assertEqual(len(entry["annexes"][0]["images"]), dv_annot["num_pages"])
        self.assertEqual(sorted(entry["annexes"][0]["images"][0].keys()), ["number", "path"])
        # signed=True: e-signed ged files and appendix files, both marked to_print
        self.assertListEqual(printed(view.get_dms_files(signed=True)), [(m0, [], [u"appendix"])])
        m1["1"].esigned = True
        m2["1"].esigned = True
        for mail in (m1, m2):
            set_to_print(mail["1"], mail["1"].to_print)  # refresh the stored esigned info
        # m2 ged file is signed but not marked to_print, so it is left out
        self.assertListEqual(
            printed(view.get_dms_files(signed=True)),
            [(m0, [], [u"appendix"]),
             (m1, [m1["1"].Title()], [])],
        )
        # m0 ged file converted to pdf when added to a sign session: only the pdf is considered
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            pdf = createContentInContainer(
                m0, "dmsommainfile", id="pdf1", title=u"converted",
                file=NamedBlobFile(fo.read(), filename=u"converted.pdf"),
                content_category=m0["1"].content_category, conv_from_uid=m0["1"].UID(),
            )
        IAnnotations(pdf)["collective.documentviewer"] = dv_annot
        set_to_print(pdf, True)
        self.assertEqual(
            printed(view.get_dms_files())[0], (m0, [u"converted"], [u"appendix"]))
        # m1 ged file mailed: only the mailed version is considered
        with open(u"%s/in-courrier2.pdf" % filespath, "rb") as fo:
            mailed = createContentInContainer(
                m1, "dmsommainfile", id="mailed1", title=u"mailed",
                file=NamedBlobFile(fo.read(), filename=u"mailed.pdf"),
                content_category=m1["1"].content_category,
            )
        IAnnotations(mailed)["collective.documentviewer"] = dv_annot
        set_to_print(mailed, True)
        IAnnotations(mailed)["documentgenerator"] = {"mailed": True, "from_doc_uid": m1["1"].UID()}
        self.assertEqual(
            printed(view.get_dms_files())[1], (m1, [u"mailed"], []))

        # Test _usable_preview: an expired (dv_clean) preview is regenerated before printing
        del IAnnotations(appendix)["collective.documentviewer"]
        Converter(appendix)()
        appendix_annot = IAnnotations(appendix)["collective.documentviewer"]
        real_num_pages = appendix_annot["num_pages"]
        self.assertGreaterEqual(real_num_pages, 1)
        appendix_annot["num_pages"] = 1
        appendix_annot["last_updated"] = PREVIEW_CLEANED_DATE
        self.assertTrue(view._usable_preview(appendix))
        self.assertEqual(IAnnotations(appendix)["collective.documentviewer"]["num_pages"], real_num_pages)
        self.assertNotEqual(
            IAnnotations(appendix)["collective.documentviewer"]["last_updated"], PREVIEW_CLEANED_DATE)
        # an email that could never be converted is never regenerated, only skipped
        IAnnotations(appendix)["collective.documentviewer"]["last_updated"] = PREVIEW_EML_DATE
        self.assertFalse(view._usable_preview(appendix))
        # no usable preview -> the file is left out of the printing and a warning is shown
        IAnnotations(appendix)["collective.documentviewer"] = {"successfully_converted": False}
        IStatusMessage(view.request).show()  # empty the queue
        self.assertEqual(printed(view.get_dms_files())[0], (m0, [u"converted"], []))
        msgs = [m.message for m in IStatusMessage(view.request).show()]
        self.assertTrue([m for m in msgs if u"no preview image found" in m], msgs)
        IAnnotations(appendix)["collective.documentviewer"] = dv_annot

        # Test print_annex_header: each template reads its own configuration option
        rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}"
        om_tmplts = self.portal["templates"]["om"]
        # without a print template in context there is no option to read
        view.pod_template = None
        self.assertRaises(KeyError, view.print_annex_header)
        # the hand signature template
        view.pod_template = om_tmplts["d-print-to-sign"]
        self.assertFalse(view.print_annex_header())
        api.portal.set_registry_record(rec.format("omail_print_manual_annex_header"), True)
        self.assertTrue(view.print_annex_header())
        # the electronic signature template reads its own option
        view.pod_template = om_tmplts["d-print-signed"]
        self.assertFalse(view.print_annex_header())
        api.portal.set_registry_record(rec.format("omail_print_esign_annex_header"), True)
        self.assertTrue(view.print_annex_header())
        # a signing request reads its own option, not the outgoing mail ones
        view.pod_template = om_tmplts["d-print-request"]
        self.assertFalse(view.print_annex_header())
        api.portal.set_registry_record(rec.format("request_print_esign_annex_header"), True)
        self.assertTrue(view.print_annex_header())
        view.pod_template = None

        # Test image_orientation: only a landscape image is rotated to fill the page
        self.assertEqual(view.image_orientation(Mock(width=200, height=100)), "-rotate 270")
        self.assertIsNone(view.image_orientation(Mock(width=100, height=200)))
        self.assertIsNone(view.image_orientation(Mock(width=100, height=100)))

        # Test is_signed_print: the rendered template tells which of the two cases applies
        self.assertFalse(view.is_signed_print())  # no pod_template at all
        view.pod_template = self.portal["templates"]["om"]["d-print-to-sign"]
        self.assertFalse(view.is_signed_print())
        view.pod_template = self.portal["templates"]["om"]["d-print-signed"]
        self.assertTrue(view.is_signed_print())
        view.pod_template = self.portal["templates"]["om"]["d-print-to-sign"]

        # Test annex_header
        entry = view.get_dms_files(signed=False)[0]
        annex = entry["annexes"][0]
        header = translate(view.annex_header(entry, annex, {"number": 2}), context=view.request)
        self.assertIn(u"1/1", header)
        self.assertIn(annex["title"], header)
        self.assertIn(u"2/{}".format(annex["number_of_images"]), header)

        # Test get_print_pages: one entry per page, ged pages first, header only on annexes
        api.portal.set_registry_record(rec.format("omail_print_manual_annex_header"), False)
        pages = view.get_print_pages()
        self.assertTrue(pages)
        self.assertEqual(sorted(pages[0].keys()), ["header", "path"])
        # header option off -> no page carries a header
        self.assertEqual([p["header"] for p in pages], [u""] * len(pages))
        # header option on -> only the annex pages carry one
        api.portal.set_registry_record(rec.format("omail_print_manual_annex_header"), True)
        headers = [p["header"] for p in view.get_print_pages()]
        self.assertTrue([h for h in headers if h], headers)
        self.assertTrue([h for h in headers if not h], headers)
        # a page whose preview image has no path on disk is left out
        self.assertTrue(all(p["path"] for p in view.get_print_pages()))


    def test_print_model_statements(self):
        """The print model inserts the preview image at the printable page size.

        Guards the binary odt file on two points. An explicit size is what scales a
        documentviewer preview to the page width, because appy only shrinks with
        maxWidth. And maxWidth and maxHeight must be given explicitly rather than left
        to their default of "page": appy reads the page layout with PageLayout.getFloat,
        which strips the unit, so a template whose page is declared in inches, as
        LibreOffice writes it, yields a ceiling 2.54 times too small.

        The header must come from an input field inside its paragraph, never from a
        "from" clause: given a plain string, appy replaces the paragraph itself and
        leaves bare text under office:text, which LibreOffice silently discards when
        collective.documentgenerator calls it with forceOoCall.
        """
        path = "%s/profiles/default/templates/d-print.odt" % PRODUCT_DIR
        content = zipfile.ZipFile(path).read("content.xml").decode("utf-8")
        self.assertIn(u"do section- for page in view.get_print_pages()", content)
        self.assertIn(u"size=view.print_image_size", content)
        self.assertIn(u"maxWidth=view.print_image_size[0]", content)
        self.assertIn(u"maxHeight=view.print_image_size[1]", content)
        self.assertIn(u"convertOptions=view.image_orientation", content)
        # the header value sits in an input field, not in a "from" clause
        self.assertIn(u"do text if page['header']".replace(u"'", u"&apos;"), content)
        self.assertIn(u"<text:text-input", content)
        self.assertNotIn(u"from page['header']".replace(u"'", u"&apos;"), content)
        # printable area of an A4 page with the 2 cm margins of that template
        view = self.omf["mail-searches"].unrestrictedTraverse("@@document_generation_helper_view")
        self.assertEqual(view.print_image_size, (17.0, 25.7))

    def test_get_dms_files_on_sign_request(self):
        """A signing request holds appendix files only, so every file it prints is an annex."""
        view = self.omf["mail-searches"].unrestrictedTraverse("@@document_generation_helper_view")
        request, req_files = create_sign_request(self.portal, oid="sr-files", nb_files=2)
        signed_file, annex_file = req_files
        # borrow a converted documentviewer annotation so both files have preview images
        dv_annot = IAnnotations(
            self.omf["202633"]["reponse1"]["1"])["collective.documentviewer"]
        for fobj, esigned, to_print in ((signed_file, True, True), (annex_file, False, True)):
            IAnnotations(fobj)["collective.documentviewer"] = dv_annot
            fobj.esigned = esigned
            fobj.to_print = to_print
            category = get_category_object(fobj, fobj.content_category)
            update_categorized_elements(request, fobj, category)
            request.categorized_elements[fobj.UID()]["to_print"] = to_print
            request.categorized_elements[fobj.UID()]["esigned"] = esigned
        request._p_changed = True
        view.print_containers = lambda: [request]
        entries = view.get_dms_files(signed=True)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        # the signed file and the file marked to print are one single annex group,
        # numbered across the whole request
        self.assertEqual(entry["mainfiles"], [])
        self.assertEqual([d["UID"] for d in entry["annexes"]],
                         [signed_file.UID(), annex_file.UID()])
        self.assertEqual([d["number"] for d in entry["annexes"]], [1, 2])
        # with the signing request option on, every printed page carries a header
        view.pod_template = self.portal["templates"]["om"]["d-print-request"]
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.request_print_esign_annex_header", True)
        self.assertTrue(all(page["header"] for page in view.get_print_pages()))
        # a file selected because it is signed is not printed a second time as an annex
        annex_file.esigned = True
        request.categorized_elements[annex_file.UID()]["esigned"] = True
        request._p_changed = True
        entry = view.get_dms_files(signed=True)[0]
        self.assertEqual(entry["mainfiles"], [])
        self.assertEqual(len(entry["annexes"]), 2)
        # a signed file not marked to_print is left out
        signed_file.to_print = False
        request.categorized_elements[signed_file.UID()]["to_print"] = False
        request._p_changed = True
        entry = view.get_dms_files(signed=True)[0]
        self.assertEqual([d["UID"] for d in entry["annexes"]], [annex_file.UID()])

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
