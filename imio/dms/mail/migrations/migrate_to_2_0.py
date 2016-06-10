# -*- coding: utf-8 -*-

import logging

from zope.component import getUtility
from zope.interface import alsoProvides

from plone import api
from plone.registry.interfaces import IRegistry

from Products.CPUtils.Extensions.utils import mark_last_version
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.migrator.migrator import Migrator

from ..setuphandlers import configure_om_rolefields, createIMailCollections

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_0(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def delete_outgoing_examples(self):
        for brain in self.catalog(portal_type='dmsoutgoingmail', id=['reponse1', 'reponse2', 'reponse3', 'reponse4',
                                  'reponse5', 'reponse6', 'reponse7', 'reponse8', 'reponse9']):
            api.content.delete(obj=brain.getObject())

    def update_site(self):
        omf = self.portal['outgoing-mail']
        # publish outgoing-mail folder
        if api.content.get_state(omf) != 'internally_published':
            api.content.transition(obj=omf, to_state="internally_published")
        # add group
        if api.group.get('expedition') is None:
            api.group.create('expedition', '1 Expédition courrier sortant')
        # rename group title
        encodeurs = api.group.get('encodeurs')
        if encodeurs.getProperty('title') != '1 Encodeurs courrier entrant':
            self.portal.portal_groups.editGroup('encodeurs', title='1 Encodeurs courrier entrant')
        # add new collection to_treat_in_my_group
        createIMailCollections(self.imf['mail-searches'])
        # update permission
        if 'Site Administrator' not in [dic['name'] for dic in
                                        self.portal.rolesOfPermission("imio.dms.mail : Write userid field")
                                        if dic['selected'] == 'SELECTED']:
            self.portal.manage_permission('imio.dms.mail : Write userid field', ('Manager', 'Site Administrator'),
                                          acquire=0)

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.0...')
        self.cleanRegistries()
        self.delete_outgoing_examples()
        self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry', 'typeinfo'])
        self.runProfileSteps('imio.dms.mail', profile='examples',
                             steps=['imiodmsmail-addOwnPersonnel', 'imiodmsmail-configureImioDmsMail'])

        # do various global adaptations
        self.update_site()

        # configure role fields on dmsoutgoingmail
        configure_om_rolefields(self.portal)

        # set front-page folder as not next/prev navigable
        if not INextPrevNotNavigable.providedBy(self.portal['front-page']):
            alsoProvides(self.portal['front-page'], INextPrevNotNavigable)

        # self.upgradeAll()

        # self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in []:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_0(context).run()
