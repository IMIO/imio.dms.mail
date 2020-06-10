# -*- coding: utf-8 -*-

from collective.documentgenerator.utils import update_oo_config
from collective.messagesviewlet.utils import add_message
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.widgets.storage import Criterion
from imio.dms.mail import _tr as _
from imio.dms.mail.setuphandlers import set_portlet
from imio.dms.mail.utils import update_solr_config
from imio.migrator.migrator import Migrator
from plone import api
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility

import logging


logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_2_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.2.1...')

        # check if oo port or solr port must be changed
        update_solr_config()
        update_oo_config()

        self.cleanRegistries()

        self.correct_actions()

        self.runProfileSteps('imio.dms.mail', steps=['actions'])

        # do various global adaptations
        self.update_site()

        self.update_dashboards()

        # update templates
        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-update-templates'], profile='singles')

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['eea.facetednavigation', 'plonetheme.imio.apps']:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()

    def correct_actions(self):
        pa = self.portal.portal_actions
        if 'portlet' in pa:
            api.content.rename(obj=pa['portlet'], new_id='object_portlet')
            set_portlet(self.portal)

    def update_site(self):
        # change permission to remove dashboard from user menu
        self.portal.manage_permission('Portlets: Manage own portlets', ('Manager', 'Site Administrator'), acquire=0)
        # clean old messages
        if 'doc' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['doc'])
            add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="https://docs.imio.be/'
                        u'imio-doc/ia.docs/" target="_blank">documentation en ligne de la '
                        u'dernière version</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                        can_hide=True, req_roles=['Authenticated'], activate=False)
        if 'new-version' in self.portal['messages-config']:
            api.content.delete(self.portal['messages-config']['new-version'])
            add_message('new-version', 'Nouvelles fonctionnalités', u'<p>Vous pouvez consulter la <a href="https://'
                        u'www.imio.be/" target="_blank">liste des nouvelles fonctionnalités</a></p>',
                        msg_type='significant', can_hide=True, req_roles=['Authenticated'], activate=False)

    def update_dashboards(self):
        # update daterange criteria
        brains = api.content.find(object_provides=IFacetedNavigable.__identifier__)
        for brain in brains:
            obj = brain.getObject()
            criterion = ICriteria(obj)
            for key, criteria in criterion.items():
                if criteria.get("widget") != "daterange":
                    continue
                if criteria.get("usePloneDateFormat") is True:
                    continue
                logger.info("Upgrade daterange widget for faceted {0}".format(obj))
                position = criterion.criteria.index(criteria)
                values = criteria.__dict__
                values["usePloneDateFormat"] = True
                values["labelStart"] = u'Start date'
                values["labelEnd"] = u'End date'
                criterion.criteria[position] = Criterion(**values)
                criterion.criteria._p_changed = 1


def migrate(context):
    '''
    '''
    Migrate_To_2_2_1(context).run()
