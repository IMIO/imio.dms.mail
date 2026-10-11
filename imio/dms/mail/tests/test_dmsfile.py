# -*- coding: utf-8 -*-
""" dmsfile.py tests for this package."""
from datetime import datetime
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.dmsfile import AnnexAddForm
from imio.dms.mail.dmsfile import AppendixFileAddForm
from imio.dms.mail.dmsfile import RestrictedNamedBlobFile
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.interface import Invalid

import imio.dms.mail as imiodmsmail
import os
import unittest


class TestDmsfile(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pc = self.portal.portal_catalog
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.imail = sub_create(self.imf, "dmsincomingmail", datetime.now(), "my-id")

    def test_RestrictedNamedBlobFile(self):
        path = "%s/batchimport/toprocess/outgoing-mail/Accusé de réception.odt" % imiodmsmail.__path__[0]
        odtfile = file(path, "rb")  # noqa F821
        odtblob = NamedBlobFile(data=odtfile.read(), filename=u"file.odt")
        odtfile.close()
        path = os.path.join(os.path.dirname(__file__), "files", "example.pdf")
        otherfile = file(path, "rb")  # noqa F821
        otherblob = NamedBlobFile(data=otherfile.read(), filename=u"file.pdf")
        otherfile.close()
        registry = getUtility(IRegistry)
        # check content type
        self.assertEqual(get_contenttype(odtblob), "application/vnd.oasis.opendocument.text")
        self.assertEqual(get_contenttype(otherblob), "application/pdf")
        field = RestrictedNamedBlobFile()
        # with om context and good file
        field.context = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        field._validate(odtblob)
        # with bad file
        self.assertRaises(Invalid, field._validate, otherblob)
        # bad file, validation adapted
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_formats_mainfile"] = ["odt", "pdf"]
        field._validate(otherblob)

    def test_AppendixFileAddForm(self):
        # the annex form shows one title field and does not require it (DMS-1217, DMS-605)
        form = AppendixFileAddForm(self.imail, self.portal.REQUEST)
        form.update()
        self.assertNotIn("IBasic.title", form.widgets)
        self.assertEqual(form.widgets["title"].mode, "input")
        self.assertFalse(form.widgets["title"].field.required)
        self.assertEqual(form.widgets["description"].mode, "hidden")
        # after adding, the user goes back to the mail
        self.assertEqual(form.nextURL(), self.imail.absolute_url())

    def test_AnnexAddForm(self):
        folder = api.content.find(portal_type="ClassificationFolder")[0].getObject()
        form = AnnexAddForm(folder, self.portal.REQUEST)
        # after adding, the user goes back to the folder
        self.assertEqual(form.nextURL(), folder.absolute_url())

    def _om_file(self, filename):
        """Add an outgoing mail main file from the batchimport examples."""
        omail = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        with open(u"{}/batchimport/toprocess/{}".format(PRODUCT_DIR, filename), "rb") as fo:
            return createContentInContainer(
                omail, "dmsommainfile", title=u"Réponse", file=NamedBlobFile(fo.read(), filename=filename.split(u"/")[-1])
            )

    def test_ImioDmsFile_Title(self):
        self.assertEqual(self._om_file(u"outgoing-mail/Réponse salle.odt").Title(), u"Réponse")

    def test_ImioDmsFile_getFile(self):
        afile = self._om_file(u"outgoing-mail/Réponse salle.odt")
        self.assertIs(afile.getFile(), afile.file)

    def test_ImioDmsFile_is_odt(self):
        self.assertTrue(self._om_file(u"outgoing-mail/Réponse salle.odt").is_odt())
        self.assertFalse(self._om_file(u"requests/1-contestation-facture.pdf").is_odt())
