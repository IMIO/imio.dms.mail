# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_organizations
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.wfadaptations.api import add_applied_adaptation
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.vocabularies import AssignedUsersWithDeactivatedVocabulary
from plone import api
from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.dexterity.utils import createContentInContainer
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield import RelationValue
from zExceptions import Redirect
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.interface import Interface
from zope.intid import IIntIds
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import unittest
import zope.event


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        intids = getUtility(IIntIds)
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', id='c1',
                                              sender=[RelationValue(intids.getId(self.portal.contacts['electrabel']))],
                                              mail_type=u'courrier', title=u'title')
        self.omf = self.portal['outgoing-mail']

    def test_item_copied(self):
        # check if protection markers are removed from copied item
        source = self.portal['templates']['om']['main']
        self.assertFalse(source.restrictedTraverse('@@various-utils').is_deletable())
        copied = api.content.copy(source, self.portal['templates']['om'], 'copied_id')
        self.assertIn('copied_id', self.portal['templates']['om'])
        self.assertTrue(copied.restrictedTraverse('@@various-utils').is_deletable())
        # check if om folder cannot be pasted
        self.assertRaises(Redirect, api.content.copy, self.portal['templates']['om'], self.portal['templates'], 'new')

    def test_item_moved(self):
        source = self.portal['templates']['om']['main']
        copied = api.content.copy(source, self.portal['templates']['om'], 'copied_id')
        self.assertIn('copied_id', self.portal['templates']['om'])
        self.assertRaises(Redirect, api.content.delete, obj=source, check_linkintegrity=False)
        self.assertRaises(Redirect, api.content.move, source, self.portal['templates']['om']['common'])
        api.content.delete(obj=copied, check_linkintegrity=False)
        self.assertNotIn('copied_id', self.portal['templates']['om'])

    def test_dmsdocument_modified(self):
        # owner changing test
        orgs = get_registry_organizations()
        with api.env.adopt_user(username='scanner'):
            imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                             **{'title': 'IMail created by scanner', 'treating_groups': orgs[0]})
            dfile = createContentInContainer(imail, 'dmsmainfile', **{'title': 'File created by scanner'})
        self.assertEquals(imail.Creator(), 'scanner')
        self.assertEquals(imail.owner_info()['id'], 'scanner')
        self.assertEquals(imail.get_local_roles_for_userid('scanner'), ('Owner',))
        self.assertEquals(dfile.Creator(), 'scanner')
        self.assertEquals(dfile.owner_info()['id'], 'scanner')
        self.assertEquals(dfile.get_local_roles_for_userid('scanner'), ('Owner',))
        with api.env.adopt_user(username='encodeur'):
            imail.setTitle('IMail modified by encodeur')
            zope.event.notify(ObjectModifiedEvent(imail))
        self.assertEquals(imail.Creator(), 'encodeur')
        self.assertEquals(imail.owner_info()['id'], 'encodeur')
        self.assertEquals(imail.get_local_roles_for_userid('encodeur'), ('Owner',))
        self.assertEquals(imail.get_local_roles_for_userid('scanner'), ())
        self.assertEquals(dfile.Creator(), 'encodeur')
        self.assertEquals(dfile.owner_info()['id'], 'encodeur')
        self.assertEquals(dfile.get_local_roles_for_userid('encodeur'), ('Owner',))
        self.assertEquals(dfile.get_local_roles_for_userid('scanner'), ())
        # tasks update test
        task1 = api.content.create(container=imail, type='task', title='task1', id='t1', assigned_group=orgs[1])
        self.assertListEqual(task1.parents_assigned_groups, [orgs[0]])
        task2 = api.content.create(container=task1, type='task', title='task2', id='t2', assigned_group=orgs[2])
        self.assertListEqual(task2.parents_assigned_groups, [orgs[0], orgs[1]])
        imail.treating_groups = orgs[4]
        zope.event.notify(ObjectModifiedEvent(imail, Attributes(Interface, 'treating_groups')))
        self.assertListEqual(task1.parents_assigned_groups, [orgs[4]])
        self.assertListEqual(task2.parents_assigned_groups, [orgs[4], orgs[1]])

    def test_dmsincomingmail_transition(self):
        self.assertEqual(api.content.get_state(self.imail), 'created')
        self.imail.treating_groups = get_registry_organizations()[1]  # direction-generale secretariat
        api.content.transition(self.imail, 'propose_to_agent')
        login(self.portal, 'agent')
        self.assertIsNone(self.imail.assigned_user)
        api.content.transition(self.imail, 'close')
        self.assertEqual(self.imail.assigned_user, 'agent')

    def test_task_transition(self):
        # task = createContentInContainer(self.imail, 'task', id='t1')
        task = self.portal['incoming-mail']['courrier1']['tache1']
        # no assigned_user and no TaskServiceValidation
        self.assertIsNone(task.assigned_user)
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_do')
        # assigned_user and no TaskServiceValidation
        api.content.transition(task, transition='back_in_created2')
        task.assigned_user = 'chef'
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_do')
        # no assigned_user but TaskServiceValidation but no user in groups
        api.content.transition(task, transition='back_in_created2')
        task.assigned_user = None
        add_applied_adaptation('imio.dms.mail.wfadaptations.TaskServiceValidation', 'task_workflow', False)
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_do')
        # no assigned_user but TaskServiceValidation and user in groups
        api.content.transition(task, transition='back_in_created2')
        api.group.create(groupname='{}_n_plus_1'.format(task.assigned_group), groups=['chef'])
        api.content.transition(task, transition='do_to_assign')
        self.assertEqual(api.content.get_state(task), 'to_assign')

    def test_dmsmainfile_modified(self):
        pc = self.portal.portal_catalog
        rid = pc(id='c1')[0].getRID()
        # before mainfile creation
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', 'title'])
        # after mainfile creation
        f1 = createContentInContainer(self.imail, 'dmsmainfile', id='f1', scan_id='010999900000690')
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', 'title', u'010999900000690', 'imio010999900000690', u'690'])
        # after mainfile modification
        f1.scan_id = '010999900000691'
        zope.event.notify(ObjectModifiedEvent(f1, Attributes(IScanFields, 'IScanFields.scan_id')))
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', 'title', u'010999900000691', 'imio010999900000691', u'691'])
        # event without scan_id attribute
        zope.event.notify(ObjectModifiedEvent(f1))

    def test_user_related_modification(self):
        voc_inst = AssignedUsersWithDeactivatedVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list,
                             [('__empty_string__', u'Empty value'), ('agent', u'Fred Agent'),
                              ('encodeur', u'Jean Encodeur'), ('lecteur', u'Jef Lecteur'), ('dirg', u'Maxime DG'),
                              ('chef', u'Michel Chef'), ('scanner', u'Scanner'), ('agent1', u'Stef Agent'),
                              ('test-user', u'test-user (Désactivé)')])
        # we change a user property
        member = api.user.get(userid='chef')
        member.setMemberProperties({'fullname': 'Michel Chef 2'})
        # we simulate the user form change event
        zope.event.notify(ConfigurationChangedEvent(UserDataConfiglet(self.portal, self.portal.REQUEST), {}))
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list,
                             [('__empty_string__', u'Empty value'), ('agent', u'Fred Agent'),
                              ('encodeur', u'Jean Encodeur'), ('lecteur', u'Jef Lecteur'), ('dirg', u'Maxime DG'),
                              ('chef', u'Michel Chef 2'), ('scanner', u'Scanner'), ('agent1', u'Stef Agent'),
                              ('test-user', u'test-user (Désactivé)')])
        # we change the activated services
        set_registry_organizations(get_registry_organizations()[0:1])  # only keep Direction générale
        api.group.remove_user(groupname='createurs_dossier', username='agent')  # remove agent from global group
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertListEqual(voc_list,
                             [('__empty_string__', u'Empty value'), ('encodeur', u'Jean Encodeur'),
                              ('dirg', u'Maxime DG'), ('chef', u'Michel Chef 2'), ('scanner', u'Scanner'),
                              ('agent', u'Fred Agent (Désactivé)'), ('lecteur', u'Jef Lecteur (Désactivé)'),
                              ('agent1', u'Stef Agent (Désactivé)'), ('test-user', u'test-user (Désactivé)')])
        # wrong configuration change
        zope.event.notify(ConfigurationChangedEvent(self.portal, {}))

    def test_user_deleted(self):
        request = self.portal.REQUEST
        # protected user
        self.assertRaises(Redirect, api.user.delete, username='scanner')
        smi = IStatusMessage(request)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'scanner'.")
        # having group
        self.assertRaises(Redirect, api.user.delete, 'lecteur')
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'lecteur', used in following groups.")
        # is used in content
        self.assertRaises(Redirect, api.user.delete, username=TEST_USER_ID)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'test_user_1_', used in 'Creator' index.")
        # is used as person user_id
        api.user.create('test@test.be', 'testuser', 'Password#1')
        agent = self.portal.contacts['personnel-folder']['agent']
        agent.userid = 'testuser'
        agent.reindexObject()
        self.assertRaises(Redirect, api.user.delete, username='testuser')
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the user name 'testuser', used in 'Mail type' index.")

    def test_group_deleted(self):
        request = self.portal.REQUEST
        # protected group
        self.assertRaises(Redirect, api.group.delete, groupname='expedition')
        smi = IStatusMessage(request)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the group 'expedition'.")
        # is used in content
        group = '%s_editeur' % get_registry_organizations()[0]
        # we remove this organization to escape plonegroup subscriber
        set_registry_organizations(get_registry_organizations()[1:])
        self.assertRaises(Redirect, api.group.delete, groupname=group)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the group '%s', used in 'Assigned group' index." % group)

    def test_organization_modified(self):
        pc = self.portal.portal_catalog
        self.elec = self.portal['contacts']['electrabel']
        rid = pc(id='travaux')[0].getRID()
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, 'electrabel|travaux 0001|')
        self.elec.title = 'Electrabel 1'
        zope.event.notify(ObjectModifiedEvent(self.elec, Attributes(IBasic, 'IBasic.title')))
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, 'electrabel 0001|travaux 0001|')
        rid = pc(id='electrabel')[0].getRID()
        index_value = pc._catalog.getIndex("sortable_title").getEntryForObject(rid, default=[])
        self.assertEqual(index_value, 'electrabel 0001|')

    def test_contact_plonegroup_change(self):
        e_groups = [('%s_encodeur' % uid, ('Contributor', )) for uid in get_registry_organizations()]
        e_groups.append(('admin', ('Owner',)))
        e_groups.append(('expedition', ('Contributor',)))
        e_groups.append(('dir_general', ('Contributor',)))
        self.assertSetEqual(set(self.omf.get_local_roles()), set(e_groups))
        self.assertEqual(len(self.omf.get_local_roles()), 14)
        set_registry_organizations(get_registry_organizations()[:3])
        self.assertEqual(len(self.omf.get_local_roles()), 6)
        # TODO tests other changes !!

    def test_cktemplate_moved(self):
        oemf = self.portal['templates']['oem']
        srvf = self.portal['contacts']['plonegroup-organization']
        org1 = srvf['direction-generale']
        org2 = srvf['direction-generale']['secretariat']
        self.assertIn(org1.UID(), oemf)
        self.assertIn(org2.UID(), oemf)
        mod1 = api.content.create(container=oemf, type='cktemplate', id='mod1', title='Modèle 1')
        annot = IAnnotations(mod1)
        self.assertEqual(annot['dmsmail.cke_tpl_tit'], u'')
        mod1 = api.content.move(mod1, oemf[org1.UID()])
        annot = IAnnotations(mod1)
        self.assertEqual(annot['dmsmail.cke_tpl_tit'], u'Direction générale')
        mod2 = api.content.copy(mod1, oemf[org2.UID()], id='mod2')
        annot = IAnnotations(mod2)
        self.assertEqual(annot['dmsmail.cke_tpl_tit'], u'Direction générale - Secrétariat')
        folder = api.content.create(container=oemf, type='Folder', id='fold1', title='héhéhé')
        mod2 = api.content.move(mod2, folder)
        annot = IAnnotations(mod2)
        self.assertEqual(annot['dmsmail.cke_tpl_tit'], u'héhéhé')
        mod2 = api.content.rename(mod2, 'mod-nextgen')
        annot = IAnnotations(mod2)
        self.assertEqual(annot['dmsmail.cke_tpl_tit'], u'héhéhé')
