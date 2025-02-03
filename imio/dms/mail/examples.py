# -*- coding: utf-8 -*-

from collective.classification.folder.utils import evaluate_internal_reference
from collective.classification.tree.utils import create_category
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_groups_mgt
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_groups_mgt
from collective.contact.plonegroup.config import set_registry_organizations
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue
from collective.dms.mailcontent.dmsmail import mailDateDefaultValue
from collective.dms.mailcontent.dmsmail import receptionDateDefaultValue
from DateTime.DateTime import DateTime
from imio.dms.mail import _tr as _
from imio.dms.mail import BLDT_DIR
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.interfaces import IProtectedItem
from imio.dms.mail.utils import DummyView
from imio.dms.mail.utils import sub_create
from imio.helpers.content import get_object
from imio.helpers.security import generate_password
from imio.helpers.security import get_environment
from imio.helpers.security import is_develop_environment
from imio.helpers.workflow import do_transitions
from imio.pyutils.system import get_git_tag
from imio.zamqp.core import base
from itertools import cycle
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds

import datetime
import logging
import os


logger = logging.getLogger("imio.dms.mail: examples")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")


def add_special_model_mail(portal):
    """Add special model mail.

    :param portal: the portal
    :return: the model mail
    """
    params = {
        "title": u"Courrier test pour création de modèles (ne pas effacer)",
        "internal_reference_no": internalReferenceOutgoingMailDefaultValue(DummyView(portal, portal.REQUEST)),
        "mail_date": datetime.date.today(),
        "mail_type": "type1",
    }
    pc = api.portal.get_tool("portal_catalog")
    brains = pc(portal_type="dmsoutgoingmail", id="test_creation_modele")
    if not brains:
        brains2 = pc(portal_type="dmsoutgoingmail", sort_on="created", sort_limit=1)
        good_dtm = datetime.datetime.now()
        if brains2:
            good_dtm = brains2[0].created.asdatetime() - datetime.timedelta(hours=2)
            params["mail_date"] = good_dtm.date()
        obj = sub_create(portal["outgoing-mail"], "dmsoutgoingmail", good_dtm, "test_creation_modele", **params)
        obj.creation_date = DateTime(good_dtm)
        obj.reindexObject()
    else:
        obj = brains[0].getObject()
    if not obj.objectIds():
        filename = u"Réponse salle.odt"
        with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
            file_object = NamedBlobFile(fo.read(), filename=filename)
            filo = createContentInContainer(obj, "dmsommainfile", id="1", title=u"Modèle de base", file=file_object)
            client_id = base.get_config("client_id")
            filo.scan_id = "%s2%s00000000" % (client_id[0:2], client_id[2:6])
            if not IProtectedItem.providedBy(filo):
                alsoProvides(filo, IProtectedItem)
    if not IProtectedItem.providedBy(obj):
        alsoProvides(obj, IProtectedItem)
    return obj


def add_test_annexes_types(context):
    """
    Add french test data: ContentCategoryGroup and ContentCategory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info("Adding annexes types")
    ccc = site["annexes_types"]
    if "annexes" not in ccc:
        category_group = api.content.create(
            type="ContentCategoryGroup",
            title="Annexes",
            container=ccc,
            id="annexes",
            # confidentiality_activated=True,
            # to_be_printed_activated=True,
            # signed_activated=True,
            # publishable_activated=True,
        )
        do_transitions(category_group, ["show_internally"])
    else:
        category_group = ccc["annexes"]
    icats = (
        ("annex", u"Annexe", u"attach.png", True),
        ("deliberation", u"Délibération", u"deliberation_signed.png", True),
        ("cahier-charges", u"Cahier des charges", u"cahier.png", False),
        ("legal-advice", u"Avis légal", u"legalAdvice.png", False),
        ("budget", u"Facture", u"budget.png", False),
    )
    for oid, title, img, show_pv in icats:
        if oid in ccc["annexes"]:
            continue
        icon_path = os.path.join(context._profile_path, "images", img)
        with open(icon_path, "rb") as fl:
            icon = NamedBlobImage(fl.read(), filename=img)
        api.content.create(
            type="ContentCategory",
            title=title,
            description=u"",
            container=category_group,
            icon=icon,
            id=oid,
            predefined_title=title,
            # confidential=True,
            # to_print=True,
            # to_sign=True,
            # signed=True,
            # publishable=True,
            # only_pdf=True,
            show_preview=show_pv,
        )


def add_test_contact_lists(context):
    """
    Add contacts list folder in directory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    contacts = site["contacts"]
    clf = contacts["contact-lists-folder"]

    if base_hasattr(clf, "common"):
        logger.warn("Nothing done: common already exists. You must first delete it to reimport!")
        return

    # set common
    clf.invokeFactory("Folder", id="common", title=u"Listes communes")
    clf["common"].setLayout("folder_tabular_view")
    alsoProvides(clf["common"], IProtectedItem)
    do_transitions(clf["common"], ["show_internally"])
    intids = getUtility(IIntIds)
    if "sergerobinet" in contacts and "bernardlermitte" in contacts:
        api.content.create(
            container=clf["common"],
            type="contact_list",
            id="list-agents-swde",
            title=u"Liste des agents SWDE",
            contacts=[
                RelationValue(intids.getId(contacts["sergerobinet"]["agent-swde"])),
                RelationValue(intids.getId(contacts["bernardlermitte"]["agent-swde"])),
            ],
        )


def add_test_directory(context):
    """
    Add french test data: directory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info("Adding test directory")
    contacts = site["contacts"]
    # if base_hasattr(contacts, 'plonegroup-organization'):
    #     logger.warn('Nothing done: directory contacts already exists. You must first delete it to reimport!')
    #     return

    # Add not encoded person (in directory)
    contacts.invokeFactory("person", "notencoded", lastname=u"Non encodé", use_parent_address=False)

    # Organisations creation (in directory)
    params = {
        "title": u"Electrabel",
        "organization_type": u"sa",
        "zip_code": u"0020",
        "city": u"E-ville",
        "street": u"Rue de l'électron",
        "number": u"1",
        "email": u"contak@electrabel.eb",
        "use_parent_address": False,
    }
    contacts.invokeFactory("organization", "electrabel", **params)
    electrabel = contacts["electrabel"]

    electrabel.invokeFactory("organization", "travaux", title=u"Travaux 1", organization_type=u"service")

    params = {
        "title": u"SWDE",
        "organization_type": u"sa",
        "zip_code": u"0020",
        "city": u"E-ville",
        "street": u"Rue de l'eau vive",
        "number": u"1",
        "email": u"contak@swde.eb",
        "use_parent_address": False,
    }
    contacts.invokeFactory("organization", "swde", **params)
    swde = contacts["swde"]

    # Persons creation (in directory)
    params = {
        "lastname": u"Courant",
        "firstname": u"Jean",
        "gender": u"M",
        "person_title": u"Monsieur",
        "use_parent_address": False,
    }
    contacts.invokeFactory("person", "jeancourant", **params)
    jeancourant = contacts["jeancourant"]

    params = {
        "lastname": u"Robinet",
        "firstname": u"Serge",
        "gender": u"M",
        "person_title": u"Monsieur",
        "use_parent_address": False,
    }
    contacts.invokeFactory("person", "sergerobinet", **params)
    sergerobinet = contacts["sergerobinet"]

    params = {
        "lastname": u"Lermitte",
        "firstname": u"Bernard",
        "gender": u"M",
        "person_title": u"Monsieur",
        "use_parent_address": False,
    }
    contacts.invokeFactory("person", "bernardlermitte", **params)
    bernardlermitte = contacts["bernardlermitte"]

    # Held positions creation (in persons)
    intids = getUtility(IIntIds)

    # link to a defined organisation
    params = {
        "start_date": datetime.date(2001, 5, 25),
        "end_date": datetime.date(2100, 1, 1),
        "position": RelationValue(intids.getId(swde)),
        "label": u"Agent",
        "email": u"serge.robinet@swde.eb",
        "phone": u"012345678",
        "use_parent_address": True,
    }
    sergerobinet.invokeFactory("held_position", "agent-swde", **params)
    params["email"] = u"bernard.lermitte@swde.eb"
    bernardlermitte.invokeFactory("held_position", "agent-swde", **params)

    params = {
        "start_date": datetime.date(2005, 5, 25),
        "end_date": datetime.date(2100, 1, 1),
        "position": RelationValue(intids.getId(electrabel)),
        "label": u"Agent",
        "email": u"jean.courant@electrabel.eb",
        "phone": u"012345678",
        "use_parent_address": True,
    }
    jeancourant.invokeFactory("held_position", "agent-electrabel", **params)


def add_test_folders(context):
    """Add french test data: tree categories"""
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info("Adding test categories")
    site = context.getSite()
    cats = [
        {"identifier": u"-1", "title": u"Tâche des organes. (*)", "parent": None},
        {"identifier": u"-1.7", "title": u"Tâches de police.", "parent": u"-1"},
        {"identifier": u"-1.75", "title": u"Ordre public. (*)", "parent": u"-1.7"},
        {"identifier": u"-1.753", "title": u"Contrôle des armes et munitions.", "parent": u"-1.75"},
        {"identifier": u"-1.754", "title": u"Police de la voie publique (voies et cours d" "eau).", "parent": u"-1.75"},
        {"identifier": u"-1.754.2", "title": u"Usage de la voie publique. (*)", "parent": u"-1.754"},
        {"identifier": u"-1.754.21", "title": u"Stationnement et amarrage. (*)", "parent": u"-1.754.2"},
        {"identifier": u"-1.758", "title": u"Police des édifices et lieux de réunions publiques.", "parent": u"-1.75"},
        {
            "identifier": u"-1.758.1",
            "title": u"Contrôle des fêtes, représentations, expositions, etc. (*)",
            "parent": u"-1.758",
        },
        {"identifier": u"-1.758.2", "title": u"Contrôle des foires, marchés et kermesses. (*)", "parent": u"-1.758"},
        {
            "identifier": u"-1.758.3",
            "title": u"Contrôle des cabarets, cafés et débits de boissons.",
            "parent": u"-1.758",
        },
        {"identifier": u"-1.758.5", "title": u"Contrôle des lieux des réunions religieuses.  (*)", "parent": u"-1.758"},
    ]
    objs = {None: site["tree"]}
    for cat in cats:
        parent = cat.pop("parent")
        if cat["identifier"] in [bb.identifier for bb in objs.get(parent).values()]:
            return
        obj = create_category(objs.get(parent), cat)
        objs[cat["identifier"]] = obj

    logger.info("Adding test folders")
    orgs = get_registry_organizations()
    data = [
        {
            "title": u"Ordre public - Règlement général de police",
            "classification_categories": [objs["-1.75"].UID()],
            "archived": False,
            "subs": [
                {"title": u"Anciens règlements", "archived": True},
                {"title": u"Adaptation pour les caméras de surveillance de l'espace public", "archived": False},
                {"title": u"Demandes de renseignements", "archived": False},
            ],
        },
        {
            "title": u"Règlement général de police : Sanctions administratives / Service de médiation",
            "classification_categories": [objs["-1.75"].UID()],
            "archived": False,
            "subs": [
                {
                    "title": u"Sanctions administratives / Amendes administratives : Agents sanctionnateurs",
                    "archived": True,
                },
                {"title": u"Sanctions administratives communales : Législation", "archived": False},
                {"title": u"Service de médiation : Bilans / Rapports annuels", "archived": False},
            ],
        },
        {
            "title": u"Contrôle des armes et munitions",
            "classification_categories": [objs["-1.753"].UID()],
            "archived": False,
            "subs": [
                {"title": u"Collectionneur d'armes : Mr Fred Chasseur", "archived": True},
                {"title": u"Stands de tir : Certificats d'agrément / Contrôles quinquennals", "archived": False},
                {"title": u"Loi sur les armes à feu : redevances fédérales - Année 2020 à", "archived": False},
            ],
        },
        {
            "title": u"Usage de la voie publique : Stationnement et amarrage",
            "classification_categories": [objs["-1.754.21"].UID()],
            "archived": False,
            "subs": [
                {"title": u"Cas particuliers : Demandes en autorisation - 2008 à 2020", "archived": True},
                {"title": u"Cas particuliers : Demandes en autorisation – 2021", "archived": False},
            ],
        },
        {
            "title": u"Usage de la voie publique : Stationnement et amarrage - Friteries",
            "classification_categories": [objs["-1.754.21"].UID()],
            "archived": False,
            "subs": [
                {"title": u"Attestations d'assurance", "archived": True},
                {"title": u"Autorisation d'exploiter : Belleville, Rue de la Fleur", "archived": False},
            ],
        },
        {
            "title": u"Police des édifices et lieux de réunions publiques : Contrôle des fêtes, bals,...",
            "classification_categories": [objs["-1.758.1"].UID()],
            "archived": False,
            "subs": [
                {"title": u"Demandes en autorisation - 2009 à 2020", "archived": True},
                {"title": u"Demandes en autorisation – 2021", "archived": False},
                {
                    "title": u"Fancy-fair (Ecoles libres ou non communales) : Demandes en autorisation - 2021",
                    "archived": False,
                },
            ],
        },
    ]
    folders = site["folders"]
    for cf_dic in data:
        cf_dic["internal_reference_no"] = evaluate_internal_reference(
            folders, folders.REQUEST, "folder_number", "folder_talexpression"
        )
        cf_dic["treating_groups"] = orgs[1]
        cf_dic["recipient_groups"] = []
        subs = cf_dic.pop("subs")
        cf_obj = createContentInContainer(folders, "ClassificationFolder", **cf_dic)
        cf_obj._increment_internal_reference()
        for i, csf_dic in enumerate(subs, start=1):
            csf_dic["internal_reference_no"] = u"{}-{:02d}".format(cf_obj.internal_reference_no, i)
            csf_dic["treating_groups"] = cf_obj.treating_groups
            csf_dic["recipient_groups"] = []
            if "classification_categories" not in csf_dic:
                csf_dic["classification_categories"] = list(cf_obj.classification_categories)
            csf_obj = createContentInContainer(cf_obj, "ClassificationSubfolder", **csf_dic)
            if not csf_dic["archived"]:
                do_transitions(csf_obj, ["deactivate"])


def add_test_mails(context):
    """
    Add french test data: mails
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info("Adding test mails")
    import imio.dms.mail as imiodmsmail

    filespath = "%s/batchimport/toprocess/incoming-mail" % imiodmsmail.__path__[0]
    files = [
        unicode(name)
        for name in os.listdir(filespath)  # noqa
        if os.path.splitext(name)[1][1:] in ("pdf", "doc", "jpg")
    ]
    files_cycle = cycle(files)

    intids = getUtility(IIntIds)

    contacts = site["contacts"]
    senders = [
        intids.getId(contacts["electrabel"]),  # sender is the organisation
        intids.getId(contacts["swde"]),  # sender is the organisation
        intids.getId(contacts["jeancourant"]),  # sender is a person
        intids.getId(contacts["sergerobinet"]),  # sender is a person
        intids.getId(contacts["jeancourant"]["agent-electrabel"]),  # sender is a person with a position
        intids.getId(contacts["sergerobinet"]["agent-swde"]),  # sender is a person with a position
    ]
    senders_cycle = cycle(senders)

    selected_orgs = [org for i, org in enumerate(get_registry_organizations()) if i in (0, 1, 2, 4, 5, 6)]
    orgas_cycle = cycle(selected_orgs)

    # incoming mails
    ifld = site["incoming-mail"]
    data = DummyView(site, site.REQUEST)
    for i in range(1, 10):
        if not "courrier%d" % i in ifld:
            scan_date = receptionDateDefaultValue(data)
            params = {
                "title": "Courrier %d" % i,
                "mail_type": "courrier",
                "internal_reference_no": internalReferenceIncomingMailDefaultValue(data),
                "reception_date": scan_date,
                "sender": [RelationValue(next(senders_cycle))],
                "treating_groups": next(orgas_cycle),
                "recipient_groups": [],
                "description": "Ceci est la description du courrier %d" % i,
            }
            mail = sub_create(ifld, "dmsincomingmail", scan_date, "courrier%d" % i, **params)
            filename = next(files_cycle)
            with open("%s/%s" % (filespath, filename), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(
                    mail,
                    "dmsmainfile",
                    title="",
                    file=file_object,
                    scan_id="0509999000000%02d" % i,
                    scan_date=scan_date,
                )

    # tasks
    mail = get_object(oid="courrier1", ptype="dmsincomingmail")
    mail.invokeFactory(
        "task", id="tache1", title=u"Tâche 1", assigned_group=mail.treating_groups, enquirer=mail.treating_groups
    )
    mail.invokeFactory(
        "task", id="tache2", title=u"Tâche 2", assigned_group=mail.treating_groups, enquirer=mail.treating_groups
    )
    mail.invokeFactory(
        "task",
        id="tache3",
        title=u"Tâche autre service",
        assigned_group=next(orgas_cycle),
        enquirer=mail.treating_groups,
    )
    task3 = mail["tache3"]
    task3.invokeFactory(
        "task", id="tache3-1", title=u"Sous-tâche 1", assigned_group=task3.assigned_group, enquirer=task3.assigned_group
    )
    task3.invokeFactory(
        "task", id="tache3-2", title=u"Sous-tâche 2", assigned_group=task3.assigned_group, enquirer=task3.assigned_group
    )

    filespath = "%s/batchimport/toprocess/outgoing-mail" % PRODUCT_DIR
    files = [safe_unicode(name) for name in os.listdir(filespath) if os.path.splitext(name)[1][1:] in ("odt",)]
    files.sort()
    files_cycle = cycle(files)
    pf = contacts["personnel-folder"]
    orgas_cycle = cycle(selected_orgs)
    recipients_cycle = cycle(senders)
    users_cycle = cycle(["chef", "agent", "agent"])
    senders_cycle = cycle(
        [pf["chef"]["responsable-grh"].UID(), pf["agent"]["agent-grh"].UID(), pf["agent"]["agent-secretariat"].UID()]
    )

    # outgoing mails
    ofld = site["outgoing-mail"]
    for i in range(1, 10):
        if not "reponse%d" % i in ofld:
            params = {
                "title": "Réponse %d" % i,
                "internal_reference_no": internalReferenceOutgoingMailDefaultValue(data),
                "mail_date": mailDateDefaultValue(data),
                "treating_groups": next(orgas_cycle),
                "mail_type": "type1",
                "sender": next(senders_cycle),
                "assigned_user": next(users_cycle),
                # temporary in comment because it doesn't pass in test and case probably errors when deleting site
                # 'in_reply_to': [RelationValue(intids.getId(inmail))],
                "recipients": [RelationValue(next(recipients_cycle))],
                "send_modes": ["post"],
            }
            mail = sub_create(ofld, "dmsoutgoingmail", datetime.datetime.now(), "reponse%d" % i, **params)
            filename = next(files_cycle)
            with open(u"%s/%s" % (filespath, filename), "rb") as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, "dmsommainfile", id="1", title="", file=file_object)


def add_test_plonegroup_services(context):
    """
    Add french test data: plonegroup organization
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    contacts = site["contacts"]
    own_orga = contacts["plonegroup-organization"]

    if len(own_orga.objectIds()):
        logger.warn("Nothing done: plonegroup-organization already contains children!")
        return

    # Departments and services creation
    sublevels = [
        (u"Direction générale", (u"Secrétariat", u"GRH", u"Informatique", u"Communication")),
        (u"Direction financière", (u"Budgets", u"Comptabilité", u"Taxes", u"Marchés publics")),
        (u"Direction technique", (u"Bâtiments", u"Voiries", u"Urbanisme")),
        (u"Département population", (u"Population", u"État-civil")),
        (u"Département culturel", (u"Enseignement", u"Culture-loisirs")),
        (u"Événements", []),
        (u"Collège communal", []),
        (u"Conseil communal", []),
    ]
    idnormalizer = queryUtility(IIDNormalizer)
    for (department, services) in sublevels:
        oid = own_orga.invokeFactory(
            "organization",
            idnormalizer.normalize(department),
            **{"title": department, "organization_type": (len(services) and u"department" or u"service")}
        )
        dep = own_orga[oid]
        for service in services:
            dep.invokeFactory(
                "organization", idnormalizer.normalize(service), **{"title": service, "organization_type": u"service"}
            )


def add_test_users_and_groups(context):
    """
    Add french test data: users and groups
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()

    # creating users
    users = {
        ("scanner", u"Scanner"): ["Batch importer"],
        ("encodeur", u"Jean Encodeur"): [],
        ("dirg", u"Maxime DG"): [],
        ("chef", u"Michel Chef"): [],
        ("agent", u"Fred Agent"): [],
        ("agent1", u"Stef Agent"): [],
        ("lecteur", u"Jef Lecteur"): [],
    }
    password = "Dmsmail69!"
    if get_environment() == "prod":
        # password = site.portal_registration.generatePassword()
        password = generate_password()
    logger.info("Generated password='%s'" % password)

    for uid, fullname in users.keys():
        try:
            member = site.portal_registration.addMember(
                id=uid, password=password, roles=["Member"] + users[(uid, fullname)]
            )
            member.setMemberProperties({"fullname": fullname, "email": "{}@macommune.be".format(uid)})
        except ValueError as exc:
            if str(exc).startswith("The login name you selected is already in use"):
                continue
            logger.error("Error creating user '%s': %s" % (uid, exc))

    if api.group.get("encodeurs") is None:
        api.group.create("encodeurs", "1 Encodeurs courrier entrant")
        site["incoming-mail"].manage_addLocalRoles("encodeurs", ["Contributor", "Reader"])
        site["contacts"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("encodeurs", ["Contributor", "Editor", "Reader"])
        #        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname="encodeurs", username="scanner")
        api.group.add_user(groupname="encodeurs", username="encodeur")
    if api.group.get("dir_general") is None:
        api.group.create("dir_general", "1 Directeur général")
        api.group.add_user(groupname="dir_general", username="dirg")
        site["outgoing-mail"].manage_addLocalRoles("dir_general", ["Contributor"])
        site["contacts"].manage_addLocalRoles("dir_general", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles(
            "dir_general", ["Contributor", "Editor", "Reader"]
        )
    if api.group.get("expedition") is None:
        api.group.create("expedition", "1 Expédition courrier sortant")
        site["outgoing-mail"].manage_addLocalRoles("expedition", ["Contributor"])
        site["contacts"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        site["contacts"]["contact-lists-folder"].manage_addLocalRoles("expedition", ["Contributor", "Editor", "Reader"])
        api.group.add_user(groupname="expedition", username="scanner")
        api.group.add_user(groupname="expedition", username="encodeur")
    if api.group.get("gestion_contacts") is None:
        api.group.create("gestion_contacts", "1 Gestion doublons contacts")
        api.group.add_user(groupname="gestion_contacts", username="encodeur")
    if api.group.get("lecteurs_globaux_ce") is None:
        api.group.create("lecteurs_globaux_ce", "2 Lecteurs Globaux CE")
    if api.group.get("createurs_dossier") is None:
        api.group.create("createurs_dossier", "1 Créateurs dossiers")
        api.group.add_user(groupname="createurs_dossier", username="dirg")
        api.group.add_user(groupname="createurs_dossier", username="agent")
        api.group.add_user(groupname="createurs_dossier", username="chef")
    if api.group.get("lecteurs_globaux_cs") is None:
        api.group.create("lecteurs_globaux_cs", "2 Lecteurs Globaux CS")
    if api.group.get("audit_contacts") is None:
        api.group.create("audit_contacts", "1 Audit contacts")
        api.group.add_user(groupname="audit_contacts", username="dirg")


def configure_batch_import(context):
    """
    Add batch import configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info("Configure batch import")
    registry = getUtility(IRegistry)
    import imio.dms.mail as imiodmsmail

    productpath = imiodmsmail.__path__[0]

    if not registry.get("collective.dms.batchimport.batchimport.ISettings.fs_root_directory"):
        registry["collective.dms.batchimport.batchimport.ISettings.fs_root_directory"] = os.path.join(
            productpath, u"batchimport/toprocess"
        )
    if not registry.get("collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory"):
        registry["collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory"] = os.path.join(
            productpath, u"batchimport/toprocess"
        )
    if not registry.get("collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping"):
        registry["collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping"] = [
            {"code": u"in", "portal_type": u"dmsincomingmail"}
        ]  # i_e ok


def configure_contact_plone_group(context):
    """
    Add french test contact plonegroup configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info("Configure contact plonegroup")
    site = context.getSite()
    if not get_registry_functions():
        set_registry_functions(
            [
                {
                    "fct_title": u"Créateur CS",
                    "fct_id": u"encodeur",
                    "fct_orgs": [],
                    "fct_management": False,
                    "enabled": True,
                },
                {
                    "fct_title": u"Lecteur",
                    "fct_id": u"lecteur",
                    "fct_orgs": [],
                    "fct_management": False,
                    "enabled": True,
                },
                {
                    "fct_title": u"Éditeur",
                    "fct_id": u"editeur",
                    "fct_orgs": [],
                    "fct_management": False,
                    "enabled": True,
                },
            ]
        )
    if not get_registry_groups_mgt():
        set_registry_groups_mgt(["dir_general", "encodeurs", "expedition"])
    if not get_registry_organizations():
        contacts = site["contacts"]
        own_orga = contacts["plonegroup-organization"]
        # full list of orgs defined in add_test_plonegroup_services ~1600
        departments = own_orga.listFolderContents(contentFilter={"portal_type": "organization"})
        dep0 = departments[0]
        dep1 = departments[1]
        dep2 = departments[2]
        services0 = dep0.listFolderContents(contentFilter={"portal_type": "organization"})
        services1 = dep1.listFolderContents(contentFilter={"portal_type": "organization"})
        services2 = dep2.listFolderContents(contentFilter={"portal_type": "organization"})
        orgas = [
            dep0,
            services0[0],
            services0[1],
            services0[3],
            dep1,
            services1[0],
            services1[1],
            dep2,
            services2[0],
            services2[1],
            departments[5],
        ]
        # selected orgs
        # u'Direction générale', (u'Secrétariat', u'GRH', u'Communication')
        # u'Direction financière', (u'Budgets', u'Comptabilité')
        # u'Direction technique', (u'Bâtiments', u'Voiries')
        # u'Événements'
        set_registry_organizations([org.UID() for org in orgas])
        # Add users to activated groups
        for org in orgas:
            uid = org.UID()
            site.acl_users.source_groups.addPrincipalToGroup("chef", "%s_encodeur" % uid)
            if org.organization_type == "service":
                site.acl_users.source_groups.addPrincipalToGroup("agent", "%s_editeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup("agent", "%s_encodeur" % uid)
                site.acl_users.source_groups.addPrincipalToGroup("lecteur", "%s_lecteur" % uid)
        site.acl_users.source_groups.addPrincipalToGroup("agent1", "%s_editeur" % departments[5].UID())
        site.acl_users.source_groups.addPrincipalToGroup("agent1", "%s_encodeur" % departments[5].UID())
        site.acl_users.source_groups.addPrincipalToGroup("encodeur", "%s_editeur" % services0[0].UID())
        site.acl_users.source_groups.addPrincipalToGroup("encodeur", "%s_encodeur" % services0[0].UID())
        # internal persons and held_positions have been created
        persons = {
            "encodeur": {
                "pers": {
                    "lastname": u"Encodeur",
                    "firstname": u"Jean",
                    "gender": u"M",
                    "person_title": u"Monsieur",
                    "zip_code": u"5000",
                    "city": u"Namur",
                    "street": u"Rue de l'église",
                    "number": u"4",
                    "primary_organization": services0[0].UID(),
                },
                "hps": {"phone": u"012345679", "label": u"Encodeur {}"},
            },
            "chef": {
                "pers": {
                    "lastname": u"Chef",
                    "firstname": u"Michel",
                    "gender": u"M",
                    "person_title": u"Monsieur",
                    "zip_code": u"4000",
                    "city": u"Liège",
                    "street": u"Rue du cimetière",
                    "number": u"2",
                    "primary_organization": dep0.UID(),
                },
                "hps": {"phone": u"012345679", "label": u"Responsable {}"},
            },
            "agent": {
                "pers": {
                    "lastname": u"Agent",
                    "firstname": u"Fred",
                    "gender": u"M",
                    "person_title": u"Monsieur",
                    "zip_code": u"7000",
                    "city": u"Mons",
                    "street": u"Rue de la place",
                    "number": u"3",
                    "primary_organization": services0[3].UID(),
                },
                "hps": {"phone": u"012345670", "label": u"Agent {}"},
            },
            "agent1": {
                "pers": {
                    "lastname": u"Agent",
                    "firstname": u"Stef",
                    "gender": u"M",
                    "person_title": u"Monsieur",
                    "zip_code": u"5000",
                    "city": u"Namur",
                    "street": u"Rue du désespoir",
                    "number": u"1",
                    "primary_organization": departments[5].UID(),
                },
                "hps": {"phone": u"012345670", "label": u"Agent {}"},
            },
        }
        pf = contacts["personnel-folder"]
        normalizer = getUtility(IIDNormalizer)
        for pers_id in persons:
            if pers_id not in pf:
                raise "Person {} not created in personnel-folder".format(pers_id)
            person = pf[pers_id]
            for fld, val in persons[pers_id]["pers"].items():
                setattr(person, fld, val)
            person.reindexObject()
            for hp in person.objectValues():
                setattr(hp, "phone", persons[pers_id]["hps"]["phone"])
                setattr(hp, "label", persons[pers_id]["hps"]["label"].format(hp.get_organization().title))
                api.content.rename(obj=hp, new_id=normalizer.normalize(hp.label))
                hp.reindexObject()


def configure_imio_dms_mail(context):
    """
    Add french test imio dms mail configuration
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    logger.info("Configure imio dms mail")
    registry = getUtility(IRegistry)

    # IM
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types"] = [
            {"value": u"courrier", "dtitle": u"Courrier", "active": True},
            {"value": u"recommande", "dtitle": u"Recommandé", "active": True},
            {"value": u"certificat", "dtitle": u"Certificat médical", "active": True},
            {"value": u"fax", "dtitle": u"Fax", "active": True},
            {"value": u"retour-recommande", "dtitle": u"Retour recommandé", "active": True},
            {"value": u"facture", "dtitle": u"Facture", "active": True},
        ]
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states"] = ["proposed_to_agent"]
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields"):
        fields = [
            "IDublinCore.title",
            "IDublinCore.description",
            "orig_sender_email",
            "sender",
            "treating_groups",
            "ITask.assigned_user",
            "recipient_groups",
            "reception_date",
            "ITask.due_date",
            "mail_type",
            "reply_to",
            "ITask.task_description",
            "external_reference_no",
            "original_mail_date",
            "IClassificationFolder.classification_categories",
            "IClassificationFolder.classification_folders",
            "internal_reference_no",
        ]
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_fields"] = [
            {"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in fields
        ]

    # IEM
    routing_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.iemail_routing"
    if not registry.get(routing_key, default=[]):
        registry[routing_key] = [
            {
                u"forward": u"agent",
                u"transfer_email_pat": u"",
                u"original_email_pat": u"",
                u"tal_condition_1": u"",
                u"user_value": u"_empty_",
                u"tal_condition_2": u"python: 'encodeurs' in modules['imio.dms.mail.utils']."
                                    u"current_user_groups_ids(userid=assigned_user)",
                u"tg_value": u"_empty_",
            },
            {
                u"forward": u"agent",
                u"transfer_email_pat": u"",
                u"original_email_pat": u"",
                u"tal_condition_1": u"",
                u"user_value": u"_transferer_",
                u"tal_condition_2": u"",
                u"tg_value": u"_hp_",
            },
        ]
    state_set_key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.iemail_state_set"
    if not registry.get(state_set_key, default=[]):
        registry[state_set_key] = [
            {
                u"forward": u"agent",
                u"transfer_email_pat": u"",
                u"original_email_pat": u"",
                u"tal_condition_1": u"",
                u"state_value": u"proposed_to_agent"
            },
        ]

    # OM
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_types"] = [
            {"value": u"type1", "dtitle": u"Type 1", "active": True},
        ]
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile"] = True
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_response_prefix"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_response_prefix"] = _(u"Response: ")
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes"):
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_send_modes"] = [
            {"value": u"post", "dtitle": u"Lettre", "active": True},
            {"value": u"post_registered", "dtitle": u"Lettre recommandée", "active": True},
            {"value": u"email", "dtitle": u"Email", "active": True},
        ]
    if registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_replyto_email_send") is None:
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_replyto_email_send"] = False
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields"):
        fields = [
            "IDublinCore.title",
            "IDublinCore.description",
            "orig_sender_email",
            "recipients",
            "treating_groups",
            "ITask.assigned_user",
            "sender",
            "recipient_groups",
            "send_modes",
            "mail_type",
            "mail_date",
            "reply_to",
            "ITask.task_description",
            "ITask.due_date",
            "outgoing_date",
            "external_reference_no",
            "IClassificationFolder.classification_categories",
            "IClassificationFolder.classification_folders",
            "internal_reference_no",
            "email_status",
            "email_subject",
            "email_sender",
            "email_recipient",
            "email_cc",
            "email_bcc",
            "email_attachments",
            "email_body",
        ]
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields"] = [
            {"field_name": v, "read_tal_condition": u"", "write_tal_condition": u""} for v in fields
        ]

    # IOM
    if not registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature"):
        from string import Template

        template = Template(
            u"""
<meta charset="UTF-8">
<tal:global define="ctct_det python: dghv.get_ctct_det(sender['hp']);
                    label python: sender['hp'].label;
                    services python: dghv.separate_full_title(sender['org_full_title']);">
<p style="font-weight: bold;" tal:condition="nothing">!! Attention: ne pas modifier ceci directement mais passer par
 "Source" !!</p>
<br />
<p><span style="font-size:large;font-family:Quicksand,Arial"
 tal:content="python:u'{} {}'.format(sender['person'].firstname, sender['person'].lastname)">Prénom Nom</span></p>

<div style="float:left;">
<div style="font-size:small; float:left;clear:both;width:350px">
<span tal:condition="label" tal:content="label">Fonction</span><br />
<span tal:content="python:services[0]">Département</span><br />
<span tal:condition="python:services[1]" tal:content="python:services[1]">Service</span><br />

<a style="display: inline-block; padding-top: 1em;" href="mailto" target="_blank"
 tal:attributes="href python:'mailto:{}'.format(ctct_det['email'])" tal:content="python:ctct_det['email']">email</a>
<br /><span tal:content="python: dghv.display_phone(phone=ctct_det['phone'], check=False, pattern='/.')">Téléphone
</span><br />

<span style="display: inline-block; padding-top: 0.5em;"
 tal:content="python:u'{}, {}'.format(ctct_det['address']['street'], ctct_det['address']['number'])">Rue, numéro
 </span><br />
<span tal:content="python:u'{} {}'.format(ctct_det['address']['zip_code'], ctct_det['address']['city'])">CP Localité
</span><br />
<!--a href="https://www.google.be/maps/" target="_blank">Plan</a-->
</div></div>

<div style="float:left;display: inline-grid;"><a href="$url" target="_blank"><img alt=""
 src="$url/++resource++imio.dms.mail/belleville.png" /></a><br />
<span style="font-size:small;text-align: center;">Administration communale de Belleville</span><br />
</div>

<p>&nbsp;</p>

<div style="font-size: x-small;color:#424242;clear:both"><br />
Limite de responsabilité: les informations contenues dans ce courrier électronique (annexes incluses) sont
 confidentielles et réservées à l'usage exclusif des destinataires repris ci-dessus. Si vous n'êtes pas le
 destinataire, soyez informé par la présente que vous ne pouvez ni divulguer, ni reproduire, ni faire usage de ces
 informations pour vous-même ou toute tierce personne. Si vous avez reçu ce courrier électronique par erreur, vous
 êtes prié d'en avertir immédiatement l'expéditeur et d'effacer le message e-mail de votre ordinateur.
</div>
</tal:global>"""
        )  # noqa
        registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_email_signature"] = template.substitute(
            url=PUBLIC_URL
        )

    # general
    api.portal.set_registry_record(
        "imio.dms.mail.browser.settings.IImioDmsMailConfig.users_hidden_in_dashboard_filter", ["scanner"]
    )

    # IImioDmsMailConfig2 settings
    api.portal.set_registry_record("imio.dms.mail.dv_clean_days", 180)
    api.portal.set_registry_record("imio.dms.mail.imail_folder_period", u"week")
    api.portal.set_registry_record("imio.dms.mail.omail_folder_period", u"week")
    if not api.portal.get_registry_record("imio.dms.mail.product_version"):
        api.portal.set_registry_record(
            "imio.dms.mail.product_version", safe_unicode(get_git_tag(BLDT_DIR, is_develop_environment()))
        )

    # mailcontent
    # Hide internal reference for outgoingmmail. Increment number automatically
    registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_edit_irn"] = u"hide"
    registry["collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_increment_number"] = True

    if (
        registry.get("collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_talexpression")
        == u"python:'in/'+number"
    ):
        registry[
            "collective.dms.mailcontent.browser.settings.IDmsMailConfig.incomingmail_talexpression"
        ] = u"python:'E%04d'%int(number)"
    if (
        registry.get("collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_talexpression")
        == u"python:'out/'+number"
    ):
        registry[
            "collective.dms.mailcontent.browser.settings.IDmsMailConfig.outgoingmail_talexpression"
        ] = u"python:'S%04d'%int(number)"
