# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2013 by CommunesPlone, Imio
#
# GNU General Public License (GPL)
#

__author__ = """Gauthier BASTIEN <gbastien@imio.be>, Stephan GEULETTE
<stephan.geulette@imio.be>"""
__docformat__ = "plaintext"

from collections import OrderedDict
from collective.ckeditortemplates.setuphandlers import FOLDER as DEFAULT_CKE_TEMPL_FOLDER
from collective.documentgenerator.interfaces import IBelowContentBodyBatchActionsMarker
from collective.documentviewer.settings import GlobalSettings
from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from collective.querynextprev.interfaces import INextPrevNotNavigable
from dexterity.localroles.utils import add_fti_configuration
from dexterity.localroles.utils import fti_configuration
from ftw.labels.interfaces import ILabelJar
from ftw.labels.interfaces import ILabelRoot
from imio.dms.mail import _tr as _
# from imio.dms.mail import CREATING_FIELD_ROLE
from imio.dms.mail.Extensions.demo import clean_examples
# from imio.dms.mail.interfaces import IActionsPanelFolderOnlyAdd
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IClassificationFoldersDashboardBatchActions
from imio.dms.mail.interfaces import IContactListsDashboardBatchActions
from imio.dms.mail.interfaces import IHeldPositionsDashboardBatchActions
from imio.dms.mail.interfaces import IIMDashboardBatchActions
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.interfaces import IOMCKTemplatesFolder
from imio.dms.mail.interfaces import IOMDashboardBatchActions
from imio.dms.mail.interfaces import IOMTemplatesFolder
from imio.dms.mail.interfaces import IOrganizationsDashboardBatchActions
from imio.dms.mail.interfaces import IPersonnelFolder
from imio.dms.mail.interfaces import IPersonsDashboardBatchActions
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.interfaces import ITaskDashboardBatchActions
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import set_dms_config
from imio.esign.interfaces import IImioSessionsManagementContext
from imio.helpers.content import create
from imio.helpers.content import create_NamedBlob
from imio.helpers.content import richtextval
from imio.helpers.emailer import get_mail_host
from imio.helpers.security import generate_password
from imio.helpers.security import get_environment
from imio.helpers.workflow import do_transitions
from plone import api
from plone.app.controlpanel.markup import MarkupControlPanelAdapter
from plone.dexterity.interfaces import IDexterityFTI
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry
from Products.CMFCore.ActionInformation import Action
# from Products.CMFPlone import PloneMessageFactory as pmf
from Products.CMFPlone.interfaces import INonInstallable
from Products.CMFPlone.utils import base_hasattr
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.MimetypesRegistry import MimeTypeException
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.interface import implementer

import copy
import logging
import os
import pkg_resources


logger = logging.getLogger("imio.dms.mail: setuphandlers")


def _no_more_used(msgid, domain="imio.dms.mail"):  # TODO delete if no more necessary
    translation_domain = queryUtility(ITranslationDomain, domain)
    sp = api.portal.get().portal_properties.site_properties
    return translation_domain.translate(msgid, target_language=sp.getProperty("default_language", "fr"))


def add_db_col_folder(folder, cid, title, displayed=""):
    if base_hasattr(folder, cid):
        return folder[cid]

    folder.invokeFactory("Folder", id=cid, title=title, rights=displayed)
    col_folder = folder[cid]
    col_folder.setConstrainTypesMode(1)
    col_folder.setLocallyAllowedTypes(["DashboardCollection"])
    col_folder.setImmediatelyAddableTypes(["DashboardCollection"])
    do_transitions(col_folder, ["show_internally"])
    alsoProvides(col_folder, ICollectionCategories)
    alsoProvides(col_folder, IProtectedItem)
    return col_folder


def order_1st_level(site):
    """Order 1st level folders."""
    ordered = ["incoming-mail", "outgoing-mail", "folders", "tasks", "plus", "contacts", "templates", "tree"]
    for i, oid in enumerate(ordered):
        site.moveObjectToPosition(oid, i)


def setup_classification(site):
    # Layer is required to ensure that faceted is correctly configured
    alsoProvides(site.REQUEST, IImioDmsMailLayer)

    if not base_hasattr(site, "folders"):
        site.invokeFactory("ClassificationFolders", id="folders", title=_(u"folders_tab"))
        folders = site["folders"]
        alsoProvides(folders, ILabelRoot)
        alsoProvides(folders, IProtectedItem)
        alsoProvides(folders, INextPrevNotNavigable)
        adapted = ILabelJar(folders)
        adapted.add("Suivi", "yellow", True)  # label_id = suivi
        do_transitions(folders, ["show_internally"])

    if not base_hasattr(site, "tree"):
        site.invokeFactory(
            "ClassificationContainer", id="tree", title=_(u"classification_tree_tab"), exclude_from_nav=True
        )
        blacklistPortletCategory(site, site["tree"])
        site["tree"].manage_addLocalRoles("AuthenticatedUsers", ["Reader"])
        alsoProvides(site["tree"], IProtectedItem)
        # do_transitions(site['tree'], ['show_internally'])

    roles_config = {
        "static_config": {
            "active": {
                "dir_general": {"roles": ["Contributor", "Editor"]},
                "encodeurs": {"roles": ["Reader"]},
                "expedition": {"roles": ["Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
            "deactivated": {
                "dir_general": {"roles": ["Contributor", "Editor"]},
                "encodeurs": {"roles": ["Reader"]},
                "expedition": {"roles": ["Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
        },
        "treating_groups": {
            "active": {"editeur": {"roles": ["Contributor", "Editor"]}, "lecteur": {"roles": ["Reader"]}},
            "deactivated": {"editeur": {"roles": ["Contributor", "Editor"]}, "lecteur": {"roles": ["Reader"]}},
        },
        "recipient_groups": {
            "active": {"editeur": {"roles": ["Reader"]}, "lecteur": {"roles": ["Reader"]}},
            "deactivated": {"editeur": {"roles": ["Reader"]}, "lecteur": {"roles": ["Reader"]}},
        },
    }

    for keyname in roles_config:
        msg = add_fti_configuration("ClassificationFolder", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        msg = add_fti_configuration("ClassificationSubfolder", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)

    roles_config = {
        "internally_published": {"createurs_dossier": {"roles": ["Contributor"]}},
        "private": {"createurs_dossier": {"roles": ["Contributor"]}},
    }
    msg = add_fti_configuration("ClassificationFolders", roles_config)
    if msg:
        logger.warn(msg)

    fti = getUtility(IDexterityFTI, name=site["folders"].portal_type)
    if "Folder" not in fti.allowed_content_types:
        original_allowed = copy.deepcopy(fti.allowed_content_types)
        fti.allowed_content_types += ("Folder",)

    # Setup dashboard collections
    collection_folder = add_db_col_folder(site["folders"], "folder-searches", _("Folders searches"), _("Folders"))
    alsoProvides(collection_folder, INextPrevNotNavigable)
    alsoProvides(collection_folder, IClassificationFoldersDashboardBatchActions)
    create_classification_folders_collections(collection_folder)

    fti.allowed_content_types = original_allowed
    configure_faceted_folder(
        collection_folder, xml="classificationfolders-searches.xml", default_UID=collection_folder["all_folders"].UID()
    )
    site["folders"].setDefaultPage("folder-searches")

    logger.info("Classification configured")


def postInstall(context):
    """Called as at the end of the setup process."""
    # the right place for your custom code

    if not context.readDataFile("imiodmsmail_marker.txt"):
        return
    site = context.getSite()

    # we adapt default portal
    adaptDefaultPortal(context)

    # we change searched types
    changeSearchedTypes(site)

    # we configure rolefields
    configure_rolefields(context)
    configure_iem_rolefields(context)
    configure_om_rolefields(context)

    if (
        base_hasattr(site.portal_types.task, "localroles")
        and site.portal_types.task.localroles.get("assigned_group", "")
        and site.portal_types.task.localroles["assigned_group"].get("created")
        and "" in site.portal_types.task.localroles["assigned_group"]["created"]
    ):
        configure_task_rolefields(context, force=True)
    else:
        configure_task_rolefields(context, force=False)

    configure_task_config(context)
    update_task_workflow(site)

    if not base_hasattr(site, "incoming-mail"):
        folderid = site.invokeFactory("Folder", id="incoming-mail", title=_(u"incoming_mail_tab"))
        im_folder = getattr(site, folderid)
        alsoProvides(im_folder, INextPrevNotNavigable)
        alsoProvides(im_folder, ILabelRoot)
        alsoProvides(im_folder, ICountableTab)
        alsoProvides(im_folder, IProtectedItem)
        adapted = ILabelJar(im_folder)
        adapted.add("Lu", "green", True)  # label_id = lu
        adapted.add("Suivi", "yellow", True)  # label_id = suivi

        # add mail-searches
        col_folder = add_db_col_folder(im_folder, "mail-searches", _("Incoming mail searches"), _("Incoming mails"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IIMDashboardBatchActions)

        createIMailCollections(col_folder)
        createStateCollections(col_folder, "dmsincomingmail")  # i_e ok
        configure_faceted_folder(col_folder, xml="im-mail-searches.xml", default_UID=col_folder["all_mails"].UID())

        # configure incoming-mail faceted
        configure_faceted_folder(
            im_folder, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_mails"].UID()
        )

        im_folder.setConstrainTypesMode(1)
        im_folder.setLocallyAllowedTypes(["dmsincomingmail", "dmsincoming_email"])
        im_folder.setImmediatelyAddableTypes(["dmsincomingmail", "dmsincoming_email"])
        do_transitions(im_folder, ["show_internally"])
        logger.info("incoming-mail folder created")

    if not base_hasattr(site, "outgoing-mail"):
        folderid = site.invokeFactory("Folder", id="outgoing-mail", title=_(u"outgoing_mail_tab"))
        om_folder = getattr(site, folderid)
        alsoProvides(om_folder, INextPrevNotNavigable)
        alsoProvides(om_folder, ILabelRoot)
        alsoProvides(om_folder, ICountableTab)
        alsoProvides(om_folder, IProtectedItem)

        # add mail-searches
        col_folder = add_db_col_folder(om_folder, "mail-searches", _("Outgoing mail searches"), _("Outgoing mails"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOMDashboardBatchActions)
        createOMailCollections(col_folder)
        createStateCollections(col_folder, "dmsoutgoingmail")
        configure_faceted_folder(col_folder, xml="om-mail-searches.xml", default_UID=col_folder["all_mails"].UID())

        # configure outgoing-mail faceted
        configure_faceted_folder(
            om_folder, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_mails"].UID()
        )

        om_folder.setConstrainTypesMode(1)
        # om_folder.setLocallyAllowedTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        om_folder.setLocallyAllowedTypes(["dmsoutgoingmail"])
        # om_folder.setImmediatelyAddableTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        om_folder.setImmediatelyAddableTypes(["dmsoutgoingmail"])
        do_transitions(om_folder, ["show_internally"])
        logger.info("outgoing-mail folder created")

    if not base_hasattr(site, "tasks"):
        folderid = site.invokeFactory("Folder", id="tasks", title=_(u"tasks_tab"))
        tsk_folder = getattr(site, folderid)
        alsoProvides(tsk_folder, INextPrevNotNavigable)
        alsoProvides(tsk_folder, ILabelRoot)
        alsoProvides(tsk_folder, ICountableTab)
        alsoProvides(tsk_folder, IProtectedItem)
        # add task-searches
        col_folder = add_db_col_folder(tsk_folder, "task-searches", _("Tasks searches"), _("Tasks"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, ITaskDashboardBatchActions)
        createTaskCollections(col_folder)
        createStateCollections(col_folder, "task")
        configure_faceted_folder(col_folder, xml="im-task-searches.xml", default_UID=col_folder["all_tasks"].UID())
        # configure outgoing-mail faceted
        configure_faceted_folder(
            tsk_folder, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_tasks"].UID()
        )

        tsk_folder.setConstrainTypesMode(1)
        tsk_folder.setLocallyAllowedTypes(["task"])
        tsk_folder.setImmediatelyAddableTypes(["task"])
        do_transitions(tsk_folder, ["show_internally"])
        logger.info("tasks folder created")

    if "plus" not in site:
        obj = api.content.create(container=site, type="Document", id="plus", title=u"● ● ●")
        do_transitions(obj, ["show_internally"])
        alsoProvides(obj, IProtectedItem)

    # Directory creation
    if not base_hasattr(site, "contacts"):
        position_types = [
            {"name": u"Président", "token": u"president"},
            {"name": u"Directeur général", "token": u"directeur-gen"},
            {"name": u"Directeur financier", "token": u"directeur-fin"},
            {"name": u"Secrétaire", "token": u"secretaire"},
            {"name": u"Employé", "token": u"employe"},
        ]
        organization_types = [
            {"name": u"Non défini", "token": u"non-defini"},
            {"name": u"SA", "token": u"sa"},
            {"name": u"Commune", "token": u"commune"},
            {"name": u"CPAS", "token": u"cpas"},
            {"name": u"Intercommunale", "token": u"intercommunale"},
            {"name": u"Zone de police", "token": u"zp"},
            {"name": u"Zone de secours", "token": u"zs"},
        ]
        organization_levels = [
            {"name": u"Non défini", "token": u"non-defini"},
            {"name": u"Département", "token": u"department"},
            {"name": u"Service", "token": u"service"},
        ]
        params = {
            "title": _(u"contacts_tab"),
            "position_types": position_types,
            "organization_types": organization_types,
            "organization_levels": organization_levels,
            "exclude_from_nav": True,
        }
        site.invokeFactory("directory", "contacts", **params)
        contacts = site["contacts"]
        alsoProvides(contacts, IProtectedItem)
        site.portal_types.directory.filter_content_types = False
        # add organizations searches
        col_folder = add_db_col_folder(contacts, "orgs-searches", _("Organizations searches"), _("Organizations"))
        contacts.moveObjectToPosition("orgs-searches", 0)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IOrganizationsDashboardBatchActions)
        createOrganizationsCollections(col_folder)
        # createStateCollections(col_folder, 'organization')
        configure_faceted_folder(col_folder, xml="organizations-searches.xml", default_UID=col_folder["all_orgs"].UID())
        # configure contacts faceted
        configure_faceted_folder(
            contacts, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_orgs"].UID()
        )
        # add held positions searches
        col_folder = add_db_col_folder(contacts, "hps-searches", _("Held positions searches"), _("Held positions"))
        contacts.moveObjectToPosition("hps-searches", 1)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IHeldPositionsDashboardBatchActions)
        createHeldPositionsCollections(col_folder)
        # createStateCollections(col_folder, 'held_position')
        configure_faceted_folder(col_folder, xml="held-positions-searches.xml", default_UID=col_folder["all_hps"].UID())
        # add persons searches
        col_folder = add_db_col_folder(contacts, "persons-searches", _("Persons searches"), _("Persons"))
        contacts.moveObjectToPosition("persons-searches", 2)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IPersonsDashboardBatchActions)
        createPersonsCollections(col_folder)
        # createStateCollections(col_folder, 'person')
        configure_faceted_folder(col_folder, xml="persons-searches.xml", default_UID=col_folder["all_persons"].UID())
        # add contact list searches
        col_folder = add_db_col_folder(contacts, "cls-searches", _("Contact list searches"), _("Contact lists"))
        contacts.moveObjectToPosition("cls-searches", 3)
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IContactListsDashboardBatchActions)
        createContactListsCollections(col_folder)
        # createStateCollections(col_folder, 'contact_list')
        configure_faceted_folder(col_folder, xml="contact-lists-searches.xml", default_UID=col_folder["all_cls"].UID())
        # add personnel folder
        contacts.invokeFactory("Folder", "personnel-folder", title=u"Mon personnel")
        # contacts.moveObjectToPosition('personnel-folder', 4)
        pf = contacts["personnel-folder"]
        alsoProvides(pf, IProtectedItem)
        alsoProvides(pf, IPersonnelFolder)
        alsoProvides(pf, IActionsPanelFolder)
        pf.layout = "personnel-listing"
        blacklistPortletCategory(pf)
        api.content.transition(obj=pf, transition="show_internally")
        pf.manage_permission(
            "collective.contact.plonegroup: Read user link fields",
            ("Manager", "Site Administrator", "Reader", "Editor", "Contributor"),
            acquire=0,
        )
        pf.manage_permission(
            "collective.contact.plonegroup: Write user link fields", ("Manager", "Site Administrator"), acquire=0
        )
        pf.setConstrainTypesMode(1)
        pf.setLocallyAllowedTypes(["person"])
        pf.setImmediatelyAddableTypes(["person"])
        # add contact list folder
        contacts.invokeFactory("Folder", "contact-lists-folder", title=u"Listes de contact")
        contacts.moveObjectToPosition("contact-lists-folder", 5)
        clf = contacts["contact-lists-folder"]
        clf.setLayout("folder_tabular_view")
        api.content.transition(obj=clf, transition="show_internally")
        alsoProvides(clf, IActionsPanelFolder)
        alsoProvides(clf, INextPrevNotNavigable)
        alsoProvides(clf, IProtectedItem)
        clf.setConstrainTypesMode(1)
        clf.setLocallyAllowedTypes(["Folder", "contact_list"])
        clf.setImmediatelyAddableTypes(["Folder", "contact_list"])
        clf.__ac_local_roles_block__ = True
        # add plonegroup-organization
        params = {
            "title": u"Mon organisation",
            "organization_type": u"commune",
            "zip_code": u"0010",
            "city": u"Ma ville",
            "street": u"Rue de la commune",
            "number": u"1",
            "email": u"contact@macommune.be",
            "use_parent_address": False,
        }
        contacts.invokeFactory("organization", "plonegroup-organization", **params)
        # contacts.moveObjectToPosition('plonegroup-organization', 5)
        alsoProvides(contacts["plonegroup-organization"], IProtectedItem)
        own_orga = contacts["plonegroup-organization"]
        blacklistPortletCategory(own_orga)

        # finishing
        site.portal_types.directory.filter_content_types = True
        do_transitions(contacts, ["show_internally"])
        logger.info("contacts folder created")

    setup_classification(site)

    # enable portal diff on mails
    pdiff = api.portal.get_tool("portal_diff")
    pdiff.setDiffForPortalType("dmsincomingmail", {"any": "Compound Diff for Dexterity types"})  # i_e ok
    pdiff.setDiffForPortalType("dmsincoming_email", {"any": "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType("dmsoutgoingmail", {"any": "Compound Diff for Dexterity types"})
    # pdiff.setDiffForPortalType('dmsoutgoing_email', {'any': "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType("task", {"any": "Compound Diff for Dexterity types"})
    pdiff.setDiffForPortalType("dmsommainfile", {"any": "Compound Diff for Dexterity types"})

    # reimport collective.contact.widget's registry step (disable jQueryUI's autocomplete)
    site.portal_setup.runImportStepFromProfile("profile-collective.contact.widget:default", "plone.app.registry")

    configure_actions_panel(site)

    configure_ckeditor(site, custom="ged", filtering="disabled")
    # add autolink plugin to ckeditor
    ckprops = site.portal_properties.ckeditor_properties
    if ckprops.hasProperty("plugins"):
        plugins_list = list(ckprops.getProperty("plugins"))
        autolink_plugin = "autolink;/++resource++ckeditor/plugins/autolink/plugin.js"
        if autolink_plugin not in plugins_list:
            plugins_list.append(autolink_plugin)
            ckprops.manage_changeProperties(plugins=plugins_list)

    # create iconified categories folders
    setup_iconified_categories(site)

    key = "collective.documentgenerator.browser.controlpanel.IDocumentGeneratorControlPanelSchema.use_stream"
    if api.portal.get_registry_record(key):
        api.portal.set_registry_record(key, False)

    configure_documentviewer(site)  # before templates to avoid auto-layout default config
    configure_fpaudit(site)

    add_templates(site)
    add_oem_templates(site)
    site.templates.exclude_from_nav = True
    site.templates.reindexObject()

    # add audit_log action
    category = site.portal_actions.get('user')
    if "audit-contacts" not in category.objectIds():
        uid = site.templates["audit-contacts"].UID()
        action = Action(
            "audit-contacts",
            title="Audit contacts",
            i18n_domain="imio.dms.mail",
            url_expr="string:${{portal_url}}/document-generation?template_uid={}&"
                     "output_format=ods".format(uid),
            available_expr="python:context.restrictedTraverse('@@various-utils').is_in_user_groups("
                           "['audit_contacts'], user=member)",
            permissions=("View",),
            visible=False,
        )
        category._setObject("audit-contacts", action)
        pos = category.getObjectPosition("logout")
        category.moveObjectToPosition("audit-contacts", pos)

    add_transforms(site)

    set_portlet(site)

    order_1st_level(site)

    # add usefull methods
    try:
        from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod

        manage_addExternalMethod(site, "sge_clean_examples", "", "imio.dms.mail.demo", "clean_examples")
        manage_addExternalMethod(site, "sge_import_contacts", "", "imports", "import_contacts")
        manage_addExternalMethod(site, "sge_import_scanned", "", "imio.dms.mail.demo", "import_scanned")
        manage_addExternalMethod(site, "sge_import_scanned2", "", "imio.dms.mail.demo", "import_scanned2")
    except Exception:
        pass

    site.portal_setup.runImportStepFromProfile(
        "profile-imio.dms.mail:singles", "imiodmsmail-add-icons-to-contact-workflow", run_dependencies=False
    )
    site.portal_setup.runImportStepFromProfile(
        "profile-imio.dms.mail:singles", "imiodmsmail-configure-wsclient", run_dependencies=False
    )
    site.portal_setup.runImportStepFromProfile(
        "profile-imio.dms.mail:singles", "imiodmsmail-contact-import-pipeline", run_dependencies=False
    )

    # remove collective.ckeditortemplates folder
    if DEFAULT_CKE_TEMPL_FOLDER in site:
        api.content.delete(obj=site[DEFAULT_CKE_TEMPL_FOLDER])

    # hide plone.portalheader message viewlet
    site.portal_setup.runImportStepFromProfile("profile-plonetheme.imioapps:default", "viewlets")

    # Add users and groups
    create_users_and_groups(site)


def blacklistPortletCategory(obj, category=CONTEXT_CATEGORY, utilityname=u"plone.leftcolumn", value=True):
    """
    block portlets on object for the corresponding category
    """
    from plone.portlets.interfaces import ILocalPortletAssignmentManager
    from plone.portlets.interfaces import IPortletManager

    # Get the proper portlet manager
    manager = queryUtility(IPortletManager, name=utilityname)
    # Get the current blacklist for the location
    blacklist = getMultiAdapter((obj, manager), ILocalPortletAssignmentManager)
    # Turn off the manager
    blacklist.setBlacklistStatus(category, value)


def setup_iconified_categories(portal):
    if 'annexes_types' not in portal:
        api.content.create(
            container=portal,
            id='annexes_types',
            title=_(u"Annexes Types"),
            type="ContentCategoryConfiguration",
            exclude_from_nav=True
        )
    ccc = portal["annexes_types"]

    # Content Category Group for classification folders
    if "annexes" not in ccc:
        annexes_category_group = api.content.create(
            type="ContentCategoryGroup",
            title=_("Folders Appendix Files"),
            container=ccc,
            id="annexes",
        )
        do_transitions(annexes_category_group, ["show_internally"])
        alsoProvides(annexes_category_group, IProtectedItem)
    else:
        annexes_category_group = ccc["annexes"]

    # Content Category Group for dms main files in incoming mails
    if "incoming_dms_files" not in ccc:
        incoming_dms_files_category_group = api.content.create(
            type="ContentCategoryGroup",
            title=_("Incoming DMS Files"),
            container=ccc,
            id="incoming_dms_files",
        )
        do_transitions(incoming_dms_files_category_group, ["show_internally"])
        alsoProvides(incoming_dms_files_category_group, IProtectedItem)
    else:
        incoming_dms_files_category_group = ccc["incoming_dms_files"]

    # Content Category Group for appendix files in incoming mails
    if "incoming_appendix_files" not in ccc:
        incoming_appendix_files_category_group = api.content.create(
            type="ContentCategoryGroup",
            title=_("Incoming Appendix Files"),
            container=ccc,
            id="incoming_appendix_files",
        )
        do_transitions(incoming_appendix_files_category_group, ["show_internally"])
        alsoProvides(incoming_appendix_files_category_group, IProtectedItem)
    else:
        incoming_appendix_files_category_group = ccc["incoming_appendix_files"]

    # Content Category Group for dms main files in outgoing mails
    if "outgoing_dms_files" not in ccc:
        outgoing_dms_files_category_group = api.content.create(
            type="ContentCategoryGroup",
            title=_("Outgoing DMS Files"),
            container=ccc,
            id="outgoing_dms_files",
            to_be_printed_activated=True,
            signed_activated=True,
            approved_activated=True,
        )
        do_transitions(outgoing_dms_files_category_group, ["show_internally"])
        alsoProvides(outgoing_dms_files_category_group, IProtectedItem)
    else:
        outgoing_dms_files_category_group = ccc["outgoing_dms_files"]

    # Content Category Group for appendix files in outgoing mails
    if "outgoing_appendix_files" not in ccc:
        outgoing_appendix_files_category_group = api.content.create(
            type="ContentCategoryGroup",
            title=_("Outgoing Appendix Files"),
            container=ccc,
            id="outgoing_appendix_files",
            to_be_printed_activated=True,
            signed_activated=True,
            approved_activated=True,
        )
        do_transitions(outgoing_appendix_files_category_group, ["show_internally"])
        alsoProvides(outgoing_appendix_files_category_group, IProtectedItem)
    else:
        outgoing_appendix_files_category_group = ccc["outgoing_appendix_files"]


def createStateCollections(folder, content_type):
    """
    create a collection for each contextual workflow state
    """
    conditions = {
        "dmsincomingmail": {  # i_e ok
            "created": "python: object.restrictedTraverse('idm-utils').created_col_cond()",
            "proposed_to_manager": "python: object.restrictedTraverse('idm-utils').proposed_to_manager_col_cond()",
        },
        "dmsoutgoingmail": {
            "scanned": "python: object.restrictedTraverse('odm-utils').scanned_col_cond()",
        },
    }
    view_fields = {
        "dmsincomingmail": {  # i_e ok
            "*": (
                u"select_row",
                u"pretty_link",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
        },
        "task": {
            "*": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
        },
        "dmsoutgoingmail": {
            "*": (
                u"select_row",
                u"pretty_link",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sent": (
                u"select_row",
                u"pretty_link",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"outgoing_date",
                u"classification_folders",
                u"actions",
            ),
        },
        "organization": {
            "*": (u"select_row", u"pretty_link", u"CreationDate", u"actions"),
        },
        "held_position": {
            "*": (u"select_row", u"pretty_link", u"CreationDate", u"actions"),
        },
        "person": {
            "*": (u"select_row", u"pretty_link", u"CreationDate", u"actions"),
        },
        "contact_list": {
            "*": (u"select_row", u"pretty_link", u"CreationDate", u"actions"),
        },
    }
    show_nb_of_items = {
        "dmsincomingmail": ("created",),  # i_e ok
        "dmsoutgoingmail": ("scanned", "signed"),
    }
    sort_on = {
        "dmsincomingmail": {  # i_e ok
            "*": u"organization_type",
        },
        "task": {"*": u"created"},
        "dmsoutgoingmail": {
            "scanned": u"organization_type",
            "*": u"created"
        },
    }

    portal_types = {"dmsincomingmail": ["dmsincomingmail", "dmsincoming_email"]}

    for state, st_tit in list_wf_states(folder, content_type):
        col_id = "searchfor_%s" % state
        if not base_hasattr(folder, col_id):
            folder.invokeFactory(
                "DashboardCollection",
                id=col_id,
                title=_(col_id),
                enabled=True,
                query=[
                    {
                        "i": "portal_type",
                        "o": "plone.app.querystring.operation.selection.is",
                        "v": portal_types.get(content_type, content_type),
                    },
                    {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": [state]},
                ],
                customViewFields=(
                    state in view_fields[content_type]
                    and view_fields[content_type][state]
                    or view_fields[content_type]["*"]
                ),
                tal_condition=conditions.get(content_type, {}).get(state),
                showNumberOfItems=(state in show_nb_of_items.get(content_type, [])),
                roles_bypassing_talcondition=["Manager", "Site Administrator"],
                sort_on=sort_on.get(content_type, {}).get(
                    state, sort_on.get(content_type, {}).get("*", u"sortable_title")
                ),
                sort_reversed=True,
                b_size=30,
                limit=0,
            )
            col = folder[col_id]
            alsoProvides(col, IProtectedItem)
            col.setSubject((u"search",))
            col.reindexObject(["Subject"])
            col.setLayout("tabular_view")


def createDashboardCollections(folder, collections):
    """
    create some dashboard collections in searches folder
    """
    for i, dic in enumerate(collections):
        if not dic.get("id"):
            continue
        if not base_hasattr(folder, dic["id"]):
            folder.invokeFactory(
                "DashboardCollection",
                dic["id"],
                enabled=dic.get("enabled", True),
                title=dic["tit"],
                query=dic["query"],
                tal_condition=dic["cond"],
                roles_bypassing_talcondition=dic["bypass"],
                customViewFields=dic["flds"],
                showNumberOfItems=dic["count"],
                sort_on=dic["sort"],
                sort_reversed=dic["rev"],
                b_size=30,
                limit=0,
            )
            collection = folder[dic["id"]]
            alsoProvides(collection, IProtectedItem)
            if "subj" in dic:
                collection.setSubject(dic["subj"])
                collection.reindexObject(["Subject"])
            collection.setLayout("tabular_view")
        if folder.getObjectPosition(dic["id"]) != i:
            folder.moveObjectToPosition(dic["id"], i)


def createIMailCollections(folder):
    """
    create some incoming mails dashboard collections
    """
    collections = [
        {
            "id": "all_mails",
            "tit": _("all_incoming_mails"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                }
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_validate",
            "tit": _("im_to_validate"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-validation",
                },
            ],
            "cond": u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsincomingmail')",  # i_e ok
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "to_treat",
            "tit": _("im_to_treat"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["proposed_to_agent"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "im_treating",
            "tit": _("im_im_treating"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["in_treatment"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("im_have_treated"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["closed"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_treat_in_my_group",
            "tit": _("im_to_treat_in_my_group"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["proposed_to_agent"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-in-treating-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_my_group",
            "tit": _("im_in_my_group"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-in-treating-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_copy_unread",
            "tit": _("im_in_copy_unread"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-in-copy-group-unread",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_copy",
            "tit": _("im_in_copy"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-in-copy-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "followed",
            "tit": _("im_followed"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-followed",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"mail_type",
                u"sender",
                u"reception_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"organization_type",
            "rev": True,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createTaskCollections(folder):
    """
    create some tasks dashboard collections
    """
    collections = [
        {
            "id": "all_tasks",
            "tit": _("all_im_tasks"),
            "subj": (u"search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]}],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_assign",
            "tit": _("tasks_to_assign"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_assign"]},
                {"i": "CompoundCriterion", "o": "plone.app.querystring.operation.compound.is", "v": "task-validation"},
            ],
            "cond": u"python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
            "enabled": False,
        },
        {
            "id": "to_treat",
            "tit": _("task_to_treat"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_do"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
        },
        {
            "id": "im_treating",
            "tit": _("task_im_treating"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["in_progress"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("task_have_treated"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["closed", "realized"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_treat_in_my_group",
            "tit": _("task_to_treat_in_my_group"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_do"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-assigned-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_my_group",
            "tit": _("tasks_in_my_group"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-assigned-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "have_created",
            "tit": _("tasks_have_created"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "Creator", "o": "plone.app.querystring.operation.string.currentUser"},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_proposing_group",
            "tit": _("tasks_in_proposing_group"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-proposing-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_close",
            "tit": _("tasks_to_close"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["realized"]},
                {"i": "CompoundCriterion", "o": "plone.app.querystring.operation.compound.is", "v": "task-validation"},
            ],
            "cond": u"python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"task_parent",
                u"review_state",
                u"assigned_group",
                u"assigned_user",
                u"due_date",
                u"CreationDate",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
            "enabled": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createOMailCollections(folder):
    """
    create some outgoing mails dashboard collections
    """
    collections = [
        {
            "id": "all_mails",
            "tit": _("all_outgoing_mails"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    # 'v': ['dmsoutgoingmail', 'dmsoutgoing_email']}], the same for all under
                    "v": ["dmsoutgoingmail"],
                }
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"outgoing_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_validate",
            "tit": _("om_to_validate"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-validation",
                },
            ],
            "cond": u"python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsoutgoingmail')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
            "enabled": False,
        },
        {
            "id": "to_treat",
            "tit": _("om_to_treat"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["created"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
        },
        {
            "id": "om_treating",
            "tit": _("om_im_treating"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_be_signed"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"send_modes",
                u"mail_type",
                u"sender",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "om_to_email",
            "tit": _("om_to_email"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_be_signed"]},
                {"i": "enabled", "o": "plone.app.querystring.operation.boolean.isTrue"},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"send_modes",
                u"mail_type",
                u"sender",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("om_have_treated"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["sent"]},
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"assigned_user",
                u"due_date",
                u"send_modes",
                u"mail_type",
                u"sender",
                u"CreationDate",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("om_in_my_group"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-in-treating-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"outgoing_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("om_in_copy"),
            "subj": (u"todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-in-copy-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"pretty_link",
                u"review_state",
                u"treating_groups",
                u"sender",
                u"recipients",
                u"send_modes",
                u"mail_type",
                u"assigned_user",
                u"CreationDate",
                u"outgoing_date",
                u"classification_folders",
                u"actions",
            ),
            "sort": u"created",
            "rev": True,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createOrganizationsCollections(folder):
    """create some dashboard collections"""
    collections = [
        {
            "id": "all_orgs",
            "tit": _("all_orgs"),
            "subj": (u"search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["organization"]}],
            "cond": u"",
            "bypass": [],
            "flds": (u"select_row", u"pretty_link", u"review_state", u"CreationDate", u"actions"),
            "sort": u"sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createHeldPositionsCollections(folder):
    """create some dashboard collections"""
    collections = [
        {
            "id": "all_hps",
            "tit": _("all_hps"),
            "subj": (u"search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["held_position"]}
            ],
            "cond": u"",
            "bypass": [],
            "flds": (u"select_row", u"pretty_link", u"review_state", u"CreationDate", u"actions"),
            "sort": u"sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createPersonsCollections(folder):
    """create some dashboard collections"""
    collections = [
        {
            "id": "all_persons",
            "tit": _("all_persons"),
            "subj": (u"search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["person"]}],
            "cond": u"",
            "bypass": [],
            "flds": (u"select_row", u"pretty_link", u"review_state", u"CreationDate", u"actions"),
            "sort": u"sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createContactListsCollections(folder):
    """create some dashboard collections"""
    collections = [
        {
            "id": "all_cls",
            "tit": _("all_cls"),
            "subj": (u"search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["contact_list"]}],
            "cond": u"",
            "bypass": [],
            "flds": (u"select_row", u"pretty_link", u"relative_path", u"review_state", u"CreationDate", u"actions"),
            "sort": u"sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def create_classification_folders_collections(folder):
    """Create classification folders default collections"""
    collections = [
        {
            "id": "all_folders",
            "tit": _("all_folders"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"classification_tree_identifiers",
                u"classification_folder_archived",
                u"classification_folder_title",
                u"classification_subfolder_archived",
                u"classification_subfolder_title",
                u"internal_reference_no",
                u"classification_treating_group",
                u"actions",
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("in_my_group"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "classificationfolder-in-treating-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"classification_tree_identifiers",
                u"classification_folder_archived",
                u"classification_folder_title",
                u"classification_subfolder_archived",
                u"classification_subfolder_title",
                u"internal_reference_no",
                u"classification_treating_group",
                u"actions",
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("in_copy"),
            "subj": (u"todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "classificationfolder-in-copy-group",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"classification_tree_identifiers",
                u"classification_folder_archived",
                u"classification_folder_title",
                u"classification_subfolder_archived",
                u"classification_subfolder_title",
                u"internal_reference_no",
                u"classification_treating_group",
                u"actions",
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "followed",
            "tit": _("followed"),
            "subj": (u"search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsincomingmail-followed",
                },
            ],
            "cond": u"",
            "bypass": [],
            "flds": (
                u"select_row",
                u"classification_tree_identifiers",
                u"classification_folder_archived",
                u"classification_folder_title",
                u"classification_subfolder_archived",
                u"classification_subfolder_title",
                u"internal_reference_no",
                u"classification_treating_group",
                u"actions",
            ),
            "sort": u"ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def create_sessions_link(portal):
    """Create sessions link in portal root if not exists"""
    if not hasattr(portal, "sessions"):
        portal.invokeFactory("Link", id="sessions", title="Sessions", remoteUrl="sessions/esign-sessions-listing")
        s_l = portal["sessions"]
        s_l.setExcludeFromNav(True)
        alsoProvides(s_l, IImioSessionsManagementContext)
        alsoProvides(s_l, IProtectedItem)
        s_l.manage_permission("Access contents information",
                              ("Contributor", "Editor", "Manager", "Reader", "Site administrator"), acquire=0)
        s_l.manage_permission("Modify portal content", ("Owner", ), acquire=0)
        s_l.manage_permission("View", ("Contributor", "Editor", "Manager", "Reader", "Site administrator"), acquire=0)
        s_l.changeOwnership(s_l.portal_membership.getMemberById("admin"))
        s_l.reindexObject()

        unlisted = list(portal.portal_properties.navtree_properties.metaTypesNotToList)
        if "Link" not in unlisted:
            unlisted.append("Link")
            portal.portal_properties.navtree_properties.manage_changeProperties(metaTypesNotToList=unlisted)
        logger.info("Sessions link created in portal root")


def adaptDefaultPortal(context):
    """
    Adapt some properties of the portal
    """
    site = context.getSite()

    # deactivate tabs auto generation in navtree_properties
    # site.portal_properties.site_properties.disable_folder_sections = True
    # remove default created objects like events, news, ...
    for obj, ids in {site: ("events", "news"), site.portal_actions.user: ("contact-contactlist-mylists",)}.items():
        for oid in ids:
            try:
                obj.manage_delObjects(ids=[oid])
                logger.info("'%s' deleted in '%s'" % (oid, obj))
            except AttributeError:
                continue

    # set member area type
    site.portal_membership.setMemberAreaType("member_area")
    site.portal_membership.memberareaCreationFlag = 0
    site.Members.setExcludeFromNav(True)
    site.Members.setConstrainTypesMode(1)
    site.Members.setLocallyAllowedTypes([])
    site.Members.setImmediatelyAddableTypes([])

    # change the content of the front-page
    try:
        frontpage = getattr(site, "front-page")
        if not base_hasattr(site, "incoming-mail"):
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype="text/html")
            # remove the presentation mode
            frontpage.setPresentation(False)
            do_transitions(frontpage, ["show_internally"])
            frontpage.reindexObject()
            logger.info("front page adapted")
        # set front-page folder as not next/prev navigable
        if not INextPrevNotNavigable.providedBy(frontpage):
            alsoProvides(frontpage, INextPrevNotNavigable)

    except AttributeError:
        # the 'front-page' object does not exist...
        pass

    # reactivate old Topic
    site.portal_types.Topic.manage_changeProperties(global_allow=True)
    for action in site.portal_controlpanel.listActions():
        if action.id == "portal_atct":
            action.visible = True

    # change default_page_types property
    if "Folder" not in site.portal_properties.site_properties.default_page_types:
        new_list = list(site.portal_properties.site_properties.default_page_types)
        new_list.append("Folder")
        site.portal_properties.site_properties.manage_changeProperties(default_page_types=new_list)

    # permissions
    # Removing owner to 'hide' sharing tab
    site.manage_permission("Sharing page: Delegate roles", ("Manager", "Site Administrator"), acquire=0)
    # Hiding layout menu
    site.manage_permission("Modify view template", ("Manager", "Site Administrator"), acquire=0)
    # Hiding folder contents
    site.manage_permission("List folder contents", ("Manager", "Site Administrator"), acquire=0)
    # List undo
    site.manage_permission("List undoable changes", ("Manager", "Site Administrator"), acquire=0)
    # History: can revert to previous versions
    site.manage_permission("CMFEditions: Revert to previous versions", ("Manager", "Site Administrator"), acquire=0)
    # imio.pm.wsclient
    site.manage_permission(
        "WS Client Access",
        ("Manager", "Site Administrator", "Contributor", "Editor", "Owner", "Reader", "Reviewer"),
        acquire=0)
    site.manage_permission("WS Client Send", ("Manager", "Site Administrator", "Editor"), acquire=0)

    # History: add history after contact merging.
    # Member needed if the treating_group is changed to another where current user doesn't have rights
    site.manage_permission(
        "CMFEditions: Access previous versions",
        ("Manager", "Site Administrator", "Contributor", "Editor", "Member", "Owner", "Reviewer"),
        acquire=0,
    )
    site.manage_permission(
        "CMFEditions: Save new version",
        ("Manager", "Site Administrator", "Contributor", "Editor", "Member", "Owner", "Reviewer"),
        acquire=0,
    )

    # CLassification tree: can get tree
    site.manage_permission("plone.restapi: Use REST API", ("Manager", "Site Administrator", "Member"), acquire=0)

    # Default roles for own permissions
    site.manage_permission("imio.dms.mail: Write mail base fields", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission("imio.dms.mail: Write treating group field", ("Manager", "Site Administrator"), acquire=0)
    # site.manage_permission('imio.dms.mail: Write creating group field', ('Manager', 'Site Administrator'),
    #                       acquire=0)

    # Default roles for ftw labels
    site.manage_permission("ftw.labels: Manage Labels Jar", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission("ftw.labels: Change Labels", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission("ftw.labels: Change Personal Labels", ("Manager", "Site Administrator", "Member"), acquire=0)
    site.manage_permission("Portlets: Manage own portlets", ("Manager", "Site Administrator"), acquire=0)

    # Set markup allowed types: for RichText field, don't display anymore types listbox
    adapter = MarkupControlPanelAdapter(site)
    adapter.set_allowed_types(["text/html"])

    # Activate browser message
    msg = site["messages-config"]["browser-warning"]
    api.content.transition(obj=msg, to_state="activated")

    # we need external edition so make sure it is activated
    # site.portal_properties.site_properties.manage_changeProperties(ext_editor=True)  # sans effet
    site.portal_memberdata.manage_changeProperties(ext_editor=True)  # par défaut pour les nouveaux utilisateurs

    # for collective.externaleditor
    registry = getUtility(IRegistry)
    registry["externaleditor.ext_editor"] = True
    if "Image" in registry["externaleditor.externaleditor_enabled_types"]:
        registry["externaleditor.externaleditor_enabled_types"] = [
            "PODTemplate",
            "ConfigurablePODTemplate",
            "DashboardPODTemplate",
            "SubTemplate",
            "StyleTemplate",
            "dmsommainfile",
            "MailingLoopTemplate",
            "annex",
        ]

    # registry
    api.portal.set_registry_record(
        name="Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.allowed", value=False
    )
    api.portal.set_registry_record(
        name="Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.search_rss_enabled", value=False
    )
    api.portal.set_registry_record(
        "collective.contact.core.interfaces.IContactCoreParameters.contact_source_metadata_content",
        u"{gft} ⏺ {number}, {street}, {zip_code}, {city} ⏺ {email}",
    )
    # chars ⏺, ↈ  , ▐ , ⬤, ● (see ubuntu character table. Use ctrl+shift+u+code)
    api.portal.set_registry_record(
        "collective.contact.core.interfaces.IContactCoreParameters.display_below_content_title_on_views", True
    )
    # imio.dms.mail configuration annotation
    # if changed, must be updated in testing.py !
    set_dms_config(
        ["wf_from_to", "dmsincomingmail", "n_plus", "from"],  # i_e ok
        [("created", "back_to_creation"), ("proposed_to_manager", "back_to_manager")],
    )
    set_dms_config(
        ["wf_from_to", "dmsincomingmail", "n_plus", "to"],  # i_e ok
        [("closed", "close"), ("proposed_to_agent", "propose_to_agent")],
    )
    set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "from"], [("created", "back_to_creation")])
    set_dms_config(
        ["wf_from_to", "dmsoutgoingmail", "n_plus", "to"],
        [("sent", "mark_as_sent"), ("to_be_signed", "propose_to_be_signed")],
    )
    # review levels configuration, used in utils and adapters
    set_dms_config(
        ["review_levels", "dmsincomingmail"], OrderedDict([("dir_general", {"st": ["proposed_to_manager"]})])  # i_e ok
    )
    set_dms_config(["review_levels", "task"], OrderedDict())
    set_dms_config(["review_levels", "dmsoutgoingmail"], OrderedDict())
    # review_states configuration, is the same as review_levels with some key, value inverted
    set_dms_config(
        ["review_states", "dmsincomingmail"], OrderedDict([("proposed_to_manager", {"group": "dir_general"})])  # i_e ok
    )
    set_dms_config(["review_states", "task"], OrderedDict())
    set_dms_config(["review_states", "dmsoutgoingmail"], OrderedDict())

    # cron4plone settings
    cron_configlet = queryUtility(ICronConfiguration, "cron4plone_config")
    if not cron_configlet.cronjobs:
        # Syntax: m h dom mon command.
        cron_configlet.cronjobs = [
            u"59 3 * * portal/@@various-utils/cron_read_label_handling",
        ]

    create_sessions_link(site)

    # configure MailHost
    if get_environment() == "prod":
        mail_host = get_mail_host()
        mail_host.smtp_queue = True
        mail_host.smtp_queue_directory = "mailqueue"
        # (re)start the mail queue
        mail_host._stopQueueProcessorThread()
        mail_host._startQueueProcessorThread()


def changeSearchedTypes(site):
    """
    Change searched types
    """
    to_show = ["dmsmainfile", "dmsommainfile"]
    to_hide = [
        "Collection",
        "ConfigurablePODTemplate",
        "DashboardCollection",
        "DashboardPODTemplate",
        "Discussion Item",
        "Document",
        "Event",
        "File",
        "Folder",
        "Image",
        "Link",
        "MessagesConfig",
        "News Item",
        "PodTemplate",
        "StyleTemplate",
        "SubTemplate",
        "Topic",
        "directory",
        "dmsdocument",
        "held_position",
        "organization",
        "person",
        "position",
        "task",
    ]
    not_searched = list(site.portal_properties.site_properties.types_not_searched)
    for typ in to_show:
        if typ in not_searched:
            not_searched.remove(typ)
    for typ in to_hide:
        if typ not in not_searched:
            not_searched.append(typ)
    site.portal_properties.site_properties.manage_changeProperties(types_not_searched=not_searched)


def configure_rolefields(context):
    """
    Configure the rolefields for dmsincomingmail
    """

    roles_config = {
        "static_config": {
            "created": {
                "encodeurs": {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                }
            },
            "proposed_to_manager": {
                "dir_general": {
                    "roles": ["Contributor", "Editor", "Reviewer", "Base Field Writer", "Treating Group Writer"]
                },
                "encodeurs": {"roles": ["Base Field Writer", "Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
            },
            "proposed_to_agent": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "Treating Group Writer"]},
                "encodeurs": {"roles": ["Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
            },
            "in_treatment": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "Treating Group Writer"]},
                "encodeurs": {"roles": ["Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
            },
            "closed": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "Treating Group Writer"]},
                "encodeurs": {"roles": ["Reader"]},
                "lecteurs_globaux_ce": {"roles": ["Reader"]},
            },
        },
        "treating_groups": {
            # 'created': {},
            # 'proposed_to_manager': {},
            "proposed_to_agent": {
                "editeur": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "in_treatment": {
                "editeur": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "closed": {"editeur": {"roles": ["Reviewer"]}, "lecteur": {"roles": ["Reader"]}},
        },
        "recipient_groups": {
            # 'created': {},
            # 'proposed_to_manager': {},
            "proposed_to_agent": {"editeur": {"roles": ["Reader"]}, "lecteur": {"roles": ["Reader"]}},
            "in_treatment": {"editeur": {"roles": ["Reader"]}, "lecteur": {"roles": ["Reader"]}},
            "closed": {"editeur": {"roles": ["Reader"]}, "lecteur": {"roles": ["Reader"]}},
        },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration("dmsincomingmail", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        msg = add_fti_configuration("dmsincoming_email", copy.deepcopy(roles_config[keyname]), keyname=keyname)
        if msg:
            logger.warn(msg)


def configure_iem_rolefields(context):
    """
    Configure the rolefields for dmsincoming_email
    """
    lr, fti = fti_configuration(portal_type="dmsincoming_email")
    lrs = lr["static_config"]
    if "Base Field Writer" not in lrs["proposed_to_agent"]["encodeurs"]["roles"]:
        lrs["proposed_to_agent"]["encodeurs"]["roles"] = [
            "Contributor",
            "Editor",
            "Base Field Writer",
            "Treating Group Writer",
        ]
    lrt = lr["treating_groups"]
    if "Base Field Writer" not in lrt["proposed_to_agent"]["editeur"]["roles"]:
        lrt["proposed_to_agent"]["editeur"]["roles"] = [
            "Contributor",
            "Editor",
            "Reviewer",
            "Base Field Writer",
            "Treating Group Writer",
        ]
    lr._p_changed = True


def configure_om_rolefields(context):
    """
    Configure the rolefields for dmsoutgoingmail
    """
    roles_config = {
        "static_config": {
            "to_be_signed": {
                "expedition": {"roles": ["Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
            "signed": {
                "expedition": {"roles": ["Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
            "sent": {
                "expedition": {"roles": ["Reader", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
                "dir_general": {"roles": ["Reader", "Reviewer"]},
                "lecteurs_globaux_cs": {"roles": ["Reader"]},
            },
            "scanned": {
                "expedition": {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "Reader",
                        "Reviewer",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                },
                "encodeurs": {"roles": ["Reader"]},
            },
        },
        "treating_groups": {
            "created": {
                "encodeur": {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "Reviewer",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                }
            },
            "to_be_signed": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Contributor", "Reviewer"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "signed": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader", "Reviewer"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "sent": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader", "Reviewer"]},
                "lecteur": {"roles": ["Reader"]},
            },
        },
        "recipient_groups": {
            "to_be_signed": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "signed": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "sent": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
        },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration("dmsoutgoingmail", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)
        # msg = add_fti_configuration('dmsoutgoing_email', roles_config[keyname], keyname=keyname)
        # if msg:
        #     logger.warn(msg)


def configure_task_rolefields(context, force=False):
    """
    Configure the rolefields on task
    """
    roles_config = {
        "static_config": {
            "to_assign": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
            },
            "to_do": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
            },
            "in_progress": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
            },
            "realized": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
            },
            "closed": {
                "dir_general": {"roles": ["Contributor", "Editor", "Reviewer"]},
                "encodeurs": {"roles": ["Reader"]},
            },
        },
        "assigned_group": {
            "to_assign": {},
            "to_do": {
                "editeur": {
                    "roles": ["Contributor", "Editor"],
                    "rel": "{'collective.task.related_taskcontainer':['Reader']}",
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "in_progress": {
                "editeur": {
                    "roles": ["Contributor", "Editor"],
                    "rel": "{'collective.task.related_taskcontainer':['Reader']}",
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "realized": {
                "editeur": {
                    "roles": ["Contributor", "Editor"],
                    "rel": "{'collective.task.related_taskcontainer':['Reader']}",
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "closed": {
                "editeur": {"roles": ["Reader"], "rel": "{'collective.task.related_taskcontainer':['Reader']}"},
                "lecteur": {"roles": ["Reader"]},
            },
        },
        "assigned_user": {},
        "enquirer": {},
        "parents_assigned_groups": {
            "to_assign": {},
            "to_do": {
                "editeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "in_progress": {
                "editeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "realized": {
                "editeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "closed": {
                "editeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
        },
        "parents_enquirers": {},
    }
    for keyname in roles_config:
        # we overwrite existing configuration from task installation !
        msg = add_fti_configuration("task", roles_config[keyname], keyname=keyname, force=force)
        if msg:
            logger.warn(msg)


def configure_task_config(context):
    """
    Configure collective task
    """
    PARENTS_FIELDS_CONFIG = [
        {
            "fieldname": u"parents_assigned_groups",
            "attribute": u"assigned_group",
            "attribute_prefix": u"ITask",
            "provided_interface": u"collective.task.interfaces.ITaskContent",
        },
        {
            "fieldname": u"parents_enquirers",
            "attribute": u"enquirer",
            "attribute_prefix": u"ITask",
            "provided_interface": u"collective.task.interfaces.ITaskContent",
        },
        {
            "fieldname": u"parents_assigned_groups",
            "attribute": u"treating_groups",
            "attribute_prefix": None,
            "provided_interface": u"collective.dms.basecontent.dmsdocument.IDmsDocument",
        },
    ]
    registry = getUtility(IRegistry)
    logger.info("Configure registry")
    registry["collective.task.parents_fields"] = PARENTS_FIELDS_CONFIG


def configure_documentviewer(site):
    """
    Set the settings of document viewer product
    """
    gsettings = GlobalSettings(site)
    gsettings.storage_location = os.path.join(os.getcwd(), "var", "dv_files")
    gsettings.storage_type = "Blob"
    gsettings.pdf_image_format = "jpg"
    gsettings.auto_select_layout = False
    if "excel" not in gsettings.auto_layout_file_types:
        gsettings.auto_layout_file_types = list(gsettings.auto_layout_file_types) + ["excel", "image"]
    gsettings.show_search = True
    # set preservation days
    api.portal.set_registry_record("imio.dms.mail.dv_clean_days", 180)


def configure_fpaudit(site):
    """Set fpaudit registry"""
    registry = getUtility(IRegistry)
    if not registry.get("imio.fpaudit.settings.log_entries"):
        registry["imio.fpaudit.settings.log_entries"] = [{"log_id": u"contacts", "audit_log": u"contacts.log",
                                                          "log_format": u"%(asctime)s - %(message)s"}]


def refreshCatalog(context):
    """
    Reindex catalog
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    site.portal_catalog.refreshCatalog()


def setupFacetedContacts(portal):
    """Setup facetednav for contacts. Was used in old migration"""


def configure_actions_panel(portal):
    """
    Configure actions panel registry
    """
    logger.info("Configure actions panel registry")
    registry = getUtility(IRegistry)

    if not registry.get("imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"):
        registry["imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"] = [
            "dmsincomingmail.back_to_creation|",
            "dmsincomingmail.back_to_manager|",
            "dmsincomingmail.back_to_treatment|",
            "dmsincomingmail.back_to_agent|",
            "dmsincoming_email.back_to_creation|",
            "dmsincoming_email.back_to_manager|",
            "dmsincoming_email.back_to_treatment|",
            "dmsincoming_email.back_to_agent|",
            "task.back_in_created|",
            "task.back_in_created2|",
            "task.back_in_to_assign|",
            "task.back_in_to_do|",
            "task.back_in_progress|",
            "task.back_in_realized|",
            "dmsoutgoingmail.back_to_agent|",
            "dmsoutgoingmail.back_to_creation|",
            "dmsoutgoingmail.back_to_be_signed|",
            "dmsoutgoingmail.back_to_signed|",
            "dmsoutgoingmail.back_to_scanned|",
        ]


def configure_faceted_folder(folder, xml=None, default_UID=None):
    """Configure faceted navigation on folder."""
    enableFacetedDashboardFor(folder, xml and os.path.dirname(__file__) + "/faceted_conf/%s" % xml or None)
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


def get_dashboard_collections(folder, uids=False):
    """Return dashboard collections"""
    brains = folder.portal_catalog.unrestrictedSearchResults(
        portal_type="DashboardCollection", path="/".join(folder.getPhysicalPath())
    )
    if uids:
        return [b.UID for b in brains]
    return brains


def list_templates():
    """Templates list used in add_templates method but also in update method"""
    dpath = pkg_resources.resource_filename("imio.dms.mail", "profiles/default/templates")
    # (cid, plone_path, os_path)
    return [
        (10, "templates/d-im-listing", os.path.join(dpath, "d-im-listing.odt")),
        (12, "templates/d-im-listing-tab", os.path.join(dpath, "d-im-listing.ods")),
        (13, "templates/d-im-listing-tab-details", os.path.join(dpath, "d-im-listing-details.ods")),
        (20, "templates/all-contacts-export", os.path.join(dpath, "contacts-export.ods")),
        (30, "templates/export-users-groups", os.path.join(dpath, "export-users-groups.ods")),
        (40, "templates/audit-contacts", os.path.join(dpath, "audit-contacts.ods")),
        (90, "templates/om/style", os.path.join(dpath, "om-styles.odt")),
        (100, "templates/om/header", os.path.join(dpath, "om-header.odt")),
        (105, "templates/om/footer", os.path.join(dpath, "om-footer.odt")),
        (110, "templates/om/intro", os.path.join(dpath, "om-intro.odt")),
        (120, "templates/om/ending", os.path.join(dpath, "om-ending.odt")),
        (150, "templates/om/mailing", os.path.join(dpath, "om-mailing.odt")),
        (200, "templates/om/d-print", os.path.join(dpath, "d-print.odt")),
        (205, "templates/om/main", os.path.join(dpath, "om-main.odt")),
        (210, "templates/om/common/receipt", os.path.join(dpath, "om-receipt.odt")),
    ]


def add_templates(site):
    """Create pod templates."""
    from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES

    template_types = POD_TEMPLATE_TYPES.keys() + ["Folder", "DashboardPODTemplate"]
    for path, title, interfaces in [
        ("templates", _(u"templates_tab"), [IActionsPanelFolderAll]),
        ("templates/om", _(u"Outgoing mail"), [IOMTemplatesFolder, IActionsPanelFolderAll]),
        ("templates/om/common", _(u"Common templates"), []),
    ]:
        parts = path.split("/")
        tid = parts[-1]
        parent = site.unrestrictedTraverse("/".join(parts[:-1]))
        if not base_hasattr(parent, tid):
            folderid = parent.invokeFactory("Folder", id=tid, title=title)
            tplt_fld = getattr(parent, folderid)
            tplt_fld.setLocallyAllowedTypes(template_types)
            tplt_fld.setImmediatelyAddableTypes(template_types)
            tplt_fld.setConstrainTypesMode(1)
            tplt_fld.setExcludeFromNav(False)
            api.content.transition(obj=tplt_fld, transition="show_internally")
            alsoProvides(tplt_fld, INextPrevNotNavigable)
            alsoProvides(tplt_fld, IProtectedItem)
            for itf in interfaces:
                alsoProvides(tplt_fld, itf)
            logger.info("'%s' folder created" % path)

    # adding view for Folder type
    # ptype = site.portal_types.Folder
    # if 'dg-templates-listing' not in ptype.view_methods:
    #     views = list(ptype.view_methods)
    #     views.append('dg-templates-listing')
    #     ptype.view_methods = tuple(views)
    site.templates.om.layout = "dg-templates-listing"
    alsoProvides(site.templates.om, IBelowContentBodyBatchActionsMarker)

    def combine_data(data, test=None):
        templates_list = list_templates()
        ret = []
        for cid, ppath, ospath in templates_list:
            if not test or test(cid):
                dic = data[cid]
                dic["cid"] = cid
                parts = ppath.split("/")
                dic["id"] = parts[-1]
                dic["cont"] = "/".join(parts[0:-1])
                if "attrs" not in dic:
                    dic["attrs"] = {}
                dic["attrs"]["odt_file"] = create_NamedBlob(ospath)
                ret.append(dic)
        return ret

    data = {
        10: {
            "title": _(u"Mail listing template"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "rename_page_styles": False,
                "dashboard_collections": [
                    b.UID
                    for b in get_dashboard_collections(site["incoming-mail"]["mail-searches"])
                    if b.id == "all_mails"
                ],
                # cond: check c10 reception date (display link), check output_format (generation view)
                "tal_condition": "python:request.get('c10[]', False) or request.get('output_format', False)",
            },
        },
        12: {
            "title": _(u"Mail listing template sheet"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "dashboard_collections": [
                    b.UID
                    for b in get_dashboard_collections(site["incoming-mail"]["mail-searches"])
                    if b.id == "all_mails"
                ],
                # cond: check c10 reception date (display link), check output_format (generation view)
                "tal_condition": "python:request.get('c10[]', False) or request.get('output_format', False)",
            },
        },
        13: {
            "title": _(u"Mail listing template sheet with details"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "dashboard_collections": [
                    b.UID
                    for b in get_dashboard_collections(site["incoming-mail"]["mail-searches"])
                    if b.id == "all_mails"
                ],
                # cond: check c10 reception date (display link), check output_format (generation view)
                "tal_condition": "python:request.get('c10[]', False) or request.get('output_format', False)",
            },
        },
        20: {
            "title": _(u"All contacts export"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "dashboard_collections": [
                    b.UID for b in get_dashboard_collections(site["contacts"]["orgs-searches"]) if b.id == "all_orgs"
                ],
                "tal_condition": "python: False",
                "roles_bypassing_talcondition": ["Manager", "Site Administrator"],
            },
        },
        30: {
            "title": _(u"Export users and groups"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "dashboard_collections": [
                    b.UID for b in get_dashboard_collections(site["contacts"]["orgs-searches"]) if b.id == "all_orgs"
                ],
                "tal_condition": "python: False",
                "roles_bypassing_talcondition": ["Manager", "Site Administrator"],
            },
        },
        40: {
            "title": _(u"Contacts audit"),
            "type": "ConfigurablePODTemplate",
            # "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "tal_condition": "python: context.absolute_url() == context.portal_url() and "
                                 "context.restrictedTraverse('@@various-utils').is_in_user_groups(['audit_contacts'],"
                                 "user=member)",
                "context_variables": [
                    {"name": u"log_id", "value": u"contacts"},
                    {"name": u"actions", "value": u""},
                    {"name": u"extras", "value": u"UID,PATH,CTX_PATH,CASE"},
                ],
            },
        },
        90: {"title": _(u"Style template"), "type": "StyleTemplate", "trans": ["show_internally"]},
    }

    templates = combine_data(data, test=lambda x: x < 100)
    cids = create(templates, pos=False)
    exists = "main" in site["templates"]["om"]

    data = {
        100: {
            "title": _(u"Header template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        105: {
            "title": _(u"Footer template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        110: {
            "title": _(u"Intro template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        120: {
            "title": _(u"Ending template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        150: {
            "title": _(u"Mailing template"),
            "type": "MailingLoopTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()], "rename_page_styles": True},
        },
    }

    templates = combine_data(data, test=lambda x: 100 <= x < 200)
    cids = create(templates, pos=False, cids=cids)

    data = {
        200: {
            "title": _(u"Print template"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "tal_condition": "python: context.restrictedTraverse('odm-utils').is_odt_activated()",
                "dashboard_collections": get_dashboard_collections(site["outgoing-mail"]["mail-searches"], uids=True),
                "style_template": [cids[90].UID()],
                "rename_page_styles": True,
            },
        },
        205: {
            "title": _(u"Base template"),
            "type": "ConfigurablePODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "pod_portal_types": ["dmsoutgoingmail"],
                "merge_templates": [
                    {"pod_context_name": u"doc_entete", "do_rendering": False, "template": cids[100].UID()},
                    {"pod_context_name": u"doc_intro", "do_rendering": False, "template": cids[110].UID()},
                    {"pod_context_name": u"doc_fin", "do_rendering": False, "template": cids[120].UID()},
                    {"pod_context_name": u"doc_pied_page", "do_rendering": False, "template": cids[105].UID()},
                ],
                "style_template": [cids[90].UID()],
                "mailing_loop_template": cids[150].UID(),
                "rename_page_styles": False,
            },
        },
        #                       'context_variables': [{'name': u'do_mailing', 'value': u'1'}]}},
        210: {
            "title": _(u"Receipt template"),
            "type": "ConfigurablePODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "pod_portal_types": ["dmsoutgoingmail"],
                "merge_templates": [
                    {"pod_context_name": u"doc_entete", "do_rendering": False, "template": cids[100].UID()},
                    {"pod_context_name": u"doc_intro", "do_rendering": False, "template": cids[110].UID()},
                    {"pod_context_name": u"doc_fin", "do_rendering": False, "template": cids[120].UID()},
                    {"pod_context_name": u"doc_pied_page", "do_rendering": False, "template": cids[105].UID()},
                ],
                "style_template": [cids[90].UID()],
                "mailing_loop_template": cids[150].UID(),
                "context_variables": [
                    {"name": u"PD", "value": u"True"},
                    {"name": u"PC", "value": u"True"},
                    {"name": u"PVS", "value": u"False"},
                ],
                "rename_page_styles": False,
            },
        },
    }

    templates = combine_data(data, test=lambda x: x >= 200)
    cids = create(templates, pos=False, cids=cids)

    for obj in cids.values():
        alsoProvides(obj, IProtectedItem)

    if not exists:
        site["templates"]["om"].moveObjectToPosition("d-print", 1)
        site["templates"]["om"].moveObjectToPosition("main", 10)
        site["templates"]["om"].moveObjectToPosition("common", 11)


def add_transforms(site):
    """
    Add some transforms
    """
    pt = site.portal_transforms
    for name, module in (
        ("pdf_to_text", "Products.PortalTransforms.transforms.pdf_to_text"),
        ("pdf_to_html", "Products.PortalTransforms.transforms.pdf_to_html"),
        ("odt_to_text", "imio.dms.mail.transforms"),
    ):
        if name not in pt.objectIds():
            try:
                pt.manage_addTransform(name, module)
                logger.info("Added '%s' transform" % name)
            except MimeTypeException as err:
                logger.info("CANNOT ADD '{}' transform: {}".format(name, err))


def add_oem_templates(site):
    """Create email templates."""
    folder_id = "oem"
    if folder_id in site.templates:
        return
    site.templates.invokeFactory("Folder", id=folder_id, title=_("Outgoing email"))
    tplt_fld = site.templates[folder_id]
    tplt_fld.setLocallyAllowedTypes(["Folder", "cktemplate"])
    tplt_fld.setImmediatelyAddableTypes(["Folder", "cktemplate"])
    tplt_fld.setConstrainTypesMode(1)
    tplt_fld.setExcludeFromNav(False)
    api.content.transition(obj=tplt_fld, transition="show_internally")
    for itf in [IActionsPanelFolderAll, INextPrevNotNavigable, IProtectedItem]:
        alsoProvides(tplt_fld, itf)
    logger.info("'templates/{}' folder created".format(folder_id))
    site.templates.moveObjectToPosition(folder_id, 1)
    site.templates.oem.layout = "ck-templates-listing"
    alsoProvides(site.templates.oem, IOMCKTemplatesFolder)

    templates = [
        {
            "cid": 10,
            "cont": "templates/oem",
            "type": "cktemplate",
            "id": "emain",
            "title": _(u"Email general template"),
            "trans": ["show_internally"],
            "attrs": {
                "content": richtextval(
                    u"<p>Bonjour,</p><p>en réponse à votre email, vous trouverez ci-dessous les "
                    u"infos demandées.</p><p>Cordialement</p><p>&nbsp;</p><p>Administration "
                    u"communale</p><p>...</p>"
                )
            },
        },
    ]
    create(templates, pos=False)


def set_portlet(portal):
    ann = IAnnotations(portal)
    portlet = ann["plone.portlets.contextassignments"]["plone.leftcolumn"]["portlet_actions"]
    portlet.ptitle = u"Liens divers"
    portlet.category = u"object_portlet"
    portlet.show_icons = False
    portlet.default_icon = None
    portlet._p_changed = True


def update_task_workflow(portal):
    """remove back_in_to_assign transition in task workflow"""
    wf = portal.portal_workflow["task_workflow"]
    if "back_in_created2" not in wf.transitions:
        wf.transitions.addTransition("back_in_created2")
        wf.transitions["back_in_created2"].setProperties(
            title="back_in_created",
            new_state_id="created",
            trigger_type=1,
            script_name="",
            actbox_name="back_in_created2",
            actbox_url="",
            actbox_icon="%(portal_url)s/++resource++collective.task/back_in_created.png",
            actbox_category="workflow",
            props={"guard_permissions": "Request review"},
        )
    # modify to_do transitions
    state = wf.states["to_do"]
    transitions = list(state.transitions)  # noqa
    if "back_in_to_assign" in transitions:
        transitions.remove("back_in_to_assign")
        transitions.append("back_in_created2")
        state.transitions = tuple(transitions)


@implementer(INonInstallable)
class HiddenProfiles(object):
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            "imio.dms.mail:singles",
        ]


def create_users_and_groups(site):
    """
    Add French scanner user and groups
    """
    # creating scanner user
    password = "Dmsmail69!"
    if get_environment() == "prod":
        password = generate_password()
    logger.info("Generated password='%s'" % password)
    uid = "scanner"
    try:
        member = site.portal_registration.addMember(
            id=uid, password=password, roles=["Member"] + ["Batch importer"]
        )
        member.setMemberProperties({"fullname": _(u"Scanner"), "email": "{}@macommune.be".format(uid)})
    except ValueError as exc:
        if not str(exc).startswith("The login name you selected is already in use"):
            logger.error("Error creating user '%s': %s" % (uid, exc))

    if api.group.get("encodeurs") is None:
        api.group.create("encodeurs", _("1 IM encoders"))
        site["incoming-mail"].manage_addLocalRoles("encodeurs", ["Contributor", "Reader"])
        site["contacts"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        #        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname="encodeurs", username="scanner")
    if api.group.get("dir_general") is None:
        api.group.create("dir_general", _("1 General manager"))
        site["outgoing-mail"].manage_addLocalRoles("dir_general", ["Contributor"])
        site["contacts"].manage_addLocalRoles("dir_general", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles(
            "dir_general", ["Contributor", "Editor", "Reader"]
        )
    if api.group.get("expedition") is None:
        api.group.create("expedition", _("1 OM dispatch"))
        site["outgoing-mail"].manage_addLocalRoles("expedition", ["Contributor"])
        site["contacts"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        api.group.add_user(groupname="expedition", username="scanner")
    if api.group.get("gestion_contacts") is None:
        api.group.create("gestion_contacts", _("1 Duplicate contacts management"))
    if api.group.get("createurs_dossier") is None:
        api.group.create("createurs_dossier", _("1 Folders creators"))
    if api.group.get("audit_contacts") is None:
        api.group.create("audit_contacts", _("1 Contacts audit"))
    if api.group.get("lecteurs_globaux_ce") is None:
        api.group.create("lecteurs_globaux_ce", _("2 IM global readers"))
    if api.group.get("lecteurs_globaux_cs") is None:
        api.group.create("lecteurs_globaux_cs", _("2 OM global readers"))
    if api.group.get("esign_watchers") is None:
        api.group.create("esign_watchers", _("2 External signing watchers"))


def clean_examples_step(context):
    """Clean some examples"""
    if not context.readDataFile("imiodmsmail_examples_minimal_marker.txt"):
        return
    site = context.getSite()
    clean_examples(site)
