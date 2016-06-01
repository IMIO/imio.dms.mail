# -*- coding: utf-8 -*-

import logging

from zope.component import getUtility
from zope.interface import alsoProvides

from plone import api
from plone.registry.interfaces import IRegistry

from Products.CPUtils.Extensions.utils import mark_last_version
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.migrator.migrator import Migrator

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_0(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')

    def delete_outgoing_examples(self):
        for brain in self.catalog(portal_type='dmsoutgoingmail', id=['reponse1', 'reponse2', 'reponse3', 'reponse4',
                                  'reponse5', 'reponse6', 'reponse7', 'reponse8', 'reponse9']):
            api.content.delete(obj=brain.getObject())

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.0...')
        self.cleanRegistries()
        self.delete_outgoing_examples()
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-addOwnPersonnel'], profile='examples')
        self.runProfileSteps('imio.dms.mail', steps=['typeinfo'])

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
