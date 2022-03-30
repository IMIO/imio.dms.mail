# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from Acquisition import aq_inner  # noqa
from Acquisition import aq_parent
from collective.ckeditortemplates.browser.cktemplatelisting import CKTemplateListingView
from collective.ckeditortemplates.cktemplate import ICKTemplate
from collective.classification.folder.content.classification_folder import IClassificationFolder
from collective.classification.folder.content.classification_folders import IClassificationFolders
from collective.classification.folder.content.classification_subfolder import IClassificationSubfolder
from collective.classification.folder.form.importform import ImportFormSecondStep
from collective.classification.folder.form.importform import ImportSecondStepView
from collective.classification.tree.contents.category import IClassificationCategory
from collective.classification.tree.contents.container import IClassificationContainer
from collective.contact.contactlist.interfaces import IContactList
from collective.contact.widget.interfaces import IContactContent
from collective.dms.basecontent.dmsfile import IDmsAppendixFile
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.dms.mailcontent.browser.utils import UtilsMethods
from collective.documentgenerator.content.pod_template import IPODTemplate
from collective.documentgenerator.content.style_template import IStyleTemplate
from collective.eeafaceted.collectionwidget.browser.views import RenderCategoryView
from collective.eeafaceted.dashboard.browser.facetedcollectionportlet import Renderer
from collective.eeafaceted.dashboard.browser.views import JSONCollectionsCount
from collective.task.behaviors import ITask
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from imio.dms.mail import BLDT_DIR
from imio.dms.mail.interfaces import IClassificationFoldersDashboard
from imio.dms.mail.interfaces import IContactsDashboard
from imio.dms.mail.interfaces import IIMDashboard
from imio.dms.mail.interfaces import IOMDashboard
from imio.history.browser.views import IHDocumentBylineViewlet
from imio.pyutils.system import read_dictcsv
from plone import api
from plone.app.controlpanel.usergroups import GroupsOverviewControlPanel
from plone.app.controlpanel.usergroups import UsersGroupsControlPanelView
from plone.app.controlpanel.usergroups import UsersOverviewControlPanel
from plone.app.layout.navigation.root import getNavigationRoot
from plone.app.layout.viewlets.common import ContentActionsViewlet as PALContentActionsViewlet
from plone.app.search.browser import Search
from plone.locking.browser.info import LockInfoViewlet as PLLockInfoViewlet
from plone.locking.browser.locking import LockingOperations as PLLockingOperations
from Products.ATContentTypes.interfaces.document import IATDocument
from Products.ATContentTypes.interfaces.folder import IATBTreeFolder
from Products.CMFPlone import utils
from Products.CMFPlone.browser.navigation import get_view_url
from Products.CMFPlone.browser.navigation import PhysicalNavigationBreadcrumbs as PlonePhysicalNavigationBreadcrumbs
from Products.CMFPlone.browser.ploneview import Plone as PloneView
from Products.CMFPlone.interfaces import IHideFromBreadcrumbs
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.interface.exceptions import Invalid

import os


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
        elif IClassificationFoldersDashboard.providedBy(self.context):
            return ViewPageTemplateFile('templates/category_classification_folders.pt')
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
        """Do not show editable border (green bar) for some contents"""
        context = aq_inner(self.context)
        interfaces = (
            ITask,
            IContactContent,
            ICKTemplate,
            IContactList,
            IDmsAppendixFile,
            IDmsFile,
            IATBTreeFolder,
            IPODTemplate,
            IStyleTemplate,
            IClassificationContainer,
            IClassificationCategory,
            IClassificationFolders,
            IClassificationFolder,
            IClassificationSubfolder,
        )
        for interface in interfaces:
            if interface.providedBy(context):
                return False
        return super(Plone, self).showEditableBorder()


class PhysicalNavigationBreadcrumbs(PlonePhysicalNavigationBreadcrumbs):
    """ Corrected the item url after a hidden part, visible 2 levels deeper."""

    def breadcrumbs(self):
        context = aq_inner(self.context)
        request = self.request
        container = utils.parent(context)

        name, item_url = get_view_url(context)

        if container is None:
            return ({
                'absolute_url': item_url,
                'Title': utils.pretty_title_or_id(context, context),
            },)

        view = getMultiAdapter((container, request), name='breadcrumbs_view')
        base = tuple(view.breadcrumbs())

        # Some things want to be hidden from the breadcrumbs
        if IHideFromBreadcrumbs.providedBy(context):
            return base

        rootpath = getNavigationRoot(context)
        itempath = '/'.join(context.getPhysicalPath())

        # don't show default pages in breadcrumbs or pages above the navigation root
        if not utils.isDefaultPage(context, request) \
           and not rootpath.startswith(itempath):
            base += ({
                'absolute_url': item_url,
                'Title': utils.pretty_title_or_id(context, context),
            },)
        return base


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

    enabled_states = ()
    sort_on = 'path'

    def __init__(self, context, request):
        super(DocsCKTemplateListingView, self).__init__(context, request)
        # portal = api.portal.get()
        # self.portal_path = '/'.join(portal.getPhysicalPath())

    def get_templates(self):
        """Sort templates by full title."""
        templates = super(DocsCKTemplateListingView, self).get_templates()
        return sorted(templates, key=lambda tup: IAnnotations(tup[0]).get('dmsmail.cke_tpl_tit', u''))

    def render_template(self, template, path):
        """Render each template as a javascript dic."""
        # TODO do it in ckeditortemplates
        base = u'{{title: "{title}", description: "", html: "{html}"}}'
        # , image: "{image}"
        # icon = u'{}/++resource++imio.dms.mail/arobase.svg'.format(self.portal_path)
        title = template.title
        annot = IAnnotations(template)
        if 'dmsmail.cke_tpl_tit' in annot and annot['dmsmail.cke_tpl_tit']:
            title = u'{} > {}'.format(annot['dmsmail.cke_tpl_tit'], title)
        return base.format(**{'title': title.replace('"', '&quot;'), 'html': template.html})


class FacetedCollectionPortletRenderer(Renderer):

    @property
    def _criteriaHolder(self):
        '''Get the element the criteria are defined on.  This will look up parents until
           a folder providing IFacetedNavigable is found.'''
        parent = self.context
        ignored_types = ("ClassificationSubfolder", "ClassificationFolder")
        # look up parents until we found the criteria holder or we reach the 'Plone Site'
        while parent and not parent.portal_type == 'Plone Site':
            if IFacetedNavigable.providedBy(parent) and parent.portal_type not in ignored_types:
                return parent
            parent = aq_parent(aq_inner(parent))


class ClassificationJSONCollectionsCount(JSONCollectionsCount):

    def get_context(self, faceted_context):
        ignored_types = ("ClassificationSubfolder", "ClassificationFolder")
        # look up parents until we found the criteria holder or we reach the 'Plone Site'
        while faceted_context and not faceted_context.portal_type == 'Plone Site':
            if IFacetedNavigable.providedBy(faceted_context) and faceted_context.portal_type not in ignored_types:
                return faceted_context
            faceted_context = aq_parent(aq_inner(faceted_context))
        return faceted_context


class DocsImportFormSecondStep(ImportFormSecondStep):

    def _get_treating_groups_titles(self):
        tgt = super(DocsImportFormSecondStep, self)._get_treating_groups_titles()
        csv_file = os.path.join(BLDT_DIR, u'imports/tg_matching.csv')
        if os.path.exists(csv_file):
            msg, rows = read_dictcsv(csv_file, fieldnames=['otgt', 'ntgt'], skip_lines=1)
            if msg:
                raise Invalid(u"Error reading '{}': '{}'".format(csv_file, msg))
            errors = []
            for row in rows:
                otgt = row['otgt'].decode('utf8')
                ntgt = row['ntgt'].decode('utf8')
                if otgt not in tgt:
                    if ntgt not in tgt:
                        errors.append(u"{}: new value '{}' not found".format(row['_ln'], ntgt))
                    else:
                        tgt[otgt] = tgt[ntgt]
            if errors:
                raise Invalid(u"Existing groups = '{}'. Errors: '{}'".format(u', '.join(tgt.keys()),
                                                                             u', '.join(errors)))
        return tgt


class DocsImportSecondStepView(ImportSecondStepView):

    form = DocsImportFormSecondStep
