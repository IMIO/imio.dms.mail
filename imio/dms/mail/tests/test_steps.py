# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.wfadaptations.api import get_applied_adaptations
from datetime import datetime
from DateTime import DateTime
from imio.dms.mail.steps import remove_om_nplus1_wfadaptation
from imio.dms.mail.steps import reset_workflows_bad
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import Dummy
from imio.dms.mail.utils import sub_create
from imio.esign.config import get_esign_registry_enabled
from imio.esign.config import get_esign_registry_file_url
from plone import api

import unittest


class TestSteps(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def _run_step(self, step_id):
        self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", step_id, run_dependencies=False
        )

    def _step_context(self):
        """Import context of a step not registered in the singles profile."""
        return Dummy(readDataFile=lambda filename: True, getSite=lambda: self.portal)

    def test_create_persons_from_users(self):
        pf = self.portal["contacts"]["personnel-folder"]
        self.assertListEqual(
            pf.objectIds(),
            ["personnel-searches", "chef", "agent", "lecteur", "agent1", "encodeur", "dirg", "bourgmestre"],
        )
        member = self.portal.portal_registration.addMember(id="newuser", password="TestUser=6")
        member.setMemberProperties({"fullname": "Leloup Pierre", "email": "test@macommune.be"})
        orgs = get_registry_organizations()
        api.group.add_user(groupname="%s_encodeur" % orgs[0], username="newuser")
        # with the added subscriber, the person and held_position are already added
        api.content.delete(pf["newuser"])
        self.portal.portal_setup.runImportStepFromProfile(
            "imio.dms.mail:singles", "imiodmsmail-create-persons-from-users-inverted", run_dependencies=False
        )
        # person
        self.assertListEqual(
            pf.objectIds(),
            ["personnel-searches", "chef", "agent", "lecteur", "agent1", "encodeur", "dirg", "bourgmestre", "newuser"],
        )
        nu_p = pf["newuser"]
        self.assertEqual(nu_p.firstname, "Pierre")
        self.assertEqual(nu_p.lastname, "Leloup")
        self.assertEqual(nu_p.portal_type, "person")
        # held position
        self.assertIn(orgs[0], nu_p)
        nu_hp = nu_p[orgs[0]]
        self.assertEqual(nu_hp.portal_type, "held_position")
        self.assertEqual(nu_hp.position.to_path, "/plone/contacts/plonegroup-organization/direction-generale")
        # mixed with manual content
        api.content.rename(obj=nu_p, new_id="newuser_renamed")
        api.content.rename(obj=nu_hp, new_id="%s_renamed" % orgs[0])
        api.group.add_user(groupname="%s_encodeur" % orgs[1], username="newuser")
        api.content.delete(pf["newuser_renamed"][orgs[1]])
        self.portal.portal_setup.runImportStepFromProfile(
            "imio.dms.mail:singles", "imiodmsmail-create-persons-from-users-inverted", run_dependencies=False
        )
        self.assertListEqual(
            pf.objectIds(),
            ["personnel-searches", "chef", "agent", "lecteur", "agent1", "encodeur", "dirg", "bourgmestre",
             "newuser_renamed"],
        )
        self.assertListEqual(nu_p.objectIds(), ["%s_renamed" % orgs[0], orgs[1]])

    def test_activate_sign_request(self):
        tabs_record = "imio.dms.mail.displayed_tabs"
        self.assertNotIn("requests", api.portal.get_registry_record(tabs_record))
        self.assertNotIn(u"demand_sign", [fct["fct_id"] for fct in get_registry_functions()])
        self.assertFalse(get_esign_registry_enabled())
        self._run_step("imiodmsmail-activate-sign-request")
        # the requests tab is shown and the signature requester function is added
        self.assertIn("requests", api.portal.get_registry_record(tabs_record))
        self.assertIn(u"demand_sign", [fct["fct_id"] for fct in get_registry_functions()])
        # electronic signing is installed and configured
        self.assertTrue(get_esign_registry_enabled())
        self.assertTrue(get_esign_registry_file_url().startswith(u"https://documents."))
        # demo sign requests are added
        brains = self.portal.portal_catalog(portal_type="sign_request", sort_on="id")
        self.assertListEqual([brain.id for brain in brains], ["demande1", "demande2", "demande3"])

    def test_add_icons_to_contact_workflow(self):
        wfl = self.portal.portal_workflow.collective_contact_core_workflow
        for transition in wfl.transitions.values():
            transition.actbox_icon = ""
        self._run_step("imiodmsmail-add-icons-to-contact-workflow")
        self.assertEqual(
            wfl.transitions["activate"].actbox_icon, "%(portal_url)s/++resource++imio.dms.mail/im_treat.png"
        )
        self.assertEqual(
            wfl.transitions["deactivate"].actbox_icon,
            "%(portal_url)s/++resource++imio.dms.mail/im_back_to_creation.png",
        )

    def test_mark_copy_im_as_read(self):
        pc = self.portal.portal_catalog
        grh_uid = self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID()
        imf = self.portal["incoming-mail"]
        old = sub_create(imf, "dmsincomingmail", datetime.now(), "old-copy", title=u"Old", recipient_groups=[grh_uid])
        old.creation_date = DateTime() - 10
        old.reindexObject(idxs=["created"])
        recent = sub_create(imf, "dmsincomingmail", datetime.now(), "recent-copy", title=u"Recent",
                            recipient_groups=[grh_uid])
        self._run_step("imiodmsmail-mark-copy-im-as-read")
        # an incoming mail in copy for more than 5 days is marked as read for the readers of the copy service
        for userid in ("agent", "lecteur"):
            self.assertEqual(len(pc(UID=old.UID(), labels="{}:lu".format(userid))), 1, userid)
            self.assertEqual(len(pc(UID=recent.UID(), labels="{}:lu".format(userid))), 0, userid)
        self.assertEqual(len(pc(UID=old.UID(), labels="chef:lu")), 0)

    def test_reset_workflows_bad(self):
        pw = self.portal.portal_workflow
        self._run_step("imiodmsmail-im_n_plus_1_wfadaptation")
        self.assertIn("propose_to_n_plus_1", pw["incomingmail_workflow"].states["created"].transitions)
        pw["incomingmail_workflow"].states["created"].title = "Bad title"
        reset_workflows_bad(self._step_context())
        imw = pw["incomingmail_workflow"]
        # the workflows are reloaded from the profile
        self.assertNotEqual(imw.states["created"].title, "Bad title")
        # and the applied adaptations are applied again
        self.assertIn("propose_to_n_plus_1", imw.states["created"].transitions)
        self.assertIn("back_in_created2", pw["task_workflow"].transitions)

    def test_remove_om_nplus1_wfadaptation(self):
        adaptation = u"imio.dms.mail.wfadaptations.OMServiceValidation"
        context = self._step_context()
        pw = self.portal.portal_workflow
        folder = self.portal["outgoing-mail"]["mail-searches"]
        # the adaptation is not applied
        self.assertEqual(remove_om_nplus1_wfadaptation(context), "OMServiceValidation already removed !")
        self._run_step("imiodmsmail-om_n_plus_1_wfadaptation")
        self.assertIn(adaptation, [dic["adaptation"] for dic in get_applied_adaptations()])
        for state in ("proposed_to_n_plus_1", "validated"):
            self.assertIn(state, pw["outgoingmail_workflow"].states)
            self.assertIn("searchfor_{}".format(state), folder)
        # an outgoing mail is waiting for a validation: nothing is done
        omail = api.content.find(portal_type="dmsoutgoingmail", id="reponse1")[0].getObject()
        api.content.transition(omail, "propose_to_n_plus_1")
        self.assertEqual(
            remove_om_nplus1_wfadaptation(context),
            "Found some outgoing mails in state 'proposed_to_n_plus_1' or 'validated'. We stop !",
        )
        self.assertIn("validated", pw["outgoingmail_workflow"].states)
        # no more outgoing mail to validate: the validation level is removed
        api.content.transition(omail, "back_to_creation")
        self.assertEqual(remove_om_nplus1_wfadaptation(context), "")
        self.assertNotIn(adaptation, [dic["adaptation"] for dic in get_applied_adaptations()])
        for state in ("proposed_to_n_plus_1", "validated"):
            self.assertNotIn(state, pw["outgoingmail_workflow"].states)
            self.assertNotIn("searchfor_{}".format(state), folder)
        self.assertFalse(folder["to_validate"].enabled)
        # the n+1 function and groups are removed (not used by another adaptation)
        self.assertNotIn(u"n_plus_1", [fct["fct_id"] for fct in get_registry_functions()])
        self.assertIsNone(api.group.get("{}_n_plus_1".format(get_registry_organizations()[0])))

    def test_configure_wsclient(self):
        prefix = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings"
        api.portal.set_registry_record("{}.viewlet_display_condition".format(prefix), u"")
        api.portal.set_registry_record("{}.generated_actions".format(prefix), [])
        self._run_step("imiodmsmail-configure-wsclient")
        self.assertEqual(api.portal.get_registry_record("{}.pm_username".format(prefix)), u"admin")
        self.assertTrue(api.portal.get_registry_record("{}.only_one_sending".format(prefix)))
        self.assertEqual(api.portal.get_registry_record("{}.viewlet_display_condition".format(prefix)), u"isLinked")
        mappings = api.portal.get_registry_record("{}.field_mappings".format(prefix))
        self.assertListEqual([dic["field_name"] for dic in mappings], [u"title", u"description"])
        actions = api.portal.get_registry_record("{}.generated_actions".format(prefix))
        self.assertListEqual([dic["pm_meeting_config_id"] for dic in actions], [u"meeting-config-college"])
        self.assertEqual(actions[0]["permissions"], "Modify view template")

    def test_contact_import_pipeline(self):
        record = "collective.contact.importexport.interfaces.IPipelineConfiguration.pipeline"
        api.portal.set_registry_record(record, u"")
        self._run_step("imiodmsmail-contact-import-pipeline")
        pipeline = api.portal.get_registry_record(record)
        self.assertTrue(pipeline.startswith(u"[transmogrifier]\npipeline =\n    initialization\n"))
        self.assertIn(u"\n    iadocs_userid\n", pipeline)
        self.assertIn(u"\n[config]\n", pipeline)
