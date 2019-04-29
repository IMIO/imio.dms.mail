# -*- coding: utf-8 -*-
""" settings tests for this package. """

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.interface import Invalid
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestSettings(unittest.TestCase):
    """Test imio.dms.mail settings."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.registry = getUtility(IRegistry)

    def test_imiodmsmail_settings_changed(self):
        """ Test some settings change """
        # changing mail types
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')
        self.assertEqual(len(voc_inst(self.portal)), 7)
        self.registry[key] += [{'mt_value': u'new_type', 'mt_title': u'New type', 'mt_active': True}]
        self.assertEqual(len(voc_inst(self.portal)), 8)

        # changing omail types
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.OMMailTypesVocabulary')
        self.assertEqual(len(voc_inst(self.portal)), 2)
        self.registry[key] += [{'mt_value': u'new_type', 'mt_title': u'New type', 'mt_active': True}]
        self.assertEqual(len(voc_inst(self.portal)), 3)

        # changing imail group encoder
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 4)
        self.registry[key] = True
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 5)
        with self.assertRaises(Invalid) as cm:
            self.registry[key] = False
        self.assertEqual(cm.exception.message, u'Unchecking the imail_group_encoder setting is not expected !!')
