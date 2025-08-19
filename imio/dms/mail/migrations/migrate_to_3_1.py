# -*- coding: utf-8 -*-
from collective.messagesviewlet.utils import add_message
from datetime import datetime
from datetime import timedelta
from imio.dms.mail import ARCHIVE_SITE
from imio.dms.mail import BLDT_DIR
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.utils import message_status
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

        if self.is_in_part("q"):  # upgrade other products
            # upgrade all except 'imio.dms.mail:default'. Needed with bin/upgrade-portals
            self.upgradeAll(
                omit=[u"imio.dms.mail:default"]
            )

        if self.is_in_part("r"):  # update templates
            old_version = api.portal.get_registry_record("imio.dms.mail.product_version", default=u"unknown")
            new_version = safe_unicode(get_git_tag(BLDT_DIR))
            logger.info("Current migration from version {} to {}".format(old_version, new_version))
            # TEMPORARY TO 3.1.0
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

            # settings change
            self.runProfileSteps('imio.dms.mail', steps=['plone.app.registry'])

            # END

            finished = True  # can be eventually returned and set by batched method
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
