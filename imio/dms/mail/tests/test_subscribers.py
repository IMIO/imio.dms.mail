# -*- coding: utf-8 -*-
import unittest

import zope.event
from zope.lifecycleevent import ObjectModifiedEvent

from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.testing import setRoles, TEST_USER_ID
from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.dexterity.utils import createContentInContainer
from plone import api

from ..testing import DMSMAIL_INTEGRATION_TESTING
from ..vocabularies import AssignedUsersVocabulary


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail')

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

    def test_user_modified(self):
        voc_inst = AssignedUsersVocabulary()
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef')]))
        member = api.user.get(userid='chef')
        member.setMemberProperties({'fullname': 'Michel Chef 2'})
        zope.event.notify(ConfigurationChangedEvent(UserDataConfiglet(self.portal, self.portal.REQUEST), {}))
        voc_list = [(t.value, t.title) for t in voc_inst(self.imail)]
        self.assertSetEqual(set(voc_list), set([('agent', 'Fred Agent'), ('chef', 'Michel Chef 2')]))
