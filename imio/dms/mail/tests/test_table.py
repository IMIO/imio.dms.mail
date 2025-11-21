# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from collective.dms.basecontent.browser.listing import CategorizedContent
from collective.dms.basecontent.browser.listing import VersionsTable
from collective.iconifiedcategory.utils import calculate_category_id
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.browser.table import AssignedGroupColumn
from imio.dms.mail.browser.table import IMVersionsTitleColumn
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile

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
            createContentInContainer(
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
        self.assertEqual(col.getLinkTitle(cc), u"Identifiant de scan: 123456789\nDate de scan: \nVersion: ")
        self.assertEqual(
            col.renderCell(cc),
            u'<a class="version-link" href="http://nohost/plone/incoming-mail/202546/my-id/testid1" '
            u'alt="Identifiant de scan: 123456789\nDate de scan: \nVersion: " title="Identifiant de '
            u'scan: 123456789\nDate de scan: \nVersion: "><img src="annexes_types/incoming_dms_files'
            u'/incoming-dms-file/@@images/%s" alt="Incoming DMS File" title="Incoming DMS File" /> '
            u'E0010 - </a><p class="discreet"></p>' % icon_name
        )

    def test_AssignedGroupColumn(self):
        group0 = get_registry_organizations()[0]
        imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        task = createContentInContainer(imail, "task", id="testid1", assigned_group=group0)
        col = AssignedGroupColumn(self.portal, self.portal.REQUEST, None)
        self.assertEqual(col.renderCell(task).encode("utf8"), "Direction générale")
