from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import get_registry_functions
from dexterity.localrolesfield.utils import get_localrole_fields
from eea.facetednavigation.interfaces import ICriteria
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility

import unittest


class TestSetuphandlers(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_postInstall(self):
        self.assertTrue(hasattr(self.portal, 'incoming-mail'))
        self.assertTrue(hasattr(self.portal, 'outgoing-mail'))

    def test_adaptDefaultPortal(self):
        #ltool = self.portal.portal_languages
        #defaultLanguage = 'fr'
        #supportedLanguages = ['en','fr']
        #ltool.manage_setLanguageSettings(defaultLanguage, supportedLanguages, setUseCombinedLanguageCodes=False)
        #ltool.setLanguageBindings()
        self.assertFalse(hasattr(self.portal, 'news'))
        self.assertFalse(hasattr(self.portal, 'events'))
        #check front-page modification
        self.assertIn('Gestion du courrier', self.portal['front-page'].Title())
        #check old Topic activation
        self.assertTrue('Collection (old-style)' in [pt.title for pt in self.portal.allowedContentTypes()])

    def test_configureBatchImport(self):
        registry = getUtility(IRegistry)
        fs_root_directory = registry['collective.dms.batchimport.batchimport.ISettings.fs_root_directory']
        self.assertTrue(fs_root_directory.endswith('batchimport/toprocess'))
        code_to_type_mapping = registry['collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping']
        self.assertEquals(len(code_to_type_mapping), 1)
        self.assertEquals(code_to_type_mapping[0]['code'], u'in')
        self.assertEquals(code_to_type_mapping[0]['portal_type'], u'dmsincomingmail')

    def test_addTestDirectory(self):
        #checking directory
        self.assertTrue(hasattr(self.portal, 'contacts'))
        contacts = self.portal['contacts']
        self.assertEquals(len(contacts.position_types), 5)
        self.assertEquals(len(contacts.organization_types), 7)
        self.assertEquals(len(contacts.organization_levels), 3)
        #checking organizations
        organizations = contacts.listFolderContents(contentFilter={'portal_type': 'organization'})
        self.assertEquals(len(organizations), 3)
        #checking positions
        pc = self.portal.portal_catalog
        positions = pc(portal_type=('position',), path={"query": 'plone/contacts'})
        self.assertEquals(len(positions), 0)
        #checking persons
        persons = contacts.listFolderContents(contentFilter={'portal_type': 'person'})
        self.assertEquals(len(persons), 4)
        #checking held positions
        held_positions = pc(portal_type=('held_position',), path={"query": 'plone/contacts'},
                            object_provides='collective.contact.plonegroup.interfaces.INotPloneGroupContact')
        self.assertEquals(len(held_positions), 3)

    def test_addTestMails(self):
        #checking incoming mails
        pc = self.portal.portal_catalog
        imails = pc(portal_type=('dmsincomingmail',), path={"query": 'plone/incoming-mail'})
        self.assertEquals(len(imails), 9)
        #checking outgoing mails
        omails = pc(portal_type=('dmsoutgoingmail',), path={"query": 'plone/outgoing-mail'})
        self.assertEquals(len(omails), 9)

    def test_addTestUsersAndGroups(self):
        #checking groups
        acl_users = getToolByName(self.portal, 'acl_users')
        lecteurs = [gd for gd in acl_users.searchGroups() if gd['groupid'].endswith('_lecteur')]
        self.assertEquals(len(lecteurs), 11)
        #checking users
        mt = getToolByName(self.portal, 'portal_membership')
        users = [member for member in mt.listMembers()
                 if member.getProperty('fullname').find(' ') >= 1]
        self.assertEquals(len(users), 6)

    def ttest_addTemplates(self):
        self.assertIn('templates', self.portal)
        self.assertEqual(len(self.portal['templates'].listFolderContents()), 2)

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

    def test_configure_group_encoder(self):
        # activate imail group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder', True)
        self.assertIn(u'group_encoder', [fct['fct_id'] for fct in get_registry_functions()])
        for portal_type in ('dmsincomingmail', 'dmsincoming_email'):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)])
            self.assertTrue(fti.localroles.get('creating_group'))  # config dic not empty
        crit = ICriteria(self.portal['incoming-mail']['mail-searches'])
        self.assertIn('c90', crit.keys())

        # activate omail group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder', True)
        self.assertIn(u'group_encoder', [fct['fct_id'] for fct in get_registry_functions()])
        for portal_type in ('dmsoutgoingmail', 'dmsoutgoing_email'):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)])
            self.assertTrue(fti.localroles.get('creating_group'))  # config dic not empty
        crit = ICriteria(self.portal['outgoing-mail']['mail-searches'])
        self.assertIn('c90', crit.keys())

        # activate contact group encoder
        api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder', True)
        self.assertIn(u'group_encoder', [fct['fct_id'] for fct in get_registry_functions()])
        for portal_type in ('organization', 'person', 'held_position', 'contact_list'):
            fti = getUtility(IDexterityFTI, name=portal_type)
            self.assertIn('creating_group', [tup[0] for tup in get_localrole_fields(fti)])
        for fid in ('orgs-searches', 'persons-searches', 'hps-searches', 'cls-searches'):
            crit = ICriteria(self.portal['contacts'][fid])
            self.assertIn('c90', crit.keys())
