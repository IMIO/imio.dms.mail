# -*- coding: utf-8 -*-
from imio.dms.mail.browser.tabular_view import TabularView
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone.app.contentlisting.interfaces import IContentListingObject

import unittest


class TestTabularView(unittest.TestCase):
    """TabularView is registered for plone.app.collection (AT) collections only."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.collection = self.portal["incoming-mail"]["mail-searches"]["all_mails"]
        self.view = TabularView(self.collection, self.portal.REQUEST)
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.brain = self.portal.portal_catalog(UID=self.im1.UID())[0]
        self.item = IContentListingObject(self.brain)  # as given by context.results() in the template

    def test_from_vocabulary(self):
        voc_name = "collective.dms.basecontent.treating_groups"
        self.assertEqual(self.view.from_vocabulary(self.brain, self.pgof["direction-generale"].UID(), voc_name),
                         u"Direction générale")
        self.assertEqual(
            self.view.from_vocabulary(
                self.brain, [self.pgof["direction-generale"].UID(), self.pgof["evenements"].UID()], voc_name
            ),
            u"Direction générale<br />Événements",
        )

    def test_render_field(self):
        self.assertEqual(
            self.view.render_field(("Title", u"Title"), self.item),
            '<a href="{}" class="state-created">E0001 - Courrier 1</a>'.format(self.im1.absolute_url()),
        )
        self.assertEqual(self.view.render_field(("review_state", u"State"), self.item), u"En création")
        self.assertEqual(self.view.render_field(("Creator", u"Creator"), self.item), "<span>admin</span>")
        self.assertEqual(self.view.render_field(("treating_groups", u"Treating"), self.item),
                         u"Direction générale")
        self.assertEqual(self.view.render_field(("recipient_groups", u"Recipients"), self.item), "")
        self.assertEqual(
            self.view.render_field(("CreationDate", u"Created"), self.item),
            "<span>{}</span>".format(self.view.plone.toLocalizedTime(self.brain.CreationDate, long_format=1)),
        )
        self.assertEqual(self.view.render_field(("mail_type", u"Type"), self.item), "courrier")
        # locked mail in the "created" search: skin lock icon
        created = [b.getObject() for b in self.portal.portal_catalog(id="searchfor_created")][0]
        view = TabularView(created, self.portal.REQUEST)
        self.im1.restrictedTraverse("lock-unlock")()
        self.assertEqual(
            view.render_field(("Title", u"Title"), self.item),
            '<img width="16" height="16" title="Locked" src="lock_icon.png">'
            '<a href="{}" class="state-created">E0001 - Courrier 1</a>'.format(self.im1.absolute_url()),
        )
