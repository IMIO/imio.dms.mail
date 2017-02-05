# -*- coding: utf-8 -*-
""" dmsfile.py tests for this package."""
import unittest

from zope.component import getUtility
from zope.interface import Invalid

from plone import api
from plone.namedfile.file import NamedBlobFile
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry

import imio.dms.mail as imiodmsmail
from ..dmsfile import RestrictedNamedBlobFile
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING


class TestDmsfile(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pc = self.portal.portal_catalog
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def test_RestrictedNamedBlobFile(self):
        path = "%s/batchimport/toprocess/outgoing-mail/Accusé de réception.odt" % imiodmsmail.__path__[0]
        odtfile = file(path, 'rb')
        odtblob = NamedBlobFile(data=odtfile.read(), filename=u'file.odt')
        odtfile.close()
        path = "%s/configure.zcml" % imiodmsmail.__path__[0]
        otherfile = file(path, 'rb')
        otherblob = NamedBlobFile(data=otherfile.read(), filename=u'file.txt')
        otherfile.close()
        registry = getUtility(IRegistry)
        # check content type
        self.assertEqual(get_contenttype(odtblob), 'application/vnd.oasis.opendocument.text')
        self.assertEqual(get_contenttype(otherblob), 'text/plain')
        field = RestrictedNamedBlobFile()
        # with om context and good file
        field.context = self.omf.reponse1['1']
        field._validate(odtblob)
        # with bad file
        self.assertRaises(Invalid, field._validate, otherblob)
        # bad file, validation deactivated
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'] = False
        field._validate(otherblob)
        # bad file with im context
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile'] = True
        field.context = self.imf.courrier1.dmsmainfile
        field._validate(otherblob)
