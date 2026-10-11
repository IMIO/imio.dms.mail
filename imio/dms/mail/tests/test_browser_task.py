# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from collective.wfadaptations.api import add_applied_adaptation
from imio.dms.mail.browser.task import Add
from imio.dms.mail.browser.task import CustomAddForm
from imio.dms.mail.browser.task import filter_task_assigned_users
from imio.dms.mail.browser.task import TaskEdit
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.content import get_object
from imio.helpers.test_helpers import ImioTestHelpers
from imio.helpers.vocabularies import SimplySortedUsers
from plone import api
from plone.formwidget.masterselect.widget import MasterSelectJSONValue
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestBrowserTask(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.change_user("siteadmin")
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        self.task = self.im1["tache1"]

    def test_filter_task_assigned_users(self):
        self.assertEqual(len(filter_task_assigned_users(None)), 0)
        selected_orgs = get_registry_organizations()
        voc = filter_task_assigned_users(selected_orgs[0])
        self.assertListEqual([t.title for t in voc._terms], [])  # direction generale => no user
        voc = filter_task_assigned_users(selected_orgs[1])
        self.assertListEqual([t.title for t in voc._terms], [u"Fred Agent", u"Jean Encodeur"])
        # masterselect json call with a single user: it becomes the default value
        api.group.add_user(groupname="{}_editeur".format(selected_orgs[0]), username="chef")
        self.request["REQUEST_METHOD"] = "GET"
        form = self.task.unrestrictedTraverse("@@edit")
        form.update()
        self.request["PUBLISHED"] = MasterSelectJSONValue(form.widgets["ITask.assigned_group"], self.request)
        voc = filter_task_assigned_users(selected_orgs[0])
        self.assertListEqual([t.value for t in voc._terms], ["chef"])
        self.assertEqual(self.request.get("_default_assigned_user_"), "chef")

    def test_TaskUpdateWidgets(self):
        self.request["REQUEST_METHOD"] = "GET"
        form = self.task.unrestrictedTraverse("@@edit")
        form.update()
        widget = form.widgets["ITask.assigned_group"]
        self.assertTrue(widget.required)
        self.assertTrue(form.widgets["ITask.enquirer"].required)
        self.assertEqual(widget.field.slave_fields[0]["vocab_method"], filter_task_assigned_users)
        self.assertTrue(widget.field.slave_fields[0]["initial_trigger"])

    def test_AssignedUsersVocabulary(self):
        voc_inst = getUtility(IVocabularyFactory, "collective.task.AssignedUsers")
        self.assertIsInstance(voc_inst, SimplySortedUsers)
        # value is userid and not username
        self.assertListEqual(
            sorted([t.value for t in voc_inst(None)]),
            ["agent", "agent1", "bourgmestre", "chef", "dirg", "encodeur", "lecteur", "scanner", "siteadmin",
             "test_user_1_"],
        )
        self.assertListEqual(
            [t.title for t in voc_inst(None)],
            [
                u"Fred Agent",
                u"Jean Encodeur",
                u"Jef Lecteur",
                u"Maxime DG",
                u"Michel Chef",
                u"Paul BM",
                u"siteadmin",
                u"Scanner",
                u"Stef Agent",
                u"test_user_1_",
            ],
        )


class TestTaskEdit(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.change_user("siteadmin")
        self.task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]

    def test_updateWidgets(self):
        self.request["REQUEST_METHOD"] = "GET"
        form = self.task.unrestrictedTraverse("@@edit")
        self.assertIsInstance(form, TaskEdit)
        form.update()
        self.assertNotEqual(form.widgets["ITask.assigned_user"].field.description,
                            u"You must select an assigned user before continuing !")
        # to assign (task service validation with a n+1 user) without assigned user: a warning description
        add_applied_adaptation("imio.dms.mail.wfadaptations.TaskServiceValidation", "task_workflow", False)
        n_plus_1 = "{}_n_plus_1".format(self.task.assigned_group)
        api.group.create(groupname=n_plus_1)
        api.group.add_user(groupname=n_plus_1, username="chef")
        api.content.transition(obj=self.task, transition="do_to_assign")
        self.assertEqual(api.content.get_state(self.task), "to_assign")
        form = self.task.unrestrictedTraverse("@@edit")
        form.update()
        self.assertEqual(form.widgets["ITask.assigned_user"].field.description,
                         u"You must select an assigned user before continuing !")


class TestCustomAddForm(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.portal.REQUEST
        self.change_user("siteadmin")
        self.im1 = get_object(oid="courrier1", ptype="dmsincomingmail")

    def test_updateWidgets(self):
        self.request["REQUEST_METHOD"] = "GET"
        # on a mail: default groups from the treating group
        view = self.im1.unrestrictedTraverse("++add++task")
        self.assertIsInstance(view, Add)
        self.assertIsInstance(view.form_instance, CustomAddForm)
        view.update()
        form = view.form_instance
        self.assertEqual(form.widgets["ITask.assigned_group"].value, self.im1.treating_groups)
        self.assertEqual(form.widgets["ITask.enquirer"].value, self.im1.treating_groups)
        self.assertTrue(form.widgets["ITask.assigned_group"].required)
        # on a task: default groups from the parent assigned group
        task3 = self.im1["tache3"]
        view = task3.unrestrictedTraverse("++add++task")
        view.update()
        form = view.form_instance
        self.assertEqual(form.widgets["ITask.assigned_group"].value, task3.assigned_group)
        self.assertEqual(form.widgets["ITask.enquirer"].value, task3.assigned_group)
