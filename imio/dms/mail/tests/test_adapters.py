# -*- coding: utf-8 -*-
import unittest
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from ..browser.settings import IImioDmsMailConfig
from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..adapters import default_criterias
from ..adapters import IncomingMailHighestValidationCriterion
from ..adapters import IncomingMailValidationCriterion, TaskValidationCriterion
from ..adapters import IncomingMailInTreatingGroupCriterion
from ..adapters import IncomingMailInCopyGroupCriterion
from ..adapters import ScanSearchableExtender, IdmSearchableExtender, org_sortable_title_index
from ..adapters import state_group_index, task_state_group_index


class TestAdapters(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pgof = self.portal['contacts']['plonegroup-organization']

    def test_IncomingMailHighestValidationCriterion(self):
        crit = IncomingMailHighestValidationCriterion(self.portal)
        # no groups, => default criterias
        self.assertEqual(crit.query, default_criterias['dmsincomingmail'])
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        # in a group _validateur
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_service_chief']},
                                      'treating_groups': {'query': ['111']}})
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        # in a group dir_general
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_manager']}})

    def test_IncomingMailValidationCriterion(self):
        crit = IncomingMailValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {'state_group': {'query': []}})
        # in a group _validateur
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_service_chief,111']}})
        # in a group dir_general
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_manager',
                                                                'proposed_to_service_chief,111']}})

    def test_TaskValidationCriterion(self):
        crit = TaskValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {'state_group': {'query': []}})
        # in a group _validateur
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['to_assign,111', 'realized,111']}})
        # in a group dir_general, but no effect for task criterion
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_manager',
                                                                'to_assign,111', 'realized,111']}})

    def test_IncomingMailInTreatingGroupCriterion(self):
        crit = IncomingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'treating_groups': {'query': []}})
        api.group.create(groupname='111_validateur')
        api.group.add_user(groupname='111_validateur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'treating_groups': {'query': ['111']}})

    def test_IncomingMailInCopyGroupCriterion(self):
        crit = IncomingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'recipient_groups': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'recipient_groups': {'query': ['111']}})

    def test_state_group_index(self):
        dguid = self.pgof['direction-generale'].UID()
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         treating_groups=dguid, assigned_user='chef')
        indexer = state_group_index(imail)
        self.assertEqual(indexer(), 'created')
        api.content.transition(obj=imail, to_state='proposed_to_manager')
        self.assertEqual(indexer(), 'proposed_to_manager')
        api.content.transition(obj=imail, to_state='proposed_to_service_chief')
        self.assertEqual(indexer(), 'proposed_to_service_chief,%s' % dguid)
        api.content.transition(obj=imail, to_state='proposed_to_agent')
        self.assertEqual(indexer(), 'proposed_to_agent,%s' % dguid)

    def test_task_state_group_index(self):
        dguid = self.pgof['direction-generale'].UID()
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                         treating_groups=dguid, assigned_user='chef')
        task = createContentInContainer(imail, 'task', assigned_group=dguid)
        indexer = task_state_group_index(task)
        self.assertEqual(indexer(), 'created,%s' % dguid)
        api.content.transition(obj=task, to_state='to_assign')
        self.assertEqual(indexer(), 'to_assign,%s' % dguid)

    def test_ScanSearchableExtender(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', title='title', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1', title='title.pdf', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2.pdf', title='testid2.pdf',
                                       description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900000690.pdf', title='010999900000690.pdf',
                                       description='description', scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900000690 IMIO010999900000690 690 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900000691.pdf', title='title',
                                       description='description', scan_id='010999900000691')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900000691 title IMIO010999900000691 691 description')
        fh = open('testfile.txt', 'w+')
        fh.write("One word\n")
        fh.seek(0)
        file_object = NamedBlobFile(fh.read(), filename=u'testfile.txt')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2', title='title', description='description',
                                       file=file_object, scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 title 010999900000690 IMIO010999900000690 690 description One word\n')

    def test_IdmSearchableExtender(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', id='my-id', title='My title',
                                         description='Description')
        ext = IdmSearchableExtender(imail)
        self.assertEqual(ext(), None)
        createContentInContainer(imail, 'dmsmainfile', id='testid1', scan_id='010999900000690')
        self.assertEqual(ext(), u'010999900000690 IMIO010999900000690 690')
        pc = imail.portal_catalog
        rid = pc(id='my-id')[0].getRID()
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', 'my', 'title', 'description', u'010999900000690',
                                           'imio010999900000690', u'690'])
        createContentInContainer(imail, 'dmsmainfile', id='testid2', scan_id='010999900000700')
        self.assertEqual(ext(), u'010999900000690 IMIO010999900000690 690 010999900000700 IMIO010999900000700 700')
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', 'my', 'title', 'description', u'010999900000690',
                                           'imio010999900000690', u'690', u'010999900000700', 'imio010999900000700',
                                           u'700'])

    def test_org_sortable_title_index(self):
        elec = self.portal['contacts']['electrabel']
        trav = elec['travaux']
        self.assertEqual(org_sortable_title_index(elec)(), 'electrabel|')
        self.assertEqual(org_sortable_title_index(trav)(), 'electrabel|travaux 0001|')

    def test_IMMCTV(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', id='my-id', title='My title',
                                         mail_type='courrier', assigned_user='agent')
        view = imail.restrictedTraverse('@@view')
        view.update()
        # the title from the vocabulary is well rendered
        self.assertIn('Courrier', view.widgets['mail_type'].render())
        # We deactivate the courrier mail type, the missing value is managed
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.mail_types
        mail_types[0]['mt_active'] = False
        settings.mail_types = mail_types
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.IMActiveMailTypesVocabulary')
        self.assertNotIn('courrier', [t.value for t in voc_inst(imail)])
        view.updateWidgets()
        self.assertIn('Courrier', view.widgets['mail_type'].render())
        # We remove the courrier mail type, the missing value cannot be managed anymore
        settings.mail_types = settings.mail_types[1:]
        view.updateWidgets()
        self.assertNotIn('Courrier', view.widgets['mail_type'].render())
        self.assertIn('Missing', view.widgets['mail_type'].render())
