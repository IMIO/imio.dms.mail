# -*- coding: utf-8 -*-

import logging

from zope.component import getUtility
from zope.interface import alsoProvides

from plone import api
from plone.registry.interfaces import IRegistry

from Products.CPUtils.Extensions.utils import mark_last_version, configure_ckeditor
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.helpers.catalog import addOrUpdateColumns, addOrUpdateIndexes
from imio.migrator.migrator import Migrator

from ..interfaces import IIMTaskDashboard
from ..setuphandlers import blacklistPortletCategory, reimport_faceted_config

logger = logging.getLogger('imio.dms.mail')


class Migrate_To_1_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')

    def update_dmsmainfile(self):
        """ Update searchabletext """
        brains = self.catalog.searchResults(portal_type='dmsmainfile')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def update_dmsincomingmail(self):
        """ Update searchabletext """
        brains = self.catalog.searchResults(portal_type='dmsincomingmail')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def add_view_field(self, fldname, folder, ids=[], before=''):
        """ Insert view field on DashboardCollection """
        crit = {'portal_type': 'DashboardCollection',
                'path': {'query': '/'.join(folder.getPhysicalPath()), 'depth': 1}}
        if ids:
            crit['id'] = ids
        brains = self.catalog.searchResults(crit)
        for brain in brains:
            col = brain.getObject()
            fields = list(col.getCustomViewFields())
            # if already activated, we pass
            if fldname in fields:
                continue
            # find before position
            i = len(fields)
            if before:
                try:
                    i = fields.index(before)
                except ValueError:
                    pass
            fields.insert(i, fldname)
            col.setCustomViewFields(tuple(fields))

    def update_count(self, folder, ids=[]):
        """ Set showNumberOfItems on collection """
        crit = {'portal_type': 'DashboardCollection',
                'path': {'query': '/'.join(folder.getPhysicalPath()), 'depth': 1}}
        if ids:
            crit['id'] = ids
        brains = self.catalog.searchResults(crit)
        for brain in brains:
            col = brain.getObject()
            col.showNumberOfItems = True

    def configure_autocomplete_widget(self, folder):
        """ Configure and add autocomplete widget """
        # ajouter ++resource++select2/select2_locale_fr.js dans portal_javascript
        reimport_faceted_config(folder, xml='im-mail-searches.xml', default_UID=folder['all_mails'].UID())
        # we reindex organizations
        for brain in self.catalog(portal_type='organization'):
            brain.getObject().reindexObject(idxs=['sortable_title'])

    def update_validation_collections(self):
        brains = self.catalog.searchResults(portal_type='DashboardCollection', id='to_validate')
        for brain in brains:
            col = brain.getObject()
            for dic in col.query:
                if dic['i'] == 'CompoundCriterion' and dic['v'].endswith('-highest-validation'):
                    dic['v'] = dic['v'].replace('-highest-validation', '-validation')

    def run(self):
        logger.info('Migrating to imio.dms.mail 1.1...')
        self.cleanRegistries()
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'cssregistry', 'jsregistry', 'workflow'])
        self.runProfileSteps('collective.messagesviewlet', steps=['collective-messagesviewlet-messages'],
                             profile='messages')
        self.upgradeProfile('collective.dms.mailcontent:default')
        self.upgradeProfile('collective.task:default')
        self.upgradeProfile('eea.facetednavigation:default')
        im_folder = self.portal['incoming-mail']

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        # set mail-searches folder as not newt/prev navigable
        if not INextPrevNotNavigable.providedBy(im_folder['task-searches']):
            alsoProvides(im_folder['task-searches'], INextPrevNotNavigable)

        # activate field on DashboardCollection
        self.add_view_field('mail_type', im_folder['mail-searches'], before='CreationDate')
        self.add_view_field('sender', im_folder['mail-searches'], before='CreationDate')
        self.add_view_field('task_parent', im_folder['task-searches'], before='review_state')

        # set showNumberOfItems on some collections
        self.update_count(im_folder['mail-searches'], ids=['to_validate', 'to_treat', 'im_treating', 'created'])
        self.update_count(im_folder['task-searches'], ids=['to_validate', 'to_treat', 'im_treating'])

        # update criterion on validation collections
        self.update_validation_collections()

        # Activate browser message
        msg = self.portal['messages-config']['browser-warning']
        api.content.transition(obj=msg, to_state='activated')

        # update searchabletext
        self.update_dmsmainfile()
        self.update_dmsincomingmail()

        # add new indexes
        addOrUpdateIndexes(self.portal, indexInfos={'state_group': ('FieldIndex', {})})

        # add metadata in portal_catalog
        addOrUpdateColumns(self.portal, columns=('mail_type',))

        # block parent portlets on contacts
        blacklistPortletCategory(self.portal, self.portal['contacts'])

        # add local roles
        self.portal['contacts'].manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])

        # configure autocomplete widget
        self.configure_autocomplete_widget(im_folder['mail-searches'])

        # configure task batch actions
        alsoProvides(im_folder['task-searches'], IIMTaskDashboard)

        # reimport contact faceted config
        reimport_faceted_config(self.portal['contacts'], xml='contacts-faceted.xml')

        # remove tinymce resources
        configure_ckeditor(self.portal, default=0, allusers=0, forceTextPaste=0, scayt=0)

#        self.upgradeAll()

        for prod in ['plone.formwidget.autocomplete', 'collective.plonefinder', 'plone.formwidget.contenttree',
                     'plone.app.dexterity', 'plone.formwidget.masterselect', 'collective.behavior.talcondition',
                     'collective.contact.facetednav', 'collective.contact.plonegroup', 'collective.contact.widget',
                     'collective.dms.batchimport', 'collective.dms.scanbehavior', 'collective.documentgenerator',
                     'collective.eeafaceted.collectionwidget', 'collective.eeafaceted.z3ctable',
                     'collective.messagesviewlet', 'collective.querynextprev', 'dexterity.localroles',
                     'dexterity.localrolesfield', 'imio.actionspanel', 'imio.dashboard', 'imio.dms.mail',
                     'plone.formwidget.datetime', 'plonetheme.imioapps']:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_1_1(context).run()
