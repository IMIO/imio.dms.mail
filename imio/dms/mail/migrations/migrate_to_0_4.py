# -*- coding: utf-8 -*-

from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.container import contained
from zope.event import notify
from zope.interface import alsoProvides, noLongerProvides

from plone import api
from plone.app.controlpanel.markup import MarkupControlPanelAdapter
from plone.dexterity import utils as dxutils
from plone.dexterity.interfaces import IDexterityFTI
import plone.dexterity.schema
from plone.registry.interfaces import IRegistry
from plone.supermodel.utils import syncSchema

from Products.CPUtils.Extensions.utils import configure_ckeditor
#from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.helpers.catalog import addOrUpdateIndexes
from imio.migrator.migrator import Migrator

from ..interfaces import IExternalContact, IInternalContact
from imio.dms.mail.interfaces import IIMDashboard
from ..setuphandlers import _, configure_faceted_folder, reimport_faceted_config
from ..setuphandlers import add_db_col_folder, configure_task_rolefields
from ..setuphandlers import createIMailCollections, createIMTaskCollections, createStateCollections

import logging
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_0_4(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)

    def delete_portlet(self, obj, portlet):
        """ Delete the defined portlet on obj """
        ann = IAnnotations(obj)
        columnkey = 'plone.leftcolumn'
        if not 'plone.portlets.contextassignments' in ann:
            logger.error("No portlets defined in this context")
        elif not columnkey in ann['plone.portlets.contextassignments']:
            logger.error("Column '%s' not found in portlets definition" % columnkey)
        elif not portlet in ann['plone.portlets.contextassignments'][columnkey]:
            logger.error("Portlet '%s' in '%s' not found in portlets definition" % (portlet, columnkey))
        else:
            fixing_up = contained.fixing_up
            contained.fixing_up = True
            del ann['plone.portlets.contextassignments'][columnkey][portlet]
            # revert our fixing_up customization
            contained.fixing_up = fixing_up

    def replaceCollections(self, im_folder):
        """ Replace Collection by DashboardCollection """
        if 'collections' in im_folder:
            api.content.delete(im_folder['collections'])

        im_folder.setConstrainTypesMode(0)
        col_folder = add_db_col_folder(im_folder, 'mail-searches', _("Incoming mail searches"),
                                       _('Incoming mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IIMDashboard)
        im_folder.moveObjectToPosition('mail-searches', 0)

        # re-create dashboard collections
        createIMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsincomingmail')
        configure_faceted_folder(col_folder, xml='im-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())

        col_folder = add_db_col_folder(im_folder, 'task-searches', _("Tasks searches"),
                                       _("I.M. tasks"))
        im_folder.moveObjectToPosition('task-searches', 1)
        createIMTaskCollections(col_folder)
        createStateCollections(col_folder, 'task')
        configure_faceted_folder(col_folder, xml='im-task-searches.xml',
                                 default_UID=col_folder['all_tasks'].UID())

        im_folder.setConstrainTypesMode(1)

    def remove_contact_interfaces(self):
        """ Remove deprecated interfaces on contact """
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(object_provides=['imio.dms.mail.interfaces.IInternalContact',
                                                        'imio.dms.mail.interfaces.IExternalContact'])
        for brain in brains:
            obj = brain.getObject()
            if IInternalContact.providedBy(obj):
                noLongerProvides(obj, IInternalContact)
            if IExternalContact.providedBy(obj):
                noLongerProvides(obj, IExternalContact)
            obj.reindexObject(idxs=['object_provides'])

    def update_local_roles(self):
        """ Add dexterity local roles config """
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        if 'static_config' in lr:
            lrsc = lr['static_config']
            if 'created' in lrsc and 'encodeurs' in lrsc['created'] and \
                    'IM Treating Group Writer' not in lrsc['created']['encodeurs']['roles']:
                lrsc['created']['encodeurs']['roles'].append('IM Treating Group Writer')
            for state in ['proposed_to_manager', 'proposed_to_service_chief', 'proposed_to_agent', 'in_treatment',
                          'closed']:
                if state in lrsc and 'dir_general' in lrsc[state] and \
                        'IM Treating Group Writer' not in lrsc[state]['dir_general']['roles']:
                    lrsc[state]['dir_general']['roles'].append('IM Treating Group Writer')
        lrtg = lr['treating_groups']
        if 'proposed_to_service_chief' in lrtg and 'validateur' in lrtg['proposed_to_service_chief'] and \
                'IM Treating Group Writer' not in lrtg['proposed_to_service_chief']['validateur']['roles']:
            lrtg['proposed_to_service_chief']['validateur']['roles'].append('IM Treating Group Writer')
        # We need to indicate that the object has been modified and must be "saved"
        fti._p_changed = True

    def update_dmsmainfile(self):
        """ Update searchabletext """
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults(portal_type='dmsmainfile')
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObject(idxs=['SearchableText'])

    def run(self):
        logger.info('Migrating to imio.dms.mail 0.4...')
        self.cleanRegistries()
        self.upgradeProfile('collective.dms.mailcontent:default')
        # We have to reapply type info before doing other subproducts migration
        self.runProfileSteps('imio.dms.mail', steps=['typeinfo'])
        # We have to update type schema because dexterity doesn't detect schema_policy modification. BUG
        for portal_type in ['dmsincomingmail', 'dmsoutgoingmail']:
            schemaName = dxutils.portalTypeToSchemaName(portal_type)
            schema = getattr(plone.dexterity.schema.generated, schemaName)
            fti = getUtility(IDexterityFTI, name=portal_type)
            model = fti.lookupModel()
            syncSchema(model.schema, schema, overwrite=True, sync_bases=True)
            notify(plone.dexterity.schema.SchemaInvalidatedEvent(portal_type))

        self.upgradeProfile('collective.task:default')
        self.upgradeProfile('dexterity.localroles:default')
        self.upgradeProfile('dexterity.localrolesfield:default')
        self.upgradeProfile('collective.contact.plonegroup:default')
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'componentregistry', 'controlpanel', 'portlets',
                                                     'repositorytool', 'rolemap', 'sharing', 'workflow'])
        self.portal.portal_workflow.updateRoleMappings()
        self.runProfileSteps('collective.dms.mailcontent', steps=['controlpanel'])
        self.runProfileSteps('collective.contact.plonegroup', steps=['controlpanel'])
        self.reinstall([
            'collective.messagesviewlet:messages',
            'collective.querynextprev:default',
            'imio.dashboard:default',
        ])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        # delete old dmsmail portlet
        self.delete_portlet(self.portal, 'portlet_maindmsmail')

        # remove deprecated interfaces
        self.remove_contact_interfaces()

        # set old vocabulary fields with new elephantvocabulary field
        #catalog = api.portal.get_tool('portal_catalog')
        #brains = catalog.searchResults(portal_type='dmsincomingmail')
        #for brain in brains:
        #    obj = brain.getObject()
        #    obj.treating_groups = obj.treating_groups and obj.treating_groups or
        #self.registry[ORGANIZATIONS_REGISTRY][0]
        #    obj.recipient_groups = obj.recipient_groups and obj.recipient_groups or None
        #    obj.assigned_group = None
        #    obj.reindexObject()

        # replace collections by Dashboard collections
        im_folder = self.portal['incoming-mail']
        alsoProvides(im_folder, INextPrevNotNavigable)
        alsoProvides(im_folder, IIMDashboard)
        self.replaceCollections(im_folder)

        # apply contact faceted config
        reimport_faceted_config(self.portal)

        # add new indexes for dashboard
        addOrUpdateIndexes(self.portal, indexInfos={'mail_type': ('FieldIndex', {}),
                                                    'mail_date': ('DateIndex', {}),
                                                    'in_out_date': ('DateIndex', {}),
                                                    })

        # set dashboard on incoming mail
        configure_faceted_folder(im_folder, xml='default_dashboard_widgets.xml',
                                 default_UID=im_folder['mail-searches']['all_mails'].UID())

        # set task local roles configuration
        configure_task_rolefields(self.portal)

        # update dexterity local roles configuration
        self.update_local_roles()

        # add task actionspanel config
        self.registry['imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions'] += \
            ['task.back_in_created|', 'task.back_in_to_assign|', 'task.back_in_to_do|',
             'task.back_in_progress|', 'task.back_in_realized|']

        # activate ckeditor
        configure_ckeditor(self.portal, custom='ged')

        # Set markup allowed types
        adapter = MarkupControlPanelAdapter(self.portal)
        adapter.set_allowed_types(['text/html'])

        self.update_dmsmainfile()

        #self.upgradeAll()
        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_0_4(context).run()
