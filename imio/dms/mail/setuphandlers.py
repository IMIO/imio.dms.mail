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
from collective.documentgenerator.interfaces import IBelowContentBodyBatchActionsMarker
from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.dashboard.interfaces import ICountableTab
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from collective.iconifiedcategory.utils import calculate_category_id
from collective.labels.interfaces import ILabelJar
from collective.labels.interfaces import ILabelRoot
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.quickupload.browser.quickupload_settings import IQuickUploadControlPanel
from dexterity.localroles.utils import add_fti_configuration
from dexterity.localroles.utils import fti_configuration
from imio.dms.mail import _tr as _
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import DEFAULT_DISPLAYED_TABS
from imio.dms.mail import FIRST_LEVEL_TABS
from imio.dms.mail.Extensions.demo import clean_examples
from imio.dms.mail.interfaces import IActionsPanelFolder
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IClassificationFoldersDashboardBatchActions
from imio.dms.mail.interfaces import IContactListsDashboardBatchActions
from imio.dms.mail.interfaces import IHeldPositionsDashboardBatchActions
from imio.dms.mail.interfaces import IIMDashboardBatchActions
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.interfaces import IOMDashboardBatchActions
from imio.dms.mail.interfaces import IOMTemplatesFolder
from imio.dms.mail.interfaces import IOrganizationsDashboardBatchActions
from imio.dms.mail.interfaces import IPersonnelDashboardBatchActions
from imio.dms.mail.interfaces import IPersonsDashboardBatchActions
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.interfaces import IReqDashboard
from imio.dms.mail.interfaces import ITaskDashboardBatchActions
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import set_dms_config
from imio.helpers.content import create
from imio.helpers.content import create_NamedBlob
from imio.helpers.content import richtextval
from imio.helpers.emailer import get_mail_host
from imio.helpers.security import generate_password
from imio.helpers.security import get_environment
from imio.helpers.workflow import do_transitions
from imio.pyutils.utils import safe_encode
from plone import api
from plone.app.contenttypes.setuphandlers import configure_members_folder
from plone.base.interfaces.constrains import ISelectableConstrainTypes
from plone.base.utils import base_hasattr
from plone.dexterity.interfaces import IDexterityFTI
from plone.namedfile.file import NamedBlobImage
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry
from Products.CMFCore.ActionInformation import Action
from Products.CMFPlone.interfaces import INonInstallable
from Products.MimetypesRegistry import MimeTypeException
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import alsoProvides
from zope.interface import implementer

import copy
import logging
import os
import pkg_resources


logger = logging.getLogger("imio.dms.mail: setuphandlers")

OM_PRINT_TO_SIGN_COLS = ("to_treat", "searchfor_created")
OM_PRINT_SIGNED_COLS = ("om_treating", "om_to_email", "searchfor_signed")


def add_db_col_folder(folder, cid, title, displayed=""):
    if base_hasattr(folder, cid):
        return folder[cid]

    folder.invokeFactory("Folder", id=cid, title=title, rights=displayed)
    col_folder = folder[cid]
    ISelectableConstrainTypes(col_folder).setConstrainTypesMode(1)
    ISelectableConstrainTypes(col_folder).setLocallyAllowedTypes(["DashboardCollection"])
    ISelectableConstrainTypes(col_folder).setImmediatelyAddableTypes(["DashboardCollection"])
    do_transitions(col_folder, ["show_internally"])
    alsoProvides(col_folder, ICollectionCategories)
    alsoProvides(col_folder, IProtectedItem)
    return col_folder


def order_1st_level(site):
    """Order 1st level folders."""
    ordered = FIRST_LEVEL_TABS
    for i, oid in enumerate(ordered):
        site.moveObjectToPosition(oid, i)


def setup_classification(site):
    # Layer is required to ensure that faceted is correctly configured
    alsoProvides(site.REQUEST, IImioDmsMailLayer)

    if not base_hasattr(site, "folders"):
        site.invokeFactory("ClassificationFolders", id="folders", title=_("folders_tab"))
        folders = site["folders"]
        alsoProvides(folders, ILabelRoot)
        alsoProvides(folders, IProtectedItem)
        alsoProvides(folders, INextPrevNotNavigable)
        adapted = ILabelJar(folders)
        adapted.add("Suivi", "yellow", True)  # label_id = suivi
        do_transitions(folders, ["show_internally"])

    if not base_hasattr(site, "tree"):
        site.invokeFactory(
            "ClassificationContainer", id="tree", title=_("classification_tree_tab"), exclude_from_nav=True
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
            logger.warning(msg)
        msg = add_fti_configuration("ClassificationSubfolder", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warning(msg)

    roles_config = {
        "internally_published": {"createurs_dossier": {"roles": ["Contributor"]}},
        "private": {"createurs_dossier": {"roles": ["Contributor"]}},
    }
    msg = add_fti_configuration("ClassificationFolders", roles_config)
    if msg:
        logger.warning(msg)

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
    configure_signrequest_rolefields(context)

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
        folderid = site.invokeFactory("Folder", id="incoming-mail", title=_("incoming_mail_tab"))
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

        ISelectableConstrainTypes(im_folder).setConstrainTypesMode(1)
        ISelectableConstrainTypes(im_folder).setLocallyAllowedTypes(["dmsincomingmail", "dmsincoming_email"])
        ISelectableConstrainTypes(im_folder).setImmediatelyAddableTypes(["dmsincomingmail", "dmsincoming_email"])
        do_transitions(im_folder, ["show_internally"])
        logger.info("incoming-mail folder created")

    if not base_hasattr(site, "outgoing-mail"):
        folderid = site.invokeFactory("Folder", id="outgoing-mail", title=_("outgoing_mail_tab"))
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

        ISelectableConstrainTypes(om_folder).setConstrainTypesMode(1)
        # ISelectableConstrainTypes(om_folder).setLocallyAllowedTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        ISelectableConstrainTypes(om_folder).setLocallyAllowedTypes(["dmsoutgoingmail"])
        # ISelectableConstrainTypes(om_folder).setImmediatelyAddableTypes(['dmsoutgoingmail', 'dmsoutgoing_email'])
        ISelectableConstrainTypes(om_folder).setImmediatelyAddableTypes(["dmsoutgoingmail"])
        do_transitions(om_folder, ["show_internally"])
        logger.info("outgoing-mail folder created")

    if not base_hasattr(site, "requests"):
        folderid = site.invokeFactory("Folder", id="requests", title=_("requests_tab"))
        req_folder = getattr(site, folderid)
        req_folder.exclude_from_nav = True
        alsoProvides(req_folder, INextPrevNotNavigable)
        alsoProvides(req_folder, ILabelRoot)
        alsoProvides(req_folder, ICountableTab)
        alsoProvides(req_folder, IProtectedItem)
        # add searches
        col_folder = add_db_col_folder(req_folder, "requests-searches", _("Requests searches"), _("Requests"))
        alsoProvides(col_folder, INextPrevNotNavigable)
        alsoProvides(col_folder, IReqDashboard)
        createReqCollections(col_folder)
        createStateCollections(col_folder, "sign_request")
        configure_faceted_folder(col_folder, xml="requests-searches.xml", default_UID=col_folder["all_requests"].UID())
        # configure faceted
        configure_faceted_folder(
            req_folder, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_requests"].UID()
        )

        ISelectableConstrainTypes(req_folder).setConstrainTypesMode(1)
        ISelectableConstrainTypes(req_folder).setLocallyAllowedTypes(["sign_request"])
        ISelectableConstrainTypes(req_folder).setImmediatelyAddableTypes(["sign_request"])
        do_transitions(req_folder, ["show_internally"])
        logger.info("requests folder created")

    if not base_hasattr(site, "tasks"):
        folderid = site.invokeFactory("Folder", id="tasks", title=_("tasks_tab"))
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

        ISelectableConstrainTypes(tsk_folder).setConstrainTypesMode(1)
        ISelectableConstrainTypes(tsk_folder).setLocallyAllowedTypes(["task"])
        ISelectableConstrainTypes(tsk_folder).setImmediatelyAddableTypes(["task"])
        do_transitions(tsk_folder, ["show_internally"])
        logger.info("tasks folder created")

    if "plus" not in site:
        obj = api.content.create(container=site, type="Document", id="plus", title="● ● ●")
        do_transitions(obj, ["show_internally"])
        alsoProvides(obj, IProtectedItem)

    # Directory creation
    if not base_hasattr(site, "contacts"):
        position_types = [
            {"name": "Président", "token": "president"},
            {"name": "Directeur général", "token": "directeur-gen"},
            {"name": "Directeur financier", "token": "directeur-fin"},
            {"name": "Secrétaire", "token": "secretaire"},
            {"name": "Employé", "token": "employe"},
        ]
        organization_types = [
            {"name": "Non défini", "token": "non-defini"},
            {"name": "SA", "token": "sa"},
            {"name": "Commune", "token": "commune"},
            {"name": "CPAS", "token": "cpas"},
            {"name": "Intercommunale", "token": "intercommunale"},
            {"name": "Zone de police", "token": "zp"},
            {"name": "Zone de secours", "token": "zs"},
        ]
        organization_levels = [
            {"name": "Non défini", "token": "non-defini"},
            {"name": "Département", "token": "department"},
            {"name": "Service", "token": "service"},
        ]
        params = {
            "title": _("contacts_tab"),
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
        contacts.invokeFactory("Folder", "personnel-folder", title="Mon personnel")
        # contacts.moveObjectToPosition('personnel-folder', 4)
        pf = contacts["personnel-folder"]
        alsoProvides(pf, IProtectedItem)
        alsoProvides(pf, IActionsPanelFolder)
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
        # add personnel searches dashboard
        create_personnel_dashboard(pf)
        ISelectableConstrainTypes(pf).setConstrainTypesMode(1)
        ISelectableConstrainTypes(pf).setLocallyAllowedTypes(["person"])
        ISelectableConstrainTypes(pf).setImmediatelyAddableTypes(["person"])
        # add contact list folder
        contacts.invokeFactory("Folder", "contact-lists-folder", title="Listes de contact")
        contacts.moveObjectToPosition("contact-lists-folder", 5)
        clf = contacts["contact-lists-folder"]
        clf.setLayout("tabular_view")
        api.content.transition(obj=clf, transition="show_internally")
        alsoProvides(clf, IActionsPanelFolder)
        alsoProvides(clf, INextPrevNotNavigable)
        alsoProvides(clf, IProtectedItem)
        ISelectableConstrainTypes(clf).setConstrainTypesMode(1)
        ISelectableConstrainTypes(clf).setLocallyAllowedTypes(["Folder", "contact_list"])
        ISelectableConstrainTypes(clf).setImmediatelyAddableTypes(["Folder", "contact_list"])
        clf.__ac_local_roles_block__ = True
        # add plonegroup-organization
        params = {
            "title": "Mon organisation",
            "organization_type": "commune",
            "zip_code": "0010",
            "city": "Ma ville",
            "street": "Rue de la commune",
            "number": "1",
            "email": "contact@macommune.be",
            "use_parent_address": False,
        }
        contacts.invokeFactory("organization", "plonegroup-organization", **params)
        # contacts.moveObjectToPosition('plonegroup-organization', 5)
        own_orga = contacts["plonegroup-organization"]
        alsoProvides(own_orga, IProtectedItem)
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

    configure_actions_panel(site)

    # create iconified categories folders
    setup_iconified_categories(site)

    key = "collective.documentgenerator.browser.controlpanel.IDocumentGeneratorControlPanelSchema.use_stream"
    if api.portal.get_registry_record(key):
        api.portal.set_registry_record(key, False)

    configure_fpaudit(site)

    add_templates(site)
    site.templates.exclude_from_nav = True
    site.templates.reindexObject()

    # add audit_log action
    category = site.portal_actions.get("user")
    if "audit-contacts" not in category.objectIds():
        uid = site.templates["audit-contacts"].UID()
        action = Action(
            "audit-contacts",
            title="Audit contacts",
            i18n_domain="imio.dms.mail",
            url_expr="string:${{portal_url}}/document-generation?template_uid={}&" "output_format=ods".format(uid),
            available_expr="python:context.restrictedTraverse('@@various-utils').is_in_user_groups("
            "['audit_contacts'], user=member)",
            permissions=("View",),
            visible=False,
        )
        category._setObject("audit-contacts", action)
        pos = category.getObjectPosition("logout")
        category.moveObjectToPosition("audit-contacts", pos)

    add_transforms(site)

    if ARCHIVE_SITE:
        api.portal.set_registry_record("plone.bundles/imio-dms-mail-archives.enabled", True)

    order_1st_level(site)

    # seed the displayed tabs setting from the current site state
    api.portal.set_registry_record("imio.dms.mail.displayed_tabs", DEFAULT_DISPLAYED_TABS)

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

    # set sim_upload_limit to 1 to prevent ZODB conflicts on concurrent uploads
    getUtility(IRegistry).forInterface(IQuickUploadControlPanel).sim_upload_limit = 1

    # hide plone.portalheader message viewlet
    site.portal_setup.runImportStepFromProfile("profile-plonetheme.imioapps:default", "viewlets")

    # Add users and groups
    create_users_and_groups(site)


def blacklistPortletCategory(obj, category=CONTEXT_CATEGORY, utilityname="plone.leftcolumn", value=True):
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
    if "annexes_types" not in portal:
        api.content.create(
            container=portal,
            id="annexes_types",
            title=_("Annexes Types"),
            type="ContentCategoryConfiguration",
            exclude_from_nav=True,
        )
    ccc = portal["annexes_types"]

    def _create_category_group(oid, title, **kwargs):
        if oid not in ccc:
            group = api.content.create(type="ContentCategoryGroup", title=title, container=ccc, id=oid, **kwargs)
            do_transitions(group, ["show_internally"])
            alsoProvides(group, IProtectedItem)
        else:
            group = ccc[oid]
        return group

    om_activated = {
        "to_be_printed_activated": True,
        "signed_activated": True,
        "approved_activated": True,
    }
    sr_activated = {
        "signed_activated": True,
        "approved_activated": True,
    }

    # Content Category Group for classification folders
    _create_category_group("annexes", _("Folders Appendix Files"))
    # Content Category Group for dms main files in incoming mails
    incoming_dms_files_category_group = _create_category_group("incoming_dms_files", _("Incoming DMS Files"))
    # Content Category Group for appendix files in incoming mails
    incoming_appendix_files_category_group = _create_category_group(
        "incoming_appendix_files", _("Incoming Appendix Files")
    )
    # Content Category Group for dms main files in outgoing mails
    outgoing_dms_files_category_group = _create_category_group(
        "outgoing_dms_files", _("Outgoing DMS Files"), **om_activated
    )
    # Content Category Group for appendix files in outgoing mails
    outgoing_appendix_files_category_group = _create_category_group(
        "outgoing_appendix_files", _("Outgoing Appendix Files"), **om_activated
    )
    # Content Category Group for appendix files in sign requests
    sr_appendix_files_category_group = _create_category_group(
        "sign_request_appendix_files", _("Sign Request Appendix Files"), **sr_activated
    )

    # Create ContentCategory objects inside each category group
    images_dir = pkg_resources.resource_filename("imio.dms.mail", "profiles/examples/images")

    def _create_category(group, oid, title, img, **kwargs):
        if oid not in group:
            icon_path = os.path.join(images_dir, img)
            with open(icon_path, "rb") as fl:
                icon = NamedBlobImage(fl.read(), filename=img)
            cat = api.content.create(
                type="ContentCategory", title=title, description="", container=group, icon=icon, id=oid, **kwargs
            )
            alsoProvides(cat, IProtectedItem)

    # Content Categories for incoming mails
    _create_category(
        incoming_dms_files_category_group, "incoming-dms-file", _("Incoming DMS File"), "file-alt-regular.png"
    )
    _create_category(
        incoming_appendix_files_category_group, "incoming-appendix-file", _("Incoming Appendix File"), "attach.png"
    )

    # Content Categories for outgoing mails
    _create_category(
        outgoing_dms_files_category_group,
        "outgoing-dms-file",
        _("Outgoing DMS File"),
        "file-alt-regular.png",
        to_sign=True,
        to_approve=True,
    )
    _create_category(
        outgoing_dms_files_category_group,
        "outgoing-scanned-dms-file",
        _("Outgoing Scanned DMS File"),
        "file-alt-regular.png",
        to_sign=True,
        to_approve=False,
    )
    _create_category(
        outgoing_appendix_files_category_group,
        "outgoing-appendix-file",
        _("Outgoing Appendix File"),
        "attach.png",
        to_sign=False,
        to_approve=False,
    )
    _create_category(
        outgoing_appendix_files_category_group,
        "outgoing-signable-appendix-file",
        _("Outgoing Signable Appendix File"),
        "attach-esign.png",
        to_sign=True,
        to_approve=True,
    )

    # Content Categories for sign requests
    _create_category(
        sr_appendix_files_category_group,
        "sign-request-appendix-file",
        _("Sign Request Appendix File"),
        "attach.png",
        to_sign=True,
        to_approve=True,
    )


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
                "select_row",
                "pretty_link",
                "treating_groups",
                "assigned_user",
                "due_date",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
        },
        "task": {
            "*": (
                "select_row",
                "pretty_link",
                "task_parent",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
        },
        "dmsoutgoingmail": {
            "*": (
                "select_row",
                "pretty_link",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sent": (
                "select_row",
                "pretty_link",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "outgoing_date",
                "classification_folders",
                "actions",
            ),
        },
        "sign_request": {
            "*": (
                "pretty_link",
                "treating_groups",
                "assigned_user",
                "CreationDate",
                "actions",
            ),
        },
        "organization": {
            "*": ("select_row", "pretty_link", "CreationDate", "actions"),
        },
        "held_position": {
            "*": ("select_row", "pretty_link", "CreationDate", "actions"),
        },
        "person": {
            "*": ("select_row", "pretty_link", "CreationDate", "actions"),
        },
        "contact_list": {
            "*": ("select_row", "pretty_link", "CreationDate", "actions"),
        },
    }
    show_nb_of_items = {
        "dmsincomingmail": ("created",),  # i_e ok
        "dmsoutgoingmail": ("scanned", "signed"),
    }
    sort_on = {
        "dmsincomingmail": {  # i_e ok
            "*": "organization_type",
        },
        "task": {"*": "created"},
        "dmsoutgoingmail": {"scanned": "organization_type", "*": "created"},
        "sign_request": {"*": "created"},
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
                    state, sort_on.get(content_type, {}).get("*", "sortable_title")
                ),
                sort_reversed=True,
                b_size=30,
                limit=0,
            )
            col = folder[col_id]
            alsoProvides(col, IProtectedItem)
            col.setSubject(("search",))
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
            "subj": ("search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                }
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_validate",
            "tit": _("im_to_validate"),
            "subj": ("todo",),
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
            "cond": "python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsincomingmail')",  # i_e ok
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "to_treat",
            "tit": _("im_to_treat"),
            "subj": ("todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["proposed_to_agent"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "im_treating",
            "tit": _("im_im_treating"),
            "subj": ("todo",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["in_treatment"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("im_have_treated"),
            "subj": ("search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["dmsincomingmail", "dmsincoming_email"],
                },
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["closed"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_treat_in_my_group",
            "tit": _("im_to_treat_in_my_group"),
            "subj": ("search",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_my_group",
            "tit": _("im_in_my_group"),
            "subj": ("search",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_copy_unread",
            "tit": _("im_in_copy_unread"),
            "subj": ("todo",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_copy",
            "tit": _("im_in_copy"),
            "subj": ("todo",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
            "rev": True,
            "count": False,
        },
        {
            "id": "followed",
            "tit": _("im_followed"),
            "subj": ("search",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "reception_date",
                "classification_folders",
                "actions",
            ),
            "sort": "organization_type",
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
            "subj": ("search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]}],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_assign",
            "tit": _("tasks_to_assign"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_assign"]},
                {"i": "CompoundCriterion", "o": "plone.app.querystring.operation.compound.is", "v": "task-validation"},
            ],
            "cond": "python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
            "enabled": False,
        },
        {
            "id": "to_treat",
            "tit": _("task_to_treat"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_do"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "im_treating",
            "tit": _("task_im_treating"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["in_progress"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("task_have_treated"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["closed", "realized"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_treat_in_my_group",
            "tit": _("task_to_treat_in_my_group"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_do"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-assigned-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "in_my_group",
            "tit": _("tasks_in_my_group"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-assigned-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "have_created",
            "tit": _("tasks_have_created"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "Creator", "o": "plone.app.querystring.operation.string.currentUser"},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_proposing_group",
            "tit": _("tasks_in_proposing_group"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "task-in-proposing-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_close",
            "tit": _("tasks_to_close"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["task"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["realized"]},
                {"i": "CompoundCriterion", "o": "plone.app.querystring.operation.compound.is", "v": "task-validation"},
            ],
            "cond": "python:object.restrictedTraverse('idm-utils').user_has_review_level('task')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                "select_row",
                "pretty_link",
                "task_parent",
                "review_state",
                "assigned_group",
                "assigned_user",
                "due_date",
                "CreationDate",
                "actions",
            ),
            "sort": "created",
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
            "subj": ("search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    # 'v': ['dmsoutgoingmail', 'dmsoutgoing_email']}], the same for all under
                    "v": ["dmsoutgoingmail"],
                }
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "outgoing_date",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_validate",
            "tit": _("om_to_validate"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-validation",
                },
            ],
            "cond": "python:object.restrictedTraverse('idm-utils').user_has_review_level('dmsoutgoingmail')",
            "bypass": ["Manager", "Site Administrator"],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
            "enabled": False,
        },
        {
            "id": "to_treat",
            "tit": _("om_to_treat"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["created"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "om_treating",
            "tit": _("om_im_treating"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["signed"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "om_to_email",
            "tit": _("om_to_email"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["signed"]},
                {"i": "enabled", "o": "plone.app.querystring.operation.boolean.isTrue"},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "have_treated",
            "tit": _("om_have_treated"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["sent"]},
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "assigned_user",
                "due_date",
                "send_modes",
                "mail_type",
                "sender",
                "CreationDate",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("om_in_my_group"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-in-treating-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "outgoing_date",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("om_in_copy"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["dmsoutgoingmail"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "dmsoutgoingmail-in-copy-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "pretty_link",
                "review_state",
                "treating_groups",
                "sender",
                "recipients",
                "send_modes",
                "mail_type",
                "assigned_user",
                "CreationDate",
                "outgoing_date",
                "classification_folders",
                "actions",
            ),
            "sort": "created",
            "rev": True,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def createReqCollections(folder):
    """
    create some signing requests dashboard collections
    """
    flds = (
        "pretty_link",
        "review_state",
        "treating_groups",
        "assigned_user",
        "CreationDate",
        "actions",
    )
    collections = [
        {
            "id": "all_requests",
            "tit": _("all_requests"),
            "subj": ("search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]}],
            "cond": "",
            "bypass": [],
            "flds": flds,
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "to_approve",
            "tit": _("req_to_approve"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]},
                {"i": "review_state", "o": "plone.app.querystring.operation.selection.is", "v": ["to_approve"]},
                {"i": "approvings", "o": "plone.app.querystring.operation.string.currentUser"},
            ],
            "cond": "python:object.restrictedTraverse('various-utils').user_is_approving(user=member)",
            "bypass": ["Manager", "Site Administrator"],
            "flds": flds,
            "sort": "created",
            "rev": True,
            "count": True,
        },
        {
            "id": "to_treat",
            "tit": _("req_to_treat"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]},
                {"i": "assigned_user", "o": "plone.app.querystring.operation.string.currentUser"},
            ],
            "cond": "",
            "bypass": [],
            "flds": flds,
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("req_in_my_group"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "sign_request-in-treating-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": flds,
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("req_in_copy"),
            "subj": ("todo",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "sign_request-in-copy-group",
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": flds,
            "sort": "created",
            "rev": True,
            "count": False,
        },
        {
            "id": "in_esign_sessions",
            "tit": _("req_in_sessions"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["sign_request"]},
                {
                    "i": "CompoundCriterion",
                    "o": "plone.app.querystring.operation.compound.is",
                    "v": "files-belonging-to-a-given-session",
                },
            ],
            "cond": "python:object.restrictedTraverse('various-utils').user_is_approving(user=member)",
            "bypass": ["Manager", "Site Administrator"],
            "flds": flds,
            "sort": "created",
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
            "subj": ("search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["organization"]}],
            "cond": "",
            "bypass": [],
            "flds": ("select_row", "pretty_link", "review_state", "CreationDate", "actions"),
            "sort": "sortable_title",
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
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["held_position"]}
            ],
            "cond": "",
            "bypass": [],
            "flds": ("select_row", "pretty_link", "review_state", "CreationDate", "actions"),
            "sort": "sortable_title",
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
            "subj": ("search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["person"]}],
            "cond": "",
            "bypass": [],
            "flds": ("select_row", "pretty_link", "review_state", "CreationDate", "actions"),
            "sort": "sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def create_personnel_dashboard(pf):
    """Create the personnel dashboard."""
    col_folder = add_db_col_folder(pf, "personnel-searches", _("Personnel searches"), _("Personnel"))
    alsoProvides(col_folder, INextPrevNotNavigable)
    alsoProvides(col_folder, IPersonnelDashboardBatchActions)
    blacklistPortletCategory(col_folder)
    collections = [
        {
            "id": "all_personnel",
            "tit": _("all_personnel"),
            "subj": ("search",),
            "query": [
                {"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["person"]},
                {
                    "i": "object_provides",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["imio.dms.mail.interfaces.IPersonnelContact"],
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": ("select_row", "pretty_link", "userid", "primary_organization", "hps"),
            "sort": "sortable_title",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(col_folder, collections)
    alsoProvides(pf, IPersonnelDashboardBatchActions)
    configure_faceted_folder(
        col_folder,
        xml="personnel-searches.xml",
        default_UID=col_folder["all_personnel"].UID(),
        show_left_column=False,
    )
    configure_faceted_folder(pf, xml="default_dashboard_widgets.xml", default_UID=col_folder["all_personnel"].UID())
    return col_folder


def createContactListsCollections(folder):
    """create some dashboard collections"""
    collections = [
        {
            "id": "all_cls",
            "tit": _("all_cls"),
            "subj": ("search",),
            "query": [{"i": "portal_type", "o": "plone.app.querystring.operation.selection.is", "v": ["contact_list"]}],
            "cond": "",
            "bypass": [],
            "flds": ("select_row", "pretty_link", "relative_path", "review_state", "CreationDate", "actions"),
            "sort": "sortable_title",
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
            "subj": ("search",),
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.is",
                    "v": ["ClassificationFolder", "ClassificationSubfolder"],
                },
            ],
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "classification_tree_identifiers",
                "classification_folder_archived",
                "classification_folder_title",
                "classification_subfolder_archived",
                "classification_subfolder_title",
                "internal_reference_no",
                "classification_treating_group",
                "actions",
            ),
            "sort": "ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_my_group",
            "tit": _("in_my_group"),
            "subj": ("search",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "classification_tree_identifiers",
                "classification_folder_archived",
                "classification_folder_title",
                "classification_subfolder_archived",
                "classification_subfolder_title",
                "internal_reference_no",
                "classification_treating_group",
                "actions",
            ),
            "sort": "ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "in_copy",
            "tit": _("in_copy"),
            "subj": ("todo",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "classification_tree_identifiers",
                "classification_folder_archived",
                "classification_folder_title",
                "classification_subfolder_archived",
                "classification_subfolder_title",
                "internal_reference_no",
                "classification_treating_group",
                "actions",
            ),
            "sort": "ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
        {
            "id": "followed",
            "tit": _("followed"),
            "subj": ("search",),
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
            "cond": "",
            "bypass": [],
            "flds": (
                "select_row",
                "classification_tree_identifiers",
                "classification_folder_archived",
                "classification_folder_title",
                "classification_subfolder_archived",
                "classification_subfolder_title",
                "internal_reference_no",
                "classification_treating_group",
                "actions",
            ),
            "sort": "ClassificationFolderSort",
            "rev": False,
            "count": False,
        },
    ]
    createDashboardCollections(folder, collections)


def adaptDefaultPortal(context):
    """
    Adapt some properties of the portal
    """
    site = context.getSite()

    # remove default created objects like events, news, ...
    for obj, ids in {site: ("events", "news"), site.portal_actions.user: ("contact-contactlist-mylists",)}.items():
        for oid in ids:
            try:
                obj.manage_delObjects(ids=[oid])
                logger.info("'%s' deleted in '%s'" % (oid, obj))
            except AttributeError:
                continue

    # set member area type (user folders are not created at login: plone.enable_user_folders stays False)
    site.portal_membership.setMemberAreaType("member_area")
    site.portal_membership.memberareaCreationFlag = 0
    # Plone 6 creates the Members folder only with the example content
    configure_members_folder(site, api.portal.get_default_language())
    site.Members.exclude_from_nav = True
    ISelectableConstrainTypes(site.Members).setConstrainTypesMode(1)
    ISelectableConstrainTypes(site.Members).setLocallyAllowedTypes([])
    ISelectableConstrainTypes(site.Members).setImmediatelyAddableTypes([])

    # change the content of the front page (Plone 6: the site root, or a front-page document of the example content)
    frontpage = site.get("front-page", None)
    if not base_hasattr(site, "incoming-mail"):
        if frontpage is not None:
            frontpage.title = _("front_page_title")
            frontpage.description = _("front_page_descr")
            frontpage.text = richtextval(_("front_page_text"))
            do_transitions(frontpage, ["show_internally"])
            frontpage.reindexObject()
        else:
            site.text = richtextval(_("front_page_text"))
        logger.info("front page adapted")
    # set front-page folder as not next/prev navigable
    if frontpage is not None and not INextPrevNotNavigable.providedBy(frontpage):
        alsoProvides(frontpage, INextPrevNotNavigable)

    # change default_page_types property
    default_page_types = list(api.portal.get_registry_record("plone.default_page_types", default=[]))
    if "Folder" not in default_page_types:
        api.portal.set_registry_record("plone.default_page_types", default_page_types + ["Folder"])

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
        acquire=0,
    )
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

    # Classification tree: can get tree
    site.manage_permission("plone.restapi: Use REST API", ("Manager", "Site Administrator", "Member"), acquire=0)

    # Default roles for own permissions
    site.manage_permission("imio.dms.mail: Write mail base fields", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission("imio.dms.mail: Write treating group field", ("Manager", "Site Administrator"), acquire=0)
    # site.manage_permission('imio.dms.mail: Write creating group field', ('Manager', 'Site Administrator'),
    #                       acquire=0)

    # Default roles for labels
    site.manage_permission("collective.labels: Manage Labels Jar", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission("collective.labels: Change Labels", ("Manager", "Site Administrator"), acquire=0)
    site.manage_permission(
        "collective.labels: Change Personal Labels", ("Manager", "Site Administrator", "Member"), acquire=0
    )
    site.manage_permission("Portlets: Manage own portlets", ("Manager", "Site Administrator"), acquire=0)

    # Set markup allowed types: for RichText field, don't display anymore types listbox
    api.portal.set_registry_record("plone.allowed_types", ("text/html",))

    # Activate browser message
    msg = site["messages-config"]["browser-warning"]
    api.content.transition(obj=msg, to_state="activated")

    # we need external edition so make sure it is activated
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
        name="plone.base.interfaces.syndication.ISiteSyndicationSettings.allowed", value=False
    )
    api.portal.set_registry_record(
        name="plone.base.interfaces.syndication.ISiteSyndicationSettings.search_rss_enabled", value=False
    )
    api.portal.set_registry_record(
        "collective.contact.core.interfaces.IContactCoreParameters.contact_source_metadata_content",
        "{gft} ⏺ {number}, {street}, {zip_code}, {city} ⏺ {email}",
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
        "directory",
        "dmsdocument",
        "held_position",
        "organization",
        "person",
        "position",
        "task",
    ]
    not_searched = list(api.portal.get_registry_record("plone.types_not_searched", default=[]))
    for typ in to_show:
        if typ in not_searched:
            not_searched.remove(typ)
    for typ in to_hide:
        if typ not in not_searched and typ in site.portal_types:  # the record only accepts existing types
            not_searched.append(typ)
    api.portal.set_registry_record("plone.types_not_searched", tuple(not_searched))


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
            logger.warning(msg)
        msg = add_fti_configuration("dmsincoming_email", copy.deepcopy(roles_config[keyname]), keyname=keyname)
        if msg:
            logger.warning(msg)


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
            logger.warning(msg)
        # msg = add_fti_configuration('dmsoutgoing_email', roles_config[keyname], keyname=keyname)
        # if msg:
        #     logger.warning(msg)


def configure_signrequest_rolefields(context):
    """
    Configure the rolefields for sign_request (per sign_request_workflow state).
    """
    roles_config = {
        "treating_groups": {
            "created": {
                "demand_sign": {"roles": ["Contributor", "Editor", "Reviewer"]},
            },
            "to_approve": {
                "demand_sign": {"roles": ["Contributor", "Reviewer"]},
            },
            "to_be_signed": {
                "demand_sign": {"roles": ["Reader", "Reviewer"]},
            },
            "signed": {
                "demand_sign": {"roles": ["Reader", "Reviewer"]},
            },
            "closed": {
                "demand_sign": {"roles": ["Reader"]},
            },
        },
        "recipient_groups": {
            "created": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
            "to_approve": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
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
            "closed": {
                "editeur": {"roles": ["Reader"]},
                "encodeur": {"roles": ["Reader"]},
                "lecteur": {"roles": ["Reader"]},
            },
        },
    }
    for keyname in roles_config:
        # don't overwrite existing configuration
        msg = add_fti_configuration("sign_request", roles_config[keyname], keyname=keyname)
        if msg:
            logger.warning(msg)


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
                    "rel": '{"collective.task.related_taskcontainer":["Reader"]}',
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "in_progress": {
                "editeur": {
                    "roles": ["Contributor", "Editor"],
                    "rel": '{"collective.task.related_taskcontainer":["Reader"]}',
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "realized": {
                "editeur": {
                    "roles": ["Contributor", "Editor"],
                    "rel": '{"collective.task.related_taskcontainer":["Reader"]}',
                },
                "lecteur": {"roles": ["Reader"]},
            },
            "closed": {
                "editeur": {"roles": ["Reader"], "rel": '{"collective.task.related_taskcontainer":["Reader"]}'},
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
            logger.warning(msg)


def configure_task_config(context):
    """
    Configure collective task
    """
    PARENTS_FIELDS_CONFIG = [
        {
            "fieldname": "parents_assigned_groups",
            "attribute": "assigned_group",
            "attribute_prefix": "ITask",
            "provided_interface": "collective.task.interfaces.ITaskContent",
        },
        {
            "fieldname": "parents_enquirers",
            "attribute": "enquirer",
            "attribute_prefix": "ITask",
            "provided_interface": "collective.task.interfaces.ITaskContent",
        },
        {
            "fieldname": "parents_assigned_groups",
            "attribute": "treating_groups",
            "attribute_prefix": None,
            "provided_interface": "collective.dms.basecontent.dmsdocument.IDmsDocument",
        },
    ]
    registry = getUtility(IRegistry)
    logger.info("Configure registry")
    registry["collective.task.parents_fields"] = PARENTS_FIELDS_CONFIG


def configure_fpaudit(site):
    """Set fpaudit registry"""
    registry = getUtility(IRegistry)
    if not registry.get("imio.fpaudit.settings.log_entries"):
        registry["imio.fpaudit.settings.log_entries"] = [
            {"log_id": "contacts", "audit_log": "contacts.log", "log_format": "%(asctime)s - %(message)s"}
        ]


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
            "sign_request.back_to_creation|",
            "sign_request.back_to_approve|",
            "sign_request.back_to_be_signed|",
            "sign_request.back_to_signed|",
        ]


def configure_faceted_folder(folder, xml=None, default_UID=None, show_left_column=True):
    """Configure faceted navigation on folder."""
    # eea.facetednavigation 16: only the types with this behavior can be faceted
    fti = getUtility(IDexterityFTI, name=folder.portal_type)
    if "eea.faceted.navigable" not in fti.behaviors:
        fti.manage_changeProperties(behaviors=tuple(fti.behaviors) + ("eea.faceted.navigable",))
    enableFacetedDashboardFor(
        folder,
        xml and os.path.dirname(__file__) + "/faceted_conf/%s" % xml or None,
        show_left_column=show_left_column,
    )
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
    # (cid, plone_path, os_path, position in parent folder: subfolders are not moved, so 'templates/om'
    #  stays first in 'templates', as 'templates/om/common' in 'templates/om')
    return [
        (10, "templates/d-im-listing", os.path.join(dpath, "d-im-listing.odt"), 1),
        (12, "templates/d-im-listing-tab", os.path.join(dpath, "d-im-listing.ods"), 2),
        (13, "templates/d-im-listing-tab-details", os.path.join(dpath, "d-im-listing-details.ods"), 3),
        (20, "templates/all-contacts-export", os.path.join(dpath, "contacts-export.ods"), 4),
        (30, "templates/export-users-groups", os.path.join(dpath, "export-users-groups.ods"), 5),
        (40, "templates/audit-contacts", os.path.join(dpath, "audit-contacts.ods"), 6),
        (90, "templates/om/style", os.path.join(dpath, "om-styles.odt"), 0),
        (100, "templates/om/header", os.path.join(dpath, "om-header.odt"), 1),
        (105, "templates/om/footer", os.path.join(dpath, "om-footer.odt"), 2),
        (110, "templates/om/intro", os.path.join(dpath, "om-intro.odt"), 3),
        (120, "templates/om/ending", os.path.join(dpath, "om-ending.odt"), 4),
        (125, "templates/om/download_barcode", os.path.join(dpath, "om-download-barcode.odt"), 5),
        (150, "templates/om/mailing", os.path.join(dpath, "om-mailing.odt"), 9),
        (200, "templates/om/d-print-to-sign", os.path.join(dpath, "d-print.odt"), 7),
        (201, "templates/om/d-print-signed", os.path.join(dpath, "d-print.odt"), 8),
        (205, "templates/om/main", os.path.join(dpath, "om-main.odt"), 6),
        (210, "templates/om/common/receipt", os.path.join(dpath, "om-receipt.odt"), 0),
    ]


def add_templates(site):
    """Create pod templates."""
    from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES

    template_types = list(POD_TEMPLATE_TYPES) + ["Folder", "DashboardPODTemplate"]
    for path, title, interfaces in [
        ("templates", _("templates_tab"), [IActionsPanelFolderAll]),
        ("templates/om", _("Outgoing mail"), [IOMTemplatesFolder, IActionsPanelFolderAll]),
        ("templates/om/common", _("Common templates"), []),
    ]:
        parts = path.split("/")
        tid = parts[-1]
        parent = site.unrestrictedTraverse("/".join(parts[:-1]))
        if not base_hasattr(parent, tid):
            folderid = parent.invokeFactory("Folder", id=tid, title=title)
            tplt_fld = getattr(parent, folderid)
            ISelectableConstrainTypes(tplt_fld).setLocallyAllowedTypes(template_types)
            ISelectableConstrainTypes(tplt_fld).setImmediatelyAddableTypes(template_types)
            ISelectableConstrainTypes(tplt_fld).setConstrainTypesMode(1)
            tplt_fld.exclude_from_nav = False
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
        for cid, ppath, ospath, pos in templates_list:
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

    category_id = calculate_category_id(site["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"])

    data = {
        10: {
            "title": _("Mail listing template"),
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
            "title": _("Mail listing template sheet"),
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
            "title": _("Mail listing template sheet with details"),
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
            "title": _("All contacts export"),
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
                "max_objects": 0,
            },
        },
        30: {
            "title": _("Export users and groups"),
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
                "max_objects": 0,
            },
        },
        40: {
            "title": _("Contacts audit"),
            "type": "ConfigurablePODTemplate",
            # "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["ods"],
                "rename_page_styles": False,
                "tal_condition": "python: context.absolute_url() == context.portal_url() and "
                "context.restrictedTraverse('@@various-utils').is_in_user_groups(['audit_contacts'],"
                "user=member)",
                "context_variables": [
                    {"name": "log_id", "value": "contacts"},
                    {"name": "actions", "value": ""},
                    {"name": "extras", "value": "UID,PATH,CTX_PATH,CASE"},
                ],
                "default_content_category": category_id,
            },
        },
        90: {"title": _("Style template"), "type": "StyleTemplate", "trans": ["show_internally"]},
    }

    templates = combine_data(data, test=lambda x: x < 100)
    cids = create(templates, pos=False)

    data = {
        100: {
            "title": _("Header template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        105: {
            "title": _("Footer template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        110: {
            "title": _("Intro template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        120: {
            "title": _("Ending template"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        125: {
            "title": _("Download barcode subtemplate"),
            "type": "SubTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()]},
        },
        150: {
            "title": _("Mailing template"),
            "type": "MailingLoopTemplate",
            "trans": ["show_internally"],
            "attrs": {"style_template": [cids[90].UID()], "rename_page_styles": True},
        },
    }

    templates = combine_data(data, test=lambda x: 100 <= x < 200)
    cids = create(templates, pos=False, cids=cids)

    data = {
        200: {
            "title": _("To sign files print template"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "dashboard_collections": [
                    b.UID
                    for b in get_dashboard_collections(site["outgoing-mail"]["mail-searches"])
                    if b.id in OM_PRINT_TO_SIGN_COLS
                ],
                "style_template": [cids[90].UID()],
                "rename_page_styles": True,
                "enabled": False,
            },
        },
        201: {
            "title": _("E-signed files print template"),
            "type": "DashboardPODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "dashboard_collections": [
                    b.UID
                    for b in get_dashboard_collections(site["outgoing-mail"]["mail-searches"])
                    if b.id in OM_PRINT_SIGNED_COLS
                ],
                "style_template": [cids[90].UID()],
                "rename_page_styles": True,
                "enabled": False,
            },
        },
        205: {
            "title": _("Base template"),
            "type": "ConfigurablePODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "pod_portal_types": ["dmsoutgoingmail"],
                "merge_templates": [
                    {"pod_context_name": "doc_entete", "do_rendering": False, "template": cids[100].UID()},
                    {"pod_context_name": "doc_intro", "do_rendering": False, "template": cids[110].UID()},
                    {"pod_context_name": "doc_fin", "do_rendering": False, "template": cids[120].UID()},
                    {"pod_context_name": "doc_pied_page", "do_rendering": False, "template": cids[105].UID()},
                    {"pod_context_name": "doc_cb_download", "do_rendering": False, "template": cids[125].UID()},
                ],
                "style_template": [cids[90].UID()],
                "mailing_loop_template": cids[150].UID(),
                "rename_page_styles": False,
                "default_content_category": category_id,
            },
        },
        #                       'context_variables': [{'name': u'do_mailing', 'value': u'1'}]}},
        210: {
            "title": _("Receipt template"),
            "type": "ConfigurablePODTemplate",
            "trans": ["show_internally"],
            "attrs": {
                "pod_formats": ["odt"],
                "pod_portal_types": ["dmsoutgoingmail"],
                "merge_templates": [
                    {"pod_context_name": "doc_entete", "do_rendering": False, "template": cids[100].UID()},
                    {"pod_context_name": "doc_intro", "do_rendering": False, "template": cids[110].UID()},
                    {"pod_context_name": "doc_fin", "do_rendering": False, "template": cids[120].UID()},
                    {"pod_context_name": "doc_pied_page", "do_rendering": False, "template": cids[105].UID()},
                    {"pod_context_name": "doc_cb_download", "do_rendering": False, "template": cids[125].UID()},
                ],
                "style_template": [cids[90].UID()],
                "mailing_loop_template": cids[150].UID(),
                "context_variables": [
                    {"name": "PD", "value": "True"},
                    {"name": "PC", "value": "True"},
                    {"name": "PVS", "value": "False"},
                ],
                "rename_page_styles": False,
                "default_content_category": category_id,
            },
        },
    }

    templates = combine_data(data, test=lambda x: x >= 200)
    cids = create(templates, pos=False, cids=cids)

    for obj in cids.values():
        alsoProvides(obj, IProtectedItem)

    # order templates in their folder: ascending position, so already placed templates aren't moved again
    for tup in sorted(list_templates(), key=lambda t: t[3]):
        parts = tup[1].split("/")
        site.unrestrictedTraverse("/".join(parts[:-1])).moveObjectToPosition(parts[-1], tup[3])


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
        member = site.portal_registration.addMember(id=uid, password=password, roles=["Member"] + ["Batch importer"])
        member.setMemberProperties({"fullname": _("Scanner"), "email": "{}@macommune.be".format(uid)})
    except ValueError as exc:
        if not str(exc).startswith("The login name you selected is already in use"):
            logger.error("Error creating user '%s': %s" % (uid, exc))

    if api.group.get("encodeurs") is None:
        api.group.create("encodeurs", safe_encode(_("1 IM encoders")))
        site["incoming-mail"].manage_addLocalRoles("encodeurs", ["Contributor", "Reader"])
        site["contacts"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        #        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname="encodeurs", username="scanner")
    if api.group.get("dir_general") is None:
        api.group.create("dir_general", safe_encode(_("1 General manager")))
        site["outgoing-mail"].manage_addLocalRoles("dir_general", ["Contributor"])
        site["contacts"].manage_addLocalRoles("dir_general", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles(
            "dir_general", ["Contributor", "Editor", "Reader"]
        )
    if api.group.get("expedition") is None:
        api.group.create("expedition", safe_encode(_("1 OM dispatch")))
        site["outgoing-mail"].manage_addLocalRoles("expedition", ["Contributor"])
        site["contacts"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        api.group.add_user(groupname="expedition", username="scanner")
    if api.group.get("gestion_contacts") is None:
        api.group.create("gestion_contacts", safe_encode(_("1 Duplicate contacts management")))
    if api.group.get("createurs_dossier") is None:
        api.group.create("createurs_dossier", safe_encode(_("1 Folders creators")))
    if api.group.get("audit_contacts") is None:
        api.group.create("audit_contacts", safe_encode(_("1 Contacts audit")))
    if api.group.get("lecteurs_globaux_ce") is None:
        api.group.create("lecteurs_globaux_ce", safe_encode(_("2 IM global readers")))
    if api.group.get("lecteurs_globaux_cs") is None:
        api.group.create("lecteurs_globaux_cs", safe_encode(_("2 OM global readers")))
    if api.group.get("esign_watchers") is None:
        api.group.create("esign_watchers", safe_encode(_("2 External signing watchers")))


def clean_examples_step(context):
    """Clean some examples"""
    if not context.readDataFile("imiodmsmail_examples_minimal_marker.txt"):
        return
    site = context.getSite()
    clean_examples(site)
