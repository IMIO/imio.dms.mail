from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class TestSetuphandlers(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_create_persons_from_users(self):
        pf = self.portal['contacts']['personnel-folder']
        self.assertListEqual(pf.objectIds(), ['chef', 'dirg', 'agent1', 'agent'])
        member = self.portal.portal_registration.addMember(id='newuser', password='TestUser=6')
        member.setMemberProperties({'fullname': 'Leloup Pierre', 'email': 'test@macommune.be'})
        orgs = get_registry_organizations()
        api.group.add_user(groupname='%s_encodeur' % orgs[0], username='newuser')
        # with the added subscriber, the person and held_position are already added
        api.content.delete(pf['newuser'])
        self.portal.portal_setup.runImportStepFromProfile('imio.dms.mail:singles',
                                                          'imiodmsmail-create-persons-from-users-inverted',
                                                          run_dependencies=False)
        # person
        self.assertListEqual(pf.objectIds(), ['chef', 'dirg', 'agent1', 'agent', 'newuser'])
        nu_p = pf['newuser']
        self.assertEqual(nu_p.firstname, 'Pierre')
        self.assertEqual(nu_p.lastname, 'Leloup')
        self.assertEqual(nu_p.portal_type, 'person')
        # held position
        self.assertIn(orgs[0], nu_p)
        nu_hp = nu_p[orgs[0]]
        self.assertEqual(nu_hp.portal_type, 'held_position')
        self.assertEqual(nu_hp.position.to_path, '/plone/contacts/plonegroup-organization/direction-generale')
        # mixed with manual content
        api.content.rename(obj=nu_p, new_id='newuser_renamed')
        api.content.rename(obj=nu_hp, new_id='%s_renamed' % orgs[0])
        api.group.add_user(groupname='%s_encodeur' % orgs[1], username='newuser')
        api.content.delete(pf['newuser_renamed'][orgs[1]])
        self.portal.portal_setup.runImportStepFromProfile('imio.dms.mail:singles',
                                                          'imiodmsmail-create-persons-from-users-inverted',
                                                          run_dependencies=False)
        self.assertListEqual(pf.objectIds(), ['chef', 'dirg', 'agent1', 'agent', 'newuser_renamed'])
        self.assertListEqual(nu_p.objectIds(), ['%s_renamed' % orgs[0], orgs[1]])
