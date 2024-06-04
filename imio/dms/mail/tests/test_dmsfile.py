# -*- coding: utf-8 -*-
""" dmsfile.py tests for this package."""
from imio.dms.mail.dmsfile import RestrictedNamedBlobFile
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.interface import Invalid

import imio.dms.mail as imiodmsmail
import unittest


class TestDmsfile(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.pc = self.portal.portal_catalog
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]

    def test_RestrictedNamedBlobFile(self):
        path = "%s/batchimport/toprocess/outgoing-mail/Accusé de réception.odt" % imiodmsmail.__path__[0]
        odtfile = file(path, "rb")
        odtblob = NamedBlobFile(data=odtfile.read(), filename=u"file.odt")
        odtfile.close()
        path = "%s/configure.zcml" % imiodmsmail.__path__[0]
        otherfile = file(path, "rb")
        otherblob = NamedBlobFile(data=otherfile.read(), filename=u"file.txt")
        otherfile.close()
        registry = getUtility(IRegistry)
        # check content type
        self.assertEqual(get_contenttype(odtblob), "application/vnd.oasis.opendocument.text")
        self.assertEqual(get_contenttype(otherblob), "text/plain")
        field = RestrictedNamedBlobFile()
        # with om context and good file
        field.context = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        field._validate(odtblob)
        # with bad file
        self.assertRaises(Invalid, field._validate, otherblob)
        # bad file, validation deactivated
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile"] = False
        field._validate(otherblob)
