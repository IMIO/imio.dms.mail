# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from collective.dms.basecontent.browser.listing import CategorizedContent
from collective.dms.basecontent.browser.listing import VersionsTable
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.table import AssignedGroupColumn
from imio.dms.mail.browser.table import IMVersionsTitleColumn
from imio.dms.mail.browser.views import ApprovalTableView
from imio.dms.mail.Extensions.demo import activate_signing
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestTable(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_VersionsTitleColumn(self):
        category = self.portal["annexes_types"]["incoming_dms_files"]["incoming-dms-file"]
        icon_name = category.unrestrictedTraverse('@@images').scale(scale='listing').__name__
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file1 = createContentInContainer(
                imail,
                "dmsmainfile",
                id="testid1",
                title="title",
                scan_id="123456789",
                content_category=calculate_category_id(category),
                file=NamedBlobFile(
                    fo.read(),
                    filename=filename,
                ),
            )
        # Cannot use scan_date because toLocalizedTime causes error in test
        brains = self.portal.portal_catalog(portal_type="dmsmainfile", id="testid1")
        self.assertEqual(len(brains), 1)
        table = VersionsTable(imail, self.portal.REQUEST, "dmsmainfile")
        col = IMVersionsTitleColumn(self.portal, self.portal.REQUEST, table)
        cc = CategorizedContent(imail, brains[0])
        formatted_date = cc.toLocalizedTime(cc.creation_date, long_format=1)
        self.assertEqual(col.getLinkTitle(cc),
                         u"⏺ Nom du fichier = Réponse salle.odt\n⏺ Identifiant de scan = 123456789\n"
                         u"⏺ Date de création = {}".format(formatted_date))
        self.assertEqual(
            col.renderCell(cc),
            u'<a class="version-link" href="{0}" alt="⏺ Nom du fichier = Réponse salle.odt\n⏺ Identifiant de scan = '
            u'123456789\n⏺ Date de création = {1}" title="⏺ Nom du fichier = Réponse salle.odt\n⏺ Identifiant de scan ='
            u' 123456789\n⏺ Date de création = {1}">'
            u'<img src="annexes_types/incoming_dms_files/incoming-dms-file/@@images/{2}" '
            u'alt="Fichier ged CE" title="Fichier ged CE" /> '
            u'title</a><p class="discreet"></p>'.format(file1.absolute_url(), formatted_date, icon_name)
        )

    def test_AssignedGroupColumn(self):
        group0 = get_registry_organizations()[0]
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        task = createContentInContainer(imail, "task", id="testid1", assigned_group=group0)
        col = AssignedGroupColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.renderCell(task).encode("utf8"), "Direction générale")

    def test_ApprovalTable(self):
        activate_signing(self.portal)

        # Create outgoing mail with two eSign signers and two files to approve
        intids = getUtility(IIntIds)
        pgof = self.portal["contacts"]["plonegroup-organization"]
        pf = self.portal["contacts"]["personnel-folder"]
        params = {
            "title": u"Courrier sortant test",
            "internal_reference_no": internalReferenceOutgoingMailDefaultValue(
                DummyView(self.portal, self.portal.REQUEST)
            ),
            "mail_type": "courrier",
            "treating_groups": pgof["direction-generale"]["grh"].UID(),
            "recipients": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "assigned_user": "agent",
            "sender": self.portal["contacts"]["jeancourant"]["agent-electrabel"].UID(),
            "send_modes": u"post",
            "signers": [
                {
                    "number": 1,
                    "signer": pf["dirg"]["directeur-general"].UID(),
                    "approvings": [u"_themself_"],
                    "editor": True,
                },
                {
                    "number": 2,
                    "signer": pf["bourgmestre"]["bourgmestre"].UID(),
                    "approvings": [u"_themself_", pf["chef"].UID()],
                    "editor": False,
                },
            ],
            "esign": True,
        }
        omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "om", **params)

        filename = u"Réponse salle.odt"
        ct = self.portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
        files = []
        for i in range(2):
            with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                files.append(
                    createContentInContainer(
                        omail,
                        "dmsommainfile",
                        id="file%s" % i,
                        scan_id="012999900000601",
                        file=file_object,
                        content_category=calculate_category_id(ct),
                    )
                )

        view = ApprovalTableView(
            omail,
            omail.REQUEST,
        )
        view.update()
        table = view.table

        # Test table
        self.assertEqual(len(table.columns), 3)
        self.assertEqual(table.values, files)

        # Test column FileName
        filename_col = table.columns[0]
        self.assertEqual(filename_col.header, u"File name")
        self.assertEqual(filename_col.renderCell(files[0]), u"R\xe9ponse salle.odt")
        self.assertEqual(filename_col.renderCell(files[1]), u"R\xe9ponse salle.odt")

        # Test column Signer
        signer_col1 = table.columns[1]
        self.assertEqual(signer_col1.header, u"Maxime DG")
        self.assertEqual(signer_col1.userid, "dirg")
        self.assertEqual(
            signer_col1.renderCell(files[0]), u'<input type="checkbox" name="approvals.%s.dirg"  />' % files[0].UID()
        )
        self.assertEqual(
            signer_col1.renderCell(files[1]), u'<input type="checkbox" name="approvals.%s.dirg"  />' % files[1].UID()
        )

        signer_col2 = table.columns[2]
        self.assertEqual(signer_col2.header, u"Paul BM")
        self.assertEqual(signer_col2.userid, "bourgmestre")
        self.assertEqual(
            signer_col2.renderCell(files[0]),
            u'<input type="checkbox" name="approvals.%s.bourgmestre"  />' % files[0].UID(),
        )
        self.assertEqual(
            signer_col2.renderCell(files[1]),
            u'<input type="checkbox" name="approvals.%s.bourgmestre"  />' % files[1].UID(),
        )

        api.content.transition(obj=omail, transition="propose_to_approve")
        table.approval.approve_file(files[0], "dirg")
        self.assertEqual(
            signer_col1.renderCell(files[0]),
            u'<input type="checkbox" name="approvals.%s.dirg" checked="checked" />' % files[0].UID(),
        )

        # Test form
        self.assertTrue(table.approval.is_file_approved(files[0].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[1].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[0].UID(), nb=1))
        self.assertFalse(table.approval.is_file_approved(files[1].UID(), nb=1))

        # Approve more files
        form_data = {
            "form.button.Save": "Save",
            "approvals.%s.dirg" % files[0].UID(): "on",
            "approvals.%s.dirg" % files[1].UID(): "on",
            # bourgmestre checkbox not checked for file[0]
            "approvals.%s.bourgmestre" % files[1].UID(): "on",
        }
        table.request.form = form_data
        view()
        self.assertTrue(table.approval.is_file_approved(files[0].UID(), nb=0))
        self.assertTrue(table.approval.is_file_approved(files[1].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[0].UID(), nb=1))
        self.assertTrue(table.approval.is_file_approved(files[1].UID(), nb=1))

        # Unapprove files in a weird pattern
        form_data = {
            "form.button.Save": "Save",
            "approvals.%s.dirg" % files[0].UID(): "on",
            # dirg checkbox not checked for file[1]
            # bourgmestre checkbox not checked for file[0]
            "approvals.%s.bourgmestre" % files[1].UID(): "on",
        }
        table.request.form = form_data
        view()
        self.assertTrue(table.approval.is_file_approved(files[0].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[1].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[0].UID(), nb=1))
        self.assertTrue(table.approval.is_file_approved(files[1].UID(), nb=1))

        # Cancel form
        form_data = {
            "form.button.Cancel": "Cancel",
            "approvals.%s.dirg" % files[0].UID(): "on",
            "approvals.%s.dirg" % files[1].UID(): "on",
            "approvals.%s.bourgmestre" % files[0].UID(): "on",
            "approvals.%s.bourgmestre" % files[1].UID(): "on",
        }
        table.request.form = form_data
        view()
        self.assertTrue(table.approval.is_file_approved(files[0].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[1].UID(), nb=0))
        self.assertFalse(table.approval.is_file_approved(files[0].UID(), nb=1))
        self.assertTrue(table.approval.is_file_approved(files[1].UID(), nb=1))
