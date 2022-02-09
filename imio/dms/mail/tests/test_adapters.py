# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.wfadaptations.api import add_applied_adaptation
from imio.dms.mail.adapters import default_criterias
from imio.dms.mail.adapters import IdmSearchableExtender
from imio.dms.mail.adapters import IncomingMailHighestValidationCriterion
from imio.dms.mail.adapters import IncomingMailInCopyGroupCriterion
from imio.dms.mail.adapters import IncomingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import IncomingMailValidationCriterion
from imio.dms.mail.adapters import OdmSearchableExtender
from imio.dms.mail.adapters import org_sortable_title_index
from imio.dms.mail.adapters import OutgoingMailInCopyGroupCriterion
from imio.dms.mail.adapters import OutgoingMailInTreatingGroupCriterion
from imio.dms.mail.adapters import OutgoingMailValidationCriterion
from imio.dms.mail.adapters import ready_for_email_index
from imio.dms.mail.adapters import ScanSearchableExtender
from imio.dms.mail.adapters import im_sender_email_index
from imio.dms.mail.adapters import state_group_index
from imio.dms.mail.adapters import TaskInAssignedGroupCriterion
from imio.dms.mail.adapters import TaskInProposingGroupCriterion
from imio.dms.mail.adapters import TaskValidationCriterion
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.testing import reset_dms_config
from imio.dms.mail.utils import set_dms_config
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import unittest


class TestAdapters(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.pgof = self.portal['contacts']['plonegroup-organization']

    def tearDown(self):
        # the modified dmsconfig is kept globally
        reset_dms_config()

    def test_IncomingMailHighestValidationCriterion(self):
        crit = IncomingMailHighestValidationCriterion(self.portal)
        # no groups, => default criterias
        self.assertEqual(crit.query, default_criterias['dmsincomingmail'])
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(['review_levels', 'dmsincomingmail'],
                       OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                    ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
        # in a group _n_plus_1
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_n_plus_1']},
                                      'treating_groups': {'query': ['111']}})
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        # in a group dir_general
        self.assertEqual(crit.query, {'review_state': {'query': ['proposed_to_manager']}})

    def test_IncomingMailValidationCriterion(self):
        crit = IncomingMailValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {'state_group': {'query': []}})
        # in a group _n_plus_1
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(['review_levels', 'dmsincomingmail'],
                       OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                    ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_n_plus_1,111']}})
        # in a group dir_general
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_manager',
                                                                'proposed_to_n_plus_1,111']}})

    def test_OutgoingMailValidationCriterion(self):
        crit = OutgoingMailValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {'state_group': {'query': []}})
        # in a group _n_plus_1
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        # update reviewlevels because n_plus_1 level is not applied by default
        set_dms_config(['review_levels', 'dmsoutgoingmail'],
                       OrderedDict([('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_n_plus_1,111']}})
        # in a group dir_general
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['proposed_to_n_plus_1,111']}})

    def test_TaskValidationCriterion(self):
        crit = TaskValidationCriterion(self.portal)
        # no groups
        self.assertEqual(crit.query, {'state_group': {'query': []}})
        # in a group _n_plus_1
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        set_dms_config(['review_levels', 'task'],
                       OrderedDict([('_n_plus_1', {'st': ['to_assign', 'realized'], 'org': 'assigned_group'})]))
        self.assertEqual(crit.query, {'state_group': {'query': ['to_assign,111', 'realized,111']}})
        # in a group dir_general, but no effect for task criterion
        api.group.add_user(groupname='dir_general', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'state_group': {'query': ['to_assign,111', 'realized,111']}})

    def test_IncomingMailInTreatingGroupCriterion(self):
        crit = IncomingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'treating_groups': {'query': []}})
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'treating_groups': {'query': ['111']}})

    def test_OutgoingMailInTreatingGroupCriterion(self):
        crit = OutgoingMailInTreatingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'treating_groups': {'query': []}})
        api.group.create(groupname='111_n_plus_1')
        api.group.add_user(groupname='111_n_plus_1', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'treating_groups': {'query': ['111']}})

    def test_IncomingMailInCopyGroupCriterion(self):
        crit = IncomingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'recipient_groups': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'recipient_groups': {'query': ['111']}})

    def test_OutgoingMailInCopyGroupCriterion(self):
        crit = OutgoingMailInCopyGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'recipient_groups': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'recipient_groups': {'query': ['111']}})

    def test_TaskInAssignedGroupCriterion(self):
        crit = TaskInAssignedGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'assigned_group': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'assigned_group': {'query': ['111']}})

    def test_TaskInProposingGroupCriterion(self):
        crit = TaskInProposingGroupCriterion(self.portal)
        self.assertEqual(crit.query, {'mail_type': {'query': []}})
        api.group.create(groupname='111_editeur')
        api.group.add_user(groupname='111_editeur', username=TEST_USER_ID)
        self.assertEqual(crit.query, {'mail_type': {'query': ['111']}})

    def test_im_sender_email_index(self):
        dguid = self.pgof['direction-generale'].UID()
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', title='test',
                                         treating_groups=dguid, assigned_user='chef',
                                         orig_sender_email=u'"Dexter Morgan" <dexter.morgan@mpd.am>')
        indexer = im_sender_email_index(imail)
        self.assertEqual(indexer(), u'dexter.morgan@mpd.am')

    def test_ready_for_email_index(self):
        omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail', id='my-id', title='My title',
                                         description='Description', send_modes=['post'])
        indexer = ready_for_email_index(omail)
        # not an email
        self.assertFalse(indexer())
        # email without docs
        omail.send_modes = ['email']
        self.assertTrue(indexer())
        # email with a doc not signed
        createContentInContainer(omail, 'dmsommainfile')
        self.assertFalse(indexer())
        # email with another doc signed
        createContentInContainer(omail, 'dmsommainfile', signed=True)
        self.assertTrue(indexer())

    def test_state_group_index(self):
        dguid = self.pgof['direction-generale'].UID()
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', title='test',
                                         treating_groups=dguid, assigned_user='chef')
        indexer = state_group_index(imail)
        self.assertEqual(indexer(), 'created')
        api.content.transition(obj=imail, to_state='proposed_to_manager')
        self.assertEqual(indexer(), 'proposed_to_manager')
        api.content.transition(obj=imail, to_state='proposed_to_agent')
        self.assertEqual(indexer(), 'proposed_to_agent')

        task = createContentInContainer(imail, 'task', assigned_group=dguid)
        indexer = state_group_index(task)
        self.assertEqual(indexer(), 'created')
        # simulate adaptation
        add_applied_adaptation('imio.dms.mail.wfadaptations.TaskServiceValidation', 'task_workflow', False)
        api.group.create(groupname='{}_n_plus_1'.format(dguid), groups=['chef'])
        api.content.transition(obj=task, transition='do_to_assign')
        self.assertEqual(indexer(), 'to_assign')
        set_dms_config(['review_states', 'task'], OrderedDict([('to_assign', {'group': '_n_plus_1',
                                                                              'org': 'assigned_group'})]))
        self.assertEqual(indexer(), 'to_assign,%s' % dguid)

    def test_ScanSearchableExtender(self):
        imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1.pdf', title='title', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid1', title='title.pdf', description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid1 title description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2.pdf', title='testid2.PDF',
                                       description='description')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900000690.pdf', title='010999900000690.pdf',
                                       description='description', scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900000690 IMIO010999900000690 description')
        obj = createContentInContainer(imail, 'dmsmainfile', id='010999900001691.pdf', title='title',
                                       description='description', scan_id='010999900001691')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), '010999900001691 title IMIO010999900001691 1691 description')
        fh = open('testfile.txt', 'w+')
        fh.write("One word\n")
        fh.seek(0)
        file_object = NamedBlobFile(fh.read(), filename=u'testfile.txt')
        obj = createContentInContainer(imail, 'dmsmainfile', id='testid2', title='title', description='description',
                                       file=file_object, scan_id='010999900000690')
        ext = ScanSearchableExtender(obj)
        self.assertEqual(ext(), 'testid2 title 010999900000690 IMIO010999900000690 description One word\n')

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

    def test_OdmSearchableExtender(self):
        omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail', id='my-id', title='My title',
                                         description='Description')
        ext = OdmSearchableExtender(omail)
        self.assertEqual(ext(), None)
        createContentInContainer(omail, 'dmsommainfile', id='testid1', scan_id='011999900000690')
        self.assertEqual(ext(), u'011999900000690 IMIO011999900000690 690')
        pc = omail.portal_catalog
        rid = pc(id='my-id')[0].getRID()
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['s0010', 'my', 'title', 'description', u'011999900000690',
                                           'imio011999900000690', u'690'])
        createContentInContainer(omail, 'dmsommainfile', id='testid2', scan_id='011999900000700')
        self.assertEqual(ext(), u'011999900000690 IMIO011999900000690 690 011999900000700 IMIO011999900000700 700')
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['s0010', 'my', 'title', 'description', u'011999900000690',
                                           'imio011999900000690', u'690', u'011999900000700', 'imio011999900000700',
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
        mail_types[0]['active'] = False
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

    def test_OMMCTV(self):
        omail = createContentInContainer(self.portal['outgoing-mail'], 'dmsoutgoingmail', id='my-id', title='My title',
                                         mail_type='type1')
        view = omail.restrictedTraverse('@@view')
        view.update()
        # the title from the vocabulary is well rendered
        self.assertIn('Type 1', view.widgets['mail_type'].render())
        # We deactivate the courrier mail type, the missing value is managed
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        mail_types = settings.omail_types
        mail_types[0]['active'] = False
        settings.omail_types = mail_types
        voc_inst = getUtility(IVocabularyFactory, 'imio.dms.mail.OMActiveMailTypesVocabulary')
        self.assertNotIn('type1', [t.value for t in voc_inst(omail)])
        view.updateWidgets()
        self.assertIn('Type 1', view.widgets['mail_type'].render())
        # We remove the courrier mail type, the missing value cannot be managed anymore
        settings.omail_types = settings.omail_types[1:]
        view.updateWidgets()
        self.assertNotIn('Type 1', view.widgets['mail_type'].render())
        self.assertIn('Missing', view.widgets['mail_type'].render())
