# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from Acquisition import aq_inner  # noqa
from collective.ckeditortemplates.browser.cktemplatelisting import CKTemplateListingView
from collective.ckeditortemplates.cktemplate import ICKTemplate
from collective.contact.contactlist.interfaces import IContactList
from collective.contact.widget.interfaces import IContactContent
from collective.dms.basecontent.dmsfile import IDmsFile, IDmsAppendixFile
from collective.dms.mailcontent.browser.utils import UtilsMethods
from collective.documentgenerator.content.pod_template import IPODTemplate
from collective.documentgenerator.content.style_template import IStyleTemplate
from collective.eeafaceted.collectionwidget.browser.views import RenderCategoryView
from collective.task.behaviors import ITask
from imio.dms.mail.interfaces import IContactsDashboard
from imio.dms.mail.interfaces import IIMDashboard
from imio.dms.mail.interfaces import IOMDashboard
from imio.history.browser.views import IHDocumentBylineViewlet
from plone import api
from plone.app.controlpanel.usergroups import GroupsOverviewControlPanel
from plone.app.controlpanel.usergroups import UsersGroupsControlPanelView
from plone.app.controlpanel.usergroups import UsersOverviewControlPanel
from plone.app.layout.viewlets.common import ContentActionsViewlet as PALContentActionsViewlet
from plone.app.search.browser import Search
from plone.locking.browser.info import LockInfoViewlet as PLLockInfoViewlet
from plone.locking.browser.locking import LockingOperations as PLLockingOperations
from Products.ATContentTypes.interfaces.document import IATDocument
from Products.ATContentTypes.interfaces.folder import IATBTreeFolder
from Products.CMFPlone.browser.ploneview import Plone as PloneView
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class IMRenderCategoryView(RenderCategoryView):
    """
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items.
    """

    def contact_infos(self):
        return {'orgs-searches': {'typ': 'organization', 'add': '++add++organization', 'img': 'organization_icon.png'},
                'hps-searches': {'typ': 'contact', 'add': '@@add-contact', 'img': 'create_contact.png'},
                'persons-searches': {'typ': 'person', 'add': '++add++person', 'img': 'person_icon.png'},
                'cls-searches': {'typ': 'contact_list', 'add': 'contact-lists-folder',
                                 'img': 'directory_icon.png', 'class': ''}
                }

    def _get_category_template(self):
        if IIMDashboard.providedBy(self.context):
            return ViewPageTemplateFile('templates/category_im.pt')
        elif IOMDashboard.providedBy(self.context):
            return ViewPageTemplateFile('templates/category_om.pt')
        elif IContactsDashboard.providedBy(self.context):
            return ViewPageTemplateFile('templates/category_contact.pt')
        return ViewPageTemplateFile('templates/category.pt')


class DocumentBylineViewlet(IHDocumentBylineViewlet):
    """
      Overrides the IHDocumentBylineViewlet to hide it for some layouts.
    """

    def show(self):
        current_layout = self.context.getLayout()
        if current_layout in ['facetednavigation_view', ]:
            return False
        return True

    def creator(self):
        if self.context.portal_type in ('dmsincomingmail', 'dmsincoming_email'):
            return None
        return super(DocumentBylineViewlet, self).creator()


class LockInfoViewlet(PLLockInfoViewlet):

    def lock_is_stealable(self):
        if self.context.portal_type in api.portal.get_registry_record('externaleditor.externaleditor_enabled_types',
                                                                      default=[]):
            return True
        return super(LockInfoViewlet, self).lock_is_stealable()


class LockingOperations(PLLockingOperations):

    def force_unlock(self, redirect=True):
        """ Can unlock external edit lock """
        if self.context.portal_type in api.portal.get_registry_record('externaleditor.externaleditor_enabled_types',
                                                                      default=[]):
            self.context.wl_clearLocks()
            self.request.RESPONSE.redirect('%s/view' % self.context.absolute_url())
        else:
            super(LockingOperations, self).force_unlock(redirect=redirect)


class Plone(PloneView):

    def showEditableBorder(self):
        context = aq_inner(self.context)
        for interface in (ITask, IContactContent, ICKTemplate, IContactList, IDmsFile, IATBTreeFolder, IPODTemplate,
                          IStyleTemplate):
            if interface.providedBy(context):
                return False
        return super(Plone, self).showEditableBorder()


class ContentActionsViewlet(PALContentActionsViewlet):
    """ """
    def render(self):
        context = aq_inner(self.context)
        for interface in (IATDocument, IDmsAppendixFile, IPloneSiteRoot):
            if interface.providedBy(context):
                return ''
        return self.index()


class PloneSearch(Search):

    def filter_query(self, query):
        qr = super(PloneSearch, self).filter_query(query)
        if qr and 'SearchableText' in qr and not qr['SearchableText'].endswith('*'):
            qr['SearchableText'] += '*'
        return qr


class IDMUtilsMethods(UtilsMethods):
    """ View containing utils methods """

    def outgoingmail_folder(self):
        return api.portal.get()['outgoing-mail']


class BaseOverviewControlPanel(UsersGroupsControlPanelView):
    """Override to filter result and remove every selectable roles."""

    @property
    def portal_roles(self):
        return ['Batch importer', 'Manager', 'Member', 'Site Administrator']

    def doSearch(self, searchString):  # noqa
        results = super(BaseOverviewControlPanel, self).doSearch(searchString)
        if check_zope_admin():
            return results
        adapted_results = []
        for item in results:
            adapted_item = item.copy()
            for role in self.portal_roles:
                adapted_item['roles'][role]['canAssign'] = False
            adapted_item['can_delete'] = False
            adapted_results.append(adapted_item)
        return adapted_results


class DocsUsersOverviewControlPanel(BaseOverviewControlPanel, UsersOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""


class DocsGroupsOverviewControlPanel(BaseOverviewControlPanel, GroupsOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""

    @property
    def portal_roles(self):
        return ['Manager', 'Member', 'Site Administrator']


class DocsCKTemplateListingView(CKTemplateListingView):
    """Change enabled_states variable class because we use another workflow to restrict access to cktemplate."""

    enabled_states = ('active', )
