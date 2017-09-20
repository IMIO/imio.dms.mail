# -*- coding: utf-8 -*-
import unittest

from zExceptions import Redirect
import zope.event
from zope.component import getUtility
from zope.interface import Interface
from zope.lifecycleevent import ObjectModifiedEvent, Attributes

from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.testing import setRoles, TEST_USER_ID
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from plone import api

from Products.CMFPlone.utils import safe_unicode
from Products.statusmessages.interfaces import IStatusMessage

from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..vocabularies import AssignedUsersVocabulary


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail', id='c1')
        self.omf = self.portal['outgoing-mail']

    def test_dmsdocument_modified(self):
        # owner changing test
        registry = getUtility(IRegistry)
        orgs = registry[ORGANIZATIONS_REGISTRY]
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

    def test_dmsmainfile_modified(self):
        pc = self.portal.portal_catalog
        rid = pc(id='c1')[0].getRID()
        # before mainfile creation
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010'])
        # after mainfile creation
        f1 = createContentInContainer(self.imail, 'dmsmainfile', id='f1', scan_id='010999900000690')
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', u'010999900000690', 'imio010999900000690', u'690'])
        # after mainfile modification
        f1.scan_id = '010999900000691'
        zope.event.notify(ObjectModifiedEvent(f1, Attributes(IScanFields, 'IScanFields.scan_id')))
        index_value = pc._catalog.getIndex("SearchableText").getEntryForObject(rid, default=[])
        self.assertListEqual(index_value, ['e0010', u'010999900000691', 'imio010999900000691', u'691'])
        # event without scan_id attribute
        zope.event.notify(ObjectModifiedEvent(f1))

    def test_user_related_modification(self):
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef')]))
        # we change a user property
        member = api.user.get(userid='chef')
        member.setMemberProperties({'fullname': 'Michel Chef 2'})
        # we simulate the user form change event
        zope.event.notify(ConfigurationChangedEvent(UserDataConfiglet(self.portal, self.portal.REQUEST), {}))
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef 2')]))
        # we change the activated services
        registry = getUtility(IRegistry)
        registry[ORGANIZATIONS_REGISTRY] = registry[ORGANIZATIONS_REGISTRY][0:1]
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('chef', 'Michel Chef 2')]))
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

    def test_group_deleted(self):
        request = self.portal.REQUEST
        # protected group
        self.assertRaises(Redirect, api.group.delete, groupname='expedition')
        smi = IStatusMessage(request)
        msgs = smi.show()
        self.assertEqual(msgs[0].message, u"You cannot delete the group 'expedition'.")
        # is used in content
        registry = getUtility(IRegistry)
        group = '%s_editeur' % registry[ORGANIZATIONS_REGISTRY][0]
        self.assertRaises(Redirect, api.group.delete, groupname=group)
        msgs = smi.show()
        orga = api.content.find(UID=registry[ORGANIZATIONS_REGISTRY][0])[0]
        if ' used in ' in msgs[0].message:
            self.assertEqual(msgs[0].message, u"You cannot delete the group '%s', used in 'Assigned group' index."
                             % group)
        else:
        # message from collective.contact.plonegroup
            self.assertEqual(msgs[0].message, u"You cannot delete the group '%s', linked to used organization '%s'." % (
                             group, safe_unicode(orga.Title)))

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
        registry = getUtility(IRegistry)
        e_groups = [('%s_encodeur' % uid, ('Contributor', )) for uid in registry[ORGANIZATIONS_REGISTRY]]
        e_groups.append(('admin', ('Owner',)))
        e_groups.append(('expedition', ('Contributor',)))
        e_groups.append(('dir_general', ('Contributor',)))
        self.assertSetEqual(set(self.omf.get_local_roles()), set(e_groups))
        self.assertEqual(len(self.omf.get_local_roles()), 14)
        registry[ORGANIZATIONS_REGISTRY] = registry[ORGANIZATIONS_REGISTRY][:3]
        self.assertEqual(len(self.omf.get_local_roles()), 6)
