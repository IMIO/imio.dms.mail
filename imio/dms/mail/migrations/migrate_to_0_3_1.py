# -*- coding: utf-8 -*-

from imio.dms.mail.setuphandlers import changeSearchedTypes
from imio.dms.mail.setuphandlers import configure_actions_panel
from imio.dms.mail.setuphandlers import createIMailCollections
from imio.dms.mail.setuphandlers import createStateCollections
from imio.dms.mail.setuphandlers import setupFacetedContacts
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.catalog import addOrUpdateIndexes
from imio.migrator.migrator import Migrator
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from Products.CMFPlone.utils import base_hasattr
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_0_3_1(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def runProfileSteps(self, profile, steps):
        """Run specific steps for profile"""
        for step_id in steps:
            self.portal.portal_setup.runImportStepFromProfile("profile-%s:default" % profile, step_id)

    def createNotEncodedPerson(self):
        """add not encoded person if not exists"""
        if not base_hasattr(self.portal.contacts, "notencoded"):
            self.portal.contacts.invokeFactory("person", "notencoded", lastname=u"Non encodé")
            self.portal.contacts.folder_position("top", "notencoded")

    def createCollectionsFolder(self, folder):
        """Create Folder, if doesn't exist, who contain all topics"""
        if base_hasattr(folder, "collections"):
            return
        folder.setConstrainTypesMode(0)
        folder.invokeFactory("Folder", id="collections", title=u"Collections: ne pas effacer")
        folder.setConstrainTypesMode(1)
        folder.folder_position("top", "collections")
        folder.setDefaultPage("collections")
        col_folder = folder["collections"]
        col_folder.setConstrainTypesMode(1)
        col_folder.setLocallyAllowedTypes(["Topic", "Collection"])
        col_folder.setImmediatelyAddableTypes(["Topic", "Collection"])

    def removeOldTopics(self, folder):
        """Remove all original topics"""
        topicsToRemove = self.portal.portal_catalog(
            portal_type="Topic", path={"query": "/".join(folder.getPhysicalPath()), "depth": 1}
        )
        folder.manage_delObjects([b.id for b in topicsToRemove])

    def changeTopicsFolder(self):
        """Remove old topics. Create a folder, if doesn't exist, who contain all topics.
        Use this folder as default page. Create new topics in this new folder."""
        im_folder = self.portal["incoming-mail"]
        self.removeOldTopics(im_folder)
        self.createCollectionsFolder(im_folder)
        col_folder = im_folder["collections"]
        createIMailCollections(col_folder)
        col_folder.setDefaultPage("all_mails")
        createStateCollections(col_folder, "dmsincomingmail")  # i_e ok

    def replaceRoleByGroup(self):
        gp = api.group.get("encodeurs")
        if gp.getProperty("title") == "Encodeurs courrier":
            gp.setGroupProperties({"title": "1 Encodeurs courrier"})
        if api.group.get("dir_general") is None:
            api.group.create("dir_general", "1 Directeur général")
        for user in api.user.get_users():  # doesnt contain ldap users !! use get_user_from_criteria
            if user.has_role("General Manager"):
                api.group.add_user(groupname="dir_general", user=user)
        # remove General Manager role
        if "General Manager" in self.portal.__ac_roles__:
            roles = list(self.portal.__ac_roles__)
            roles.remove("General Manager")
            self.portal.__ac_roles__ = tuple(roles)
        # add localroles config
        fti = getUtility(IDexterityFTI, name="dmsincomingmail")  # i_e ok
        lrc = getattr(fti, "localroleconfig")
        if "proposed_to_manager" not in lrc or "dir_general" not in lrc["proposed_to_manager"]:
            for state in [
                "proposed_to_manager",
                "proposed_to_service_chief",
                "proposed_to_agent",
                "in_treatment",
                "closed",
            ]:
                if state not in lrc:
                    lrc[state] = {}
                lrc[state]["dir_general"] = ["Contributor", "Editor", "Reviewer", "IM Field Writer"]
        if "created" not in lrc:
            lrc["created"] = {}
        if "encodeurs" not in lrc["created"]:
            lrc["created"]["encodeurs"] = ["Contributor", "Editor", "IM Field Writer"]
        if (
            "encodeurs" in lrc["proposed_to_manager"]
            and "IM Field Writer" not in lrc["proposed_to_manager"]["encodeurs"]
        ):
            lrc["proposed_to_manager"]["encodeurs"].append("IM Field Writer")
        if "encodeurs" not in lrc["closed"]:
            for state in [
                "proposed_to_manager",
                "proposed_to_service_chief",
                "proposed_to_agent",
                "in_treatment",
                "closed",
            ]:
                if "encodeurs" not in lrc[state]:
                    lrc[state]["encodeurs"] = []
                lrc[state]["encodeurs"].append("Reader")

    def run(self):
        logger.info("Migrating to imio.dms.mail 0.3.1...")
        self.reinstall(["collective.task:uninstall_1.0"])
        self.cleanRegistries()
        self.reinstall(
            [
                "imio.actionspanel:default",
                "imio.history:default",
                "collective.task:default",
                "collective.compoundcriterion:default",
                "collective.behavior.talcondition:default",
                "collective.contact.facetednav:default",
                "collective.contact.duplicated:default",
                "plone.app.versioningbehavior:default",
            ]
        )
        self.runProfileSteps(
            "imio.dms.mail",
            [
                "actions",
                "catalog",
                "componentregistry",
                "jsregistry",
                "plone.app.registry",
                "rolemap",
                "typeinfo",
                "update-workflow-rolemap",
                "viewlets",
                "workflow",
            ],
        )
        self.runProfileSteps("collective.dms.basecontent", ["atcttool", "catalog"])
        self.runProfileSteps("collective.dms.scanbehavior", ["catalog"])

        api.portal.get_tool("portal_diff").setDiffForPortalType(
            "dmsincomingmail", {"any": "Compound Diff for Dexterity types"}
        )  # i_e ok
        self.createNotEncodedPerson()
        self.changeTopicsFolder()
        self.replaceRoleByGroup()
        self.portal.portal_workflow.updateRoleMappings()

        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.searchResults(portal_type="dmsincomingmail")  # i_e ok
        if brains:
            factory = getUtility(IVocabularyFactory, "collective.dms.basecontent.treating_groups")
            voc = factory(brains[0].getObject())
            good_values = voc.by_token
        for brain in brains:
            im = brain.getObject()
            # new_incomingmail(im, None)
            if isinstance(im.treating_groups, list):
                if len(im.treating_groups) > 1:
                    logger.error("More than one treating_groups %s for %s object" % (im.treating_groups, im))
                    keep = None
                    for tg in im.treating_groups:
                        if tg in good_values:
                            keep = tg
                            break
                    logger.warn("Kept %s" % keep)
                    im.treating_groups = keep
                elif not im.treating_groups:
                    logger.warn(
                        "Replaced old value %s by first good value %s for %s object"
                        % (im.treating_groups[0], good_values.keys()[0], im)
                    )
                    im.treating_groups = good_values.keys()[0]
                elif im.treating_groups[0] in good_values:
                    # elif catalog(UID=im.treating_groups[0]):
                    im.treating_groups = im.treating_groups[0]
                else:
                    logger.warn(
                        "Replaced old value %s by first good value %s for %s object"
                        % (im.treating_groups[0], good_values.keys()[0], im)
                    )
                    im.treating_groups = good_values.keys()[0]

        addOrUpdateIndexes(
            self.portal,
            indexInfos={
                "treating_groups": ("KeywordIndex", {}),
                "recipient_groups": ("KeywordIndex", {}),
                "organization_type": ("FieldIndex", {}),
            },
        )
        addOrUpdateColumns(self.portal, columns=("treating_groups", "recipient_groups"))
        # a global recatalog is made after
        # brains = catalog.searchResults(portal_type='organization')
        # for brain in brains:
        #    brain.getObject().reindexObject(idxs=['organization_type'])

        setupFacetedContacts(self.portal)

        changeSearchedTypes(self.portal)

        configure_actions_panel(self.portal)

        self.upgradeAll()
        self.refreshDatabase()
        self.finish()


def migrate(context):
    """ """
    Migrate_To_0_3_1(context).run()
