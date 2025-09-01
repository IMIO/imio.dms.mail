# -*- coding: utf-8 -*-
""" settings tests for this package. """

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_person_from_userid
from dexterity.localrolesfield.utils import get_localrole_fields
from eea.facetednavigation.criteria.interfaces import ICriteria
from imio.dms.mail import _tr
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.content.behaviors import default_creating_group
from imio.dms.mail.Extensions.demo import activate_group_encoder
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.app.testing import logout
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.interfaces import IRegistry
from z3c.form import validator
from zope.component import getUtility
from zope.component import queryUtility
from zope.i18n import ITranslationDomain
from zope.interface import Invalid
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestSettings(unittest.TestCase, ImioTestHelpers):
    """Test imio.dms.mail settings."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        self.registry = getUtility(IRegistry)

    def test_validate_settings1(self):
        """Check invariant"""
        record_proxy = self.registry.forInterface(IImioDmsMailConfig)
        invariants = validator.InvariantsValidator(record_proxy, None, None, IImioDmsMailConfig, None)
        # test uniqueness
        data = {
            "mail_types": [
                {"dtitle": u"Job", "active": True, "value": u"job"},
                {"dtitle": u"Pub", "active": True, "value": u"pub"},
            ]
        }
        self.assertFalse(invariants.validate(data))
        data = {
            "mail_types": [
                {"dtitle": u"Job", "active": True, "value": u"job"},
                {"dtitle": u"Pub", "active": True, "value": u"job"},
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        # test omail_send_modes part
        data = {"omail_send_modes": [{"dtitle": u"Lettre", "active": True, "value": u"email"}]}
        self.assertFalse(invariants.validate(data))
        data = {"omail_send_modes": [{"dtitle": u"Lettre", "active": True, "value": u"bad"}]}
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = (u"Onglet « Courrier sortant »: le champ « Formes d'envoi » doit uniquement contenir des "
                     u"« valeurs stockées » commencant par « post », « email » ou « other »")
        self.assertEqual(_tr(errors[0].message), error_msg)
        # test imail_group_encoder
        rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder"
        api.portal.set_registry_record(rec, True)
        data = {"omail_send_modes": [], "imail_group_encoder": False}  # needs omail_send_modes !!
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = (
            u"Onglet « Courrier entrant »: décocher le paramètre « Activation de plusieurs groupes d'indicatage » n'"
            u"est pas prévu !"
        )
        self.assertEqual(
            _tr(errors[0].message, mapping={"tab": _tr("Incoming mail"), "field": _tr("Activate group encoder")}),
            error_msg,
        )

    def test_validate_settings2(self):
        """Check invariant"""
        record_proxy = self.registry.forInterface(IImioDmsMailConfig)
        invariants = validator.InvariantsValidator(record_proxy, None, None, IImioDmsMailConfig, None)
        # test mandatory fields
        im_flds = [
            "IDublinCore.title",
            "IDublinCore.description",
            "orig_sender_email",
            "sender",
            "treating_groups",
            "ITask.assigned_user",
            "recipient_groups",
            "reception_date",
            "mail_type",
            "reply_to",
            "internal_reference_no",
        ]
        om_flds = [
            "IDublinCore.title",
            "IDublinCore.description",
            "orig_sender_email",
            "recipients",
            "treating_groups",
            "ITask.assigned_user",
            "sender",
            "recipient_groups",
            "send_modes",
            "reply_to",
            "outgoing_date",
            "internal_reference_no",
            "email_status",
            "email_subject",
            "email_sender",
            "email_recipient",
            "email_cc",
            "email_bcc",
            "email_attachments",
            "email_body",
            "IDmsMailCreatingGroup.creating_group",
        ]
        data = {
            "omail_send_modes": [],
            "imail_fields": [{"field_name": fld} for fld in im_flds],
            "omail_fields": [{"field_name": fld} for fld in om_flds],
        }
        # required fields are there
        errors = invariants.validate(data)
        self.assertEqual(len(errors), 0)
        # missing one mandatory field
        removed = im_flds.pop()
        data["imail_fields"] = [{"field_name": fld} for fld in im_flds]
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        self.assertIn(u"Champs obligatoires manquants: ", errors[0].message)
        self.assertIn(u"courrier entrant", errors[0].message)
        self.assertIn(u"Référence interne", errors[0].message)
        # test positions
        im_flds.append(removed)
        # we change required position
        removed = im_flds.pop(1)
        im_flds.append(removed)
        data["imail_fields"] = [{"field_name": fld} for fld in im_flds]
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        self.assertIn(u"Position obligatoire pour les champs: ", errors[0].message)
        self.assertIn(u"courrier entrant", errors[0].message)
        self.assertIn(u"'Description': position 2.", errors[0].message)

    def test_settings_translations(self):
        # not needed anymore but kept as example
        domain = "imio.dms.mail"
        td = queryUtility(ITranslationDomain, domain)
        cat_name = td._catalogs.get("fr")[0]
        cat = td._data.get(cat_name)
        flds = ["zip_code"]
        missing = []
        for fld in flds:
            if cat.queryMessage(fld) is None:
                missing.append(fld)
        self.assertFalse(missing)

    def test_imiodmsmail_settings_changed(self):
        """Test some settings change"""
        # changing mail types
        key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types"
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.IMMailTypesVocabulary")
        self.assertEqual(len(voc_inst(self.portal)), 6)
        self.registry[key] += [{"value": u"new_type", "dtitle": u"New type", "active": True}]
        self.assertEqual(len(voc_inst(self.portal)), 7)

        # changing omail types
        key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types"
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.OMMailTypesVocabulary")
        self.assertEqual(len(voc_inst(self.portal)), 1)
        self.registry[key] += [{"value": u"new_type", "dtitle": u"New type", "active": True}]
        self.assertEqual(len(voc_inst(self.portal)), 2)

        # changing imail group encoder
        key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder"
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 3)
        self.registry[key] = True
        self.assertEqual(len(self.registry[FUNCTIONS_REGISTRY]), 4)

    def test_default_creating_group(self):
        self.change_user("agent")
        self.assertIsNone(default_creating_group())
        # we activate contact group encoder
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder", True)
        orgs = get_registry_organizations()
        # selected orgs
        # u'Direction générale', (u'Secrétariat', u'GRH', u'Communication')
        # u'Direction financière', (u'Budgets', u'Comptabilité')
        # u'Direction technique', (u'Bâtiments', u'Voiries')
        # u'Événements'
        functions = get_registry_functions()
        self.assertEqual(u"group_encoder", functions[-1]["fct_id"])
        self.assertIsNone(default_creating_group())
        # we configure the function orgs
        functions[-1]["fct_orgs"] = [orgs[1], orgs[2], orgs[3]]
        set_registry_functions(functions)
        self.assertIsNone(default_creating_group())
        # we add user in groups
        for org in functions[-1]["fct_orgs"]:
            api.group.add_user(groupname="{}_{}".format(org, CREATING_GROUP_SUFFIX), username="agent")
        self.assertEqual(default_creating_group(), orgs[3])  # primary org
        # user not in selected groups: no interaction
        self.assertEqual(default_creating_group(api.user.get(userid="agent1")), orgs[1])
        # we change the primary organization
        get_person_from_userid("agent").primary_organization = None
        self.assertEqual(default_creating_group(api.user.get(userid="agent")), orgs[1])
        # user logout
        logout()

    def test_configure_group_encoder(self):
        change_user(self.portal)
        # activate imail group encoder
        activate_group_encoder(self.portal)
        self.assertIn(CREATING_GROUP_SUFFIX, [fct["fct_id"] for fct in get_registry_functions()])
        for portal_type in ("dmsincomingmail", "dmsincoming_email"):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn("imio.dms.mail.content.behaviors.IDmsMailCreatingGroup", fti.behaviors)
            self.assertIn("creating_group", [tup[0] for tup in get_localrole_fields(fti)])
            self.assertTrue(fti.localroles.get("creating_group"))  # config dic not empty
        crit = ICriteria(self.portal["incoming-mail"]["mail-searches"])
        self.assertIn("c90", crit.keys())
        fields = api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields")
        self.assertIn("IDmsMailCreatingGroup.creating_group", [f["field_name"] for f in fields])

        # activate omail group encoder
        activate_group_encoder(self.portal, typ="omail")
        self.assertIn(CREATING_GROUP_SUFFIX, [fct["fct_id"] for fct in get_registry_functions()])
        # for portal_type in ('dmsoutgoingmail', 'dmsoutgoing_email'):
        for portal_type in ("dmsoutgoingmail",):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn("imio.dms.mail.content.behaviors.IDmsMailCreatingGroup", fti.behaviors, portal_type)
            self.assertIn("creating_group", [tup[0] for tup in get_localrole_fields(fti)], portal_type)
            self.assertTrue(fti.localroles.get("creating_group"), portal_type)  # config dic not empty
        crit = ICriteria(self.portal["outgoing-mail"]["mail-searches"])
        self.assertIn("c90", crit.keys())
        fields = api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields")
        self.assertIn("IDmsMailCreatingGroup.creating_group", [f["field_name"] for f in fields])

        # activate contact group encoder
        activate_group_encoder(self.portal, typ="contact")
        self.assertIn(CREATING_GROUP_SUFFIX, [fct["fct_id"] for fct in get_registry_functions()])
        self.assertIn(CONTACTS_PART_SUFFIX, [fct["fct_id"] for fct in get_registry_functions()])
        for portal_type in ("organization", "person", "held_position", "contact_list"):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn("imio.dms.mail.content.behaviors.IDmsMailCreatingGroup", fti.behaviors)
            self.assertIn("creating_group", [tup[0] for tup in get_localrole_fields(fti)])
        for fid in ("orgs-searches", "persons-searches", "hps-searches", "cls-searches"):
            crit = ICriteria(self.portal["contacts"][fid])
            self.assertIn("c90", crit.keys())
