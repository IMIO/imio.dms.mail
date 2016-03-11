# -*- coding: utf-8 -*-
import unittest

import zope.event
from zope.component import getUtility
from zope.lifecycleevent import ObjectModifiedEvent, Attributes

from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.testing import setRoles, TEST_USER_ID
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from plone import api

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

    def test_replace_scanner(self):
        with api.env.adopt_user(username='scanner'):
            imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                             **{'title': 'IMail created by scanner'})
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
