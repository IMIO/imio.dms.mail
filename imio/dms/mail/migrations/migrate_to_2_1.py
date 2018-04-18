# -*- coding: utf-8 -*-

import logging

from zope.i18n.interfaces import ITranslationDomain
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.interface import alsoProvides

from plone import api
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.Portal import member_indexhtml
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import _createObjectByType

from Products.CPUtils.Extensions.utils import mark_last_version
from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES
from collective.messagesviewlet.utils import add_message
#from collective.querynextprev.interfaces import INextPrevNotNavigable
from ftw.labels.interfaces import ILabelRoot, ILabelJar
from imio.helpers.content import transitions
from imio.migrator.migrator import Migrator

from ..setuphandlers import (_, add_templates, add_transforms, createDashboardCollections, reimport_faceted_config)

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

    def update_templates(self):
        # Change addable types
        template_types = POD_TEMPLATE_TYPES.keys() + ['Folder', 'DashboardPODTemplate']
        for path in ['templates', 'templates/om', 'templates/om/common']:
            obj = self.portal.unrestrictedTraverse(path)
            obj.setLocallyAllowedTypes(template_types)
            obj.setImmediatelyAddableTypes(template_types)

        # add templates configuration
        add_templates(self.portal)

        ml_uid = self.portal.restrictedTraverse('templates/om/mailing').UID()
        for path in ('templates/om/base',):
            obj = self.portal.restrictedTraverse(path)
            obj.mailing_loop_template = ml_uid

    def update_site(self):
        # add documentation message
        if False:
            add_message('doc2-1', 'Documentation 2.1', u'<p>Vous pouvez consulter la <a href="http://www.imio.be/'
                        u'support/documentation/topic/cp_app_ged" target="_blank">documentation en ligne de la '
                        u'version 2.1</a>, ainsi que d\'autres documentations liées.</p>', msg_type='significant',
                        can_hide=True, req_roles=['Authenticated'], activate=True)

        # update front-page
        frontpage = self.portal['front-page']
        if False and frontpage.Title() == 'Gestion du courrier 2.0':
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype='text/html')

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
        labels = {self.imf: [('Lu', 'green', True)],
                  self.omf: [],
                  self.portal['tasks']: []}
        for folder in labels:
            if not ILabelRoot.providedBy(folder):
                alsoProvides(folder, ILabelRoot)
                adapted = ILabelJar(folder)
                for title, color, by_user in labels[folder]:
                    adapted.add(title, color, by_user)
        self.portal.manage_permission('ftw.labels: Manage Labels Jar', ('Manager', 'Site Administrator'),
                                      acquire=0)
        self.portal.manage_permission('ftw.labels: Change Labels', ('Manager', 'Site Administrator'),
                                      acquire=0)
        self.portal.manage_permission('ftw.labels: Change Personal Labels', ('Manager', 'Site Administrator', 'Member'),
                                      acquire=0)
        collections = [
            {}, {}, {}, {}, {}, {}, {},
            {'id': 'in_copy_unread', 'tit': _('im_in_copy_unread'), 'subj': (u'todo', ), 'query': [
                {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsincomingmail']},
                {'i': 'CompoundCriterion', 'o': 'plone.app.querystring.operation.compound.is',
                 'v': 'dmsincomingmail-in-copy-group'}],
                'cond': u"", 'bypass': [],
                'flds': (u'select_row', u'pretty_link', u'review_state', u'treating_groups', u'assigned_user',
                         u'due_date', u'mail_type', u'sender', u'CreationDate', u'actions'),
                'sort': u'organization_type', 'rev': True, 'count': False}, ]
        createDashboardCollections(self.imf['mail-searches'], collections)
        reimport_faceted_config(self.imf['mail-searches'], xml='im-mail-searches.xml',
                                default_UID=self.imf['mail-searches']['all_mails'].UID())

    def run(self):
        logger.info('Migrating to imio.dms.mail 2.1...')
        self.cleanRegistries()

        self.set_Members()

        self.upgradeProfile('collective.dms.mailcontent:default')
        self.upgradeProfile('collective.documentgenerator:default')

        self.reinstall(['collective.contact.contactlist:default', ])

        self.runProfileSteps('imio.dms.mail', steps=['cssregistry', 'jsregistry', 'typeinfo'])
#        self.portal.portal_workflow.updateRoleMappings()

        #set member area type
        self.portal.portal_membership.setMemberAreaType('member_area')

        add_transforms(self.portal)

        # update templates
        self.update_templates()

        # do various global adaptations
        self.update_site()

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        #self.upgradeAll(omit=['imio.dms.mail:default'])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry['collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete'] = False

        for prod in []:
            mark_last_version(self.portal, product=prod)

        #self.refreshDatabase()
        self.finish()


def migrate(context):
    '''
    '''
    Migrate_To_2_1(context).run()
