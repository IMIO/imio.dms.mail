# -*- coding: utf-8 -*-

from imio.dms.mail.setuphandlers import createStateTopics
from imio.dms.mail.setuphandlers import createTopicView
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
        if not base_hasattr(folder, 'collections'):
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
        createStateTopics(col_folder, 'dmsincomingmail')
        createTopicView(col_folder, 'dmsincomingmail', u'all_incoming_mails')

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.3.1...')
        self.cleanRegistries()
        self.reinstall(['imio.actionspanel:default', 'collective.task:default'])
        self.importImioDmsMailStep(('typeinfo', 'workflow', 'update-workflow-rolemap', 'viewlets', 'componentregitry'))
        self.createNotEncodedPerson()
        self.changeTopicsFolder()
        self.portal.portal_workflow.updateRoleMappings()
        self.upgradeAll()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_3_1(context).run()
