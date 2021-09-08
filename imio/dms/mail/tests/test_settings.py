# -*- coding: utf-8 -*-
""" settings tests for this package. """

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import get_registry_functions
from dexterity.localrolesfield.utils import get_localrole_fields
from eea.facetednavigation.criteria.interfaces import ICriteria
from imio.dms.mail import _tr
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.Extensions.demo import activate_group_encoder
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.interfaces import IRegistry
from z3c.form import validator
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

    def test_validate_settings(self):
        """ Check invariant """
        invariants = validator.InvariantsValidator(None, None, None, IImioDmsMailConfig, None)
        # test omail_send_modes part
        data = {'omail_send_modes': [{'dtitle': u'Lettre', 'active': True, 'value': u'email'}]}
        self.assertFalse(invariants.validate(data))
        data = {'omail_send_modes': [{'dtitle': u'Lettre', 'active': True, 'value': u'bad'}]}
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = _tr(msgid=u"Outgoingmail tab: send_modes field must have values starting with 'post' or 'email'")
        self.assertEqual(_tr(errors[0].message), error_msg)
        # test imail_group_encoder
        rec = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'
        api.portal.set_registry_record(rec, True)
        data = {'omail_send_modes': [], 'imail_group_encoder': False}  # needs omail_send_modes !!
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Courrier entrant: décocher le paramètre 'Activation de plusieurs groupes d'indicatage' n'est " \
                    u"pas prévu !"
        self.assertEqual(_tr(errors[0].message, mapping={'tab': _tr('Incoming mail'),
                                                         'field': _tr('Activate group encoder')}), error_msg)

    def test_imiodmsmail_settings_changed(self):
        """ Test some settings change """
        # changing mail types
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')
        self.assertEqual(len(voc_inst(self.portal)), 6)
        self.registry[key] += [{'value': u'new_type', 'dtitle': u'New type', 'active': True}]
        self.assertEqual(len(voc_inst(self.portal)), 7)

        # changing omail types
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types'
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.OMMailTypesVocabulary')
        self.assertEqual(len(voc_inst(self.portal)), 1)
        self.registry[key] += [{'value': u'new_type', 'dtitle': u'New type', 'active': True}]
        self.assertEqual(len(voc_inst(self.portal)), 2)

        # changing imail group encoder
        key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 3)
        self.registry[key] = True
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 4)

    def test_configure_group_encoder(self):
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        # activate imail group encoder
        activate_group_encoder(self.portal)
        self.assertIn(CREATING_GROUP_SUFFIX, [fct['fct_id'] for fct in get_registry_functions()])
        for portal_type in ('dmsincomingmail', 'dmsincoming_email'):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('imio.dms.mail.content.behaviors.IDmsMailCreatingGroup', fti.behaviors)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)])
            self.assertTrue(fti.localroles.get('creating_group'))  # config dic not empty
        crit = ICriteria(self.portal['incoming-mail']['mail-searches'])
        self.assertIn('c90', crit.keys())

        # activate omail group encoder
        activate_group_encoder(self.portal, typ='omail')
        self.assertIn(CREATING_GROUP_SUFFIX, [fct['fct_id'] for fct in get_registry_functions()])
        # for portal_type in ('dmsoutgoingmail', 'dmsoutgoing_email'):
        for portal_type in ('dmsoutgoingmail', ):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('imio.dms.mail.content.behaviors.IDmsMailCreatingGroup', fti.behaviors, portal_type)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)], portal_type)
            self.assertTrue(fti.localroles.get('creating_group'), portal_type)  # config dic not empty
        crit = ICriteria(self.portal['outgoing-mail']['mail-searches'])
        self.assertIn('c90', crit.keys())

        # activate contact group encoder
        activate_group_encoder(self.portal, typ='contact')
        self.assertIn(CREATING_GROUP_SUFFIX, [fct['fct_id'] for fct in get_registry_functions()])
        self.assertIn(CONTACTS_PART_SUFFIX, [fct['fct_id'] for fct in get_registry_functions()])
        for portal_type in ('organization', 'person', 'held_position', 'contact_list'):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('imio.dms.mail.content.behaviors.IDmsMailCreatingGroup', fti.behaviors)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)])
        for fid in ('orgs-searches', 'persons-searches', 'hps-searches', 'cls-searches'):
            crit = ICriteria(self.portal['contacts'][fid])
            self.assertIn('c90', crit.keys())
