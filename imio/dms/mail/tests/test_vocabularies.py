# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_person_from_userid
from datetime import datetime
from imio.dms.mail import _tr
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.browser.settings import configure_group_encoder
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.utils import sub_create
from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
from imio.dms.mail.vocabularies import AssignedUsersForFacetedFilterVocabulary
from imio.dms.mail.vocabularies import AssignedUsersWithDeactivatedVocabulary
from imio.dms.mail.vocabularies import CreatingGroupVocabulary
from imio.dms.mail.vocabularies import DmsFilesCategoryVocabulary
from imio.dms.mail.vocabularies import encodeur_active_orgs
from imio.dms.mail.vocabularies import get_settings_vta_table
from imio.dms.mail.vocabularies import IMReviewStatesVocabulary
from imio.dms.mail.vocabularies import MyLabelsVocabulary
from imio.dms.mail.vocabularies import OMActiveMailTypesVocabulary
from imio.dms.mail.vocabularies import OMActiveSenderVocabulary
from imio.dms.mail.vocabularies import OMMailTypesVocabulary
from imio.dms.mail.vocabularies import OMSenderVocabulary
from imio.dms.mail.vocabularies import PloneGroupInterfacesVocabulary
from imio.dms.mail.vocabularies import TaskReviewStatesVocabulary
from imio.helpers import EMPTY_STRING
from imio.helpers import EMPTY_TITLE
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestVocabularies(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        self.imail = sub_create(self.portal["incoming-mail"], "dmsincomingmail", datetime.now(), "my-id")
        self.omail = sub_create(self.portal["outgoing-mail"], "dmsoutgoingmail", datetime.now(), "my-id", title=u"OM1")
        self.maxDiff = None

    def test_IMReviewStatesVocabulary(self):
        voc_inst = IMReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(
            voc_list,
            [
                ("created", u"En création"),
                ("proposed_to_manager", u"À valider par le DG"),
                ("proposed_to_agent", u"À traiter"),
                ("in_treatment", u"En cours de traitement"),
                ("closed", u"Clôturé"),
            ],
        )

    def test_TaskReviewStatesVocabulary(self):
        voc_inst = TaskReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(
            voc_list,
            [
                ("created", u"Created"),
                ("to_assign", u"To assign"),
                ("to_do", u"To do"),
                ("in_progress", u"In progress"),
                ("realized", u"Realized"),
                ("closed", u"Closed"),
            ],
        )

    def test_AssignedUsersWithDeactivatedVocabulary(self):
        voc_inst = AssignedUsersWithDeactivatedVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )
        # add inactive group and user in it
        guid = self.portal.contacts["plonegroup-organization"]["departement-culturel"].UID()
        new_group = api.group.create("{}_lecteur".format(guid))
        api.group.add_user(group=new_group, username="test-user")
        self.change_user("siteadmin")  # refresh getGroups
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )
        # add same user in active group
        guid = self.portal.contacts["plonegroup-organization"][u"direction-generale"].UID()
        api.group.add_user(groupname="{}_lecteur".format(guid), username="test-user")
        self.change_user("siteadmin")  # refresh getGroups
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("scanner", u"Scanner"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user"),
            ],
        )

    def test_AssignedUsersForFacetedFilterVocabulary(self):
        voc_inst = AssignedUsersForFacetedFilterVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
                ("agent", u"Fred Agent"),
                ("encodeur", u"Jean Encodeur"),
                ("lecteur", u"Jef Lecteur"),
                ("dirg", u"Maxime DG"),
                ("chef", u"Michel Chef"),
                ("bourgmestre", u"Paul BM"),
                ("siteadmin", u"siteadmin"),
                ("agent1", u"Stef Agent"),
                ("test-user", u"test-user (Désactivé)"),
            ],
        )

    def test_get_settings_vta_table(self):
        voc_list = [(t.value, t.title) for t in get_settings_vta_table("mail_types")]
        self.assertEquals(
            voc_list,
            [
                (u"courrier", u"Courrier"),
                (u"recommande", u"Recommandé"),
                (u"certificat", u"Certificat médical"),
                (u"fax", u"Fax"),
                (u"retour-recommande", u"Retour recommandé"),
                (u"facture", u"Facture"),
            ],
        )
        voc_list = [(t.value, t.title) for t in get_settings_vta_table("omail_send_modes", choose=True)]
        self.assertEqual(voc_list[0], (None, "Choose a value !"))
        voc_list = [(t.value, t.title) for t in get_settings_vta_table("omail_send_modes", active=(False,))]
        self.assertTrue(len(voc_list) == 0)
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes",
            [
                {"value": u"none", "dtitle": u"Travaille fieu", "active": True},
                {"value": u"post", "dtitle": u"Lettre", "active": False},
                {"value": u"post_registered", "dtitle": u"Lettre recommandée", "active": True},
                {"value": u"email", "dtitle": u"Email", "active": True},
            ],
        )
        voc_list = [(t.value, t.title) for t in get_settings_vta_table("omail_send_modes", choose=True)]
        self.assertEqual(voc_list[0], (None, u"Travaille fieu"))
        voc_list = [(t.value, t.title) for t in get_settings_vta_table("omail_send_modes", active=(False,))]
        self.assertTrue(len(voc_list) == 1)

    def test_IMMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.IMMailTypesVocabulary")
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                (u"courrier", u"Courrier"),
                (u"recommande", u"Recommandé"),
                (u"certificat", u"Certificat médical"),
                (u"fax", u"Fax"),
                (u"retour-recommande", u"Retour recommandé"),
                (u"facture", u"Facture"),
            ],
        )

    def test_IMActiveMailTypesVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, "imio.dms.mail.IMActiveMailTypesVocabulary")
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list, [None, u"courrier", u"recommande", u"certificat", u"fax", u"retour-recommande", u"facture"]
        )
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]["active"] = False
        settings.mail_types = mail_types
        # After a registry change, the vocabulary cache has been cleared
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [None, u"recommande", u"certificat", u"fax", u"retour-recommande", u"facture"])

    def test_PloneGroupInterfacesVocabulary(self):
        voc_inst = PloneGroupInterfacesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(
            voc_list,
            [
                ("collective.contact.plonegroup.interfaces.IPloneGroupContact", "IPloneGroupContact"),
                ("collective.contact.plonegroup.interfaces.INotPloneGroupContact", "INotPloneGroupContact"),
                ("imio.dms.mail.interfaces.IPersonnelContact", "IPersonnelContact"),
            ],
        )

    def test_OMActiveSenderVocabulary(self):
        voc_inst = OMActiveSenderVocabulary()
        self.assertEqual(len(voc_inst(self.omail)), 23)
        # get first part, as unique value, keeping order
        res = OrderedDict.fromkeys([" ".join(s.title.split()[:3]).strip(",") for s in voc_inst(self.omail)]).keys()
        # res is sorted by firstname
        self.assertEqual(
            res, [u"Monsieur Fred Agent", u"Monsieur Jean Encodeur", u"Monsieur Michel Chef", u"Monsieur Stef Agent"]
        )
        api.portal.set_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_sender_firstname_sorting", False
        )
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMActiveSenderVocabulary")
        res = OrderedDict.fromkeys([" ".join(s.title.split()[:3]).strip(",") for s in voc_inst(self.omail)]).keys()
        # res is sorted by lastname
        self.assertEqual(
            res, [u"Monsieur Fred Agent", u"Monsieur Stef Agent", u"Monsieur Michel Chef", u"Monsieur Jean Encodeur"]
        )
        # deactivation
        pf = self.portal.contacts["personnel-folder"]
        api.content.transition(obj=pf["agent"]["agent-grh"], transition="deactivate")
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMActiveSenderVocabulary")
        self.assertEqual(len(voc_inst(self.omail)), 22)
        # full sender vocabulary
        voc_all_inst = OMSenderVocabulary()
        self.assertEqual(len(voc_all_inst(self.omail)), 34)

    def test_OMMailTypesVocabulary(self):
        voc_inst = OMMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u"courrier"])

    def test_OMActiveMailTypesVocabulary(self):
        voc_inst = OMActiveMailTypesVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, [u"courrier"])

    def test_encodeur_active_orgs0(self):
        factory = getUtility(IVocabularyFactory, u"collective.dms.basecontent.treating_groups")
        all_titles = [t.title for t in factory(self.omail)]
        # expedition group or Manager
        self.change_user("encodeur")
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
        self.change_user("admin")
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
        # normal user
        self.change_user("agent")
        # omail context but state not created
        with api.env.adopt_roles(["Manager"]):
            self.omail.treating_groups = get_registry_organizations()[1]  # secretariat
            api.content.transition(obj=self.omail, transition="mark_as_sent")
        self.assertEqual(api.content.get_state(self.omail), "sent")
        self.assertListEqual([t.title for t in encodeur_active_orgs(self.omail)], all_titles)
        # omail context with created state
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=self.omail, transition="back_to_creation")
        self.assertEqual(api.content.get_state(self.omail), "created")
        # agent primary organization first (communication)
        self.assertListEqual(
            [t.title for t in encodeur_active_orgs(self.omail)],
            [all_titles[3]] + [t for i, t in enumerate(all_titles) if i not in (0, 3, 4, 7)],
        )
        # agent primary organization is None
        get_person_from_userid("agent").primary_organization = None
        self.assertListEqual(
            [t.title for t in encodeur_active_orgs(self.omail)],
            [t for i, t in enumerate(all_titles) if i not in (0, 4, 7)],
        )

    def test_LabelsVocabulary(self):
        self.change_user("agent")
        voc_inst = MyLabelsVocabulary()
        voc_list = [t.value for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list, ["agent:lu", "agent:suivi"])

    def test_CreatingGroupVocabulary(self):
        voc_inst1 = CreatingGroupVocabulary()
        voc_inst2 = ActiveCreatingGroupVocabulary()
        self.assertEqual(len(voc_inst1(self.imail)), 0)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        configure_group_encoder("imail_group_encoder")
        self.assertEqual(len(voc_inst1(self.imail)), 12)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        # defining specific group_encoder orgs
        selected_orgs = [t.value for i, t in enumerate(voc_inst1(self.imail)) if i <= 1]
        functions = api.portal.get_registry_record(FUNCTIONS_REGISTRY)
        functions[-1]["fct_orgs"] = selected_orgs
        api.portal.set_registry_record(FUNCTIONS_REGISTRY, functions)
        self.assertEqual(len(voc_inst1(self.imail)), 2)
        self.assertEqual(len(voc_inst2(self.imail)), 0)
        # adding user to group_encoder plone groups
        for org_uid in selected_orgs:
            api.group.add_user(groupname="{}_{}".format(org_uid, CREATING_GROUP_SUFFIX), username="agent")
        self.change_user("siteadmin")  # refresh getGroups
        self.assertEqual(len(voc_inst1(self.imail)), 2)
        self.assertEqual(len(voc_inst2(self.imail)), 2)

    def test_DmsFilesCategoryVocabulary(self):
        """Test DmsFilesCategoryVocabulary"""

        def voc_to_tokens(voc):
            return [v.token for v in voc]

        voc_inst = DmsFilesCategoryVocabulary()

        # === No match: mail context itself with no typeupload → empty ===
        # context_type is "dmsincomingmail"/"dmsoutgoingmail", inner conditions don't match → path stays []
        self.assertEqual(len(voc_inst(self.imail)), 0)
        self.assertEqual(len(voc_inst(self.omail)), 0)

        # === Trigger via typeupload REQUEST parameter (quick-upload add forms) ===
        self.portal.REQUEST.form["typeupload"] = "dmsappendixfile"
        try:
            # incoming context → incoming_appendix_files (1 category)
            self.assertEqual(
                voc_to_tokens(voc_inst(self.imail)),
                ["plone-annexes_types_-_incoming_appendix_files_-_incoming-appendix-file"],
            )
            # outgoing context → outgoing_appendix_files (2 categories)
            self.assertEqual(
                voc_to_tokens(voc_inst(self.omail)),
                [
                    "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-appendix-file",
                    "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-signable-appendix-file",
                ],
            )
        finally:
            del self.portal.REQUEST.form["typeupload"]

        # === Trigger via context_type (child content objects) ===
        # dmsmainfile inside incoming mail → incoming_dms_files (1 category)
        mainfile = api.content.create(container=self.imail, type="dmsmainfile", id="mf")
        self.assertEqual(
            voc_to_tokens(voc_inst(mainfile)), ["plone-annexes_types_-_incoming_dms_files_-_incoming-dms-file"]
        )

        # dmsappendixfile inside incoming mail → incoming_appendix_files (1 category)
        iappendix = api.content.create(container=self.imail, type="dmsappendixfile", id="iaf")
        self.assertEqual(
            voc_to_tokens(voc_inst(iappendix)),
            ["plone-annexes_types_-_incoming_appendix_files_-_incoming-appendix-file"],
        )

        # dmsommainfile inside outgoing mail → outgoing_dms_files (2 categories)
        ommainfile = api.content.create(container=self.omail, type="dmsommainfile", id="omf")
        self.assertEqual(
            voc_to_tokens(voc_inst(ommainfile)),
            [
                "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file",
                "plone-annexes_types_-_outgoing_dms_files_-_outgoing-scanned-dms-file",
            ],
        )

        # dmsappendixfile inside outgoing mail → outgoing_appendix_files (2 categories)
        oappendix = api.content.create(container=self.omail, type="dmsappendixfile", id="oaf")
        self.assertEqual(
            voc_to_tokens(voc_inst(oappendix)),
            [
                "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-appendix-file",
                "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-signable-appendix-file",
            ],
        )

        # === Trigger via URL suffix (add form URLs) ===
        orig_url = self.portal.REQUEST.other["URL"]
        try:
            # URL ending "dmsmainfile", incoming context → incoming_dms_files (1 category)
            self.portal.REQUEST.other["URL"] = self.imail.absolute_url() + "/++add++dmsmainfile"
            self.assertEqual(
                voc_to_tokens(voc_inst(self.imail)), ["plone-annexes_types_-_incoming_dms_files_-_incoming-dms-file"]
            )

            # URL ending "dmsappendixfile", incoming context → incoming_appendix_files (1 category)
            self.portal.REQUEST.other["URL"] = self.imail.absolute_url() + "/++add++dmsappendixfile"
            self.assertEqual(
                voc_to_tokens(voc_inst(self.imail)),
                ["plone-annexes_types_-_incoming_appendix_files_-_incoming-appendix-file"],
            )

            # URL ending "dmsommainfile", outgoing context → outgoing_dms_files (2 categories)
            self.portal.REQUEST.other["URL"] = self.omail.absolute_url() + "/++add++dmsommainfile"
            self.assertEqual(
                voc_to_tokens(voc_inst(self.omail)),
                [
                    "plone-annexes_types_-_outgoing_dms_files_-_outgoing-dms-file",
                    "plone-annexes_types_-_outgoing_dms_files_-_outgoing-scanned-dms-file",
                ],
            )

            # URL ending "dmsappendixfile", outgoing context → outgoing_appendix_files (2 categories)
            self.portal.REQUEST.other["URL"] = self.omail.absolute_url() + "/++add++dmsappendixfile"
            self.assertEqual(
                voc_to_tokens(voc_inst(self.omail)),
                [
                    "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-appendix-file",
                    "plone-annexes_types_-_outgoing_appendix_files_-_outgoing-signable-appendix-file",
                ],
            )
        finally:
            self.portal.REQUEST.other["URL"] = orig_url

        # === ClassificationFolder/ClassificationSubfolder context → annexes (5 categories) ===
        cf = api.content.find(portal_type="ClassificationFolder")[0].getObject()
        self.assertEqual(
            voc_to_tokens(voc_inst(cf)),
            [
                "plone-annexes_types_-_annexes_-_annex",
                "plone-annexes_types_-_annexes_-_deliberation",
                "plone-annexes_types_-_annexes_-_cahier-charges",
                "plone-annexes_types_-_annexes_-_legal-advice",
                "plone-annexes_types_-_annexes_-_budget",
            ],
        )

        csf = api.content.find(portal_type="ClassificationSubfolder")[0].getObject()
        self.assertEqual(
            voc_to_tokens(voc_inst(csf)),
            [
                "plone-annexes_types_-_annexes_-_annex",
                "plone-annexes_types_-_annexes_-_deliberation",
                "plone-annexes_types_-_annexes_-_cahier-charges",
                "plone-annexes_types_-_annexes_-_legal-advice",
                "plone-annexes_types_-_annexes_-_budget",
            ],
        )

        # === Other context → get all content categories ===
        tasks_folder = api.content.get(path="/tasks")
        self.assertEqual(len(voc_inst(tasks_folder)), 11)
