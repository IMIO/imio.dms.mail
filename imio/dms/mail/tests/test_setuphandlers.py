import unittest
from zope.component import getUtility
from plone.app.testing import setRoles, TEST_USER_ID
from Products.CMFCore.utils import getToolByName
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING


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
        self.assertFalse(hasattr(self.portal, 'Members'))
        #check front-page modification
        self.assertEquals(getattr(self.portal, 'front-page').Title(), 'Gestion du courrier')
        #check old Topic activation
        self.assertTrue('Collection (old-style)' in [pt.title for pt in self.portal.allowedContentTypes()])

    def test_configureBatchImport(self):
        from plone.registry.interfaces import IRegistry
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
        self.assertEquals(len(contacts.organization_types), 4)
        self.assertEquals(len(contacts.organization_levels), 3)
        #checking organizations
        organizations = contacts.listFolderContents(contentFilter={'portal_type': 'organization'})
        self.assertEquals(len(organizations), 3)
        #checking positions
        pc = self.portal.portal_catalog
        positions = pc(portal_type=('position',), path={"query": 'plone/contacts'})
        self.assertEquals(len(positions), 2)
        #checking persons
        persons = contacts.listFolderContents(contentFilter={'portal_type': 'person'})
        self.assertEquals(len(persons), 4)
        #checking held positions
        held_positions = pc(portal_type=('held_position',), path={"query": 'plone/contacts'})
        self.assertEquals(len(held_positions), 3)

    def test_addTestMails(self):
        #checking incoming mails
        pc = self.portal.portal_catalog
        imails = pc(portal_type=('dmsincomingmail',), path={"query": 'plone/incoming-mail'})
        self.assertEquals(len(imails), 9)
        #checking outgoing mails
        omails = pc(portal_type=('dmsoutgoingmail',), path={"query": 'plone/outgoing-mail'})
        self.assertEquals(len(omails), 0)

    def test_addTestUsersAndGroups(self):
        #checking groups
        acl_users = getToolByName(self.portal, 'acl_users')
        lecteurs = [gd for gd in acl_users.searchGroups() if gd['groupid'].endswith('_lecteur')]
        self.assertEquals(len(lecteurs), 6)
        #checking users
        mt = getToolByName(self.portal, 'portal_membership')
        users = [member for member in mt.listMembers()
                 if member.getProperty('fullname').find(' ') >= 1]
        self.assertEquals(len(users), 5)
