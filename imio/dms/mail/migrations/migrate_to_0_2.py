# -*- coding: utf-8 -*-

from imio.migrator.migrator import Migrator

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_2(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)

    def _deleteOldLocalRoles(self):
        """ Delete old local roles """
        logger.info("Delete old local roles.")
        brains = self.portal.portal_catalog(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            for groups in (obj.treating_groups, obj.recipient_groups):
                if groups:
                    obj.manage_delLocalRoles(groups)

    def _replacePrincipalIdsByOrganizationUids(self):
        logger.info("Replace principal ids of localrolefields by organization uids.")
        pcat = self.portal.portal_catalog
        own_orga = self.portal.contacts['plonegroup-organization']
        uids = {}
        brains = pcat(path={"query": '/'.join(own_orga.getPhysicalPath()), "depth": 1}, portal_type="organization",
                      sort_on="getObjPositionInParent")
        for brain in brains:
            dep = brain.getObject()
            services_brains = pcat(path={"query": '/'.join(dep.getPhysicalPath()), "depth": 1},
                                   portal_type="organization", sort_on="getObjPositionInParent")
            if not services_brains:
                uids[dep.Title()] = dep.UID()
            for service_brain in services_brains:
                comb = "%s - %s" % (dep.Title(), service_brain.Title)
                uids[comb] = service_brain.UID

        brains = pcat(portal_type='dmsincomingmail')

        def split_principals(principals):
            ret = []
            for principal_id in principals:
                ret.append(principal_id.split('_')[0])
            return ret

        def get_uids(obj, attr):
            ret = []
            for principal in getattr(obj, attr):
                if principal not in uids:
                    logger.error("principal '%s' not in uids dict for '%s'" % (principal, obj))
                    return ['ERROR']
                ret.append(uids[principal])
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

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.2...')
        self.upgradeProfile('collective.dms.mailcontent')
        self.reinstall('collective.contact.plonegroup:default')
        self._deleteOldLocalRoles()
        self._replacePrincipalIdsByOrganizationUids()


def migrate(context):
    '''
    '''
    Migrate_To_0_2(context).run()
