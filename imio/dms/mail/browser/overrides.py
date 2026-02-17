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
from BTrees.IIBTree import IITreeSet
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
from collective.iconifiedcategory.content.category import ICategory
from collective.iconifiedcategory.content.categoryconfiguration import ICategoryConfiguration
from collective.iconifiedcategory.content.categorygroup import ICategoryGroup
from collective.task.behaviors import ITask
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from imio.annex.content.annex import IAnnex
from imio.dms.mail import BLDT_DIR
from imio.dms.mail.interfaces import IClassificationFoldersDashboard
from imio.dms.mail.interfaces import IContactsDashboard
from imio.dms.mail.interfaces import IIMDashboard
from imio.dms.mail.interfaces import IOMDashboard
from imio.helpers.security import check_zope_admin
from imio.history.browser.views import IHDocumentBylineViewlet
from imio.pyutils.system import read_dictcsv
from logging import getLogger
from plone import api
from plone.app.controlpanel.usergroups import GroupsOverviewControlPanel
from plone.app.controlpanel.usergroups import UsersGroupsControlPanelView
from plone.app.controlpanel.usergroups import UsersOverviewControlPanel
from plone.app.layout.navigation.root import getNavigationRoot
from plone.app.layout.viewlets.common import ContentActionsViewlet as PALContentActionsViewlet
from plone.locking.browser.info import LockInfoViewlet as PLLockInfoViewlet
from plone.locking.browser.locking import LockingOperations as PLLockingOperations
from Products.ATContentTypes.interfaces.document import IATDocument
from Products.ATContentTypes.interfaces.folder import IATBTreeFolder
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import utils
from Products.CMFPlone.browser.navigation import get_view_url
from Products.CMFPlone.browser.navigation import PhysicalNavigationBreadcrumbs as PlonePhysicalNavigationBreadcrumbs
from Products.CMFPlone.browser.ploneview import Plone as PloneView
from Products.CMFPlone.interfaces import IHideFromBreadcrumbs
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from time import clock
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.interface.exceptions import Invalid

import os
import sys


class IMRenderCategoryView(RenderCategoryView):
    """
    Override the way a category is rendered in the portlet based on the
    faceted collection widget so we can manage some usecases where icons
    are displayed to add items.
    """

    def contact_infos(self):
        return {
            "orgs-searches": {"typ": "organization", "add": "++add++organization", "img": "organization_icon.png"},
            "hps-searches": {"typ": "contact", "add": "@@add-contact", "img": "create_contact.png"},
            "persons-searches": {"typ": "person", "add": "++add++person", "img": "person_icon.png"},
            "cls-searches": {
                "typ": "contact_list",
                "add": "contact-lists-folder",
                "img": "directory_icon.png",
                "class": "",
            },
        }

    def _get_category_template(self):
        if IIMDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_im.pt")
        elif IOMDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_om.pt")
        elif IContactsDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_contact.pt")
        elif IClassificationFoldersDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_classification_folders.pt")
        return ViewPageTemplateFile("templates/category.pt")


class DocumentBylineViewlet(IHDocumentBylineViewlet):
    """
    Overrides the IHDocumentBylineViewlet to hide it for some layouts.
    """

    def show(self):
        current_layout = self.context.getLayout()
        if current_layout in [
            "facetednavigation_view",
        ]:
            return False
        return True

    def creator(self):
        if self.context.portal_type in ("dmsincomingmail", "dmsincoming_email"):
            return None
        return super(DocumentBylineViewlet, self).creator()


class LockInfoViewlet(PLLockInfoViewlet):
    def lock_is_stealable(self):
        if self.context.portal_type in api.portal.get_registry_record(
            "externaleditor.externaleditor_enabled_types", default=[]
        ):
            return True
        return super(LockInfoViewlet, self).lock_is_stealable()


class LockingOperations(PLLockingOperations):
    def force_unlock(self, redirect=True):
        """Can unlock external edit lock"""
        if self.context.portal_type in api.portal.get_registry_record(
            "externaleditor.externaleditor_enabled_types", default=[]
        ):
            self.context.wl_clearLocks()
            self.request.RESPONSE.redirect("%s/view" % self.context.absolute_url())
        else:
            super(LockingOperations, self).force_unlock(redirect=redirect)


class Plone(PloneView):
    def showEditableBorder(self):
        """Do not show editable border (green bar) for some contents"""
        context = aq_inner(self.context)
        interfaces = (
            ITask,
            IContactContent,
            IClassificationFolders,
            IClassificationFolder,
            IClassificationSubfolder,
            ICKTemplate,
            IContactList,
            IDmsAppendixFile,
            IDmsFile,
            IAnnex,
            IATBTreeFolder,
            IPODTemplate,
            IStyleTemplate,
            IClassificationContainer,
            IClassificationCategory,
            ICategory,
            ICategoryGroup,
            ICategoryConfiguration,
        )
        for interface in interfaces:
            if interface.providedBy(context):
                return False
        return super(Plone, self).showEditableBorder()


class PhysicalNavigationBreadcrumbs(PlonePhysicalNavigationBreadcrumbs):
    """Corrected the item url after a hidden part, visible 2 levels deeper."""

    def breadcrumbs(self):
        context = aq_inner(self.context)
        request = self.request
        container = utils.parent(context)

        name, item_url = get_view_url(context)

        if container is None:
            return (
                {
                    "absolute_url": item_url,
                    "Title": utils.pretty_title_or_id(context, context),
                },
            )

        view = getMultiAdapter((container, request), name="breadcrumbs_view")
        base = tuple(view.breadcrumbs())

        # Some things want to be hidden from the breadcrumbs
        if IHideFromBreadcrumbs.providedBy(context):
            return base

        rootpath = getNavigationRoot(context)
        itempath = "/".join(context.getPhysicalPath())

        # don't show default pages in breadcrumbs or pages above the navigation root
        if not utils.isDefaultPage(context, request) and not rootpath.startswith(itempath):
            base += (
                {
                    "absolute_url": item_url,
                    "Title": utils.pretty_title_or_id(context, context),
                },
            )
        return base


class ContentActionsViewlet(PALContentActionsViewlet):
    """ """

    def render(self):
        context = aq_inner(self.context)
        for interface in (IATDocument, IDmsAppendixFile, IPloneSiteRoot):
            if interface.providedBy(context):
                return ""
        return self.index()


class IDMUtilsMethods(UtilsMethods):
    """View containing utils methods"""

    def outgoingmail_folder(self):
        return api.portal.get()["outgoing-mail"]


class BaseOverviewControlPanel(UsersGroupsControlPanelView):
    """Override to filter result and remove every selectable roles."""

    @property
    def portal_roles(self):
        return ["Batch importer", "Manager", "Member", "Site Administrator"]

    def doSearch(self, searchString):  # noqa
        results = super(BaseOverviewControlPanel, self).doSearch(searchString)
        if check_zope_admin():
            return results
        adapted_results = []
        for item in results:
            adapted_item = item.copy()
            for role in self.portal_roles:
                adapted_item["roles"][role]["canAssign"] = False
            adapted_item["can_delete"] = False
            adapted_results.append(adapted_item)
        return adapted_results


class DocsUsersOverviewControlPanel(BaseOverviewControlPanel, UsersOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""


class DocsGroupsOverviewControlPanel(BaseOverviewControlPanel, GroupsOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""

    @property
    def portal_roles(self):
        return ["Manager", "Member", "Site Administrator"]


class DocsCKTemplateListingView(CKTemplateListingView):
    """Change enabled_states variable class because we use another workflow to restrict access to cktemplate."""

    enabled_states = ()
    sort_on = "path"

    def __init__(self, context, request):
        super(DocsCKTemplateListingView, self).__init__(context, request)
        # portal = api.portal.get()
        # self.portal_path = '/'.join(portal.getPhysicalPath())

    def get_templates(self):
        """Sort templates by full title."""
        templates = super(DocsCKTemplateListingView, self).get_templates()
        return sorted(templates, key=lambda tup: IAnnotations(tup[0]).get("dmsmail.cke_tpl_tit", u""))

    def render_template(self, template, path):
        """Render each template as a javascript dic."""
        # TODO do it in ckeditortemplates
        base = u'{{title: "{title}", description: "", html: "{html}"}}'
        # , image: "{image}"
        # icon = u'{}/++resource++imio.dms.mail/arobase.svg'.format(self.portal_path)
        title = template.title
        annot = IAnnotations(template)
        if "dmsmail.cke_tpl_tit" in annot and annot["dmsmail.cke_tpl_tit"]:
            title = u"{} > {}".format(annot["dmsmail.cke_tpl_tit"], title)
        return base.format(**{"title": title.replace('"', "&quot;"), "html": template.html()})


class FacetedCollectionPortletRenderer(Renderer):
    @property
    def _criteriaHolder(self):
        """Get the element the criteria are defined on.  This will look up parents until
        a folder providing IFacetedNavigable is found."""
        parent = self.context
        ignored_types = ("ClassificationSubfolder", "ClassificationFolder")
        # look up parents until we found the criteria holder or we reach the 'Plone Site'
        while parent and not parent.portal_type == "Plone Site":
            if IFacetedNavigable.providedBy(parent) and parent.portal_type not in ignored_types:
                return parent
            parent = aq_parent(aq_inner(parent))


class ClassificationJSONCollectionsCount(JSONCollectionsCount):
    def get_context(self, faceted_context):
        # TODO : yet necessary ???
        ignored_types = ("ClassificationSubfolder", "ClassificationFolder", "annex")
        # look up parents until we found the criteria holder or we reach the 'Plone Site'
        while faceted_context and not faceted_context.portal_type == "Plone Site":
            if IFacetedNavigable.providedBy(faceted_context) and faceted_context.portal_type not in ignored_types:
                return faceted_context
            faceted_context = aq_parent(aq_inner(faceted_context))
        return faceted_context


class DocsImportFormSecondStep(ImportFormSecondStep):
    def _get_treating_groups_titles(self):
        tgt = super(DocsImportFormSecondStep, self)._get_treating_groups_titles()
        csv_file = os.path.join(BLDT_DIR, u"imports/tg_matching.csv")
        if os.path.exists(csv_file):
            msg, rows = read_dictcsv(csv_file, fieldnames=["otgt", "ntgt"], skip_lines=1)
            if msg:
                raise Invalid(u"Error reading '{}': '{}'".format(csv_file, msg))
            errors = []
            for row in rows:
                otgt = row["otgt"].decode("utf8")
                ntgt = row["ntgt"].decode("utf8")
                if otgt not in tgt:
                    if ntgt not in tgt:
                        errors.append(u"{}: new value '{}' not found".format(row["_ln"], ntgt))
                    else:
                        tgt[otgt] = tgt[ntgt]
            if errors:
                raise Invalid(
                    u"Existing groups = '{}'. Errors: '{}'".format(u", ".join(tgt.keys()), u", ".join(errors))
                )
        return tgt


class DocsImportSecondStepView(ImportSecondStepView):

    form = DocsImportFormSecondStep


# collective.solr maintenance view

try:
    from collective.solr.browser.maintenance import checkpointIterator
    from collective.solr.browser.maintenance import MAX_ROWS
    from collective.solr.browser.maintenance import notimeout
    from collective.solr.browser.maintenance import SolrMaintenanceView
    from collective.solr.browser.maintenance import timer
    from collective.solr.indexer import SolrIndexProcessor
    from collective.solr.interfaces import ICheckIndexable
    from collective.solr.interfaces import ISolrConnectionManager
    from collective.solr.parser import parse_date_as_datetime
    from collective.solr.parser import SolrResponse
    from collective.solr.parser import unmarshallers

    BaseMaintenanceView = SolrMaintenanceView
except ImportError:
    BaseMaintenanceView = BrowserView

logger = getLogger("collective.solr.maintenance docs")


class DocsSolrMaintenanceView(BaseMaintenanceView):
    """Overrides sync method to take into account a BATCH"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.batch_value = int(os.getenv("BATCH", "0"))

    def sync(self, batch=1000, preImportDeleteQuery="*:*"):
        """Sync the Solr index with the portal catalog. Records contained
        in the catalog but not in Solr will be indexed and records not
        contained in the catalog will be removed.
        Overrided following c99d607cc9af47ca7614ba09016b17483e441ce5 version
        """
        manager = queryUtility(ISolrConnectionManager)
        proc = SolrIndexProcessor(manager)
        conn = manager.getConnection()
        key = queryUtility(ISolrConnectionManager).getSchema().uniqueKey
        zodb_conn = self.context._p_jar
        catalog = getToolByName(self.context, "portal_catalog")
        getIndex = catalog._catalog.getIndex
        modified_index = getIndex("modified")
        uid_index = getIndex(key)
        log = self.mklog()
        real = timer()  # real time
        lap = timer()  # real lap time (for intermediate commits)
        cpu = timer(clock)  # cpu time
        # get Solr status
        response = conn.search(q=preImportDeleteQuery, rows=MAX_ROWS, fl="%s modified" % key)
        # avoid creating DateTime instances
        simple_unmarshallers = unmarshallers.copy()
        simple_unmarshallers["date"] = parse_date_as_datetime
        flares = SolrResponse(response, simple_unmarshallers)
        response.close()
        solr_results = {}
        solr_uids = set()

        def _utc_convert(value):
            t_tup = value.utctimetuple()
            return (((t_tup[0] * 12 + t_tup[1]) * 31 + t_tup[2]) * 24 + t_tup[3]) * 60 + t_tup[4]

        for flare in flares:
            uid = flare[key]
            solr_uids.add(uid)
            solr_results[uid] = _utc_convert(flare["modified"])
        # get catalog status
        cat_results = {}
        cat_uids = set()
        for uid, rid in uid_index._index.items():
            cat_uids.add(uid)
            cat_results[uid] = rid
        # differences
        index = cat_uids.difference(solr_uids)
        solr_uids.difference_update(cat_uids)
        unindex = solr_uids
        processed = 0
        flush = notimeout(lambda: conn.flush())

        def checkPoint():
            msg = "intermediate commit (%d items processed, " "last batch in %s)...\n" % (processed, lap.next())
            log(msg)
            logger.info(msg)
            flush()
            zodb_conn.cacheGC()
            if self.batch_value and processed >= self.batch_value:
                logger.info("EXITED following BATCH env value {}".format(self.batch_value))
                conn.commit()
                sys.exit(0)

        cpi = checkpointIterator(checkPoint, batch)
        # Look up objects
        uid_rid_get = cat_results.get
        rid_path_get = catalog._catalog.paths.get
        catalog_traverse = catalog.unrestrictedTraverse

        def lookup(
            uid, rid=None, uid_rid_get=uid_rid_get, rid_path_get=rid_path_get, catalog_traverse=catalog_traverse
        ):
            if rid is None:
                rid = uid_rid_get(uid)
            if not rid:
                return None
            if not isinstance(rid, int):
                rid = tuple(rid)[0]
            path = rid_path_get(rid)
            if not path:
                return None
            try:
                obj = catalog_traverse(path)
            except AttributeError:
                return None
            return obj

        log('processing %d "unindex" operations next...\n' % len(unindex))
        op = notimeout(lambda uid: conn.delete(id=uid))
        for uid in unindex:
            obj = lookup(uid)
            if obj is None:
                op(uid)
                processed += 1
                cpi.next()
            else:
                log("not unindexing existing object %r.\n" % uid)
        log('processing %d "index" operations next...\n' % len(index))
        op = notimeout(lambda obj: proc.index(obj))
        for uid in index:
            obj = lookup(uid)
            if ICheckIndexable(obj)():
                op(obj)
                processed += 1
                cpi.next()
            else:
                log("not indexing unindexable object %r.\n" % uid)
            if obj is not None:
                obj._p_deactivate()
        log('processing "reindex" operations next...\n')
        op = notimeout(lambda obj: proc.reindex(obj))
        cat_mod_get = modified_index._unindex.get
        solr_mod_get = solr_results.get
        done = unindex.union(index)
        for uid, rid in cat_results.items():
            if uid in done:
                continue
            if isinstance(rid, IITreeSet):
                rid = rid.keys()[0]
            if cat_mod_get(rid) != solr_mod_get(uid):
                obj = lookup(uid, rid=rid)
                if ICheckIndexable(obj)():
                    op(obj)
                    processed += 1
                    cpi.next()
                else:
                    log("not reindexing unindexable object %r.\n" % uid)
                if obj is not None:
                    obj._p_deactivate()
        conn.commit()
        log("solr index synced.\n")
        msg = "processed %d object(s) in %s (%s cpu time)."
        msg = msg % (processed, real.next(), cpu.next())
        log(msg)
        logger.info(msg)
