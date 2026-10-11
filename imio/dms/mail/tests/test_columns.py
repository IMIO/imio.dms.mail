# -*- coding: utf-8 -*-
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.adapters import SignRequestApprovalAdapter
from imio.dms.mail.browser.table import OMVersionsTable
from imio.dms.mail.browser.table import SignRequestVersionsTable
from imio.dms.mail.columns import AssignedUserColumn
from imio.dms.mail.columns import CKPathColumn
from imio.dms.mail.columns import CKTemplatesTitleColumn
from imio.dms.mail.columns import ContactsColumn
from imio.dms.mail.columns import ContactTitleColumn
from imio.dms.mail.columns import FilesizeColumn
from imio.dms.mail.columns import IMSendModesColumn
from imio.dms.mail.columns import IMTitleColumn
from imio.dms.mail.columns import MailTypeColumn
from imio.dms.mail.columns import OMColorColumn
from imio.dms.mail.columns import OMSendModesColumn
from imio.dms.mail.columns import OMTitleColumn
from imio.dms.mail.columns import OutgoingDateColumn
from imio.dms.mail.columns import PathColumn
from imio.dms.mail.columns import PersonnelHPFacetedColumn
from imio.dms.mail.columns import PersonnelPrimaryOrganisationFacetedColumn
from imio.dms.mail.columns import PersonnelUseridFacetedColumn
from imio.dms.mail.columns import RecipientsColumn
from imio.dms.mail.columns import ReviewStateColumn
from imio.dms.mail.columns import SenderColumn
from imio.dms.mail.columns import SessionIdColumn
from imio.dms.mail.columns import TaskActionsColumn
from imio.dms.mail.columns import TaskParentColumn
from imio.dms.mail.columns import TreatingGroupsColumn
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.esign.utils import add_files_to_session
from imio.esign.utils import create_session
from imio.helpers.content import get_object
from persistent.list import PersistentList
from plone import api
from plone.app.testing import login
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestColumns(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.intids = getUtility(IIntIds)
        self.mail_table = self.portal["incoming-mail"]["mail-searches"].unrestrictedTraverse("@@faceted-table-view")
        self.task_table = self.portal["incoming-mail"]["mail-searches"].unrestrictedTraverse("@@faceted-table-view")
        self.imf = self.portal["incoming-mail"]
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.im5 = get_object(oid="courrier5", ptype="dmsincomingmail")
        self.ta1 = self.im1["tache1"]
        self.ta31 = self.im1["tache3"]["tache3-1"]
        self.om1 = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.om_table = self.portal["outgoing-mail"]["mail-searches"].unrestrictedTraverse("@@faceted-table-view")
        self.pc = self.portal.portal_catalog
        self.maxDiff = None

    def brain(self, obj):
        return self.pc(UID=obj.UID())[0]

    def test_SenderColumn(self):
        column = SenderColumn(self.portal, self.portal.REQUEST, self.mail_table)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(
            column.renderCell(brain),
            u"<a href='http://nohost/plone/contacts/jeancourant/agent-electrabel' target='_blank' "
            "class='pretty_link link-tooltip'><span class='pretty_link_icons'><img title='Held position' "
            "src='http://nohost/plone/held_position_icon.png' /></span><span class='pretty_link_content'"
            ">Monsieur Jean Courant, Agent (Electrabel)</span></a>",
        )
        # multiple senders
        self.im5.sender.append(RelationValue(self.intids.getId(self.portal["contacts"]["sergerobinet"])))
        self.im5.reindexObject(idxs=["sender_index"])
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        rendered = column.renderCell(brain)
        self.assertIn('<ul class="contacts_col"><li>', rendered)
        self.assertEqual(rendered.count("<a href"), 2)
        # no sender
        imail = sub_create(
            self.portal["incoming-mail"],
            "dmsincomingmail",
            datetime.now(),
            "my-id",
            **{"title": u"My title", "description": u"Description"}
        )
        brain = self.portal.portal_catalog(UID=imail.UID())[0]
        self.assertEqual(column.renderCell(brain), "-")
        # sender not found: we delete it
        self.im5.sender = self.im5.sender[0:1]
        self.im5.reindexObject(idxs=["sender_index"])
        api.content.delete(obj=self.portal["contacts"]["jeancourant"]["agent-electrabel"], check_linkintegrity=False)
        brain = self.portal.portal_catalog(UID=self.im5.UID())[0]
        self.assertEqual(column.renderCell(brain), "-")

    def test_IMTitleColumn(self):
        column = IMTitleColumn(self.portal, self.portal.REQUEST, self.mail_table)
        self.assertDictEqual(column.params, {"showContentIcon": True, "display_tag_title": False})
        rendered = column.renderCell(self.brain(self.im1))
        self.assertIn(u"href='{}'".format(self.im1.absolute_url()), rendered)
        self.assertIn(u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png'", rendered)
        self.assertIn(u"E0001 - Courrier 1", rendered)

    def test_OMTitleColumn(self):
        column = OMTitleColumn(self.portal, self.portal.REQUEST, self.om_table)
        rendered = column.renderCell(self.brain(self.om1))
        self.assertIn(u"href='{}'".format(self.om1.absolute_url()), rendered)
        self.assertIn(u"src='http://nohost/plone/++resource++imio.dms.mail/dmsoutgoingmail_icon.png'", rendered)

    def test_OMColorColumn(self):
        column = OMColorColumn(self.portal, self.portal.REQUEST, self.om_table)
        # inline javascript in header (tooltipster)
        self.assertEqual(
            column.header_js,
            '<script type="text/javascript">$(document).ready(function() {'
            '$(".tooltip-title").tooltipster({position: "right", theme: "tooltipster-shadow"});});</script>',
        )
        brain = self.brain(self.om1)
        printable = column.is_printable(brain)
        self.assertEqual(printable, bool(brain.markers) and "lastDmsFileIsOdt" in brain.markers)
        self.assertEqual(
            column.getCSSClasses(brain),
            {"tr": "min-height", "td": "{}_printable_{}".format(column.cssClassPrefix, printable)},
        )
        self.assertTrue(column.renderCell(brain).startswith(u'<div class="tooltip-title" title="'))
        self.assertTrue(column.renderCell(brain).endswith(u'">&nbsp;</div>'))
        # brain without markers
        self.assertFalse(column.is_printable(self.brain(self.im1)))

    def test_TreatingGroupsColumn(self):
        # attrName is the registration name, set by the table
        column = self.mail_table.nameColumn(
            TreatingGroupsColumn(self.portal, self.portal.REQUEST, self.mail_table), "treating_groups"
        )
        self.assertEqual(column.renderCell(self.brain(self.im1)), u"Direction générale")

    def test_AssignedUserColumn(self):
        column = AssignedUserColumn(self.portal, self.portal.REQUEST, self.om_table)
        self.assertEqual(column.renderCell(self.brain(self.om1)), u"Michel Chef")

    def test_MailTypeColumn(self):
        column = self.mail_table.nameColumn(MailTypeColumn(self.portal, self.portal.REQUEST, self.mail_table),
                                            "mail_type")
        self.assertEqual(column.renderCell(self.brain(self.im1)), u"Courrier")

    def test_IMSendModesColumn(self):
        column = IMSendModesColumn(self.portal, self.portal.REQUEST, self.mail_table)
        self.assertEqual(column.renderCell(self.brain(self.im1)), u"Courrier postal")

    def test_OMSendModesColumn(self):
        column = OMSendModesColumn(self.portal, self.portal.REQUEST, self.om_table)
        self.assertEqual(column.renderCell(self.brain(self.om1)), u"Courrier postal")

    def test_OutgoingDateColumn(self):
        column = OutgoingDateColumn(self.portal, self.portal.REQUEST, self.om_table)
        self.assertEqual(column.attrName, u"in_out_date")
        # plonelocales short format, the test request negotiates English
        self.assertEqual(column.renderCell(self.brain(self.im1)), self.im1.reception_date.strftime("%b %d, %Y"))

    def test_ContactsColumn(self):
        # _icons: icon url built from the portal type icon_expr (skin images)
        column = ContactsColumn(self.portal, self.portal.REQUEST, self.mail_table)
        ctct = self.portal["contacts"]
        self.assertEqual(
            column._icons(self.brain(ctct["electrabel"])),
            u"<img title='Organization' src='http://nohost/plone/organization_icon.png' />",
        )
        self.assertEqual(
            column._icons(self.brain(ctct["jeancourant"])),
            u"<img title='Person' src='http://nohost/plone/person_icon.png' />",
        )
        self.assertEqual(
            column._icons(self.brain(ctct["jeancourant"]["agent-electrabel"])),
            u"<img title='Held position' src='http://nohost/plone/held_position_icon.png' />",
        )

    def test_RecipientsColumn(self):
        column = RecipientsColumn(self.portal, self.portal.REQUEST, self.om_table)
        self.assertEqual(
            column.renderCell(self.brain(self.om1)),
            u"<a href='http://nohost/plone/contacts/electrabel' target='_blank' class='pretty_link link-tooltip'>"
            u"<span class='pretty_link_icons'><img title='Organization' "
            u"src='http://nohost/plone/organization_icon.png' /></span><span class='pretty_link_content'>"
            u"Electrabel</span></a>",
        )
        # "all under" values (l:) are not displayed
        self.om1.recipients = []
        self.om1.reindexObject(idxs=["recipients_index"])
        self.assertEqual(column.renderCell(self.brain(self.om1)), "-")

    def test_ReviewStateColumn(self):
        column = self.mail_table.nameColumn(ReviewStateColumn(self.portal, self.portal.REQUEST, self.mail_table),
                                            "review_state")
        # plone domain state titles ("created", "om_created"), the test request negotiates English
        self.assertEqual(column.renderCell(self.brain(self.im1)), u"Created")
        self.assertEqual(column.renderCell(self.brain(self.om1)), u"Created")

    def test_ContactTitleColumn(self):
        column = ContactTitleColumn(self.portal, self.portal.REQUEST, self.mail_table)
        hp = self.portal["contacts"]["jeancourant"]["agent-electrabel"]
        self.assertEqual(column.contentValue(hp), u"Monsieur Jean Courant, Agent (Electrabel)")

    def test_PathColumn(self):
        cls = self.portal["contacts"]["cls-searches"]
        table = cls.unrestrictedTraverse("@@faceted-table-view")
        column = PathColumn(cls, self.portal.REQUEST, table)
        clf = self.portal["contacts"]["contact-lists-folder"]
        brain = self.brain(clf["common"]["list-agents-swde"])
        self.assertEqual(column.getLinkURL(brain), clf["common"].absolute_url())
        self.assertEqual(column.getLinkContent(brain), clf["common"].title)
        self.assertEqual(column.root_path, "/plone/contacts/contact-lists-folder")
        self.assertEqual(
            column.renderCell(brain),
            u'<a href="{}" target="_blank">{}</a>'.format(clf["common"].absolute_url(), clf["common"].title),
        )

    def test_CKTemplatesTitleColumn(self):
        tpl = self.portal["templates"]["oem"]["emain"]
        column = CKTemplatesTitleColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(column.getLinkCSS(tpl), ' class="state-{}"'.format(api.content.get_state(tpl)))
        self.assertEqual(column.getLinkContent(tpl), tpl.title)

    def test_CKPathColumn(self):
        tpl = self.portal["templates"]["oem"]["emain"]
        column = CKPathColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(column.getLinkURL(tpl), "http://nohost/plone/templates/oem")
        self.assertEqual(column.getLinkContent(tpl), "-")
        IAnnotations(tpl)["dmsmail.cke_tpl_tit"] = u"Service > Modèles"
        self.assertEqual(column.getLinkContent(tpl), u"Service > Modèles")

    def test_PersonnelUseridFacetedColumn(self):
        pf = self.portal["contacts"]["personnel-folder"]
        table = pf["personnel-searches"].unrestrictedTraverse("@@faceted-table-view")
        column = PersonnelUseridFacetedColumn(self.portal, self.portal.REQUEST, table)
        self.assertEqual(
            column.renderCell(self.brain(pf["agent"])),
            u'<a href="http://nohost/plone/@@usergroup-usermembership?userid=agent" target="_blank">agent</a>',
        )
        pf["agent"].userid = None
        self.assertEqual(column.renderCell(self.brain(pf["agent"])), u"-")

    def test_PersonnelHPFacetedColumn(self):
        pf = self.portal["contacts"]["personnel-folder"]
        table = pf["personnel-searches"].unrestrictedTraverse("@@faceted-table-view")
        column = PersonnelHPFacetedColumn(self.portal, self.portal.REQUEST, table)
        rendered = column.renderCell(self.brain(pf["dirg"]))
        self.assertTrue(rendered.startswith(u'<ul class="hp_col"><li class=\'plonegroup_1\'>'))
        self.assertIn(u"<a href='{}' target='_blank' class='pretty_link link-tooltip'>".format(
            pf["dirg"]["directeur-general"].absolute_url()), rendered)
        self.assertIn(u"<span class='signer-icon' title='", rendered)
        # person without held position
        person = api.content.create(container=pf, type="person", id="nohp", lastname=u"Nohp")
        self.assertEqual(column.renderCell(self.brain(person)), "-")

    def test_PersonnelPrimaryOrganisationFacetedColumn(self):
        pf = self.portal["contacts"]["personnel-folder"]
        table = pf["personnel-searches"].unrestrictedTraverse("@@faceted-table-view")
        column = PersonnelPrimaryOrganisationFacetedColumn(self.portal, self.portal.REQUEST, table)
        self.assertTrue(column.the_object)
        self.assertEqual(column.attrName, "primary_organization")

    def test_FilesizeColumn(self):
        table = OMVersionsTable(self.om1, self.portal.REQUEST, None)
        column = FilesizeColumn(self.om1, self.portal.REQUEST, table)
        column.header = u"Filesize"
        # small files: no total
        self.assertEqual(column.renderHeadCell(), u"Taille")
        # big files: total displayed
        ct = self.portal["annexes_types"]["outgoing_appendix_files"]["outgoing-appendix-file"]
        createContentInContainer(
            self.om1, "dmsappendixfile", id="big", file=NamedBlobFile(b"x" * 2 * 1024 * 1024, filename=u"big.txt"),
            content_category=calculate_category_id(ct)
        )
        table = OMVersionsTable(self.om1, self.portal.REQUEST, None)
        column = FilesizeColumn(self.om1, self.portal.REQUEST, table)
        column.header = u"Filesize"
        self.assertIn(u"<p>(Tot: <span class='soft_warn_filesize'>", column.renderHeadCell())

    def test_TaskParentColumn(self):
        column = TaskParentColumn(self.portal, self.portal.REQUEST, self.task_table)
        brain = self.portal.portal_catalog(UID=self.ta1.UID())[0]
        mail = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.assertEqual(
            column.renderCell(brain),
            u"<a class='pretty_link' title='E0001 - Courrier 1' "
            u"href='{}' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
            u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png' style="
            u"\"width: 16px; height: 16px;\" /></span><span class='pretty_link_content state-created'>"
            u"E0001 - Courrier 1</span></a>".format(mail.absolute_url()),
        )
        brain = self.portal.portal_catalog(UID=self.ta31.UID())[0]
        self.assertEqual(
            column.renderCell(brain),
            u"<a class='pretty_link' title='E0001 - Courrier 1' "
            u"href='{}' target='_blank'><span class='pretty_link_icons'><img title='Incoming Mail' "
            u"src='http://nohost/plone/++resource++imio.dms.mail/dmsincomingmail_icon.png' style="
            u"\"width: 16px; height: 16px;\" /></span><span class='pretty_link_content state-created'>"
            u"E0001 - Courrier 1</span></a>".format(mail.absolute_url()),
        )

    def test_TaskActionsColumn(self):
        column = TaskActionsColumn(self.portal, self.portal.REQUEST, None)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username=TEST_USER_ID)
        rendered = column.renderCell(self.ta1)
        self.assertIn("do_to_assign", rendered)
        self.assertIn('title="Edit"', rendered)
        self.assertIn('title="Delete"', rendered)
        self.assertIn('"overlay-history"', rendered)
        column.view_name = ""
        self.assertRaises(KeyError, column.renderCell, self.ta1)


class TestSessionIdColumn(unittest.TestCase):
    """Tests for SessionIdColumn."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.layer["app"], "admin")
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-om-signing", run_dependencies=False
        )
        change_user(self.portal)

        # 1 omail, 3 files: file_a in 2 sessions, file_b in 1 session, file_c in no session
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        file_a = omail["1"]
        file_b = get_object(oid="reponse2", ptype="dmsoutgoingmail")["1"]
        file_c = get_object(oid="reponse3", ptype="dmsoutgoingmail")["1"]

        signers = [("agent", "agent@macommune.be", u"Test Agent", u"Agent")]
        self.sid0, _session = create_session(signers)
        add_files_to_session(signers, [file_a.UID(), file_b.UID()], session_id=self.sid0)
        self.sid1, _session = create_session(signers)
        add_files_to_session(signers, [file_a.UID()], session_id=self.sid1)

        approval = OMApprovalAdapter(omail)
        approval.annot["session_ids"] = PersistentList([self.sid0, self.sid1])

        # 1 sign request, 1 file in 2 sessions discriminated on the sign_request portal_type
        sign_request, sr_files = create_sign_request(self.portal, oid="sr-session-id")
        self.sid2, _session = create_session(signers, discriminators=("sign_request",))
        add_files_to_session(signers, [sr_files[0].UID()], session_id=self.sid2)
        self.sid3, _session = create_session(signers, discriminators=("sign_request",))
        add_files_to_session(signers, [sr_files[0].UID()], session_id=self.sid3)
        sr_approval = SignRequestApprovalAdapter(sign_request)
        sr_approval.annot["session_ids"] = PersistentList([self.sid2, self.sid3])

        pc = api.portal.get_tool("portal_catalog")
        self.brain_a = pc(UID=file_a.UID())[0]  # in sid0 and sid1
        self.brain_b = pc(UID=file_b.UID())[0]  # in sid0 only
        self.brain_c = pc(UID=file_c.UID())[0]  # in no session
        self.brain_sr = pc(UID=sr_files[0].UID())[0]  # in sid2 and sid3
        self.table = OMVersionsTable(omail, self.portal.REQUEST, None)
        self.sr_table = SignRequestVersionsTable(sign_request, self.portal.REQUEST, None)
        self.column = SessionIdColumn(self.portal, self.portal.REQUEST, None)
        self.column.table = self.table

    def test_renderHeadCell(self):
        # relative image url (relies on <base>)
        self.assertEqual(
            self.column.renderHeadCell(),
            u'<img src="++resource++imio.esign/parapheo.svg" style="height:1em;vertical-align:middle"> ID',
        )

    def test_renderCell(self):
        """Empty for <=1 sessions; empty when file not in any session; single badge; comma-separated badges."""
        approval = self.table.approval

        # Guard: <=1 session_ids -> empty regardless of which file
        approval.annot["session_ids"] = PersistentList([])
        self.assertEqual(self.column.renderCell(self.brain_a), u"")
        approval.annot["session_ids"] = PersistentList([self.sid0])
        self.assertEqual(self.column.renderCell(self.brain_a), u"")
        approval.annot["session_ids"] = PersistentList([self.sid0, self.sid1])  # back to setUp

        # File not in any session -> empty
        self.assertEqual(self.column.renderCell(self.brain_c), u"")

        # File in exactly one of the two sessions -> one badge, no comma
        rendered = self.column.renderCell(self.brain_b)
        collection_uid = self.portal["outgoing-mail"]["mail-searches"]["in_esign_sessions"].UID()
        self.assertEqual(
            rendered,
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=0 "
            u'title="Paraphéo session ID: 0" class="pdf-session-badge">0</a>'.format(collection_uid),
        )

        # File in both sessions -> two badges, comma-separated, sorted by session id
        rendered = self.column.renderCell(self.brain_a)
        self.assertEqual(
            rendered,
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=0 "
            u'title="Paraphéo session ID: 0" class="pdf-session-badge">0</a>, '
            u"<a href=http://nohost/plone/outgoing-mail/mail-searches#c3=20&b_start=0&c1={}&esign_session_id=1 "
            u'title="Paraphéo session ID: 1" class="pdf-session-badge">1</a>'.format(collection_uid, collection_uid),
        )

        # Signing request table: approval and _session_annotation are inherited from OMVersionsTable parent
        # class, badges point to the requests dashboard
        self.column.table = self.sr_table
        sr_collection_uid = self.portal["requests"]["requests-searches"]["in_esign_sessions"].UID()
        self.assertEqual(
            self.column.renderCell(self.brain_sr),
            u"<a href=http://nohost/plone/requests/requests-searches#c3=20&b_start=0&c1={0}&esign_session_id={1} "
            u'title="Paraphéo session ID: {1}" class="pdf-session-badge">{1}</a>, '
            u"<a href=http://nohost/plone/requests/requests-searches#c3=20&b_start=0&c1={0}&esign_session_id={2} "
            u'title="Paraphéo session ID: {2}" class="pdf-session-badge">{2}</a>'.format(
                sr_collection_uid, self.sid2, self.sid3
            ),
        )
