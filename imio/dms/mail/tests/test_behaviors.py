# -*- coding: utf-8 -*-
from datetime import datetime
from imio.dms.mail import _tr
from imio.dms.mail.content.behaviors import ISigningBehavior
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from z3c.form import validator
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.interface import Interface
from zope.interface import Invalid
from zope.intid import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import modified

import unittest


class TestBehaviors(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.intids = getUtility(IIntIds)
        self.change_user("siteadmin")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.pf = self.portal["contacts"]["personnel-folder"]

    def test_signing_behavior(self):
        dirg = self.pf["dirg"]
        dirg_hp = dirg["directeur-general"]
        bourgmestre = self.pf["bourgmestre"]
        bourgmestre_hp = bourgmestre["bourgmestre"]
        omail = sub_create(
            self.portal["outgoing-mail"],
            "dmsoutgoingmail",
            datetime.now(),
            "my-id",
            title="My title",
            description="Description",
            send_modes=["post"],
            treating_groups=self.pgof["direction-generale"].UID(),
            mail_type="type1",
        )
        invariants = validator.InvariantsValidator(omail, None, None, ISigningBehavior, None)

        # Test base case, valid data
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                }
            ]
        }
        errors = invariants.validate(data)
        self.assertEqual(errors, ())

        # Test duplicate approver with themself
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_", dirg.UID()],
                    "number": 1,
                    "editor": True,
                }
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"La ligne 1 des signataires a un doublon d'approbateur avec lui-même."
        self.assertEqual(_tr(errors[0].message), error_msg)

        # Test duplicate approvers between signers
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": bourgmestre_hp.UID(),
                    "approvings": [dirg.UID()],
                    "number": 2,
                    "editor": True,
                },
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"L'utilisateur dirg existe déjà dans les approbateurs lignes 1 <=> 2"
        self.assertEqual(_tr(errors[0].message, mapping={"userid": "dirg", "o": "1", "c": "2"}), error_msg)

        # Test duplicate signing persons
        params = {
            "position": RelationValue(
                self.intids.getId(self.portal["contacts"]["plonegroup-organization"]["college-communal"])
            ),
            "usages": ["signer"],
        }
        dirg_hp2 = dirg.invokeFactory("held_position", "directeur-general-college-communal", **params)
        dirg_hp2 = dirg[dirg_hp2]
        modified(dirg_hp2, Attributes(Interface, "usages"))  # interface behavior
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": dirg_hp2.UID(),
                    "approvings": [u"_themself_"],
                    "number": 2,
                    "editor": True,
                },
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Vous ne pouvez pas avoir le m\xeame signataire plusieurs fois (Monsieur Maxime DG) !"
        self.assertEqual(_tr(errors[0].message, mapping={"signer_title": dirg_hp.get_person_title()}), error_msg)

        # Test duplicate emails in signers
        api.user.get("bourgmestre").setMemberProperties({"email": "duplicate@belleville.eb"})
        api.user.get("dirg").setMemberProperties({"email": "duplicate@belleville.eb"})
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": bourgmestre_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 2,
                    "editor": True,
                },
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Vous ne pouvez pas avoir le même email (duplicate@belleville.eb) pour plusieurs signataires !"
        self.assertEqual(_tr(errors[0].message, mapping={"email": "duplicate@belleville.eb"}), error_msg)

        # Test signer with no userid
        jeancourant_hp = self.portal["contacts"]["jeancourant"]["agent-electrabel"]
        data = {
            "signers": [
                {
                    "signer": jeancourant_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                }
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = (
            u"Le signataire 'Monsieur Jean Courant' n'a pas d'utilisateur Plone s\xe9lectionn\xe9 sur sa personne !"
        )
        self.assertEqual(_tr(errors[0].message, mapping={"signer_title": jeancourant_hp.get_person_title()}), error_msg)

        # Test signer with wrong uid
        data = {
            "signers": [
                {
                    "signer": u"wrong-uid",
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                }
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = (
            u"Le signataire avec la position occupée dont le UID est wrong-uid n'existe pas !"
        )
        self.assertEqual(_tr(errors[0].message, mapping={"uid": "wrong-uid"}), error_msg)

        # Test approver with wrong uid
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"wrong-uid"],
                    "number": 1,
                    "editor": True,
                }
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = (
            u"L'approbateur dont le UID de sa personne est wrong-uid n'existe pas !"
        )
        self.assertEqual(_tr(errors[0].message, mapping={"uid": "wrong-uid"}), error_msg)

        # Test duplicate numbers
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": bourgmestre_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Vous ne pouvez pas avoir le même numéro pour plusieurs signataires !"
        self.assertEqual(_tr(errors[0].message), error_msg)

        # Test missing numbers in sequence
        bourgmestre = self.portal["contacts"]["personnel-folder"]["bourgmestre"]
        bourgmestre_hp = bourgmestre["bourgmestre"]
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": bourgmestre_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 3,
                    "editor": True,
                },
            ]
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Un signataire est manquant aux positions 2 !"
        self.assertEqual(_tr(errors[0].message, mapping={"positions": "2"}), error_msg)

        # Test no approvings with esign activated
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_empty_"],
                    "number": 1,
                    "editor": True,
                },
            ],
            "esign": True,
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        self.assertEqual(_tr(errors[0].message), u"Vous devez définir des approbateurs pour chaque signataire si "
                                                 u"la signature électronique est utilisée !")

        # Test no approvings with esign deactivated
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_empty_"],
                    "number": 1,
                    "editor": True,
                },
            ],
            "esign": False,
        }
        errors = invariants.validate(data)
        self.assertEqual(errors, ())

        # Test no approvings and approvings mixed
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_empty_"],
                    "number": 1,
                    "editor": True,
                },
                {
                    "signer": bourgmestre_hp.UID(),
                    "approvings": [dirg.UID()],
                    "number": 2,
                    "editor": True,
                },
            ],
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Vous ne pouvez pas avoir des lignes avec des approbateurs parfois vides, parfois non !"
        self.assertEqual(_tr(errors[0].message), error_msg)

        # Test seal with no esign activated
        data = {
            "signers": [
                {
                    "signer": dirg_hp.UID(),
                    "approvings": [u"_themself_"],
                    "number": 1,
                    "editor": True,
                },
            ],
            "esign": False,
            "seal": True,
        }
        errors = invariants.validate(data)
        self.assertTrue(isinstance(errors[0], Invalid))
        error_msg = u"Vous ne pouvez pas avoir de cachet et de signataire sans cocher 'Signature élec.' !"
        self.assertEqual(_tr(errors[0].message), error_msg)
