# -*- coding: utf-8 -*-

from collections import OrderedDict
from collective.contact.facetednav.interfaces import IActionsEnabled
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.documentgenerator.content.pod_template import POD_TEMPLATE_TYPES
from collective.documentgenerator.utils import update_oo_config
from collective.eeafaceted.collectionwidget.interfaces import ICollectionCategories
from collective.messagesviewlet.utils import add_message
from collective.querynextprev.interfaces import INextPrevNotNavigable
from collective.wfadaptations.api import apply_from_registry
from eea.facetednavigation.settings.interfaces import IDisableSmartFacets
from eea.facetednavigation.settings.interfaces import IHidePloneLeftColumn
from eea.facetednavigation.settings.interfaces import IHidePloneRightColumn
from ftw.labels.interfaces import ILabelJar
from ftw.labels.interfaces import ILabelRoot
from imio.dms.mail import _tr as _
from imio.dms.mail.interfaces import IActionsPanelFolderAll
from imio.dms.mail.interfaces import IContactListsDashboardBatchActions
from imio.dms.mail.interfaces import IDirectoryFacetedNavigable
from imio.dms.mail.interfaces import IHeldPositionsDashboardBatchActions
from imio.dms.mail.interfaces import IIMDashboard
from imio.dms.mail.interfaces import IIMDashboardBatchActions
from imio.dms.mail.interfaces import IOMDashboard
from imio.dms.mail.interfaces import IOMDashboardBatchActions
from imio.dms.mail.interfaces import IOrganizationsDashboardBatchActions
from imio.dms.mail.interfaces import IPersonsDashboardBatchActions
from imio.dms.mail.interfaces import ITaskDashboard
from imio.dms.mail.interfaces import ITaskDashboardBatchActions
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
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import set_dms_config
from imio.helpers.workflow import do_transitions
from imio.migrator.migrator import Migrator
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from plone.app.uuid.utils import uuidToObject
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.Portal import member_indexhtml
from Products.CMFPlone.utils import _createObjectByType
from Products.CPUtils.Extensions.utils import mark_last_version
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.i18n.interfaces import ITranslationDomain
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

import logging


# createStateCollections
logger = logging.getLogger("imio.dms.mail")


class Migrate_To_2_1(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)
        self.registry = getUtility(IRegistry)
        self.catalog = api.portal.get_tool("portal_catalog")
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]

    def set_Members(self):
        if "Members" in self.portal:
            return
        _createObjectByType("Folder", self.portal, id="Members", title="Users", description="Site Users")
        util = getUtility(ITranslationDomain, "plonefrontpage")
        members = getattr(self.portal, "Members")
        members.setTitle(util.translate(u"members-title", target_language="fr", default="Users"))
        members.setDescription(util.translate(u"members-description", target_language="fr", default="Site Users"))
        members.unmarkCreationFlag()
        members.setLanguage("fr")
        members.setExcludeFromNav(True)
        members.setConstrainTypesMode(1)
        members.setLocallyAllowedTypes([])
        members.setImmediatelyAddableTypes([])
        members.reindexObject()
        self.portal.portal_membership.memberareaCreationFlag = 0
        self.portal.portal_membership.setMemberAreaType("member_area")

        do_transitions(members, "show_internally")

        # add index_html to Members area
        if "index_html" not in members.objectIds():
            addPy = members.manage_addProduct["PythonScripts"].manage_addPythonScript
            addPy("index_html")
            index_html = getattr(members, "index_html")
            index_html.write(member_indexhtml)
            index_html.ZPythonScript_setTitle("User Search")

        # Block all right column portlets by default
        manager = getUtility(IPortletManager, name="plone.rightcolumn")
        if manager is not None:
            assignable = queryMultiAdapter((members, manager), ILocalPortletAssignmentManager)
            assignable.setBlacklistStatus("context", True)
            assignable.setBlacklistStatus("group", True)
            assignable.setBlacklistStatus("content_type", True)

    def update_templates(self):
        # Removed useless template
        if "contacts-export" in self.portal["templates"]:
            api.content.delete(self.portal["templates"]["contacts-export"])
        # Change addable types
        template_types = POD_TEMPLATE_TYPES.keys() + ["Folder", "DashboardPODTemplate"]
        for path in ["templates", "templates/om", "templates/om/common"]:
            obj = self.portal.unrestrictedTraverse(path)
            obj.setLocallyAllowedTypes(template_types)
            obj.setImmediatelyAddableTypes(template_types)

        # add templates configuration
        add_templates(self.portal)

        ml_uid = self.portal.restrictedTraverse("templates/om/mailing").UID()
        brains = api.content.find(context=self.portal["templates"]["om"], portal_type=["ConfigurablePODTemplate"])
        for brain in brains:
            ob = brain.getObject()
            if not ob.mailing_loop_template:
                ob.mailing_loop_template = ml_uid

    def update_tasks(self):
        # NOT USED !
        # change klass on task
        "collective.task.content.task.Task"
        for brain in self.catalog(portal_type="task"):
            migrate_base_class_to_new_class(
                brain.getObject(),
                old_class_name="collective.task.content.task.Task",
                new_class_name="imio.dms.mail.browser.task.Task",
            )

    def update_collections(self):
        # update incomingmail collections
        for brain in api.content.find(context=self.imf["mail-searches"], portal_type="DashboardCollection"):
            obj = brain.getObject()
            if "CreationDate" in obj.customViewFields:
                buf = list(obj.customViewFields)
                buf[buf.index("CreationDate")] = u"reception_date"
                obj.customViewFields = tuple(buf)

        collections = [
            {},
            {},
            {},
            {},
            {},
            {},
            {},
            {
                "id": "in_copy_unread",
                "tit": _("im_in_copy_unread"),
                "subj": (u"todo",),
                "query": [
                    {
                        "i": "portal_type",
                        "o": "plone.app.querystring.operation.selection.is",
                        "v": ["dmsincomingmail"],
                    },  # i_e ok
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
                    u"actions",
                ),
                "sort": u"organization_type",
                "rev": True,
                "count": True,
            },
            {},
            {
                "id": "followed",
                "tit": _("im_followed"),
                "subj": (u"search",),
                "query": [
                    {
                        "i": "portal_type",
                        "o": "plone.app.querystring.operation.selection.is",
                        "v": ["dmsincomingmail"],
                    },  # i_e ok
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
                    u"actions",
                ),
                "sort": u"organization_type",
                "rev": True,
                "count": False,
            },
        ]
        if "in_copy_unread" not in self.imf["mail-searches"]:
            createDashboardCollections(self.imf["mail-searches"], collections)

        # ICollectionCategories
        alsoProvides(self.imf["mail-searches"], ICollectionCategories)
        alsoProvides(self.omf["mail-searches"], ICollectionCategories)
        alsoProvides(self.portal["tasks"]["task-searches"], ICollectionCategories)
        # I...BatchActions
        noLongerProvides(self.imf["mail-searches"], IIMDashboard)
        alsoProvides(self.imf["mail-searches"], IIMDashboardBatchActions)
        noLongerProvides(self.omf["mail-searches"], IOMDashboard)
        alsoProvides(self.omf["mail-searches"], IOMDashboardBatchActions)
        noLongerProvides(self.portal["tasks"]["task-searches"], ITaskDashboard)
        alsoProvides(self.portal["tasks"]["task-searches"], ITaskDashboardBatchActions)
        # Rename category label
        self.imf["mail-searches"].setRights("Courrier entrant")
        self.omf["mail-searches"].setRights("Courrier sortant")
        # Rename collection title
        self.imf["mail-searches"]["all_mails"].setTitle(u"Tout")
        self.imf["mail-searches"]["all_mails"].reindexObject()
        self.imf["mail-searches"]["have_treated"].setTitle(u"Que j'ai traité")
        self.imf["mail-searches"]["have_treated"].reindexObject()
        self.omf["mail-searches"]["all_mails"].setTitle(u"Tout")
        self.omf["mail-searches"]["all_mails"].reindexObject()
        self.omf["mail-searches"]["have_treated"].setTitle(u"Que j'ai traité")
        self.omf["mail-searches"]["have_treated"].reindexObject()
        self.portal["tasks"]["task-searches"]["to_treat"].setTitle(u"Qui me sont assignées")
        self.portal["tasks"]["task-searches"]["to_treat"].reindexObject()

        # reimport faceted
        reimport_faceted_config(
            self.imf["mail-searches"],
            xml="im-mail-searches.xml",
            default_UID=self.imf["mail-searches"]["all_mails"].UID(),
        )
        reimport_faceted_config(
            self.omf["mail-searches"],
            xml="om-mail-searches.xml",
            default_UID=self.omf["mail-searches"]["all_mails"].UID(),
        )

    def update_site(self):
        # add documentation message
        if "doc" not in self.portal["messages-config"]:
            add_message(
                "doc",
                "Documentation",
                u'<p>Vous pouvez consulter la <a href="http://www.imio.be/'
                u'support/documentation/topic/cp_app_ged" target="_blank">documentation en ligne de la '
                u"dernière version</a>, ainsi que d'autres documentations liées.</p>",
                msg_type="significant",
                can_hide=True,
                req_roles=["Authenticated"],
                activate=True,
            )
        if "doc2-0" in self.portal["messages-config"]:
            api.content.delete(obj=self.portal["messages-config"]["doc2-0"])

        # update front-page
        frontpage = self.portal["front-page"]
        if frontpage.Title() == "Gestion du courrier 2.0":
            frontpage.setTitle(_("front_page_title"))
            frontpage.setDescription(_("front_page_descr"))
            frontpage.setText(_("front_page_text"), mimetype="text/html")

        # update portal title
        self.portal.title = "Gestion du courrier"

        # for collective.externaleditor
        if "MailingLoopTemplate" not in self.registry["externaleditor.externaleditor_enabled_types"]:
            self.registry["externaleditor.externaleditor_enabled_types"] = [
                "PODTemplate",
                "ConfigurablePODTemplate",
                "DashboardPODTemplate",
                "SubTemplate",
                "StyleTemplate",
                "dmsommainfile",
                "MailingLoopTemplate",
            ]
        # documentgenerator
        api.portal.set_registry_record(
            "collective.documentgenerator.browser.controlpanel."
            "IDocumentGeneratorControlPanelSchema.raiseOnError_for_non_managers",
            True,
        )

        # ftw.labels
        if not ILabelRoot.providedBy(self.imf):
            labels = {
                self.imf: [("Lu", "green", True), ("Suivi", "yellow", True)],
                self.omf: [],
                self.portal["tasks"]: [],
            }
            for folder in labels:
                if not ILabelRoot.providedBy(folder):
                    alsoProvides(folder, ILabelRoot)
                    adapted = ILabelJar(folder)
                    existing = [dic["title"] for dic in adapted.list()]
                    for title, color, by_user in labels[folder]:
                        if title not in existing:
                            adapted.add(title, color, by_user)

            self.portal.manage_permission("ftw.labels: Manage Labels Jar", ("Manager", "Site Administrator"), acquire=0)
            self.portal.manage_permission("ftw.labels: Change Labels", ("Manager", "Site Administrator"), acquire=0)
            self.portal.manage_permission(
                "ftw.labels: Change Personal Labels", ("Manager", "Site Administrator", "Member"), acquire=0
            )

            self.runProfileSteps("imio.dms.mail", steps=["imiodmsmail-mark-copy-im-as-read"], profile="singles")

        # INextPrevNotNavigable
        alsoProvides(self.portal["tasks"], INextPrevNotNavigable)

        # registry
        api.portal.set_registry_record(
            name="Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings." "search_rss_enabled", value=False
        )

        # activing versioning
        self.portal.portal_diff.setDiffForPortalType("task", {"any": "Compound Diff for Dexterity types"})
        self.portal.portal_diff.setDiffForPortalType("dmsommainfile", {"any": "Compound Diff for Dexterity types"})

        # change permission
        self.portal.manage_permission("imio.dms.mail: Write userid field", (), acquire=0)
        pf = self.portal.contacts["personnel-folder"]
        pf.manage_permission("imio.dms.mail: Write userid field", ("Manager", "Site Administrator"), acquire=0)

        # ckeditor skin
        self.portal.portal_properties.ckeditor_properties.skin = "moono-lisa"

        # update mailcontent options
        self.registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_edit_irn"] = u"hide"
        self.registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_increment_number"] = True

        # hide faceted actions
        paob = self.portal.portal_actions.object_buttons
        for act in (
            "faceted.sync",
            "faceted.disable",
            "faceted.enable",
            "faceted.search.disable",
            "faceted.search.enable",
            "faceted.actions.disable",
            "faceted.actions.enable",
        ):
            if act in paob:
                paob[act].visible = False

    def update_contacts(self):
        contacts = self.portal["contacts"]
        if not IDirectoryFacetedNavigable.providedBy(contacts):
            return
        blacklistPortletCategory(contacts, value=False)
        noLongerProvides(contacts, IHidePloneLeftColumn)
        noLongerProvides(contacts, IHidePloneRightColumn)
        noLongerProvides(contacts, IDisableSmartFacets)
        noLongerProvides(contacts, IDirectoryFacetedNavigable)
        noLongerProvides(contacts, IActionsEnabled)
        self.portal.portal_types.directory.filter_content_types = False
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
        self.portal.portal_types.directory.filter_content_types = True
        # order
        contacts.moveObjectToPosition("personnel-folder", 4)
        # contact lists folder
        self.runProfileSteps("imio.dms.mail", profile="examples", steps=["imiodmsmail-add_test_contact_lists"])
        cl_folder = contacts["contact-lists-folder"]
        cl_folder.manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        cl_folder.manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        cl_folder.manage_addLocalRoles("dir_general", ["Contributor", "Editor", "Reader"])
        dic = cl_folder["common"].__ac_local_roles__
        for uid in self.registry[ORGANIZATIONS_REGISTRY]:
            dic["%s_encodeur" % uid] = ["Contributor"]
            if uid not in cl_folder:
                obj = uuidToObject(uid)
                full_title = obj.get_full_title(separator=" - ", first_index=1)
                folder = api.content.create(container=cl_folder, type="Folder", id=uid, title=full_title)
                folder.setLayout("folder_tabular_view")
                alsoProvides(folder, IActionsPanelFolderAll)
                alsoProvides(folder, INextPrevNotNavigable)
                roles = ["Contributor"]
                api.group.grant_roles(groupname="%s_encodeur" % uid, roles=roles, obj=folder)
                folder.reindexObjectSecurity()
        cl_folder["common"]._p_changed = True
        # various
        contacts.moveObjectToPosition("plonegroup-organization", 6)
        blacklistPortletCategory(contacts["plonegroup-organization"])
        blacklistPortletCategory(contacts["personnel-folder"])

    def dms_config(self):
        try:
            get_dms_config()
            return
        except KeyError:
            pass
        set_dms_config(
            ["review_levels", "dmsincomingmail"],  # i_e ok
            OrderedDict(
                [
                    ("dir_general", {"st": ["proposed_to_manager"]}),
                    ("_validateur", {"st": ["proposed_to_service_chief"], "org": "treating_groups"}),
                ]
            ),
        )
        set_dms_config(
            ["review_levels", "task"],
            OrderedDict([("_validateur", {"st": ["to_assign", "realized"], "org": "assigned_group"})]),
        )
        set_dms_config(
            ["review_levels", "dmsoutgoingmail"],
            OrderedDict([("_validateur", {"st": ["proposed_to_service_chief"], "org": "treating_groups"})]),
        )
        set_dms_config(
            ["review_states", "dmsincomingmail"],  # i_e ok
            OrderedDict(
                [
                    ("proposed_to_manager", {"group": "dir_general"}),
                    ("proposed_to_service_chief", {"group": "_validateur", "org": "treating_groups"}),
                ]
            ),
        )
        set_dms_config(
            ["review_states", "task"],
            OrderedDict(
                [
                    ("to_assign", {"group": "_validateur", "org": "assigned_group"}),
                    ("realized", {"group": "_validateur", "org": "assigned_group"}),
                ]
            ),
        )
        set_dms_config(
            ["review_states", "dmsoutgoingmail"],
            OrderedDict([("proposed_to_service_chief", {"group": "_validateur", "org": "treating_groups"})]),
        )

    def run(self):
        logger.info("Migrating to imio.dms.mail 2.1...")
        self.cleanRegistries()

        self.set_Members()

        self.upgradeProfile("collective.contact.plonegroup:default")
        self.upgradeProfile("collective.dms.mailcontent:default")
        self.upgradeProfile("collective.messagesviewlet:default")
        self.upgradeProfile("imio.dashboard:default")
        self.upgradeProfile("collective.documentgenerator:default")
        self.runProfileSteps("imio.helpers", steps=["jsregistry"])

        self.install(["collective.contact.contactlist"])
        try:
            self.install(["ftw.labels"])
        except LookupError as e:
            if not e.message.startswith("Could not find ILabelJar on any parents"):
                raise e
        if "contact-contactlist-mylists" in self.portal.portal_actions.user:
            self.portal.portal_actions.user.manage_delObjects(ids=["contact-contactlist-mylists"])

        self.runProfileSteps(
            "imio.dms.mail",
            steps=["actions", "cssregistry", "jsregistry", "repositorytool", "typeinfo", "viewlets", "workflow"],
        )
        self.portal.portal_workflow.updateRoleMappings()
        # Apply workflow adaptations
        RECORD_NAME = "collective.wfadaptations.applied_adaptations"
        if api.portal.get_registry_record(RECORD_NAME, default=False):
            success, errors = apply_from_registry()
            if errors:
                logger.error("Problem applying wf adaptations: %d errors" % errors)

        # check if oo port must be changed
        update_oo_config()

        self.runProfileSteps("imio.dms.mail", steps=["imiodmsmail-add-icons-to-contact-workflow"], profile="singles")

        add_transforms(self.portal)

        # replace faceted on contacts
        self.update_contacts()

        # update templates
        self.update_templates()
        self.runProfileSteps("imio.dms.mail", steps=["imiodmsmail-update-templates"], profile="singles")

        # set config
        self.dms_config()

        # update collections
        self.update_collections()

        # do various global adaptations
        self.update_site()

        # self.catalog.refreshCatalog(clear=1)
        # recatalog
        for brain in self.catalog(portal_type="dmsincomingmail"):  # i_e ok
            brain.getObject().reindexObject(["get_full_title", "organization_type"])

        # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
        self.upgradeAll(omit=["imio.dms.mail:default"])

        # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
        self.registry["collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete"] = False

        for prod in [
            "collective.behavior.talcondition",
            "collective.ckeditor",
            "collective.contact.core",
            "collective.contact.contactlist",
            "collective.contact.duplicated",
            "collective.contact.plonegroup",
            "collective.contact.widget",
            "collective.dms.basecontent",
            "collective.dms.scanbehavior",
            "collective.eeafaceted.batchactions",
            "collective.eeafaceted.collectionwidget",
            "collective.eeafaceted.z3ctable",
            "collective.js.underscore",
            "collective.messagesviewlet",
            "collective.plonefinder",
            "collective.querynextprev",
            "collective.task",
            "collective.z3cform.datagridfield",
            "collective.z3cform.datetimewidget",
            "dexterity.localroles",
            "imio.actionspanel",
            "imio.dashboard",
            "imio.dms.mail",
            "imio.history",
            "plone.app.dexterity",
            "plone.formwidget.autocomplete",
            "plone.formwidget.contenttree",
            "plone.formwidget.datetime",
            "plonetheme.classic",
            "plonetheme.imioapps",
        ]:
            mark_last_version(self.portal, product=prod)

        # self.refreshDatabase()
        self.finish()


def migrate(context):
    """ """
    Migrate_To_2_1(context).run()
