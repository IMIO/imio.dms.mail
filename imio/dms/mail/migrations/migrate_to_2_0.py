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

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.0...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-addOwnPersonnel'], profile='examples')
        #self.runProfileSteps('imio.dms.mail', steps=[])

        # set mail-searches folder as not next/prev navigable
        # if not INextPrevNotNavigable.providedBy(im_folder['task-searches']):
        #     alsoProvides(im_folder['task-searches'], INextPrevNotNavigable)

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
