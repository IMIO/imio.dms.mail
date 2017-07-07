# -*- coding: utf-8 -*-

import copy
import logging

from zope import event
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.lifecycleevent import modified

from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr

from Products.CPUtils.Extensions.utils import mark_last_version, change_user_properties
#from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.documentgenerator.config import set_oo_port, set_uno_path
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.content import transitions
from imio.migrator.migrator import Migrator

from ..interfaces import IOMDashboard, ITaskDashboard
from ..setuphandlers import (_, add_db_col_folder, changeSearchedTypes, configure_om_rolefields, configure_task_config,
                             configure_task_rolefields, createIMailCollections, createStateCollections,
                             createOMailCollections, configure_faceted_folder, createTaskCollections, add_templates,
                             reimport_faceted_config)

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

    def manage_localroles(self):
        rpl = {'IM Field Writer': 'Base Field Writer', 'IM Treating Group Writer': 'Treating Group Writer'}
        # add new roles, remove old sharing utilities, add new sharing utilities
        self.runProfileSteps('imio.dms.mail', steps=['rolemap', 'sharing'])
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        changes = False
        if 'IM Field Writer' in self.portal.__ac_roles__:
            # delete old roles
            roles = list(self.portal.__ac_roles__)
            for role in rpl.keys():
                roles.remove(role)
            self.portal.__ac_roles__ = tuple(roles)
            # replace old roles in incomingmail fti config
            for k in lr:  # k is 'static_config' or a field name
                for state in lr[k]:
                    for princ in lr[k][state]:
                        lr[k][state][princ]['roles'] = [r in rpl and rpl[r] or r for r in lr[k][state][princ]['roles']]
            fti._p_changed = True  # doesn't work !!
            changes = True
        # add DmsFile Contributor role
        if 'static_config' in lr:
            lrsc = lr['static_config']
            if 'created' in lrsc and 'encodeurs' in lrsc['created'] and \
                    'DmsFile Contributor' not in lrsc['created']['encodeurs']['roles']:
                lrsc['created']['encodeurs']['roles'].append('DmsFile Contributor')
                fti._p_changed = True  # doesn't work !!
                changes = True
        if changes:
            setattr(fti, 'localroles', copy.copy(lr))
        # obj.reindexObjectSecurity() is done later

    def create_tasks_folder(self):
        if base_hasattr(self.portal['incoming-mail'], 'task-searches'):
            api.content.delete(obj=self.portal['incoming-mail']['task-searches'])
        if not base_hasattr(self.portal, 'tasks'):
            self.portal.invokeFactory("Folder", id='tasks', title=_(u"Tasks"))
            tsk_folder = getattr(self.portal, 'tasks')
            self.portal.moveObjectToPosition('tasks', self.portal.getObjectPosition('contacts'))
            # add task-searches
            col_folder = add_db_col_folder(tsk_folder, 'task-searches', _("Tasks searches"),
                                           _("Tasks"))
            alsoProvides(col_folder, INextPrevNotNavigable)
            alsoProvides(col_folder, ITaskDashboard)
            createTaskCollections(col_folder)
            createStateCollections(col_folder, 'task')
            configure_faceted_folder(col_folder, xml='im-task-searches.xml',
                                     default_UID=col_folder['all_tasks'].UID())
            # configure tasks faceted
            configure_faceted_folder(tsk_folder, xml='default_dashboard_widgets.xml',
                                     default_UID=col_folder['all_tasks'].UID())

            tsk_folder.setConstrainTypesMode(1)
            tsk_folder.setLocallyAllowedTypes(['task'])
            tsk_folder.setImmediatelyAddableTypes(['task'])
            self.portal.portal_workflow.doActionFor(tsk_folder, "show_internally")
            logger.info('tasks folder created')

    def migrate_tasks(self):
        for brain in self.catalog(portal_type='task'):
            obj = brain.getObject()
            # replace userid by organization
            if not obj.enquirer or obj.enquirer not in self.registry[ORGANIZATIONS_REGISTRY]:
                if base_hasattr(obj.aq_parent, 'treating_groups') and obj.aq_parent.treating_groups:
                    obj.enquirer = obj.aq_parent.treating_groups
                elif base_hasattr(obj.aq_parent, 'assigned_group') and obj.aq_parent.assigned_group:
                    obj.enquirer = obj.aq_parent.assigned_group
                modified(obj)

    def update_collections(self):
        """ No more applied """
        for folder, fid, colid in [(self.imf, 'mail-searches', 'all_mails'), (self.omf, 'mail-searches', 'all_mails'),
                                   (self.tkf, 'task-searches', 'all_tasks')]:
            col = folder[fid][colid]
            fields = list(col.getCustomViewFields())
            if u'actions' in fields:
                fields.remove(u'actions')
                col.setCustomViewFields(tuple(fields))

    def update_site(self):
        # documentgenerator config
        set_oo_port()
        set_uno_path()

        # add templates configuration
        add_templates(self.portal)

        # set som objects as not next/prev navigable
        for obj in (self.portal['front-page'], self.portal['contacts'], self.portal['templates']):
            if not INextPrevNotNavigable.providedBy(obj):
                alsoProvides(obj, INextPrevNotNavigable)

        # publish outgoing-mail folder
        if api.content.get_state(self.omf) != 'internally_published':
            transitions(self.omf, ["show_internally"])
        # add group
        if api.group.get('expedition') is None:
            api.group.create('expedition', '1 Expédition courrier sortant')
            self.portal['outgoing-mail'].manage_addLocalRoles('expedition', ['Contributor'])
            self.portal['contacts'].manage_addLocalRoles('expedition', ['Contributor', 'Editor', 'Reader'])
            api.group.add_user(groupname='expedition', username='scanner')
        # dir_general can add outgoing mails
        self.portal['outgoing-mail'].manage_addLocalRoles('dir_general', ['Contributor'])

        # rename group title
        encodeurs = api.group.get('encodeurs')
        if encodeurs.getProperty('title') != '1 Encodeurs courrier entrant':
            self.portal.portal_groups.editGroup('encodeurs', title='1 Encodeurs courrier entrant')
        # update im mail-searches
        # alsoProvides(self.imf['mail-searches'], ICollectionCategories)
        # add new collection to_treat_in_my_group
        createIMailCollections(self.imf['mail-searches'])
        reimport_faceted_config(self.imf['mail-searches'], xml='im-mail-searches.xml',
                                default_UID=self.imf['mail-searches']['all_mails'].UID())
        # update permissions
        for perm in ("imio.dms.mail: Write mail base fields", "imio.dms.mail: Write treating group field",
                     "imio.dms.mail: Write userid field"):
            if 'Site Administrator' not in [dic['name'] for dic in self.portal.rolesOfPermission(perm)
                                            if dic['selected'] == 'SELECTED']:
                self.portal.manage_permission(perm, ('Manager', 'Site Administrator'), acquire=0)

        # configure external edition
        self.portal.portal_memberdata.manage_changeProperties(ext_editor=True)
        self.registry['externaleditor.ext_editor'] = True
        if 'Image' in self.registry['externaleditor.externaleditor_enabled_types']:
            self.registry['externaleditor.externaleditor_enabled_types'] = ['PODTemplate', 'ConfigurablePODTemplate',
                                                                            'DashboardPODTemplate', 'SubTemplate',
                                                                            'StyleTemplate', 'dmsommainfile']
        change_user_properties(self.portal, kw='ext_editor:True', dochange='1')

        # searched types
        changeSearchedTypes(self.portal)

        # add documentation message
        add_message('doc2-0', 'Documentation 2.0', u'<p>Vous pouvez consulter la <a href="http://www.imio.be/'
                    u'support/documentation/topic/cp_app_ged" target="_blank">documentation en ligne de la '
                    u'version 2.0</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                    can_hide=True, req_roles=['Authenticated'], activate=True)

        val = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsoutgoingmail.back_to_agent|' not in val:
            val += ['dmsoutgoingmail.back_to_agent|', 'dmsoutgoingmail.back_to_creation|',
                    'dmsoutgoingmail.back_to_service_chief|', 'dmsoutgoingmail.back_to_print|',
                    'dmsoutgoingmail.back_to_be_signed|', 'dmsoutgoingmail.back_to_scanned|']
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           val)
        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 1.1':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

    def configure_dashboard(self):
        """ add DashboardCollection """
        alsoProvides(self.omf, INextPrevNotNavigable)
        alsoProvides(self.omf, IOMDashboard)
        self.omf.setConstrainTypesMode(0)
        col_folder = add_db_col_folder(self.omf, 'mail-searches', _("Outgoing mail searches"),
                                       _('Outgoing mails'))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOMDashboard)
        self.omf.moveObjectToPosition('mail-searches', 0)

        createOMailCollections(col_folder)
        createStateCollections(col_folder, 'dmsoutgoingmail')
        configure_faceted_folder(col_folder, xml='om-mail-searches.xml',
                                 default_UID=col_folder['all_mails'].UID())
        self.omf.setConstrainTypesMode(1)
        configure_faceted_folder(self.omf, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_mails'].UID())
        # add metadata in portal_catalog
        addOrUpdateColumns(self.portal, columns=('in_out_date',))

    def add_missing_transforms(self):
        """ pdf_to_... are maybe missing (if pdftotext not installed by example) """
        pt = self.portal.portal_transforms
        for name in ('pdf_to_text', 'pdf_to_html'):
            if name not in pt.objectIds():
                pt.manage_addTransform(name, "Products.PortalTransforms.transforms.%s" % name)
                logger.info("Added '%s' transform" % name)

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.0...')
        self.cleanRegistries()
        self.delete_outgoing_examples()
        self.upgradeProfile('collective.task:default')
        self.upgradeProfile('collective.contact.core:default')
        self.upgradeProfile('collective.dms.scanbehavior:default')
#        self.upgradeProfile('collective.schedulefield:default')
        self.manage_localroles()
        self.runProfileSteps('imio.dms.mail', steps=['actions', 'componentregistry', 'jsregistry', 'plone.app.registry',
                                                     'propertiestool', 'typeinfo', 'workflow'])
        self.portal.portal_workflow.updateRoleMappings()
        self.runProfileSteps('imio.dms.mail', profile='examples',
                             steps=['imiodmsmail-addOwnPersonnel', 'imiodmsmail-configureImioDmsMail'])

        # add missing pdf transforms
        self.add_missing_transforms()

        # configure dashboard on omf
        self.configure_dashboard()

        # do various global adaptations
        self.update_site()

        # configure local roles on omf and add folders in templates
        # call event to do it at modification
        record = self.registry.records.get('collective.contact.plonegroup.browser.settings.IContactPlonegroupConfig.'
                                           'organizations')
        event.notify(RecordModifiedEvent(record, [], []))

        # manage task for both incoming and outgoing mails
        self.create_tasks_folder()

        # migrate tasks: enquirer field
        self.migrate_tasks()

        # configure role fields on task
        configure_task_rolefields(self.portal, force=True)
        configure_task_config(self.portal)

        # remove actions on all_... collections
        #self.update_collections()

        # configure role fields on dmsoutgoingmail
        configure_om_rolefields(self.portal)

        # refresh some indexes
        brains = self.catalog.searchResults(portal_type=['dmsincomingmail'])
        for brain in brains:
            obj = brain.getObject()
            obj.reindexObjectSecurity()

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        self.catalog.reindexIndex(['assigned_user', 'mail_date', 'in_out_date', 'due_date'], self.portal.REQUEST)

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry'])

        self.reinstall([
            'collective.js.fancytree:default',
            'collective.js.fancytree:theme-vista',
        ])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ["plone.formwidget.autocomplete", "collective.ckeditor", "collective.plonefinder",
                     "plone.formwidget.contenttree", "collective.z3cform.datagridfield", "plone.app.dexterity",
                     "eea.facetednavigation", "eea.jquery", "plone.formwidget.masterselect", "collective.quickupload",
                     "plone.app.relationfield", "collective.behavior.talcondition", "collective.compoundcriterion",
                     "collective.contact.core", "collective.contact.duplicated", "collective.contact.facetednav",
                     "collective.contact.plonegroup", "collective.contact.widget", "collective.dms.basecontent",
                     "collective.dms.batchimport", "collective.dms.mailcontent", "collective.dms.scanbehavior",
                     "collective.documentgenerator", "collective.eeafaceted.collectionwidget",
                     "collective.eeafaceted.z3ctable", "collective.externaleditor", "collective.messagesviewlet",
                     "collective.querynextprev", "collective.task", "communesplone.layout", "dexterity.localroles",
                     "dexterity.localrolesfield", "imio.actionspanel", "imio.dashboard", "imio.dms.mail",
                     "imio.history", "plone.app.collection", "plonetheme.imioapps"]:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_0(context).run()
