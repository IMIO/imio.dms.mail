# -*- coding: utf-8 -*-

from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY, ORGANIZATIONS_REGISTRY
from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def _rename_own_organization(self):
        logger.info('Rename own-organization')
        if base_hasattr(self.portal.contacts, 'own-organization'):
            self.portal.contacts.manage_renameObject('own-organization', 'plonegroup-organization')
        if not base_hasattr(self.portal.contacts, 'plonegroup-organization'):
            logger.error('ERROR!! own-organization not renamed')

    def _deleteOldLocalRoles(self):
        """ Delete old local roles """
        logger.info("Delete old local roles.")
        brains = self.portal.portal_catalog(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            for groups in (obj.treating_groups, obj.recipient_groups):
                if groups:
                    obj.manage_delLocalRoles(groups)

    def _configure_plonegroup(self):
        logger.info("Configure contact plone group")
        pcat = self.portal.portal_catalog
        own_orga = self.portal.contacts['plonegroup-organization']
        # dict containing uid value for a title combination
        self.uids = {}
        # uid list
        uids = []
        brains = pcat(path={"query": '/'.join(own_orga.getPhysicalPath()), "depth": 1}, portal_type="organization",
                      sort_on="getObjPositionInParent")
        for brain in brains:
            dep = brain.getObject()
            self.uids[dep.Title()] = dep.UID()
            uids.append(dep.UID())
            services_brains = pcat(path={"query": '/'.join(dep.getPhysicalPath()), "depth": 1},
                                   portal_type="organization", sort_on="getObjPositionInParent")
            for service_brain in services_brains:
                comb = "%s - %s" % (dep.Title(), service_brain.Title)
                self.uids[comb] = service_brain.UID
                uids.append(service_brain.UID)

        registry = getUtility(IRegistry)
        if not registry.get(FUNCTIONS_REGISTRY):
            registry[FUNCTIONS_REGISTRY] = [
                {'fct_title': u'Encodeur', 'fct_id': u'encodeur'},
                {'fct_title': u'Lecteur', 'fct_id': u'lecteur'},
                {'fct_title': u'Éditeur', 'fct_id': u'editeur'},
                {'fct_title': u'Validateur', 'fct_id': u'validateur'},
            ]
        if not registry.get(ORGANIZATIONS_REGISTRY):
            registry[ORGANIZATIONS_REGISTRY] = uids

    def _replacePrincipalIdsByOrganizationUids(self):
        logger.info("Replace principal ids of localrolefields by organization uids.")
        pcat = self.portal.portal_catalog

        brains = pcat(portal_type='dmsincomingmail')

        def split_principals(principals):
            ret = []
            for principal_id in principals:
                ret.append(principal_id.split('_')[0])
            return ret

        def get_uids(obj, attr):
            ret = []
            for principal in getattr(obj, attr):
                if principal not in self.uids:
                    logger.error("principal '%s' not in uids dict for '%s'" % (principal, obj))
                    return ['ERROR']
                ret.append(self.uids[principal])
            return ret

        for brain in brains:
            obj = brain.getObject()
            if obj.treating_groups:
                if obj.treating_groups[0].find('_') > 0:
                    obj.treating_groups = split_principals(obj.treating_groups)
                else:
                    obj.treating_groups = get_uids(obj, 'treating_groups')
            if obj.recipient_groups:
                if obj.recipient_groups[0].find('_') > 0:
                    obj.recipient_groups = split_principals(obj.recipient_groups)
                else:
                    obj.recipient_groups = get_uids(obj, 'recipient_groups')

    def _configure_product(self):
        logger.info("Configure folders")
        from imio.dms.mail.setuphandlers import _, createTopicView, createStateTopics
        folder = self.portal['incoming-mail']
        folder.setConstrainTypesMode(0)
        createTopicView(folder, 'dmsincomingmail', _(u'all_incoming_mails'))
        createStateTopics(self.portal, folder, 'dmsincomingmail')
        folder.setConstrainTypesMode(1)
        folder.setLocallyAllowedTypes(['dmsincomingmail'])
        folder.setImmediatelyAddableTypes(['dmsincomingmail'])
        self.portal.portal_workflow.doActionFor(folder, "show_internally")
        folder.manage_delObjects(ids=['topic_page'])
        folder = self.portal['outgoing-mail']
        folder.setConstrainTypesMode(0)
        createTopicView(folder, 'dmsoutgoingmail', _('Outgoing mail'))
        folder.setConstrainTypesMode(1)
        folder.setLocallyAllowedTypes(['dmsoutgoingmail'])
        folder.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        logger.info("Configure document viewer")
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:examples',
                                                          'imiodmsmail-configureDocumentViewer')

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.2...')
        self.upgradeProfile('collective.dms.mailcontent:default')
        self.reinstall(['collective.contact.plonegroup:default'])
        self._rename_own_organization()
        self._deleteOldLocalRoles()
        self._configure_plonegroup()
        self._replacePrincipalIdsByOrganizationUids()
        self.portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:default',
                                                          'workflow')
        self._configure_product()


def migrate(context):
    '''
    '''
    Migrate_To_0_2(context).run()
