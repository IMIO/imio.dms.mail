# -*- coding: utf-8 -*-

from collective.contact.facetednav.interfaces import IActionsEnabled
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES
from collective.documentviewer.convert import runConversion
from collective.documentviewer.settings import GlobalSettings
from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.wfadaptations.api import apply_from_registry
from eea.facetednavigation.settings.interfaces import IDisableSmartFacets
from eea.facetednavigation.settings.interfaces import IHidePloneLeftColumn
from eea.facetednavigation.settings.interfaces import IHidePloneRightColumn
from ftw.labels.interfaces import ILabelJar
from ftw.labels.interfaces import ILabelRoot
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IContactListsDashboard
from imio.dms.mail.interfaces import IContactListsDashboardBatchActions
from imio.dms.mail.interfaces import IDirectoryFacetedNavigable
from imio.dms.mail.interfaces import IHeldPositionsDashboard
from imio.dms.mail.interfaces import IHeldPositionsDashboardBatchActions
from imio.dms.mail.interfaces import IOrganizationsDashboard
from imio.dms.mail.interfaces import IPersonsDashboard
from imio.dms.mail.interfaces import IPersonsDashboardBatchActions
from imio.dms.mail.setuphandlers import _
from imio.dms.mail.setuphandlers import add_db_col_folder
from imio.dms.mail.setuphandlers import add_templates
from imio.dms.mail.setuphandlers import add_transforms
from imio.dms.mail.setuphandlers import blacklistPortletCategory
from imio.dms.mail.setuphandlers import configure_faceted_folder
from imio.dms.mail.setuphandlers import createContactListsCollections
from imio.dms.mail.setuphandlers import createDashboardCollections
from imio.dms.mail.setuphandlers import createHeldPositionsCollections
from imio.dms.mail.setuphandlers import createOrganizationsCollections
from imio.dms.mail.setuphandlers import createPersonsCollections
from imio.dms.mail.setuphandlers import reimport_faceted_config
from imio.helpers.content import transitions
from imio.migrator.migrator import Migrator
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from plone.app.uuid.utils import uuidToObject
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.Portal import member_indexhtml
from Products.CMFPlone.utils import _createObjectByType
from Products.CPUtils.Extensions.utils import dv_images_size
from Products.CPUtils.Extensions.utils import fileSize
from Products.CPUtils.Extensions.utils import mark_last_version
from Products.CPUtils.Extensions.utils import tobytes
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

import logging


# createStateCollections
logger = logging.getLogger('imio.dms.mail')


class Migrate_To_2_1(Migrator):

    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool('portal_catalog')
        self.imf = self.portal['incoming-mail']
        self.omf = self.portal['outgoing-mail']

    def set_Members(self):
        if 'Members' in self.portal:
            return
        _createObjectByType('Folder', self.portal, id='Members', title='Users', description="Site Users")
        util = getUtility(ITranslationDomain, 'plonefrontpage')
        members = getattr(self.portal, 'Members')
        members.setTitle(util.translate(u'members-title', target_language='fr', default='Users'))
        members.setDescription(util.translate(u'members-description', target_language='fr', default="Site Users"))
        members.unmarkCreationFlag()
        members.setLanguage('fr')
        members.setExcludeFromNav(True)
        members.setConstrainTypesMode(1)
        members.setLocallyAllowedTypes([])
        members.setImmediatelyAddableTypes([])
        members.reindexObject()
        self.portal.portal_membership.memberareaCreationFlag = 0
        self.portal.portal_membership.setMemberAreaType('member_area')

        transitions(members, 'show_internally')

        # add index_html to Members area
        if 'index_html' not in members.objectIds():
            addPy = members.manage_addProduct['PythonScripts'].manage_addPythonScript
            addPy('index_html')
            index_html = getattr(members, 'index_html')
            index_html.write(member_indexhtml)
            index_html.ZPythonScript_setTitle('User Search')

        # Block all right column portlets by default
        manager = getUtility(IPortletManager, name='plone.rightcolumn')
        if manager is not None:
            assignable = queryMultiAdapter((members, manager), ILocalPortletAssignmentManager)
            assignable.setBlacklistStatus('context', True)
            assignable.setBlacklistStatus('group', True)
            assignable.setBlacklistStatus('content_type', True)

    def update_dv_images(self):
        # Set image_format to jpg
        gsettings = GlobalSettings(self.portal)
        if gsettings.pdf_image_format == 'jpg':
            return
        gsettings.pdf_image_format = 'jpg'
        from datetime import datetime
        start = datetime(1973, 02, 12).now()
        logger.info("Starting dv_conversion at %s" % start)
        brains = self.catalog(portal_type=['dmsmainfile', 'dmsommainfile', 'dmsappendixfile'])
        bl = len(brains)
        logger.info("Found %d objects" % bl)
        total = {'orig': 0, 'pages': 0, 'old_i': 0, 'new_i': 0}
        loggerdv = logging.getLogger('collective.documentviewer')
        loggerdv.setLevel(30)
        for i, brain in enumerate(brains):
            obj = brain.getObject()
            total['orig'] += tobytes(brain.getObjSize)
            sizes = dv_images_size(obj)
            total['old_i'] += (sizes['large'] + sizes['normal'] + sizes['small'])
            total['pages'] += sizes['pages']
            if i and not i % 1000:
                logger.info("dv_conversion: treating %d" % i)
            ret = runConversion(obj)
            if ret == 'failure':
                logger.error("Error during conversion of %s" % brain.getURLPath())
            sizes = dv_images_size(obj)
            total['new_i'] += (sizes['large'] + sizes['normal'] + sizes['small'])
        end = datetime(1973, 02, 12).now()
        delta = end - start
        loggerdv.setLevel(20)
        logger.info("Finishing dv_conversion, duration %s" % delta)
        logger.info("Files: '%d', PDF: '%s', Pages: '%d', old: '%s', new: '%s'" %
                    (bl, fileSize(total['orig'], decimal=','), total['pages'], fileSize(total['old_i'], decimal=','),
                     fileSize(total['new_i'], decimal=',')))

    def update_templates(self):
        # Removed useless template
        if 'contacts-export' in self.portal['templates']:
            api.content.delete(self.portal['templates']['contacts-export'])
        # Change addable types
        template_types = POD_TEMPLATE_TYPES.keys() + ['Folder', 'DashboardPODTemplate']
        for path in ['templates', 'templates/om', 'templates/om/common']:
            obj = self.portal.unrestrictedTraverse(path)
            obj.setLocallyAllowedTypes(template_types)
            obj.setImmediatelyAddableTypes(template_types)

        # add templates configuration
        add_templates(self.portal)

        ml_uid = self.portal.restrictedTraverse('templates/om/mailing').UID()
        for path in ('templates/om/main',):
            obj = self.portal.restrictedTraverse(path)
            obj.mailing_loop_template = ml_uid

    def update_tasks(self):
        # NOT USED !
        # change klass on task
        'collective.task.content.task.Task'
        for brain in self.catalog(portal_type='task'):
            migrate_base_class_to_new_class(brain.getObject(), old_class_name='collective.task.content.task.Task',
                                            new_class_name='imio.dms.mail.browser.task.Task')

    def update_collections(self):
        # update incomingmail collections
        for brain in api.content.find(context=self.imf['mail-searches'], portal_type='DashboardCollection'):
            obj = brain.getObject()
            if 'CreationDate' in obj.customViewFields:
                buf = list(obj.customViewFields)
                buf[buf.index('CreationDate')] = u'reception_date'
                obj.customViewFields = tuple(buf)

        collections = [
            {}, {}, {}, {}, {}, {}, {},
            {'id': 'in_copy_unread', 'tit': _('im_in_copy_unread'), 'subj': (u'todo', ), 'query': [
                {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
                {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
                 'v': 'dmsincomingmail-in-copy-group-unread'}],
                'cond': u"", 'bypass': [],
                'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                         u'due_date', u'mail_type', u'sender', u'reception_date', u'actions'),
                'sort': u'organization_type', 'rev': True, 'count': True}, {},
            {'id': 'followed', 'tit': _('im_followed'), 'subj': (u'search', ), 'query': [
                {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
                {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
                 'v': 'dmsincomingmail-followed'}],
                'cond': u"", 'bypass': [],
                'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                         u'due_date', u'mail_type', u'sender', u'reception_date', u'actions'),
                'sort': u'organization_type', 'rev': True, 'count': False}]
        createDashboardCollections(self.imf['mail-searches'], collections)
        reimport_faceted_config(self.imf['mail-searches'], xml='im-mail-searches.xml',
                                default_UID=self.imf['mail-searches']['all_mails'].UID())

        # ICollectionCategories
        alsoProvides(self.imf['mail-searches'], ICollectionCategories)
        alsoProvides(self.omf['mail-searches'], ICollectionCategories)
        alsoProvides(self.portal['tasks']['task-searches'], ICollectionCategories)
        # Rename category label
        self.imf['mail-searches'].setRights('Courrier entrant')
        self.omf['mail-searches'].setRights('Courrier sortant')

    def update_site(self):
        # add documentation message
        if 'doc' not in self.portal['messages-config']:
            add_message('doc', 'Documentation', u'<p>Vous pouvez consulter la <a href="http://www.imio.be/'
                        u'support/documentation/topic/cp_app_ged" target="_blank">documentation en ligne de la '
                        u'dernière version</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                        can_hide=True, req_roles=['Authenticated'], activate=True)
        if 'doc2-0' in self.portal['messages-config']:
            api.content.delete(obj=self.portal['messages-config']['doc2-0'])

        # update front-page
        frontpage = self.portal['front-page']
        if frontpage.Title() == 'Gestion du courrier 2.0':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

        # update portal title
        self.portal.title = 'Gestion du courrier'

        # for collective.externaleditor
        if 'MailingLoopTemplate' not in self.registry['externaleditor.externaleditor_enabled_types']:
            self.registry['externaleditor.externaleditor_enabled_types'] = ['PODTemplate', 'ConfigurablePODTemplate',
                                                                            'DashboardPODTemplate', 'SubTemplate',
                                                                            'StyleTemplate', 'dmsommainfile',
                                                                            'MailingLoopTemplate']
        # documentgenerator
        api.portal.set_registry_record('collective.documentgenerator.browser.controlpanel.'
                                       'IDocumentGeneratorControlPanelSchema.raiseOnError_for_non_managers', True)

        # ftw.labels
        labels = {self.imf: [('Lu', 'green', True), ('Suivi', 'yellow', True)],
                  self.omf: [],
                  self.portal['tasks']: []}
        for folder in labels:
            if not ILabelRoot.providedBy(folder):
                alsoProvides(folder, ILabelRoot)
                adapted = ILabelJar(folder)
                existing = [dic['title'] for dic in adapted.list()]
                for title, color, by_user in labels[folder]:
                    if title not in existing:
                        adapted.add(title, color, by_user)
        self.portal.manage_permission('ftw.labels: Manage Labels Jar', ('Manager', 'Site Administrator'),
                                      acquire=0)
        self.portal.manage_permission('ftw.labels: Change Labels', ('Manager', 'Site Administrator'),
                                      acquire=0)
        self.portal.manage_permission('ftw.labels: Change Personal Labels', ('Manager', 'Site Administrator', 'Member'),
                                      acquire=0)

        # INextPrevNotNavigable
        alsoProvides(self.portal['tasks'], INextPrevNotNavigable)

        # registry
        api.portal.set_registry_record(name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.'
                                            'search_rss_enabled', value=False)

        # activing versioning
        self.portal.portal_diff.setDiffForPortalType('task', {'any': "Compound Diff for Dexterity types"})
        self.portal.portal_diff.setDiffForPortalType('dmsommainfile', {'any': "Compound Diff for Dexterity types"})

        # change permission
        self.portal.manage_permission('imio.dms.mail: Write userid field', (),
                                      acquire=0)
        pf = self.portal.contacts['personnel-folder']
        pf.manage_permission('imio.dms.mail: Write userid field', ('Manager', 'Site Administrator'),
                             acquire=0)

    def update_contacts(self):
        contacts = self.portal['contacts']
        blacklistPortletCategory(contacts, contacts, value=False)
        noLongerProvides(contacts, IHidePloneLeftColumn)
        noLongerProvides(contacts, IHidePloneRightColumn)
        noLongerProvides(contacts, IDisableSmartFacets)
        noLongerProvides(contacts, IDirectoryFacetedNavigable)
        noLongerProvides(contacts, IActionsEnabled)
        self.portal.portal_types.directory.filter_content_types = False
        # add organizations searches
        col_folder = add_db_col_folder(contacts, 'orgs-searches', _("Organizations searches"), _("Organizations"))
        contacts.moveObjectToPosition('orgs-searches', 0)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOrganizationsDashboard)
        alsoProvides(col_folder, IHeldPositionsDashboardBatchActions)
        createOrganizationsCollections(col_folder)
        # createStateCollections(col_folder, 'organization')
        configure_faceted_folder(col_folder, xml='organizations-searches.xml',
                                 default_UID=col_folder['all_orgs'].UID())
        # configure outgoing-mail faceted
        configure_faceted_folder(contacts, xml='default_dashboard_widgets.xml',
                                 default_UID=col_folder['all_orgs'].UID())
        # add held positions searches
        col_folder = add_db_col_folder(contacts, 'hps-searches', _("Held positions searches"), _("Held positions"))
        contacts.moveObjectToPosition('hps-searches', 1)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IHeldPositionsDashboard)
        alsoProvides(col_folder, IHeldPositionsDashboardBatchActions)
        createHeldPositionsCollections(col_folder)
        # createStateCollections(col_folder, 'held_position')
        configure_faceted_folder(col_folder, xml='held-positions-searches.xml',
                                 default_UID=col_folder['all_hps'].UID())
        # add persons searches
        col_folder = add_db_col_folder(contacts, 'persons-searches', _("Persons searches"), _("Persons"))
        contacts.moveObjectToPosition('persons-searches', 2)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IPersonsDashboard)
        alsoProvides(col_folder, IPersonsDashboardBatchActions)
        createPersonsCollections(col_folder)
        # createStateCollections(col_folder, 'person')
        configure_faceted_folder(col_folder, xml='persons-searches.xml',
                                 default_UID=col_folder['all_persons'].UID())
        # add contact list searches
        col_folder = add_db_col_folder(contacts, 'cls-searches', _("Contact list searches"), _("Contact lists"))
        contacts.moveObjectToPosition('cls-searches', 3)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IContactListsDashboard)
        alsoProvides(col_folder, IContactListsDashboardBatchActions)
        createContactListsCollections(col_folder)
        # createStateCollections(col_folder, 'contact_list')
        configure_faceted_folder(col_folder, xml='contact-lists-searches.xml',
                                 default_UID=col_folder['all_cls'].UID())
        self.portal.portal_types.directory.filter_content_types = True
        # order
        contacts.moveObjectToPosition('personnel-folder', 4)
        # contact lists folder
        self.runProfileSteps('imio.dms.mail', profile='examples', steps=['imiodmsmail-addContactListsFolder'])
        cl_folder = contacts['contact-lists-folder']
        cl_folder.manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
        cl_folder.manage_addLocalRoles('expedition', ['Contributor', 'Editor', 'Reader'])
        cl_folder.manage_addLocalRoles('dir_general', ['Contributor', 'Editor', 'Reader'])
        dic = cl_folder['common'].__ac_local_roles__
        for uid in self.registry[ORGANIZATIONS_REGISTRY]:
            dic["%s_encodeur" % uid] = ['Contributor']
            if uid not in cl_folder:
                obj = uuidToObject(uid)
                full_title = obj.get_full_title(separator=' - ', first_index=1)
                folder = api.content.create(container=cl_folder, type='Folder', id=uid, title=full_title)
                folder.setLayout('folder_tabular_view')
                alsoProvides(folder, IActionsPanelFolderAll)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ['Contributor']
                api.group.grant_roles(groupname='%s_encodeur' % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
        cl_folder['common']._p_changed = True
        # various
        contacts.moveObjectToPosition('plonegroup-organization', 6)
        blacklistPortletCategory(self, contacts['plonegroup-organization'])
        blacklistPortletCategory(self, contacts['personnel-folder'])

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.1...')
        self.cleanRegistries()

        self.set_Members()

        self.upgradeProfile('collective.dms.mailcontent:default')
        self.upgradeProfile('collective.documentgenerator:default')

        self.reinstall(['collective.contact.contactlist:default', ])
        if 'contact-contactlist-mylists' in self.portal.portal_actions.user:
            self.portal.portal_actions.user.manage_delObjects(ids=['contact-contactlist-mylists'])

        self.runProfileSteps('imio.dms.mail', steps=['actions', 'cssregistry', 'jsregistry', 'repositorytool',
                                                     'typeinfo', 'viewlets', 'workflow'])
        self.portal.portal_workflow.updateRoleMappings()
        # Apply workflow adaptations
        success, errors = apply_from_registry()

        self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-add-icons-to-contact-workflow'], profile='singles')

        add_transforms(self.portal)

        # set unicode on internal_reference_number !!

        # replace faceted on contacts
        self.update_contacts()

        # update templates
        self.update_templates()

        # update collections
        self.update_collections()

        # do various global adaptations
        self.update_site()

        # recatalog
        for brain in self.catalog(portal_type='dmsincomingmail'):
            brain.getObject().reindexObject(['get_full_title'])

        # converting dv images
        self.update_dv_images()

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=['imio.dms.mail:default'])

        # correct collective.z3cform.datagridfield 1.3.0 version
        self.runProfileSteps('collective.z3cform.datagridfield', steps=['browserlayer'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in ['collective.behavior.talcondition', 'collective.ckeditor', 'collective.contact.core',
                     'collective.contact.duplicated', 'collective.contact.plonegroup', 'collective.contact.widget',
                     'collective.dms.basecontent', 'collective.dms.scanbehavior', 'collective.eeafaceted.batchactions',
                     'collective.eeafaceted.collectionwidget', 'collective.eeafaceted.z3ctable',
                     'collective.js.underscore', 'collective.messagesviewlet', 'collective.plonefinder',
                     'collective.querynextprev', 'collective.task', 'collective.z3cform.datagridfield',
                     'collective.z3cform.datetimewidget', 'imio.actionspanel', 'imio.dashboard', 'imio.dms.mail',
                     'imio.history', 'plone.app.dexterity', 'plone.formwidget.autocomplete',
                     'plone.formwidget.contenttree', 'plone.formwidget.datetime', 'plonetheme.classic',
                     'plonetheme.imioapps']:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_1(context).run()
