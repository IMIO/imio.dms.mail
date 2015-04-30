# -*- coding: utf-8 -*-

from zope.component import getUtility
from plone import api
from plone.dexterity.interfaces import IDexterityFTI

from imio.dms.mail.setuphandlers import createStateTopics, createTopicView, createIMTodoTopics, setupFacetedContacts, mark_organizations
from imio.helpers.catalog import addOrUpdateIndexes, addOrUpdateColumns
from imio.migrator.migrator import Migrator

from Products.CMFPlone.utils import base_hasattr

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_3_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def importImioDmsMailStep(self, step_ids):
        ''' Set ILocking behavior and reinstall workflow'''
        for step_id in step_ids:
            self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:default', step_id)

    def createNotEncodedPerson(self):
        ''' add not encoded person if not exists'''
        if not base_hasattr(self.portal.contacts, 'notencoded'):
            self.portal.contacts.invokeFactory('person', 'notencoded', lastname=u'Non encodé')
            self.portal.contacts.folder_position('top', 'notencoded')

    def createCollectionsFolder(self, folder):
        ''' Create Folder, if doesn't exist, who contain all topics'''
        if base_hasattr(folder, 'collections'):
            return
        folder.setConstrainTypesMode(0)
        folder.invokeFactory("Folder", id='collections', title=u"Collections: ne pas effacer")
        folder.setConstrainTypesMode(1)
        folder.folder_position('top', 'collections')
        folder.setDefaultPage('collections')
        col_folder = folder['collections']
        col_folder.setConstrainTypesMode(1)
        col_folder.setLocallyAllowedTypes(['Topic', 'Collection'])
        col_folder.setImmediatelyAddableTypes(['Topic', 'Collection'])

    def removeOldTopics(self, folder):
        ''' Remove all original topics'''
        topicsToRemove = self.portal.portal_catalog(portal_type='Topic',
                                                    path={'query': '/'.join(folder.getPhysicalPath()), 'depth': 1})
        folder.manage_delObjects([b.id for b in topicsToRemove])

    def changeTopicsFolder(self):
        ''' Remove old topics. Create a folder, if doesn't exist, who contain all topics.
            Use this folder as default page. Create new topics in this new folder.'''
        im_folder = self.portal['incoming-mail']
        self.removeOldTopics(im_folder)
        self.createCollectionsFolder(im_folder)
        col_folder = im_folder['collections']
        createTopicView(col_folder, 'dmsincomingmail', u'all_incoming_mails')
        createStateTopics(col_folder, 'dmsincomingmail')
        createIMTodoTopics(col_folder)

    def replaceRoleByGroup(self):
        gp = api.group.get('encodeurs')
        if gp.getProperty('title') == 'Encodeurs courrier':
            gp.setGroupProperties({'title': '1 Encodeurs courrier'})
        if api.group.get('dir_general') is None:
            api.group.create('dir_general', '1 Directeur général')
        for user in api.user.get_users():
            if user.has_role('General Manager'):
                api.group.add_user(groupname='dir_general', user=user)
        # remove General Manager role
        if 'General Manager' in self.portal.__ac_roles__:
            roles = list(self.portal.__ac_roles__)
            roles.remove('General Manager')
            self.portal.__ac_roles__ = tuple(roles)
        # add localroles config
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lrc = getattr(fti, 'localroleconfig')
        if 'proposed_to_manager' not in lrc or 'dir_general' not in lrc['proposed_to_manager']:
            for state in ['proposed_to_manager', 'proposed_to_service_chief', 'proposed_to_agent', 'in_treatment',
                          'closed']:
                if state not in lrc:
                    lrc[state] = {}
                lrc[state]['dir_general'] = ['Contributor', 'Editor', 'Reviewer', 'IM Field Writer']
        if 'created' not in lrc:
            lrc['created'] = {}
        if 'encodeurs' not in lrc['created']:
            lrc['created']['encodeurs'] = ['IM Field Writer']
        if 'encodeurs' in lrc['proposed_to_manager'] and 'IM Field Writer' not in \
                lrc['proposed_to_manager']['encodeurs']:
            lrc['proposed_to_manager']['encodeurs'].append('IM Field Writer')

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.3.1...')
        self.cleanRegistries()
        self.reinstall([
            'imio.actionspanel:default',
            'imio.history:default',
            'collective.task:default',
            'collective.compoundcriterion:default',
            'collective.behavior.talcondition:default',
            'collective.contact.facetednav:default',
            'collective.contact.duplicated:default',
            'plone.app.versioningbehavior:default',
        ])
        self.importImioDmsMailStep((
            'typeinfo',
            'workflow',
            'update-workflow-rolemap',
            'viewlets',
            'componentregistry',
            'catalog',
            'jsregistry',
            'repositorytool',
            'actions',
        ))
        api.portal.get_tool('portal_diff').setDiffForPortalType(
            'dmsincomingmail', {'any': "Compound Diff for Dexterity types"})
        self.createNotEncodedPerson()
        self.changeTopicsFolder()
        self.replaceRoleByGroup()
        self.portal.portal_workflow.updateRoleMappings()
        addOrUpdateIndexes(self.portal, indexInfos={'treating_groups': ('KeywordIndex', {}),
                                                    'recipient_groups': ('KeywordIndex', {}),
                                                    'organization_type': ('FieldIndex', {}),
                                                    })
        addOrUpdateColumns(self.portal, columns=('treating_groups', 'recipient_groups'))
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(portal_type='organization')
        for brain in brains:
            brain.getObject().reindexObject(idxs=['organization_type'])

        setupFacetedContacts(self.portal)

        # migrate plonegroup organizations
        mark_organizations(self.portal)

        self.upgradeAll()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_3_1(context).run()
