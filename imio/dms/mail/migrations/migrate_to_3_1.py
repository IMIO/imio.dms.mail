# -*- coding: utf-8 -*-
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import update_categorized_elements
from collective.messagesviewlet.utils import add_message
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from datetime import datetime
from datetime import timedelta
from dexterity.localroles.utils import fti_configuration
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.setuphandlers import createStateCollections
from imio.dms.mail.utils import message_status
from imio.dms.mail.utils import update_solr_config
from imio.helpers.setup import load_type_from_package
from imio.helpers.setup import load_workflow_from_package
from imio.migrator.migrator import Migrator
from imio.pyutils.system import get_git_tag
from plone import api
from plone.registry.events import RecordModifiedEvent
from Products.CMFPlone.utils import safe_unicode
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from zope.event import notify

import logging
import OFS
import os
import transaction


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1(Migrator):  # noqa
    def __init__(self, context, disable_linkintegrity_checks=False):
        Migrator.__init__(self, context, disable_linkintegrity_checks=disable_linkintegrity_checks)
        self.imf = self.portal["incoming-mail"]
        self.omf = self.portal["outgoing-mail"]
        self.acl = self.portal["acl_users"]
        self.contacts = self.portal["contacts"]
        self.batch_value = int(os.getenv("BATCH", "0"))
        self.commit_value = int(os.getenv("COMMIT", "0"))

    def savepoint_flush(self):
        transaction.savepoint(True)
        self.portal._p_jar.cacheGC()

    def run(self):
        logger.info("Migrating to imio.dms.mail 3.1...")
        self.log_mem("START")

        if self.is_in_part("a"):  # install and upgrade products
            # check if oo port or solr port must be changed
            update_solr_config()
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr:
                logger.info("Deactivating solr")
                api.portal.set_registry_record("collective.solr.active", False)

        if self.is_in_part("q"):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            self.upgradeAll(
                omit=[u"imio.dms.mail:default"]
            )

            # add group
            if api.group.get("esign_watchers") is None:
                api.group.create("esign_watchers", "2 Observateurs module signature")
                api.group.add_user(groupname="esign_watchers", username="dirg")

        if self.is_in_part("r"):  # update templates
            old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
            new_version = safe_unicode(get_git_tag(BLDT_DIR))
            logger.info("Current migration from version {} to {}".format(old_version, new_version))

            # Update dashboard pod templates
            self.portal["templates"]["export-users-groups"].max_objects = 0
            self.portal["templates"]["all-contacts-export"].max_objects = 0

            # Update imio.pm.wsclient generated actions translations
            notify(RecordModifiedEvent(
                self.registry.records.get("imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
                [],
                api.portal.get_registry_record(
                    "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions"),
            ))

            self.install(["imio.esign"])

            # signing
            self.runProfileSteps("imio.dms.mail", steps=["catalog", "plone.app.registry"])
            load_type_from_package("dmsoutgoingmail", "profile-imio.dms.mail:default")  # behavior
            load_type_from_package("held_position", "profile-imio.dms.mail:default")  # behavior
            load_type_from_package("dmsappendixfile", "profile-imio.dms.mail:default")  # iconified
            load_type_from_package("dmsommainfile", "profile-imio.dms.mail:default")  # iconified
            self.runProfileSteps('imio.dms.mail', steps=['imiodmsmail-add-test-annexes-types'], profile='examples')

            # Update wf changes
            reset = load_workflow_from_package("outgoingmail_workflow", "imio.dms.mail:default")
            applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()
                                   if dic["workflow"] == "outgoingmail_workflow"]
            finished1 = finished2 = True
            if reset:
                logger.info("outgoingmail_workflow reloaded")
                for name in applied_adaptations:
                    success, errors = apply_from_registry(reapply=True, name=name)
                    if errors:
                        logger.error("Problem applying wf adaptations '%s': %d errors" % (name, errors))
                # update permissions, roles and reindex allowedRolesAndUsers
                # count = self.portal.portal_workflow.updateRoleMappings()  out of memory
                # logger.info("Updated {} items".format(count))
                finished1 = self.reindexIndexes(['allowedRolesAndUsers'], portal_types=['dmsoutgoingmail'])
                if finished1:
                    finished2 = self.reindexIndexes(['allowedRolesAndUsers'],
                                                    portal_types=['dmsommainfile', "dmsappendixfile", "task"])
                else:
                    finished2 = False
            else:
                logger.error("outgoingmail_workflow not reloaded !")

            # update localroles
            finished = finished1 and finished2
            if finished:
                lr, fti = fti_configuration(portal_type="dmsoutgoingmail")
                changes = False
                if "imio.dms.mail.content.behaviors.IDmsMailCreatingGroup" in fti.behaviors:
                    lrcg = lr["creating_group"]
                    if "signed" not in lrcg:
                        changes = True
                        lrcg["signed"] = {CREATING_GROUP_SUFFIX: {"roles": ["Reader", "Reviewer"]}}
                    if "to_be_signed" in lrcg and CREATING_GROUP_SUFFIX in lrcg["to_be_signed"] and "Editor" in \
                            lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"]:
                        changes = True
                        # correction !
                        lrcg["to_be_signed"][CREATING_GROUP_SUFFIX]["roles"].remove("Editor")
                lrsc = lr["static_config"]
                if "signed" not in lrsc:
                    changes = True
                    lrsc["signed"] = {
                        "expedition": {"roles": ["Editor", "Reviewer"]},
                        "encodeurs": {"roles": ["Reader"]},
                        "dir_general": {"roles": ["Contributor", "Editor", "Reviewer", "DmsFile Contributor"]},
                        "lecteurs_globaux_cs": {"roles": ["Reader"]},
                    }
                lrtg = lr["treating_groups"]
                if "signed" not in lrtg:
                    changes = True
                    lrtg["signed"] = {
                        "editeur": {"roles": ["Reader"]},
                        "encodeur": {"roles": ["Reader", "Reviewer"]},
                        "lecteur": {"roles": ["Reader"]},
                    }
                if "to_be_signed" in lrtg and "encodeur" in lrtg["to_be_signed"] and "Editor" in \
                        lrtg["to_be_signed"]["encodeur"]["roles"]:
                    changes = True
                    # correction !
                    lrtg["to_be_signed"]["encodeur"]["roles"].remove("Editor")
                lrrg = lr["recipient_groups"]
                if "signed" not in lrrg:
                    changes = True
                    lrrg["signed"] = {
                        "editeur": {"roles": ["Reader"]},
                        "encodeur": {"roles": ["Reader"]},
                        "lecteur": {"roles": ["Reader"]},
                    }
                if u"imio.dms.mail.wfadaptations.OMServiceValidation" in applied_adaptations:
                    if "signed" in lrtg and "n_plus_1" not in lrtg["signed"]:
                        changes = True
                        lrtg["signed"]["n_plus_1"] = {"roles": ["Reader"]}
                    if "signed" in lrrg and "n_plus_1" not in lrrg["signed"]:
                        changes = True
                        lrrg["signed"]["n_plus_1"] = {"roles": ["Reader"]}

                if changes:
                    lr._p_changed = True

                # change back confirmation message
                key = "imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions"
                values = list(api.portal.get_registry_record(key, default=[]))
                if values and "dmsoutgoingmail.back_to_signed|" not in values:
                    values.append("dmsoutgoingmail.back_to_signed|")
                    api.portal.set_registry_record(key, values)

                # add signed collection
                col_folder = self.portal["outgoing-mail"]["mail-searches"]
                createStateCollections(self.portal["outgoing-mail"]["mail-searches"], "dmsoutgoingmail")
                pos = col_folder.getObjectPosition("searchfor_to_be_signed")
                col_folder.moveObjectToPosition("searchfor_signed", pos + 1)

                # reindex om markers
                for brain in self.omf.portal_catalog.unrestrictedSearchResults(portal_type="dmsoutgoingmail"):
                    obj = brain._unrestrictedGetObject()
                    obj.reindexObject(idxs=["markers"])

            # imio.annex integration to dms files with iconified category
            self.context.runImportStepFromProfile('collective.dms.basecontent:default', 'catalog')
            load_type_from_package("dmsmainfile", "imio.dms.mail:default")
            load_type_from_package("dmsommainfile", "imio.dms.mail:default")
            load_type_from_package("dmsappendixfile", "imio.dms.mail:default")
            self.context.runImportStepFromProfile(u'imio.dms.mail:examples', u'imiodmsmail-add-test-annexes-types')
            files = self.portal.portal_catalog.unrestrictedSearchResults(portal_type=["dmsmainfile", "dmsommainfile",
                                                                                      "dmsappendixfile"])
            category = self.portal["annexes_types"]["signable_files"]["signable-ged-file"]
            for f in files:
                obj = f.getObject()
                if not hasattr(obj, "approved"):
                    obj.approved = False
                if not hasattr(obj, "to_print"):
                    obj.to_print = False
                if not hasattr(obj, "content_category"):
                    obj.content_category = calculate_category_id(category)
                    update_categorized_elements(obj.aq_parent, obj, category)
            catalog = self.portal.portal_catalog
            indexes = catalog.indexes()
            wanted = [
                ('to_print', 'BooleanIndex'),
                ('to_be_signed', 'BooleanIndex'),
                ('signed', 'BooleanIndex'),
                ('approved', 'BooleanIndex'),
            ]
            added = set()
            for name, meta_type in wanted:
                if name not in indexes:
                    catalog.addIndex(name, meta_type)
                    added.add(name)
            if added:
                self.reindexIndexes(idxs=list(added),
                                    portal_types=["dmsmainfile", "dmsommainfile", "dmsappendixfile"],
                                    update_metadata=True)

            # END

                # END

            # finished = True  # can be eventually returned and set by batched method
            if finished and old_version != new_version:
                zope_app = self.portal
                while not isinstance(zope_app, OFS.Application.Application):
                    zope_app = zope_app.aq_parent
                if "cputils_install" not in zope_app.objectIds():
                    manage_addExternalMethod(zope_app, "cputils_install", "", "CPUtils.utils", "install")
                ret = zope_app.cputils_install(zope_app)
                ret = ret.replace("<div>Those methods have been added: ", "").replace("</div>", "")
                if ret:
                    logger.info('CPUtils added methods: "{}"'.format(ret.replace("<br />", ", ")))
                if message_status("doc", older=timedelta(days=90), to_state="inactive"):
                    logger.info("doc message deactivated")
                manage_addExternalMethod(self.portal, "idm_activate_signing", "", "imio.dms.mail.demo",
                                         "activate_signing")
                self.runProfileSteps("imio.dms.mail", steps=["cssregistry", "jsregistry"])
                if ARCHIVE_SITE:
                    cssr = self.portal.portal_css
                    if not cssr.getResource("imiodmsmail_archives.css").getEnabled():
                        cssr.updateStylesheet("imiodmsmail_archives.css", enabled=True)
                        cssr.cookResources()
                self.cleanRegistries()
                # set jqueryui autocomplete to False. If not, contact autocomplete doesn't work
                self.registry["collective.js.jqueryui.controlpanel.IJQueryUIPlugins.ui_autocomplete"] = False
                # version
                api.portal.set_registry_record("imio.dms.mail.product_version", new_version)
                end = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d-%H%M")
                if old_version != new_version:
                    if "new-version" in self.portal["messages-config"]:
                        api.content.delete(self.portal["messages-config"]["new-version"])
                    # with solr, bug in col.iconifiedcategory.content.events.categorized_content_container_moved
                    # self.portal["messages-config"].REQUEST.set("defer_categorized_content_created_event", True)
                    add_message(
                        "new-version",
                        "Maj version",
                        u"<p><strong>iA.docs a été mis à jour de la version {} à la version {}</strong>. Vous "
                        u"pouvez consulter les changements en cliquant sur le numéro de version en bas de page."
                        u"</p>".format(old_version, new_version),
                        msg_type="significant",
                        can_hide=True,
                        end=end,
                        req_roles=["Authenticated"],
                        activate=True,
                    )
                # model om mail
                add_special_model_mail(self.portal)
                # update templates
                self.runProfileSteps(
                    "imio.dms.mail",
                    steps=["imiodmsmail-create-templates", "imiodmsmail-update-templates"],
                    profile="singles",
                )
                self.portal["templates"].moveObjectToPosition("d-im-listing-tab-details", 4)  # TEMPORARY
            # if active_solr:
            #     logger.info("Activating solr")
            #     api.portal.set_registry_record("collective.solr.active", True)

        if self.is_in_part("x"):  # clear solr
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr is not None:
                if not active_solr:
                    logger.info("Activating solr")
                    api.portal.set_registry_record("collective.solr.active", True)
                logger.info("Clearing solr on %s" % self.portal.absolute_url_path())
                maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
                maintenance.clear()

        if self.is_in_part("y"):  # sync solr (long time, batchable)
            active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
            if active_solr is not None:
                if not active_solr:
                    logger.info("Activating solr")
                    api.portal.set_registry_record("collective.solr.active", True)
                self.sync_solr()

        self.log_mem("END")
        logger.info("Really finished at {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.finish()

    def sync_solr(self):
        full_key = "collective.solr.port"
        configured_port = api.portal.get_registry_record(full_key, default=None)
        if configured_port is None:
            return
        active_solr = api.portal.get_registry_record("collective.solr.active", default=None)
        if not active_solr:
            logger.info("Activating solr")
            api.portal.set_registry_record("collective.solr.active", True)
        logger.info("Syncing solr on %s" % self.portal.absolute_url_path())
        response = self.portal.REQUEST.RESPONSE
        original = response.write
        response.write = lambda x: x  # temporarily ignore output
        maintenance = self.portal.unrestrictedTraverse("@@solr-maintenance")
        maintenance.sync()  # BATCHED
        response.write = original


def migrate(context):
    Migrate_To_3_1(context).run()
