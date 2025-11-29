# -*- coding: utf-8 -*-
from collections import OrderedDict
from collective.classification.tree import caching
from collective.classification.tree.utils import iterate_over_tree
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_organizations
from collective.dms.batchimport.utils import createDocument
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from datetime import datetime
from imio.dms.mail import add_path
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.dmsmail import ImioDmsOutgoingMail
from imio.dms.mail.examples import add_special_model_mail
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.utils import create_period_folder
from imio.dms.mail.utils import DummyView
from imio.helpers.content import find
from imio.helpers.security import check_zope_admin
from imio.helpers.workflow import do_transitions
from imio.pyutils.utils import safe_encode
from itertools import cycle
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import check_role
from Products.CPUtils.Extensions.utils import log_list
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.intid import IIntIds

import copy
import os
import time


def get_org_user(directory, keys, userid=""):
    """Get internal org corresponding to keys"""
    f_user = None
    f_org = directory["plonegroup-organization"]
    for key in keys:
        if key not in f_org:
            continue
        f_org = f_org[key]
        if key == keys[-1]:
            users = [u.getId() for u in api.user.get_users(groupname="{}_editeur".format(f_org.UID()))]
            if userid in users:
                f_user = userid
            elif users:
                f_user = users[0]
            break
    else:  # if the demo org has been deleted, we search another org with a configured user
        f_org = None
        orgs = get_registry_organizations()
        for org in orgs:
            users = [u.getId() for u in api.user.get_users(groupname="{}_editeur".format(org))]
            if userid in users:
                f_org = org
                f_user = userid
                break
            elif users:
                f_org = org
                f_user = users[0]
    return f_org, f_user


def import_scanned(self, number=2, only="", ptype="dmsincomingmail", redirect="1"):  # i_e ok
    """
    Import some incoming mail for demo site
    """
    if ptype not in ("dmsincomingmail", "dmsincoming_email"):
        return "ptype parameter must be in ('dmsincomingmail', 'dmsincoming_email') values"
    now = datetime.now()
    portal = getToolByName(self, "portal_url").getPortalObject()
    pc = portal.portal_catalog
    contacts = portal.contacts
    intids = getUtility(IIntIds)
    onlys = only.split(",")
    docs = {
        "dmsincomingmail": {  # i_e ok
            "59.PDF": {
                "c": {"mail_type": "courrier", "file_title": "010500000000001.pdf", "recipient_groups": []},
                "f": {
                    "scan_id": "010500000000001",
                    "pages_number": 1,
                    "scan_date": now,
                    "scan_user": "Opérateur",
                    "scanner": "Ricola",
                },
            },
            "60.PDF": {
                "c": {"mail_type": "courrier", "file_title": "010500000000002.pdf", "recipient_groups": []},
                "f": {
                    "scan_id": "010500000000002",
                    "pages_number": 1,
                    "scan_date": now,
                    "scan_user": "Opérateur",
                    "scanner": "Ricola",
                },
            },
        },
        "dmsincoming_email": OrderedDict(
            [
                (
                    "email3.pdf",
                    {
                        "c": {
                            "title": u"Organisation de la braderie annuelle début septembre",
                            "mail_type": u"courrier",
                            "file_title": u"email.pdf",
                            "recipient_groups": [],
                            "orig_sender_email": u"josiane@gmail.com",
                            "tg": ["evenements"],
                            "user": "agent",
                        },
                        "f": {"scan_id": "", "pages_number": 1, "scan_date": now, "scan_user": "", "scanner": ""},
                        "s": "proposed_to_agent",
                    },
                ),
                (
                    "email4.pdf",
                    {
                        "c": {
                            "title": u"Facture 3P XX12345",
                            "mail_type": u"courrier",
                            "file_title": u"email.pdf",
                            "recipient_groups": [],
                            "orig_sender_email": u"facturation@3p.be",
                        },
                        "f": {"scan_id": "", "pages_number": 1, "scan_date": now, "scan_user": "", "scanner": ""},
                        "a": ["facture-3P-XX12345.pdf"],
                    },
                ),
                (
                    "email1.pdf",
                    {
                        "c": {
                            "title": u"Réservation de la salle Le Foyer",
                            "mail_type": u"courrier",
                            "file_title": u"email.pdf",
                            "recipient_groups": [],
                            "orig_sender_email": u"s.geul@mail.com",
                            "tg": ["direction-generale", "secretariat"],
                            "user": "agent",
                        },
                        "f": {"scan_id": "", "pages_number": 1, "scan_date": now, "scan_user": "", "scanner": ""},
                        "s": "proposed_to_agent",
                    },
                ),
                (
                    "email2.pdf",
                    {
                        "c": {
                            "title": u"Où se situe votre entité par rapport aux Objectifs de développement durable ?",
                            "mail_type": u"courrier",
                            "file_title": u"email.pdf",
                            "recipient_groups": [],
                            "orig_sender_email": u"m.bou@rw.be",
                        },
                        "f": {"scan_id": "", "pages_number": 1, "scan_date": now, "scan_user": "", "scanner": ""},
                    },
                ),
            ]
        ),
    }
    # update config with tg, user, sender
    for fil in docs[ptype]:
        if "tg" in docs[ptype][fil]["c"]:
            org, user = get_org_user(contacts, docs[ptype][fil]["c"].pop("tg"), docs[ptype][fil]["c"].pop("user"))
            if org:
                docs[ptype][fil]["c"].update({"treating_groups": org.UID(), "assigned_user": user})
        if "orig_sender_email" in docs[ptype][fil]["c"]:
            results = pc.unrestrictedSearchResults(
                email=docs[ptype][fil]["c"]["orig_sender_email"],
                portal_type=["organization", "person", "held_position"],
            )
            if results:
                docs[ptype][fil]["c"]["sender"] = [
                    RelationValue(intids.getId(brain._unrestrictedGetObject())) for brain in results
                ]

    docs_cycle = cycle(docs[ptype])
    folder = portal["incoming-mail"]
    count = 1
    limit = int(number)
    while count <= limit:
        doc = docs_cycle.next()
        if only and doc not in onlys:
            time.sleep(0.5)
            continue
        with open(add_path("Extensions/%s" % doc), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=safe_unicode(doc))

        irn = internalReferenceIncomingMailDefaultValue(DummyView(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[ptype][doc]["c"])
        doc_metadata["internal_reference_no"] = irn
        (document, main_file) = createDocument(
            DummyView(portal, portal.REQUEST),
            create_period_folder(folder, datetime.now()),
            ptype,
            "",
            file_object,
            owner="scanner",
            metadata=doc_metadata,
        )
        for key, value in docs[ptype][doc]["f"].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=("scan_id", "internal_reference_number"))
        # transaction.commit()  # commit here to be sure to index preceding when using collective.indexing
        # change has been done in IdmSearchableExtender to avoid using catalog
        document.reindexObject(idxs=("SearchableText",))
        # attachments
        for attachment in docs[ptype][doc].get("a", []):
            with open(add_path("Extensions/%s" % attachment), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=safe_unicode(doc))
            createContentInContainer(document, "dmsappendixfile", title=attachment, file=file_object)
        # state
        if "s" in docs[ptype][doc]:
            to_state = docs[ptype][doc]["s"]
            state = api.content.get_state(document)
            i = 0
            while state != to_state and i < 10:
                do_transitions(
                    document,
                    [
                        "propose_to_agent",
                        "propose_to_n_plus_1",
                        "propose_to_n_plus_2",
                        "propose_to_n_plus_3",
                        "propose_to_n_plus_4",
                        "propose_to_n_plus_5",
                        "propose_to_manager",
                        "propose_to_pre_manager",
                    ],
                )
                state = api.content.get_state(document)
                i += 1
        count += 1
    if redirect:
        return portal.REQUEST.response.redirect(folder.absolute_url())


def import_scanned2(self, number=2):
    """
    Import some outgoing mail for demo site
    """
    now = datetime.now()
    docs = {
        u"011500000000001.pdf": {
            "c": {"mail_type": "type1", "file_title": u"011500000000001.pdf", "outgoing_date": now},
            "f": {
                "scan_id": "011500000000001",
                "pages_number": 1,
                "scan_date": now,
                "scan_user": "Opérateur",
                "scanner": "Ricola",
            },
        },
        u"011500000000002.pdf": {
            "c": {"mail_type": "type1", "file_title": u"011500000000002.pdf", "outgoing_date": now},
            "f": {
                "scan_id": "011500000000002",
                "pages_number": 1,
                "scan_date": now,
                "scan_user": "Opérateur",
                "scanner": "Ricola",
            },
        },
    }
    docs_cycle = cycle(docs)
    portal = getToolByName(self, "portal_url").getPortalObject()
    folder = portal["outgoing-mail"]
    count = 1
    limit = int(number)
    user = api.user.get_current()
    while count <= limit:
        doc = docs_cycle.next()
        with open(add_path("Extensions/%s" % doc), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=doc)
        count += 1
        irn = internalReferenceOutgoingMailDefaultValue(DummyView(portal, portal.REQUEST))
        doc_metadata = copy.copy(docs[doc]["c"])
        doc_metadata["internal_reference_no"] = irn
        (document, main_file) = createDocument(
            DummyView(portal, portal.REQUEST),
            create_period_folder(folder, datetime.now()),
            "dmsoutgoingmail",
            "",
            file_object,
            mainfile_type="dmsommainfile",
            owner="scanner",
            metadata=doc_metadata,
        )
        for key, value in docs[doc]["f"].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=("scan_id", "internal_reference_number"))
        document.reindexObject(idxs=("SearchableText"))
        # we adopt roles for robotframework
        # with api.env.adopt_roles(roles=['Batch importer', 'Manager']):
        # previous is not working
        api.user.grant_roles(user=user, roles=["Batch importer"], obj=document)
        api.content.transition(obj=document, transition="set_scanned")
        api.user.revoke_roles(user=user, roles=["Batch importer"], obj=document)

    return portal.REQUEST.response.redirect(folder.absolute_url())


def create_main_file(self, filename="", title="1", mainfile_type="dmsmainfile", redirect="1"):
    """
    Create a main file on context
    """
    if not filename:
        return "You must pass the filename parameter"
    exm = self.REQUEST["PUBLISHED"]
    path = os.path.dirname(exm.filepath())
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return "The file path '%s' doesn't exist" % filepath
    with open(filepath, "rb") as fo:
        file_object = NamedBlobFile(fo.read(), filename=safe_unicode(filename))
        obj = createContentInContainer(self, mainfile_type, title=safe_unicode(title), file=file_object)
    if redirect:
        return obj.REQUEST.response.redirect("%s/view" % obj.absolute_url())


def clean_examples(self, doit="1"):
    """Clean created examples"""
    if not check_zope_admin():
        return "You must be a zope manager to run this script"
    if doit == "1":
        doit = True
    else:
        doit = False
    out = []
    portal = api.portal.getSite()
    if doit:
        portal.portal_properties.site_properties.enable_link_integrity_checks = False
    registry = getUtility(IRegistry)

    # Delete om
    brains = find(unrestricted=True, portal_type="dmsoutgoingmail")
    for brain in brains:
        log_list(out, "Deleting om '%s'" % brain.getPath())
        if doit and brain.id != "test_creation_modele":
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    if doit:
        registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_number"] = 1
    # Delete im
    brains = find(unrestricted=True, portal_type=["dmsincomingmail", "dmsincoming_email"])
    for brain in brains:
        log_list(out, "Deleting im '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    if doit:
        registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_number"] = 1
    # Delete own personnel
    pf = portal["contacts"]["personnel-folder"]
    brains = find(unrestricted=True, context=pf, portal_type="person")
    for brain in brains:
        log_list(out, "Deleting person '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    # Deactivate own organizations
    ownorg = portal["contacts"]["plonegroup-organization"]
    brains = find(
        unrestricted=True,
        context=ownorg,
        portal_type="organization",
        id=["plonegroup-organization", "college-communal"],
    )
    kept_orgs = [brain.UID for brain in brains]
    log_list(out, "Activating only 'college-communal'")
    if doit:
        set_registry_organizations([ownorg["college-communal"].UID()])
    # Delete organization and template folders
    tmpl_folder = portal["templates"]["om"]
    brains = find(
        unrestricted=True, context=ownorg, portal_type="organization", sort_on="path", sort_order="descending"
    )
    for brain in brains:
        uid = brain.UID
        if uid in kept_orgs:
            continue
        log_list(out, "Deleting organization '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
        if uid in tmpl_folder:
            log_list(out, "Deleting template folder '%s'" % "/".join(tmpl_folder[uid].getPhysicalPath()))
            if doit:
                api.content.delete(obj=tmpl_folder[uid])
    # Delete contacts
    brains = find(unrestricted=True, context=portal["contacts"], portal_type="contact_list")
    for brain in brains:
        log_list(out, "Deleting contact list '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    brains = find(
        unrestricted=True,
        context=portal["contacts"],
        portal_type="person",
        id=["jeancourant", "sergerobinet", "bernardlermitte"],
    )
    for brain in brains:
        log_list(out, "Deleting person '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    brains = find(unrestricted=True, context=portal["contacts"], portal_type="organization", id=["electrabel", "swde"])
    for brain in brains:
        log_list(out, "Deleting organization '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
    # Delete signer rules config
    rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
    api.portal.set_registry_record(rk, [])
    log_list(out, "Deleting signer rules config")
    # Delete users
    for userid in ["encodeur", "dirg", "chef", "agent", "agent1", "lecteur", "bourgmestre"]:
        user = api.user.get(userid=userid)
        for brain in find(unrestricted=True, Creator=userid, sort_on="path", sort_order="descending"):
            log_list(out, "Deleting object '%s' created by '%s'" % (brain.getPath(), userid))
            if doit:
                api.content.delete(obj=brain._unrestrictedGetObject(), check_linkintegrity=False)
        for group in api.group.get_groups(user=user):
            if group.id == "AuthenticatedUsers":
                continue
            log_list(out, "Removing user '%s' from group '%s'" % (userid, group.getProperty("title")))
            if doit:
                api.group.remove_user(group=group, user=user)
        log_list(out, "Deleting user '%s'" % userid)
        if doit:
            api.user.delete(user=user)
    # Delete groups
    functions = [dic["fct_id"] for dic in get_registry_functions()]
    groups = api.group.get_groups()
    for group in groups:
        if "_" not in group.id or group.id in [
            "createurs_dossier",
            "dir_general",
            "lecteurs_globaux_ce",
            "lecteurs_globaux_cs",
        ]:
            continue
        parts = group.id.split("_")
        if len(parts) == 1:
            continue
        org_uid = parts[0]
        function = "_".join(parts[1:])
        if org_uid in kept_orgs or function not in functions:
            continue
        log_list(out, "Deleting group '%s'" % group.getProperty("title"))
        if doit:
            api.group.delete(group=group)
    # Delete folders
    for brain in find(
        unrestricted=True,
        portal_type=("ClassificationFolder", "ClassificationSubfolder"),
        sort_on="path",
        sort_order="descending",
    ):
        log_list(out, "Deleting classification folder '%s'" % brain.getPath())
        if doit:
            api.content.delete(obj=brain._unrestrictedGetObject())
    # Delete categories
    caching.invalidate_cache("collective.classification.tree.utils.iterate_over_tree", portal["tree"].UID())
    res = iterate_over_tree(portal["tree"])
    for category in reversed(res):
        log_list(out, "Deleting category '%s - %s'" % (safe_encode(category.identifier), safe_encode(category.title)))
        if doit:
            api.content.delete(objects=[category])
    if doit:
        caching.invalidate_cache("collective.classification.tree.utils.iterate_over_tree", portal["tree"].UID())
        portal.portal_properties.site_properties.enable_link_integrity_checks = True
    # Create test om
    if doit:
        add_special_model_mail(portal)
    return "\n".join(out)


def activate_group_encoder(self, typ="imail"):
    """Activate group encoder"""
    if not check_role(self):
        return "You must be a manager to run this script"
    portal = api.portal.getSite()
    # activate group encoder
    api.portal.set_registry_record(
        "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}_group_encoder".format(typ), True
    )
    # we add organizations
    orgs = [
        portal["contacts"]["plonegroup-organization"]["direction-generale"]["secretariat"].UID(),
        portal["contacts"]["plonegroup-organization"]["evenements"].UID(),
    ]
    functions = get_registry_functions()
    for dic in functions:
        if dic["fct_id"] != CREATING_GROUP_SUFFIX:
            continue
        if not dic["fct_orgs"]:
            dic["fct_orgs"] = orgs
    set_registry_functions(functions)
    # we add members in groups
    if "encodeur" not in [
        u.getId() for u in api.user.get_users(groupname="{}_{}".format(orgs[0], CREATING_GROUP_SUFFIX))
    ]:
        api.group.add_user(groupname="{}_{}".format(orgs[0], CREATING_GROUP_SUFFIX), username="encodeur")
        api.group.add_user(groupname="{}_{}".format(orgs[1], CREATING_GROUP_SUFFIX), username="agent1")

    return portal.REQUEST.response.redirect(portal.absolute_url())


def activate_signing(self):
    self.portal_setup.runImportStepFromProfile(
        "profile-imio.dms.mail:singles", "imiodmsmail-activate-esigning", run_dependencies=False
    )


def disable_resources_debug_mode(self):
    portal = self
    css_tool = portal.portal_css
    js_tool = portal.portal_javascripts
    if getattr(css_tool, 'getDebugMode', None):
        css_tool.setDebugMode(False)
    if getattr(js_tool, 'getDebugMode', None):
        js_tool.setDebugMode(False)


def approval_annot(self):
    """Display approval annotation on outgoing mail"""
    if not isinstance(self, ImioDmsOutgoingMail):
        return "You have to call this script on an outgoing mail"
    oma = IOMApproval(self)

    def to_native(obj):
        if isinstance(obj, PersistentMapping):
            return {k: to_native(v) for k, v in obj.items()}
        elif isinstance(obj, PersistentList):
            return [to_native(v) for v in obj]
        return obj

    dic = to_native(oma.annot)
    import pprint

    # api.portal.show_message(
    #     message=u"<pre>{}</pre>".format(safe_unicode(pprint.pformat(dic))),
    #     request=self.REQUEST,
    #     type="info",
    # )
    # return self.REQUEST["RESPONSE"].redirect(self.absolute_url())
    return pprint.pformat(dic)
