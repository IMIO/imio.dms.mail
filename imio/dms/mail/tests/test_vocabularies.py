# -*- coding: utf-8 -*-
import unittest
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..vocabularies import (IMReviewStatesVocabulary, TaskReviewStatesVocabulary,
                            AssignedUsersVocabulary)


class TestVocabularies(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')

    def test_IMReviewStatesVocabulary(self):
        voc_inst = IMReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'Created'), ('proposed_to_manager', u'Proposed to manager'),
                                    ('proposed_to_service_chief', u'Proposed to service chief'),
                                    ('proposed_to_agent', u'Proposed to agent'), ('in_treatment', u'In treatment'),
                                    ('closed', u'Closed')])

    def test_TaskReviewStatesVocabulary(self):
        voc_inst = TaskReviewStatesVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [('created', u'Created'), ('to_assign', u'To assign'), ('to_do', u'To do'),
                                    ('in_progress', u'In progress'), ('realized', u'Realized'),
                                    ('closed', u'Closed')])

    def test_AssignedUsersVocabulary(self):
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertEqual(voc_list, [])
