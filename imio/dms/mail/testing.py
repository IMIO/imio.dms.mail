# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_organizations
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import sub_create
from imio.helpers.cache import setup_ram_cache
from imio.helpers.content import get_object
from imio.helpers.workflow import do_transitions
from imio.pyutils.system import runCommand
from itertools import cycle
from plone import api
from plone.api.validation import at_least_one_of
from plone.app.robotframework.remote import RemoteLibrary
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing.helpers import PloneWithPackageLayer
from plone.app.testing.layers import PloneFixture
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.testing import z2
from plone.testing import zca
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from profilehooks import timecall
from Testing import ZopeTestCase as ztc
# from z3c.relationfield import RelationValue
from zope.component import getSiteManager
from zope.component import getUtility
from zope.globalrequest.local import setLocal
from zope.i18n import translate
from zope.intid import IIntIds
from zope.ramcache.interfaces.ram import IRAMCache

import datetime
import imio.dms.mail
import inspect
import os


try:
    from imio.helpers.ram import imio_global_cache
except ImportError:
    imio_global_cache = None


class PloneDmsFixture(PloneFixture):
    def setUpZCML(self):
        """Include imio.dms.mail i18n locales before Plone to override plone messages."""
        pr = list(self.products)
        pr.insert(-2, ("imio.dms.mail", {"loadZCML": True, "load_only": {"configure.zcml": "testing_locales.zcml"}}))
        self.products = tuple(pr)

        # Create a new global registry
        zca.pushGlobalRegistry()

        from zope.configuration import xmlconfig

        self["configurationContext"] = context = zca.stackConfigurationContext(self.get("configurationContext"))

        # Turn off z3c.autoinclude
        xmlconfig.string(
            """\
<configure xmlns="http://namespaces.zope.org/zope" xmlns:meta="http://namespaces.zope.org/meta">
    <meta:provides feature="disable-autoinclude" />
</configure>
""",
            context=context,
        )

        from zope.dottedname.resolve import resolve

        def loadAll(filename):
            for p, config in self.products:
                if not config["loadZCML"]:
                    continue
                # we don't want to load overrides.zcml now !
                if "load_only" in config and filename not in config["load_only"]:
                    continue
                try:
                    package = resolve(p)
                except ImportError:
                    continue
                try:
                    if "load_only" in config and filename in config["load_only"]:
                        xmlconfig.file(config["load_only"][filename], package, context=context)
                    else:
                        xmlconfig.file(filename, package, context=context)
                except IOError:
                    pass

        loadAll("meta.zcml")
        loadAll("configure.zcml")
        loadAll("overrides.zcml")


PLONE_DMS_FIXTURE = PloneDmsFixture()


class DmsmailLayer(PloneWithPackageLayer):

    defaultBases = (PLONE_DMS_FIXTURE,)  # testing_locales.zcml inclusion

    def setUpPloneSite(self, portal):
        portal.portal_registration.addMember(id="siteadmin", password="SiteAdm!n0")
        api.group.add_user(groupname="Administrators", username="siteadmin")
        setLocal("request", portal.REQUEST)
        # if not os.getenv('IS_ROBOT', False) and imio_global_cache:
        if imio_global_cache:
            sml = getSiteManager(portal)
            sml.unregisterUtility(provided=IRAMCache)
            sml.registerUtility(component=imio_global_cache, provided=IRAMCache)
            print("=> Ram cache is now {}".format(getUtility(IRAMCache)))
            setup_ram_cache()

        manage_addExternalMethod(portal, "import_scanned", "import_scanned", "imio.dms.mail.demo", "import_scanned")
        manage_addExternalMethod(portal, "import_scanned2", "import_scanned2", "imio.dms.mail.demo", "import_scanned2")
        manage_addExternalMethod(
            portal, "create_main_file", "create_main_file", "imio.dms.mail.demo", "create_main_file"
        )
        manage_addExternalMethod(
            portal, "activate_group_encoder", "activate_group_encoder", "imio.dms.mail.demo", "activate_group_encoder"
        )
        manage_addExternalMethod(portal, "delete-category", "", "imio.dms.mail.robot", "delete_category")
        manage_addExternalMethod(portal, "lock-unlock", "", "imio.dms.mail.robot", "lock")
        manage_addExternalMethod(portal, "robot_init", "", "imio.dms.mail.robot", "robot_init")
        manage_addExternalMethod(portal, "video_doc_init", "", "imio.dms.mail.robot", "video_doc_init")

        sp = portal.portal_properties.site_properties
        sp.default_language = "fr"
        # we create a front-page document that will be modified in setup
        _createObjectByType("Document", portal, id="front-page")
        portal.setDefaultPage("front-page")
        _createObjectByType("Folder", portal, id="Members", title="Users", description="Site Users")
        members = getattr(portal, "Members")
        members.setTitle(translate(u"members-title", target_language="fr", domain="plonefrontpage", default="Users"))
        members.setDescription(
            translate(u"members-description", target_language="fr", domain="plonefrontpage", default="Site Users")
        )
        members.unmarkCreationFlag()
        members.setLanguage("fr")
        members.reindexObject()

        # install dmsmail (apply profile)
        super(DmsmailLayer, self).setUpPloneSite(portal)
        applyProfile(portal, "collective.MockMailHost:default")
        api.content.transition(obj=members, transition="show_internally")

        # copy template
        setRoles(portal, TEST_USER_ID, ["Manager"])
        folder_uid = portal["contacts"]["plonegroup-organization"]["direction-generale"]["secretariat"].UID()
        newobj = api.content.copy(portal["templates"]["om"]["main"], portal["templates"]["om"][folder_uid])
        newobj.title = u"Modèle type"
        newobj.reindexObject()

        # avoid redirection after document generation
        from imio.dms.mail.browser.documentgenerator import OMPDGenerationView

        OMPDGenerationView.redirects = lambda a, b: None

        # set ia.docs version if passed with `env version=xx make robot-server`
        if os.getenv("version"):
            api.portal.set_registry_record("imio.dms.mail.product_version", safe_unicode(os.getenv("version")))

        caller = inspect.stack()[1][3]
        if caller == "setUp":
            end_setup(portal)
        setRoles(portal, TEST_USER_ID, ["Member"])

    def setUpZope(self, app, configurationContext):
        ztc.utils.setupCoreSessions(app)
        super(DmsmailLayer, self).setUpZope(app, configurationContext)
        from App.config import _config

        if not base_hasattr(_config, "product_config"):
            _config.product_config = {
                "imio.zamqp.core": {
                    "ws_url": "http://localhost:6543",
                    "ws_password": "test",
                    "ws_login": "testuser",
                    "routing_key": "019999",
                    "client_id": "019999",
                }
            }
        (stdout, stderr, st) = runCommand("%s/bin/soffice.sh restart" % os.getenv("PWD"))

    def tearDownZope(self, app):
        """Tear down Zope."""
        super(DmsmailLayer, self).tearDownZope(app)
        (stdout, stderr, st) = runCommand("%s/bin/soffice.sh stop" % os.getenv("PWD"))


class DmsmailLayerNP1(DmsmailLayer):
    def setUpPloneSite(self, portal):
        super(DmsmailLayerNP1, self).setUpPloneSite(portal)
        setRoles(portal, TEST_USER_ID, ["Manager"])
        # Change some settings
        api.portal.set_registry_record(
            "collective.contact.core.interfaces.IContactCoreParameters.contact_source_metadata_content",
            u"{gft} # {number}, {street}, {zip_code}, {city} # {email}",
        )
        # Activate n+1
        portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )
        portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-om_n_plus_1_wfadaptation", run_dependencies=False
        )
        portal.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-task_n_plus_1_wfadaptation", run_dependencies=False
        )
        # Delete om
        brains = api.content.find(portal_type="dmsoutgoingmail")
        for brain in brains:
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        api.portal.set_registry_record(
            "collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_number", 1
        )
        # Delete im
        brains = api.content.find(portal_type=["dmsincomingmail", "dmsincoming_email"])
        for brain in brains:
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        api.portal.set_registry_record(
            "collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_number", 1
        )

        setRoles(portal, TEST_USER_ID, ["Member"])
        end_setup(portal)


class DmsmailRemote(RemoteLibrary):
    @at_least_one_of("oid", "title")
    def get_mail_path(self, ptype="dmsincomingmail", oid="", title=""):
        """Get a mail path from its id or title"""
        return "/".join(
            api.portal.get_tool("portal_url").getRelativeContentPath(get_object(ptype=ptype, oid=oid, title=title))
        )


DMSMAIL_FIXTURE = DmsmailLayer(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=("Products.PythonScripts", "imio.dashboard", "imio.dms.mail", "Products.PasswordStrength"),
    gs_profile_id="imio.dms.mail:testing",
    name="DMSMAIL_FIXTURE",
)

DMSMAIL_NP1_FIXTURE = DmsmailLayerNP1(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=("Products.PythonScripts", "imio.dashboard", "imio.dms.mail", "Products.PasswordStrength"),
    gs_profile_id="imio.dms.mail:testing",
    name="DMSMAIL_NP1_FIXTURE",
)

DMSMAIL_INTEGRATION_TESTING = IntegrationTesting(bases=(DMSMAIL_FIXTURE,), name="DmsMailFixture:Integration")

DMSMAIL_FUNCTIONAL_TESTING = FunctionalTesting(bases=(DMSMAIL_FIXTURE,), name="DmsMailFixture:Functional")

# testing_locales.zcml inclusion
REMOTE_LIBRARY_BUNDLE_FIXTURE.__bases__ = (PLONE_DMS_FIXTURE,)
REMOTE_LIBRARY_BUNDLE_FIXTURE.libraryBases = tuple(
    [lib for lib in REMOTE_LIBRARY_BUNDLE_FIXTURE.libraryBases] + [DmsmailRemote]
)
DMSMAIL_ROBOT_TESTING = FunctionalTesting(
    bases=(
        DMSMAIL_NP1_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="DMSMAIL_ROBOT_TESTING",
)


def end_setup(portal):
    setattr(portal, "_v_ready", True)


def reset_dms_config():
    set_dms_config(None, value="dict")
    set_dms_config(
        ["wf_from_to", "dmsincomingmail", "n_plus", "from"],  # i_e ok
        [("created", "back_to_creation"), ("proposed_to_manager", "back_to_manager")],
    )
    set_dms_config(
        ["wf_from_to", "dmsincomingmail", "n_plus", "to"], [("proposed_to_agent", "propose_to_agent")]  # i_e ok
    )
    set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "from"], [("created", "back_to_creation")])
    set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"],
                   [("sent", "mark_as_sent"), ("to_be_signed", "propose_to_be_signed")])
    set_dms_config(
        ["review_levels", "dmsincomingmail"], OrderedDict([("dir_general", {"st": ["proposed_to_manager"]})])  # i_e ok
    )
    set_dms_config(["review_levels", "task"], OrderedDict())
    set_dms_config(["review_levels", "dmsoutgoingmail"], OrderedDict())
    set_dms_config(
        ["review_states", "dmsincomingmail"], OrderedDict([("proposed_to_manager", {"group": "dir_general"})])  # i_e ok
    )
    set_dms_config(["review_states", "task"], OrderedDict())
    set_dms_config(["review_states", "dmsoutgoingmail"], OrderedDict())
    set_dms_config(["transitions_auc", "dmsincomingmail"], OrderedDict())  # i_e ok
    set_dms_config(["transitions_levels", "dmsincomingmail"], OrderedDict())  # i_e ok
    set_dms_config(["transitions_levels", "dmsoutgoingmail"], OrderedDict())
    set_dms_config(["transitions_levels", "task"], OrderedDict())


def add_user_in_groups(tc, userid, nb, start=1):
    """Add a user in groups"""
    with api.env.adopt_roles(["Manager"]):
        for i in range(start, nb + 1):
            gid = "group_{}".format(i)
            api.group.add_user(groupname=gid, username=userid)


def create_groups(tc, nb, start=1):
    """Create groups"""
    with api.env.adopt_roles(["Manager"]):
        for i in range(start, nb + 1):
            gid = "group_{}".format(i)
            if not api.group.get(gid):
                api.group.create(gid, "Group {}".format(i))


def change_user(portal, user="siteadmin"):
    logout()
    login(portal, user)


@timecall
def create_im_mails(tc, start=1, end=100, senders=[], transitions=[], by_days=200):
    """Create a number of im"""
    print("Creating {} incoming mails".format(end - start + 1))
    import imio.dms.mail as imiodmsmail

    filespath = "%s/batchimport/toprocess/incoming-mail" % imiodmsmail.__path__[0]
    files = [unicode(name) for name in os.listdir(filespath) if os.path.splitext(name)[1][1:] in ("pdf", "doc", "jpg")]
    files_cycle = cycle(files)

    intids = getUtility(IIntIds)
    isenders = [intids.getId(ct) for ct in senders]
    senders_cycle = cycle(isenders)

    services = get_registry_organizations()
    selected_orgs = [org for i, org in enumerate(services) if i in (0, 1, 2, 4, 5, 6)]
    orgas_cycle = cycle(selected_orgs)

    ifld = tc.layer["portal"]["incoming-mail"]
    setattr(ifld, "folder_period", u"day")
    with api.env.adopt_user(username="encodeur"):
        days = 0
        for i in range(start, end + 1):
            if i % by_days == 0:
                days += 1
            mid = "im{}".format(i)
            if mid not in ifld:
                scan_date = datetime.datetime.now() - datetime.timedelta(days=days)
                params = {
                    "title": "Courrier %d" % i,
                    "mail_type": "courrier",
                    "internal_reference_no": "E{:04d}".format(i),
                    "reception_date": scan_date,
                    # 'sender': [RelationValue(senders_cycle.next())],
                    "treating_groups": orgas_cycle.next(),
                    "recipient_groups": [services[3]],  # Direction générale, communication
                    "description": "Ceci est la description du courrier %d" % i,
                }
                t_st = datetime.datetime.now()
                mail = sub_create(ifld, "dmsincomingmail", scan_date, mid, **params)
                if i == start or i % 1000 == 0:
                    print("Creation time at {}: '{}'".format(i, datetime.datetime.now() - t_st))
                filename = files_cycle.next()
                with open("%s/%s" % (filespath, filename), "rb") as fo:
                    file_object = NamedBlobFile(fo.read(), filename=filename)
                    createContentInContainer(
                        mail,
                        "dmsmainfile",
                        title="",
                        file=file_object,
                        scan_id="0509999{:08d}".format(i),
                        scan_date=scan_date,
                    )
                do_transitions(mail, transitions)
