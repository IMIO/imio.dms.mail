# -*- coding: utf-8 -*-

# Copyright (c) 2021 by Imio
# GNU General Public License (GPL)
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.config import set_registry_organizations
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.contact.plonegroup.utils import get_suffixed_groups
from collective.documentgenerator.utils import update_templates
from collective.wfadaptations.api import add_applied_adaptation
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from copy import deepcopy
from dexterity.localroles.utils import fti_configuration
from dexterity.localroles.utils import update_roles_in_fti
from eea.facetednavigation.criteria.interfaces import ICriteria
from ftw.labels.interfaces import ILabeling
from imio.dms.mail import ALL_SERVICE_FUNCTIONS
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import OM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.setuphandlers import add_templates
from imio.dms.mail.setuphandlers import createStateCollections
from imio.dms.mail.setuphandlers import list_templates
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.utils import create_personnel_content
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_approvers_settings
from imio.dms.mail.utils import update_transitions_levels_config
from imio.dms.mail.wfadaptations import IMServiceValidation
from imio.dms.mail.wfadaptations import OMServiceValidation
from imio.dms.mail.wfadaptations import OMToApproveAdaptation
from imio.dms.mail.wfadaptations import OMToPrintAdaptation
from imio.dms.mail.wfadaptations import TaskServiceValidation
from imio.esign.config import set_registry_enabled
from imio.esign.config import set_registry_file_url
from imio.esign.config import set_registry_seal_code
from imio.esign.config import set_registry_seal_email
from imio.esign.config import set_registry_vat_number
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.emailer import get_mail_host
from imio.helpers.security import get_user_from_criteria
from imio.helpers.setup import load_workflow_from_package
from imio.helpers.workflow import do_transitions
from imio.pyutils.system import read_csv
from imio.pyutils.utils import append
from imio.pyutils.utils import safe_encode
from persistent.list import PersistentList
from plone import api
from plone.app.portlets.storage import PortletAssignmentMapping
from plone.namedfile import NamedImage
from plone.portlet.static.static import Assignment as StaticAssignment
from plone.portlets.constants import CONTENT_TYPE_CATEGORY
from plone.portlets.interfaces import IPortletManager
from Products.CMFCore.ActionInformation import Action
from Products.CMFPlone.utils import safe_unicode
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import datetime
import logging
import os
import pwd


logger = logging.getLogger("imio.dms.mail: steps")


def create_persons_from_users(portal, fn_first=True, functions=ALL_SERVICE_FUNCTIONS, userid=""):
    """create own personnel from plone users"""
    out = []
    for udic in get_user_from_criteria(portal, email=""):  # all users
        groups = get_plone_groups_for_user(user_id=udic["userid"])
        out.extend(create_personnel_content(udic["userid"], groups, primary=True, fn_first=fn_first))
    return out


# #############
# Singles steps
# #############


def activate_esigning(context):
    """Activate approbation and esigning functionality for imio.dms.mail"""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Activate signing functionality")
    site = context.getSite()

    site.portal_quickinstaller.installProduct("imio.esign", forceProfile=True)
    log = ["Installed imio.esign"]

    set_registry_enabled(True)

    if not api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_esign_formats"):
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_esign_formats",
                                       ["odt", "pdf"])

    if not api.portal.get_registry_record("imio.esign.signing_users_email_content"):
        from string import Template
        template = Template(
            u"""
Bonjour {fullname},

Vous avez été invité sur Paraphéo, la plateforme de signature de iMio.

Avant de pouvoir signer des documents, vous devez activer votre compte.

Veuillez suivre ces étapes:
1. Visiter https://simplycosi-1.trustsigneurope.com/login?tenantName=IMIO
2. Entrez votre adresse email ({email}) dans le champ "utilisateur"
3. Cliquez sur "mot de passe oublié" pour définir votre mot de passe
4. Connectez-vous une première fois sur la plateforme

L'activation ne doit être faite qu'une seule fois. Vous pourrez ensuite commencer à signer des documents.

Bien cordialement,
L'équipe iMio"""
        )
        api.portal.set_registry_record(
            "imio.esign.signing_users_email_content",
            template.substitute(),
        )

    omf = api.portal.get_registry_record(
        "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields", default=[]
    )
    om_fns = [dic["field_name"] for dic in omf]
    if "ISigningBehavior.signers" not in om_fns:
        pos = om_fns.index("internal_reference_no")
        omf.insert(pos + 1,
                   {"field_name": "ISigningBehavior.signers", "read_tal_condition": u"", "write_tal_condition": u""})
        omf.insert(pos + 2,
                   {"field_name": "ISigningBehavior.seal", "read_tal_condition": u"", "write_tal_condition": u""})
        omf.insert(pos + 3,
                   {"field_name": "ISigningBehavior.esign", "read_tal_condition": u"", "write_tal_condition": u""})
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_fields",
                                       omf)
        log.append("Updated omail_fields registry record")

    site.portal_setup.runImportStepFromProfile(
        "profile-imio.dms.mail:singles", "imiodmsmail-om_to_approve_wfadaptation", run_dependencies=False
    )
    log.append("Updated outgoingmail_workflow with to_approve state")

    # add signed collection
    col_folder = site["outgoing-mail"]["mail-searches"]
    createStateCollections(col_folder, "dmsoutgoingmail")
    pos = col_folder.getObjectPosition("searchfor_to_be_signed")
    col_folder.moveObjectToPosition("searchfor_signed", pos + 1)

    # update approvers settings
    update_approvers_settings()
    return "\n".join(log)


def create_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    add_templates(context.getSite())


def update_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list)
    ret = "\n".join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode("utf8")
    logger.info("\n{}".format(ret))
    return ret


def override_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list, force=True)
    ret = "\n".join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode("utf8")
    logger.info("\n{}".format(ret))
    return ret


def create_persons_from_users_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    return "\n".join(create_persons_from_users(context.getSite())).encode("utf8")


def create_persons_from_users_step_inverted(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    return "\n".join(create_persons_from_users(context.getSite(), fn_first=False)).encode("utf8")


def add_icons_to_contact_workflow(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    wfl = site.portal_workflow.collective_contact_core_workflow
    for name, icon in (("activate", "im_treat"), ("deactivate", "im_back_to_creation")):
        tr = wfl.transitions.get(name)
        tr.actbox_icon = "%%(portal_url)s/++resource++imio.dms.mail/%s.png" % icon


def mark_copy_im_as_read(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    # adapted = ILabelJar(site['incoming-mail']); adapted.list()
    days_back = 5
    start = datetime.datetime(1973, 2, 12)
    end = datetime.datetime.now() - datetime.timedelta(days=days_back)
    users = {}
    functions = {"i": IM_READER_SERVICE_FUNCTIONS, "o": OM_READER_SERVICE_FUNCTIONS}
    brains = site.portal_catalog.unrestrictedSearchResults(
        portal_type=["dmsincomingmail", "dmsincoming_email"],
        created={"query": (start, end), "range": "min:max"},
        sort_on="created",
    )
    out = ["%d mails" % len(brains)]
    changed_mails = 0
    related_users = set()
    for brain in brains:
        if not brain.recipient_groups:
            continue
        typ = brain.portal_type[3:4]
        user_ids = set()
        for org_uid in brain.recipient_groups:
            if org_uid not in users:
                users[org_uid] = {}
            if typ not in users[org_uid]:
                users[org_uid][typ] = get_selected_org_suffix_principal_ids(org_uid, functions[typ])
            for userid in users[org_uid][typ]:
                user_ids.add(userid)
        if len(user_ids):
            related_users.update(user_ids)
            obj = brain._unrestrictedGetObject()
            labeling = ILabeling(obj)
            labeling.storage["lu"] = PersistentList(user_ids)
            obj.reindexObject(idxs=["labels"])
            changed_mails += 1
    out.append('%d mails labelled with "lu"' % changed_mails)
    out.append("%d users are concerned" % len(related_users))
    return "\n".join(out)


def im_n_plus_1_wfadaptation(context):
    """
    Add n_plus_1 level in incomingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Apply n_plus_1 level on incomingmail_workflow")
    site = context.getSite()
    n_plus_1_params = {
        "validation_level": 1,
        "state_title": u"À valider par le chef de service",
        "forward_transition_title": u"Proposer au chef de service",
        "backward_transition_title": u"Renvoyer au chef de service",
        "function_title": u"N+1",
    }
    sva = IMServiceValidation()
    adapt_is_applied = sva.patch_workflow("incomingmail_workflow", **n_plus_1_params)
    if adapt_is_applied:
        add_applied_adaptation(
            "imio.dms.mail.wfadaptations.IMServiceValidation", "incomingmail_workflow", True, **n_plus_1_params
        )
    # Add users to activated groups
    if "chef" in [ud["userid"] for ud in get_user_from_criteria(site, email="")]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup("chef", "%s_n_plus_1" % uid)


def om_n_plus_1_wfadaptation(context):
    """
    Add n_plus_1 level in outgoingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Apply n_plus_1 level on outgoingmail_workflow")
    site = context.getSite()
    n_plus_1_params = {
        "validation_level": 1,
        "state_title": u"À valider par le chef de service",
        "forward_transition_title": u"Proposer au chef de service",
        "backward_transition_title": u"Renvoyer au chef de service",
        "function_title": u"N+1",
        "validated_from_created": False,
    }
    sva = OMServiceValidation()
    adapt_is_applied = sva.patch_workflow("outgoingmail_workflow", **n_plus_1_params)
    if adapt_is_applied:
        add_applied_adaptation(
            "imio.dms.mail.wfadaptations.OMServiceValidation", "outgoingmail_workflow", True, **n_plus_1_params
        )
    # Add users to activated groups
    if "chef" in [ud["userid"] for ud in get_user_from_criteria(site, email="")]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup("chef", "%s_n_plus_1" % uid)


def om_to_approve_wfadaptation(context):
    """
    Add to_approve level in outgoingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Apply to_approve level on outgoingmail_workflow")
    sva = OMToApproveAdaptation()
    adapt_is_applied = sva.patch_workflow("outgoingmail_workflow")
    if adapt_is_applied:
        add_applied_adaptation(
            "imio.dms.mail.wfadaptations.OMToApproveAdaptation", "outgoingmail_workflow", True
        )


def om_to_print_wfadaptation(context):
    """
    Add to_print level in outgoingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Apply to_print level on outgoingmail_workflow")
    sva = OMToPrintAdaptation()
    adapt_is_applied = sva.patch_workflow("outgoingmail_workflow")
    if adapt_is_applied:
        add_applied_adaptation(
            "imio.dms.mail.wfadaptations.OMToPrintAdaptation", "outgoingmail_workflow", True
        )


def task_n_plus_1_wfadaptation(context):
    """
    Add n_plus_1 level in task_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Apply n_plus_1 level on task_workflow")
    site = context.getSite()
    sva = TaskServiceValidation()
    adapt_is_applied = sva.patch_workflow("task_workflow", **{})
    if adapt_is_applied:
        add_applied_adaptation("imio.dms.mail.wfadaptations.TaskServiceValidation", "task_workflow", True, **{})
    # Add users to activated groups
    if "chef" in [ud["userid"] for ud in get_user_from_criteria(site, email="")]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup("chef", "%s_n_plus_1" % uid)


def manage_classification(context, active):
    """Activate or deactivate classification"""
    logger.info("Manage classification by {}activating related things".format(not active and "de-" or ""))
    site = context.getSite()
    # handle navtree_properties
    unlisted = list(site.portal_properties.navtree_properties.metaTypesNotToList)
    update = False
    for ptype in ("ClassificationFolders", "ClassificationContainer"):
        if active and ptype in unlisted:
            unlisted.remove(ptype)
            update = True
        elif not active and ptype not in unlisted:
            unlisted.append(ptype)
            update = True
    if update:
        site.portal_properties.navtree_properties.manage_changeProperties(metaTypesNotToList=unlisted)
    # handle fields
    for rec in ("imail_fields", "omail_fields"):
        update = False
        rec_name = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(rec)
        showed = api.portal.get_registry_record(rec_name, default=[])
        showed_ids = [dic["field_name"] for dic in showed]
        # imf = [ for v in im_fo]
        for fld in (
            u"IClassificationFolder.classification_folders",
            u"IClassificationFolder.classification_categories",
        ):
            if active and fld not in showed_ids:
                idx = showed_ids.index("internal_reference_no")
                showed.insert(idx, {"field_name": fld, "read_tal_condition": u"", "write_tal_condition": u""})
                update = True
            elif not active and fld in showed_ids:
                showed = [dic for dic in showed if dic["field_name"] != fld]
                update = True
        if update:
            api.portal.set_registry_record(rec_name, list(showed))
    # handle criterias
    for dpath, crit_ids in (("incoming-mail", ["c20", "c21"]), ("outgoing-mail", ["c19", "c20"])):
        mspath = os.path.join(dpath, "mail-searches")
        folder = site.unrestrictedTraverse(mspath)
        criterias = ICriteria(folder)
        for crit_id in crit_ids:
            criterion = criterias.get(crit_id)
            if active and criterion.hidden:
                criterion.hidden = False
                criterias.criteria._p_changed = 1
            elif not active and not criterion.hidden:
                criterion.hidden = True
                criterias.criteria._p_changed = 1
    # handle columns
    for dpath in ("incoming-mail", "outgoing-mail"):
        obj = site.unrestrictedTraverse(dpath)
        brains = site.portal_catalog(portal_type="DashboardCollection", path="/".join(obj.getPhysicalPath()))
        for brain in brains:
            col = brain.getObject()
            buf = list(col.customViewFields)
            if active and u"classification_folders" not in buf:
                if "actions" in buf:
                    buf.insert(buf.index("actions"), u"classification_folders")
                else:
                    buf.append(u"classification_folders")
                col.customViewFields = tuple(buf)
            elif not active and u"classification_folders" in buf:
                buf.remove(u"classification_folders")
                col.customViewFields = tuple(buf)


def deactivate_classification(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    manage_classification(context, False)


def activate_classification(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    manage_classification(context, True)


def reset_workflows_bad(context):
    """Reset workflows and reapply wf adaptations."""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    # TODO
    # find what's deleted (with local roles config or collection ?)
    # reset dms_config
    # clean local roles
    # delete collection
    # clean registry with prefix prefix:imio.actionspanel.browser.registry.IImioActionsPanelConfig
    # clean remark config
    # clean function if all removed ?
    # reindex

    site.portal_setup.runImportStepFromProfile("profile-imio.dms.mail:default", "workflow", run_dependencies=False)
    applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()]
    if applied_adaptations:
        success, errors = apply_from_registry(reapply=True)
        if errors:
            logger.error("Problem applying wf adaptations: %d errors" % errors)
    if "imio.dms.mail.wfadaptations.TaskServiceValidation" not in applied_adaptations:
        update_task_workflow(site)
    site.portal_workflow.updateRoleMappings()
    logger.info("Workflow reset done")


def remove_om_nplus1_wfadaptation(context):
    """"""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    val_states = ["validated", "proposed_to_n_plus_1"]
    p_t = "dmsoutgoingmail"
    fct_id = u"n_plus_1"
    log = []
    site = context.getSite()
    applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()]
    if u"imio.dms.mail.wfadaptations.OMServiceValidation" not in applied_adaptations:
        logger.info(append(log, "OMServiceValidation already removed !"))
        return "\n".join(log)
    # are there oms ?
    brains = site.portal_catalog.unrestrictedSearchResults(portal_type=p_t, review_state=val_states)
    if brains:
        logger.error(append(log, "Found some outgoing mails in state 'proposed_to_n_plus_1' or 'validated'. We stop !"))
        return "\n".join(log)
    # reset workflow
    if not load_workflow_from_package("outgoingmail_workflow", "profile-imio.dms.mail:default"):
        raise Exception("Cannot reload workflow from package")
    # remove function if not used elsewhere
    lr_types = [p_t]
    other_nplus = True
    functions = get_registry_functions()
    for wfa in (
        u"imio.dms.mail.wfadaptations.TaskServiceValidation",
        u"imio.dms.mail.wfadaptations.IMServiceValidation",
    ):
        if wfa in applied_adaptations:
            logger.info(append(log, "Do not remove n_plus_1 function because it's used by another adaptation"))
            break
    else:
        lr_types.extend(("ClassificationFolder", "ClassificationSubfolder"))
        other_nplus = False
        if fct_id in [fct["fct_id"] for fct in functions]:
            set_registry_functions([fct for fct in functions if fct["fct_id"] != fct_id])
        # empty and delete groups...
        groups = get_suffixed_groups(["n_plus_1"])
        for group in groups:
            for user in api.user.get_users(group=group):
                api.group.remove_user(group=group, user=user)
            api.group.delete(group=group)
    # remove dexterity local roles on om and folders
    for ptype in lr_types:
        lr, fti = fti_configuration(portal_type=ptype)
        for i, keyname in enumerate(("static_config", "treating_groups", "recipient_groups")):
            if keyname not in lr:
                continue
            lrd = lr[keyname]
            for state in val_states:
                if state not in lrd:
                    continue
                update_roles_in_fti(ptype, {state: deepcopy(lrd[state])}, action="rem", keyname=keyname)
            if other_nplus:  # no need to remove n_plus_ suffix
                continue
            config = {}
            for state in lrd:
                if fct_id in lrd[state]:
                    config.update({state: {fct_id: deepcopy(lrd[state][fct_id])}})
            if config:
                update_roles_in_fti(ptype, config, action="rem", keyname=keyname)
    # update dms config
    wf_from_to = get_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus"])
    new_to_value = [tup for tup in wf_from_to["to"] if tup[0] != val_states[0]]  # we remove validated
    if wf_from_to["to"] != new_to_value:
        set_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus", "to"], new_to_value)
    # --
    tr_config = get_dms_config(["transitions_levels", "dmsoutgoingmail"])
    new_value = {k: v for (k, v) in tr_config.items() if k not in val_states}
    if tr_config != new_value:
        set_dms_config(["transitions_levels", "dmsoutgoingmail"], new_value)
        update_transitions_levels_config(["dmsoutgoingmail"])
    # --
    rl_config = get_dms_config(["review_levels", "dmsoutgoingmail"])
    suffix = "_{}".format(fct_id)
    if suffix in rl_config:
        rl_config.pop(suffix)
        set_dms_config(keys=["review_levels", "dmsoutgoingmail"], value=rl_config)
    # --
    rs_config = get_dms_config(["review_states", "dmsoutgoingmail"])
    if val_states[1] in rs_config:
        rs_config.pop(val_states[1])
        set_dms_config(keys=["review_states", "dmsoutgoingmail"], value=rs_config)
    update_transitions_levels_config(["dmsoutgoingmail"])
    # remove collections, update some
    folder = site["outgoing-mail"]["mail-searches"]
    val_col_uid = folder["searchfor_{}".format(val_states[0])].UID()
    for state_id in val_states:
        col_id = "searchfor_{}".format(state_id)
        if col_id in folder:
            api.content.delete(folder[col_id])
    if folder["to_validate"].enabled:
        folder["to_validate"].enabled = False
        folder["to_validate"].reindexObject()
    col = folder["om_treating"]
    query = list(col.query)
    modif = False
    for dic in query:
        if dic["i"] == "review_state":
            for st_id in val_states:
                if st_id in dic["v"]:
                    modif = True
                    dic["v"] = [st for st in dic["v"] if st != st_id]
    if modif:
        col.query = query
    # Remove collection from template
    tmpl = site["templates"]["om"]["d-print"]
    cols = tmpl.dashboard_collections
    if val_col_uid in cols:
        cols.remove(val_col_uid)
        tmpl.dashboard_collections = cols
    # update cache
    invalidate_cachekey_volatile_for("collective.eeafaceted.collectionwidget.cachedcollectionvocabulary")
    invalidate_cachekey_volatile_for("imio.dms.mail.utils.list_wf_states.dmsoutgoingmail")
    invalidate_cachekey_volatile_for("_users_groups_value")
    # update actionspanel back transitions registry
    lst = api.portal.get_registry_record("imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions")
    lst_len = len(lst)
    for tr_id in ("back_to_{}".format(fct_id), "back_to_{}".format(val_states[0])):
        if "dmsoutgoingmail.{}|".format(tr_id) in lst:
            lst.remove("dmsoutgoingmail.{}|".format(tr_id))
    if len(lst) != lst_len:
        api.portal.set_registry_record("imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions", lst)
    # update remark states
    lst = (
        api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states", default=False
        )
        or []
    )
    for st_id in val_states:
        if st_id in lst:
            lst.remove(st_id)
    api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states", lst)
    # update state_group (use dms_config), permissions
    for brain in site.portal_catalog.unrestrictedSearchResults(portal_type="dmsoutgoingmail"):
        obj = brain._unrestrictedGetObject()
        obj.reindexObject(idxs=["allowedRolesAndUsers", "state_group"])
        for child in obj.objectValues():
            child.reindexObject(idxs=["allowedRolesAndUsers"])
    # remove wfadaptation entry
    record = api.portal.get_registry_record(RECORD_NAME)
    api.portal.set_registry_record(
        RECORD_NAME, [d for d in record if d["adaptation"] != u"imio.dms.mail.wfadaptations.OMServiceValidation"]
    )
    return "\n".join(log)


def configure_wsclient(context):
    """Configure wsclient"""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    logger.info("Configure wsclient step")
    log = ["Installing imio.pm.wsclient"]
    site.portal_setup.runAllImportStepsFromProfile("profile-imio.pm.wsclient:default")

    log.append("Defining settings")
    prefix = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings"
    if not api.portal.get_registry_record("{}.pm_url".format(prefix), default=False):
        pmurl = gedurl = os.getenv("PUBLIC_URL", "")
        pmurl = pmurl.replace("-docs", "-pm")
        if pmurl != gedurl:
            api.portal.set_registry_record("{}.pm_url".format(prefix), u"{}".format(pmurl))
        api.portal.set_registry_record("{}.pm_username".format(prefix), u"admin")
        pmpass = os.getenv("PM_PASS", "")  # not used
        if pmpass:
            api.portal.set_registry_record("{}.pm_password".format(prefix), pmpass)
        api.portal.set_registry_record("{}.only_one_sending".format(prefix), True)
        from imio.pm.wsclient.browser.vocabularies import pm_item_data_vocabulary

        orig_call = pm_item_data_vocabulary.__call__
        pm_item_data_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
            [
                SimpleTerm(u"title"),
                SimpleTerm(u"description"),
                SimpleTerm(u"detailedDescription"),
            ]
        )
        api.portal.set_registry_record(
            "{}.field_mappings".format(prefix),
            [
                {"field_name": u"title", "expression": u"context/title"},
                {
                    "field_name": u"description",
                    "expression": u"python: u'{}\\n{}'.format(context.description, "
                    u"context.restrictedTraverse('@@IncomingmailRestWSClient')"
                    u".detailed_description())",
                },
                # {'field_name': u'detailedDescription',
                #  'expression': u'context/@@IncomingmailRestWSClient/detailed_description'},
            ],
        )
        # u'string: ${context/@@ProjectWSClient/description}<br />${context/@@ProjectWSClient/detailed_description}'
        pm_item_data_vocabulary.__call__ = orig_call
        # api.portal.set_registry_record('{}.user_mappings'.format(prefix),
        #                                [{'local_userid': u'admin', 'pm_userid': u'dgen'}])
        from imio.pm.wsclient.browser.vocabularies import pm_meeting_config_id_vocabulary

        orig_call = pm_meeting_config_id_vocabulary.__call__
        pm_meeting_config_id_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
            [SimpleTerm(u"meeting-config-college")]
        )
        from imio.dms.mail.subscribers import wsclient_configuration_changed
        from plone.registry.interfaces import IRecordModifiedEvent

        gsm = getGlobalSiteManager()
        gsm.unregisterHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
        api.portal.set_registry_record(
            "{}.generated_actions".format(prefix),
            [
                {
                    "pm_meeting_config_id": u"meeting-config-college",
                    "condition": u"python: context.getPortalTypeName() in ('dmsincomingmail', 'dmsincoming_email')",
                    "permissions": "Modify view template",
                }
            ],
        )
        api.portal.set_registry_record("{}.viewlet_display_condition".format(prefix), u"isLinked")
        pm_meeting_config_id_vocabulary.__call__ = orig_call
        gsm.registerHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
    [logger.info(msg) for msg in log]
    return "\n".join(log)


def configure_demo_site(context):
    """Configure demo site"""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    # change workflow of Document type to intranet_workflow, so the page can be published
    logger.info("Configure demo site")
    site.portal_workflow.setChainForPortalTypes(['Document'], ('intranet_workflow',))

    # add a default home page on portal root
    if "demo-front-page" not in site.objectIds():
        page = api.content.create(
            type="Document",
            title=u"Accueil démo de la gestion du courrier 3.1",
            id="demo-front-page",
            container=site,
            text=u"""
<p>L'application contient actuellement les <strong>fonctionnalités suivantes</strong>:</p>
<ul>
<li>Création d'une fiche courrier entrant
<ul>
<li>automatiquement après avoir scanné les courriers papier, avec un code barre séparateur collé sur la première page
de chaque courrier</li>
<li>automatiquement après transfert autonome d'un email depuis un boîte générale ou transfert manuel</li>
<li>manuellement avec la possibilité d'associer ensuite un document scanné</li>
</ul>
</li>
<li>Création d'une fiche courrier sortant
<ul>
<li>en réponse à un (ou plusieurs) courrier entrant avec reprise des données encodées sur l'entrant</li>
<li>manuellement avec la possibilité d'associer ensuite un document au format bureautique qui peut être généré à partir
d’un modèle prédéfini</li>
<li>automatiquement après avoir scanné des courriers, avec un code barre séparateur (par exemple un courrier généré par
une autre application, déjà imprimé et signé)</li>
</ul>
</li>
<li>Signature électronique en lot des courriers sortants et/ou d'annexes, avec approbation préalable</li>
<li>Envoi possible d'un courrier sortant par email (avec pièces jointes, signature dynamique et modèle de message)</li>
<li>Gestion d'un arbre de classement (pour la classification)</li>
<li>Intégration d'une gestion de dossiers (avec les notions de farde et chemise), permettant de regrouper les courriers
d'un dossier</li>
<li>L'utilisation d'un modèle de courrier sortant a comme avantage de gérer automatiquement la fusion de données,
l'impression en lot, l'intégration d'un code-barre, le publipostage</li>
<li>Le code barre intégré dans le courrier sortant généré permet d’effectuer un scan des documents après signature
manuscrite.</li>
<li>Workflow de validation configurable (de n+1 à n+5) et variable suivant les services</li>
<li>Lien avec iA.Delib: création d'un point depuis une fiche courrier</li>
<li>etc.</li>
</ul>
<p>&nbsp;</p>
<h2>Explications démo</h2>
<p>Il est possible dans cette démo de vous connecter avec les <strong>profils suivants</strong> (tous les utilisateurs
ont le mot de passe "<strong>courrier</strong>"):</p>
<ul>
<li>Une personne pouvant encoder le courrier entrant et le courrier sortant scanné. Le nom d'utilisateur est
"<strong>encodeur</strong>".</li>
<li>Le directeur général (qui va valider le courrier en premier). Le nom d'utilisateur est "<strong>dirg</strong>".</li>
<li>Le chef de service (qui va valider le courrier ensuite). Le nom d'utilisateur est "<strong>chef</strong>".</li>
<li>L'agent du service concerné qui va pouvoir gérer le courrier. Le nom d'utilisateur est "<strong>agent</strong>".
</li>
</ul>
<p>&nbsp;</p>
<p>Remarque: par facilité dans la démo, les utilisateurs "chef" et "agent" peuvent gérer les courriers de tous les
services sélectionnables.</p>
<p>&nbsp;</p>
<p>La <a href="https://docs.imio.be/iadocs/" target="_blank">documentation complète</a> est disponible en ligne: elle
comprend les nouveautés de la version 3.1.</p>
""")
        page.setPresentation(False)
        page.setExcludeFromNav(True)
        site.setDefaultPage("demo-front-page")
        do_transitions(page, ["publish_internally", "publish_externally"])
        # exclude front-page from nav
        site["front-page"].setExcludeFromNav(True)
        site["front-page"].reindexObject()

    # Add an help document
    if "aide" not in site.objectIds():
        page = api.content.create(
            type="Document",
            title=u"AIDE",
            id="aide",
            container=site,
            text=u"""
<p><strong>Connexion</strong></p>
<p>Connectez-vous suivant le profil expliqué en page d'accueil</p>
<p>&nbsp;</p>
<p><strong>Ligne de conduite pour le courrier entrant (en tant qu'encodeur):</strong></p>
<ol>
<li>Cliquer sur l'onglet "Courrier entrant"</li>
<li>Cliquer sur le lien "Simulation scanner" pour simuler l'importation automatique du courrier via les scanners.</li>
<li>Ou cliquer sur le lien "Simulation transfert email" pour simuler le transfert d'un email par un agent ou via une
boîte générale</li>
<li>Cliquer sur l'intitulé du courrier nouvellement créé pour éditer les données.</li>
</ol>
<p>OU</p>
<ol>
<li>Ajouter un courrier entrant ou un email entrant via l'icône affichée à droite de l'intitulé "Courriers entrants"
du menu.</li>
<li>Ajouter ensuite une pièce jointe.</li>
</ol>
<p>&nbsp;</p>
<p><strong>Ligne de conduite pour le courrier sortant:</strong></p>
<p>En tant qu'agent:</p>
<ol>
<li>Cliquer sur le bouton "Répondre" à partir d'un courrier entrant</li>
<li>Ajouter ensuite un document depuis un modèle (nécessite des outils installés localement) ou Ajouter un
"fichier ged" à partir du menu d'ajout</li>
</ol>
<p>OU</p>
<ol>
<li>Cliquer sur l'onglet "Courrier sortant"</li>
<li>Ajouter un courrier sortant via l'icône affichée à droite de l'intitulé "Courriers sortants" du menu.</li>
<li>Ajouter ensuite un document depuis un modèle (nécessite des outils installés localement) ou Ajouter un
"fichier ged" à partir du menu d'ajout</li>
</ol>
<p>OU</p>
<p>En tant qu'encodeur</p>
<ol>
<li>Cliquer sur l'onglet "Courrier sortant"</li>
<li>Cliquer sur le lien "Simulation scanner" pour simuler l'importation automatique du courrier via les scanners.</li>
<li>Cliquer sur l'intitulé du courrier nouvellement créé pour éditer les données.</li>
</ol>
<p>&nbsp;</p>
<p>Pour les emails, si on choisit "email" dans le champ forme d'envoi, un bouton complémentaire apparaît pour compléter
les informations d'envoi d'un email et il est possible alors de l'envoyer dans une seconde étape.</p>
<p>&nbsp;</p>
<p><strong>Manuel d'utilisation</strong></p>
<p>La <a href="https://docs.imio.be/iadocs" target="_blank">documentation complète</a> est disponible en ligne.</p>
"""
        )
        page.setPresentation(False)
        do_transitions(page, ["publish_internally", "publish_externally"])

    # Add a content type portlet on Document type (to display on demo-front-page
    left_column = getUtility(IPortletManager, name="plone.leftcolumn")
    content_type_category = left_column[CONTENT_TYPE_CATEGORY]
    if "Document" not in content_type_category:
        content_type_category["Document"] = PortletAssignmentMapping(
            manager="plone.leftcolumn",
            category=CONTENT_TYPE_CATEGORY,
            name="Document"
        )
    mapping = content_type_category["Document"]
    if "aide" not in mapping:
        portlet = StaticAssignment(
            header=u"AIDE",
            text=u"""
<p>&nbsp;</p>
<p><strong>Connexion</strong></p>
<p>Connectez-vous suivant le profil expliqué en page d'accueil</p>
<p><strong>Explications sommaires</strong></p>
<p>Ouvrir le <a href="./aide">document d'aide</a> pour avoir une ligne de conduite rapide dans le site de démo.</p>
""",
            omit_border=False
        )
        mapping["aide"] = portlet

    # Add external methods
    if "import_scanned" not in site.objectIds():
        manage_addExternalMethod(site, "import_scanned", "", "imio.dms.mail.demo", "import_scanned")
    if "import_scanned2" not in site.objectIds():
        manage_addExternalMethod(site, "import_scanned2", "", "imio.dms.mail.demo", "import_scanned2")

    # Add object_portlet actions to be displayed in "divers" portlet
    category = site.portal_actions.object_portlet
    if "scanner_im" not in category.objectIds():
        action = Action(
            "scanner_im",
            title="Simulation scanner",
            i18n_domain="imio.dms.mail",
            url_expr="string:${globals_view/navigationRootUrl}/import_scanned",
            available_expr="python:context.getId() == 'incoming-mail' or (context.getId() == 'mail-searches' and "
                           "context.aq_parent.getId() == 'incoming-mail')",
            permissions=("collective.dms.batchimport: Batch import",),
            visible=True,
        )
        category._setObject("scanner_im", action)
    if "scanner_iem" not in category.objectIds():
        action = Action(
            "scanner_iem",
            title="Simulation transfert email",
            i18n_domain="imio.dms.mail",
            url_expr="string:${globals_view/navigationRootUrl}/import_scanned?ptype=dmsincoming_email",
            available_expr="python:context.getId() == 'incoming-mail' or (context.getId() == 'mail-searches' and "
                           "context.aq_parent.getId() == 'incoming-mail')",
            permissions=("collective.dms.batchimport: Batch import",),
            visible=True,
        )
        category._setObject("scanner_iem", action)
    if "scanner_om" not in category.objectIds():
        action = Action(
            "scanner_om",
            title="Simulation scanner",
            i18n_domain="imio.dms.mail",
            url_expr="string:${globals_view/navigationRootUrl}/import_scanned2",
            available_expr="python:context.getId() == 'outgoing-mail' or (context.getId() == 'mail-searches' and "
                           "context.aq_parent.getId() == 'outgoing-mail')",
            permissions=("collective.dms.batchimport: Batch import",),
            visible=True,
        )
        category._setObject("scanner_om", action)

    # Add N+1 validation
    applied_adaptations = [dic["adaptation"] for dic in get_applied_adaptations()
                           if dic["workflow"] == "outgoingmail_workflow"]
    if u"imio.dms.mail.wfadaptations.OMServiceValidation" not in applied_adaptations:
        site.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-im_n_plus_1_wfadaptation", run_dependencies=False
        )
        site.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-om_n_plus_1_wfadaptation", run_dependencies=False
        )
        site.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-task_n_plus_1_wfadaptation", run_dependencies=False
        )

    # activate signing
    rk = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
    signer_rules = deepcopy(api.portal.get_registry_record(rk, default=[]))
    pf = site["contacts"]["personnel-folder"]
    if not site.portal_quickinstaller.isProductInstalled("imio.esign"):
        site.portal_setup.runImportStepFromProfile(
            "profile-imio.dms.mail:singles", "imiodmsmail-activate-esigning", run_dependencies=False
        )
        set_registry_vat_number(u"BE0000000097")
        set_registry_file_url("https://fileserver.files.be")
        set_registry_seal_code(u"PADES_SEAL")
        set_registry_seal_email(u"sceau@imio.be")
        # set_registry_sign_code(u"BULK_VISA")

        activated_orgs = get_registry_organizations()
        for dic in signer_rules:
            dic["esign"] = True
            dic["approvings"] = [u"_themself_"]
            dic["treating_groups"] = activated_orgs
            dic["tal_condition"] = u"python: member.getId() in ('admin', 'agent', 'agent1', 'chef', 'dirg')"
        api.portal.set_registry_record(rk, signer_rules)

    # Change user passwords to 'courrier'
    for userid in ("agent", "agent1", "chef", "dirg", "encodeur", "lecteur"):
        site.acl_users.source_users.userSetPassword(userid, "courrier")

    # remove dirg from watchers group
    if "dirg" in api.user.get_users(groupname="esign_watchers"):
        api.group.remove_user(groupname="esign_watchers", user="dirg")

    # Added some users from a configuration csv file
    username = os.getenv("USER", "zope")
    home_dir = pwd.getpwnam(username).pw_dir
    filename = os.path.join(home_dir, "demo_docs_users.csv")
    sr_len = len(signer_rules)
    user_ids = ["agent", "agent1", "chef", "dirg", "encodeur"]
    logger.info("Loading users file: '{}' ?".format(filename))
    if os.path.exists(filename):
        pgo = site["contacts"]["plonegroup-organization"]
        groups_data = api.group.get_groups()
        groups = [(gd.id, safe_encode(gd.getProperty("title"))) for gd in groups_data]
        for columns in read_csv(filename, strip_chars=" ", replace_dq=True, skip_empty=True, skip_lines=1):
            (u_id, fullname, email, group_titles, esign, pswd) = columns
            user = api.user.get(userid=u_id)
            if user is None:
                user = api.user.create(
                    username=u_id,
                    email=safe_encode(email),
                    password=safe_encode(pswd),
                    properties={"fullname": safe_encode(fullname)},
                )
            user_ids.append(safe_encode(u_id))
            if group_titles:
                for group_title in group_titles.split("\n"):
                    for (g_id, title) in groups:
                        if title == safe_encode(group_title):
                            if u_id not in api.user.get_users(groupname=g_id):
                                api.group.add_user(groupname=g_id, user=user)
                            break
                    else:
                        logger.warning("Group with title '{}' not found.".format(safe_encode(group_title)))
            if esign and "\n" in esign:
                parts = esign.split("\n")
                own_service = None
                if len(parts) == 2:
                    (org_path, usages) = parts
                elif len(parts) == 3:
                    (org_path, usages, own_service_path) = parts
                    try:
                        own_service = pgo.restrictedTraverse(own_service_path)
                    except KeyError:
                        own_service = None
                    if not own_service:
                        parent = pgo.restrictedTraverse("/".join(own_service_path.split("/")[:-1]))
                        oid = own_service_path.split("/")[-1]
                        oid = parent.invokeFactory(
                            "organization",
                            oid,
                            title=oid.upper(),
                            organization_type=u"service",
                        )
                        own_service = parent[oid]
                        activated_orgs = get_registry_organizations()
                        if parent.UID() in activated_orgs:
                            pos = activated_orgs.index(parent.UID())
                            activated_orgs.insert(pos + 1, own_service.UID())
                        else:
                            activated_orgs.append(parent.UID())
                        set_registry_organizations(activated_orgs)

                    for suffix in ("editeur", "encodeur"):
                        api.group.add_user(groupname="{}_{}".format(own_service.UID(), suffix), user=user)
                        for userid in ("agent", "chef"):
                            api.group.add_user(groupname="{}_{}".format(own_service.UID(), suffix), username=userid)
                else:
                    raise ValueError("Invalid esign value for user '{}': '{}'".format(u_id, esign))

                usages_list = [u.strip().lower() for u in usages.split(",")]
                org_uid = pgo.restrictedTraverse(org_path).UID()
                hp = pf[u_id][org_uid]
                hp.usages = usages_list
                hp.reindexObject()
                if "signer" in usages_list:
                    if hp.UID() not in [dic["signer"] for dic in signer_rules]:
                        signer_rules.append(
                            {
                                "number": 1,
                                "signer": hp.UID(),
                                "editor": False,
                                "approvings": [u"_themself_"],
                                "esign": True,
                                "valid_from": None,
                                "valid_until": None,
                                "treating_groups": [],
                                "mail_types": [],
                                "send_modes": [],
                                "tal_condition": u"python: member.getId() == '{}'".format(u_id),
                            },
                        )
                    if (own_service and not [rule for rule in signer_rules
                                             if rule["signer"] == hp.UID()
                                             and rule["treating_groups"] == [own_service.UID()]]):
                        signer_rules.insert(
                            0,
                            {
                                "number": 1,
                                "signer": hp.UID(),
                                "editor": True,
                                "approvings": [u"_themself_"],
                                "esign": True,
                                "valid_from": None,
                                "valid_until": None,
                                "treating_groups": [own_service.UID()],
                                "mail_types": [],
                                "send_modes": [],
                                "tal_condition": u"",
                            },
                        )
        if len(signer_rules) > sr_len:
            api.portal.set_registry_record(rk, signer_rules)
            update_approvers_settings()

    # Configure delib link
    prefix = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings"
    if not api.portal.get_registry_record("{}.pm_password".format(prefix), default=False):
        api.portal.set_registry_record("{}.pm_url".format(prefix), u"https://demo-pm.imio.be")
        api.portal.set_registry_record("{}.pm_username".format(prefix), u"docs_delib")
        pmpass = os.getenv("PM_PASS", "")  # not used
        if pmpass:
            api.portal.set_registry_record("{}.pm_password".format(prefix), pmpass)
        api.portal.set_registry_record("{}.only_one_sending".format(prefix), False)
        from imio.pm.wsclient.browser.vocabularies import pm_item_data_vocabulary

        orig_call = pm_item_data_vocabulary.__call__
        pm_item_data_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
            [
                SimpleTerm(u"title"),
                SimpleTerm(u"description"),
                SimpleTerm(u"detailedDescription"),
                SimpleTerm(u"ignore_validation_for"),
            ]
        )
        api.portal.set_registry_record(
            "{}.field_mappings".format(prefix),
            [
                {"field_name": u"title", "expression": u"context/title"},
                {"field_name": u"description", "expression": u"context/Description"},
                {
                    "field_name": u"detailedDescription",
                    "expression": u"python: u'{}\\n{}'.format(context.description, "
                    u"context.restrictedTraverse('@@IncomingmailRestWSClient')"
                    u".detailed_description())",
                },
                {"field_name": u"ignore_validation_for", "expression": u"string:groupsInCharge"},
            ],
        )
        pm_item_data_vocabulary.__call__ = orig_call
        api.portal.set_registry_record("{}.user_mappings".format(prefix),
                                       [{"local_userid": safe_unicode(u_id), "pm_userid": u"dgen"}
                                        for u_id in user_ids])
        from imio.pm.wsclient.browser.vocabularies import pm_meeting_config_id_vocabulary

        orig_call = pm_meeting_config_id_vocabulary.__call__
        terms = [SimpleTerm(u"meeting-config-college"), SimpleTerm(u"meeting-config-council"),
                 SimpleTerm(u"bourgmestre")]
        pm_meeting_config_id_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(terms)
        from imio.dms.mail.subscribers import wsclient_configuration_changed
        from plone.registry.interfaces import IRecordModifiedEvent

        gsm = getGlobalSiteManager()
        gsm.unregisterHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))
        api.portal.set_registry_record(
            "{}.generated_actions".format(prefix),
            [
                {
                    "pm_meeting_config_id": term.value,
                    "condition": u"python: context.getPortalTypeName() in ('dmsincomingmail', 'dmsincoming_email')",
                    "permissions": "Modify view template",
                } for term in terms
            ],
        )
        pm_meeting_config_id_vocabulary.__call__ = orig_call
        gsm.registerHandler(wsclient_configuration_changed, (IRecordModifiedEvent,))

    # Add demo contacts in contact folder
    params = {
        "lastname": u"Kordi",
        "firstname": u"Annie",
        "gender": u"F",
        "person_title": u"Madame",
        "zip_code": u"5032",
        "city": u"Isnes",
        "street": u"Rue du Yoyo",
        "number": u"1",
        "email": u"tata_yoyo@gmail.com",
        "use_parent_address": False,
    }
    if "anniekordi" not in site.contacts:
        site.contacts.invokeFactory("person", "anniekordi", **params)
        anniekordi = site.contacts["anniekordi"]
        # add a namedimage on the photo field
        image_path = os.path.join(PRODUCT_DIR, "profiles", "examples", "images", "Annie_Kordi.jpg")
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
        named_image = NamedImage(data=image_data, filename=u"Annie_Kordi.jpg", contentType="image/jpeg")
        anniekordi.photo = named_image
        anniekordi.reindexObject()

    params = {
        "title": u"IMIO",
        "organization_type": u"sa",
        "zip_code": u"5032",
        "city": u"Isnes",
        "street": u"Rue Léon Morel",
        "number": u"1",
        "email": u"contak@imio.be",
        "use_parent_address": False,
    }
    if "imio" not in site.contacts:
        site.contacts.invokeFactory("organization", "imio", **params)

    # Add mailhost config
    mailhost = get_mail_host(check=False)
    if not mailhost.smtp_host:
        mailhost.smtp_host = "localhost"
        site.email_from_name = "Gestion courrier 3.1"
        site.email_from_address = "support-docs@imio.be"


def contact_import_pipeline(context):
    """Set contact import pipeline record."""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info("Set contact import pipeline")
    api.portal.set_registry_record(
        "collective.contact.importexport.interfaces.IPipelineConfiguration.pipeline",
        u"""[transmogrifier]
pipeline =
    initialization
    csv_disk_source
#    csv_ssh_source
    csv_reader
    common_input_checks
    plonegrouporganizationpath
    plonegroupinternalparent
#    iadocs_inbw_subtitle
    dependencysorter
#    stop
    relationsinserter
    updatepathinserter
    parentpathinserter
    moveobject
    pathinserter
#    iadocs_inbw_merger
    constructor
    iadocs_userid
#    iadocs_creating_group
    schemaupdater
    reindexobject
    transitions_inserter
    workflowupdater
    breakpoint
    short_log
#    logger
    lastsection

# mandatory section !
[config]
# needed if contact encoding group is enabled in Plone
creating_group =
# if empty, first found directory is used. Else relative path in portal
directory_path =
csv_encoding = utf8
# needed if plone-group organization is imported
plonegroup_org_title =
organizations_filename =
organizations_fieldnames = _id _oid title description organization_type use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country enterprise_number internal_number _uid _ic
persons_filename =
persons_fieldnames = _id lastname firstname gender person_title birthday use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country internal_number _uid _ic
held_positions_filename =
held_positions_fieldnames = _id _pid _oid _fid label start_date end_date use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country internal_number _uid _ic
raise_on_error = 1

[initialization]
blueprint = collective.contact.importexport.init
# basepath is an absolute directory. If empty, buildout dir will be used
basepath =
# if subpath, it will be appended to basepath
subpath = imports

[csv_disk_source]
blueprint = collective.contact.importexport.csv_disk_source
organizations_filename = ${config:organizations_filename}
persons_filename = ${config:persons_filename}
held_positions_filename = ${config:held_positions_filename}

[csv_ssh_source]
blueprint = collective.contact.importexport.csv_ssh_source
servername = sftp-client.imio.be
username =
server_files_path = .../upload_success
registry_filename = 0_registry.dump
transfer_path = copied

[csv_reader]
blueprint = collective.contact.importexport.csv_reader
fmtparam-strict = python:True
# fmtparam-delimiter = python:';'
csv_headers = python:True
raise_on_error = ${config:raise_on_error}

[common_input_checks]
blueprint = collective.contact.importexport.common_input_checks
phone_country = BE
language = fr
organization_uniques = _uid internal_number
organization_booleans = use_parent_address _ic _inactive
organization_hyphen_newline = title street
person_uniques = _uid internal_number
person_booleans = use_parent_address _ic _inactive
held_position_uniques = _uid
held_position_booleans = use_parent_address _ic _inactive
raise_on_error = ${config:raise_on_error}

[plonegrouporganizationpath]
blueprint = imio.transmogrifier.contact.plonegrouporganizationpath
plonegroup_org_title = ${config:plonegroup_org_title}

[plonegroupinternalparent]
blueprint = imio.transmogrifier.contact.plonegroupinternalparent

[iadocs_inbw_subtitle]
blueprint = imio.transmogrifier.contact.iadocs_inbw_subtitle_updater

[dependencysorter]
blueprint = collective.contact.importexport.dependencysorter

[relationsinserter]
blueprint = collective.contact.importexport.relationsinserter
raise_on_error = ${config:raise_on_error}

[updatepathinserter]
blueprint = collective.contact.importexport.updatepathinserter
# list of 'column' 'index name' 'item condition' 'must-exist' quartets used to search in catalog for an existing object
organization_uniques = _uid UID python:True python:True internal_number internal_number python:True python:False
person_uniques = _uid UID python:True python:True internal_number mail_type python:item['_ic'] python:False internal_number internal_number python:True python:False
held_position_uniques = _uid UID python:True python:True
raise_on_error = ${config:raise_on_error}

[parentpathinserter]
blueprint = collective.contact.importexport.parentpathinserter
raise_on_error = ${config:raise_on_error}

[moveobject]
blueprint = collective.contact.importexport.moveobject
raise_on_error = ${config:raise_on_error}

[pathinserter]
blueprint = collective.contact.importexport.pathinserter
organization_id_keys = title
person_id_keys = firstname lastname
held_position_id_keys = label
raise_on_error = ${config:raise_on_error}

[iadocs_inbw_merger]
blueprint = imio.transmogrifier.contact.iadocs_inbw_merger
raise_on_error = ${config:raise_on_error}

[constructor]
blueprint = collective.transmogrifier.sections.constructor

[iadocs_userid]
blueprint = imio.transmogrifier.contact.iadocs_userid_inserter
raise_on_error = ${config:raise_on_error}

[iadocs_creating_group]
blueprint = imio.transmogrifier.contact.iadocs_creating_group_inserter
creating_group = ${config:creating_group}

[schemaupdater]
blueprint = transmogrify.dexterity.schemaupdater

[reindexobject]
blueprint = plone.app.transmogrifier.reindexobject

[transitions_inserter]
blueprint = collective.contact.importexport.transitions_inserter

[workflowupdater]
blueprint = plone.app.transmogrifier.workflowupdater

[short_log]
blueprint = collective.contact.importexport.short_log

[lastsection]
blueprint = collective.contact.importexport.lastsection
send_mail = 1

[logger]
blueprint = collective.transmogrifier.sections.logger
name = logger
level = INFO
delete =
    _oid
    title
    description
    organization_type
    use_parent_address
    street
    number
    additional_address_details
    zip_code
    city
    phone
    cell_phone
    fax
    email
    website
    region
    country
    internal_number
    _uid
    _ic
    lastname
    firstname
    gender
    person_title
    birthday
    _pid
    _fid
    label
    start_date
    end_date
    position
    userid
    _files
    _level
    _ln
    _parent
    _typ

[breakpoint]
blueprint = collective.contact.importexport.breakpoint
condition = python:item.get('_id', u'') == u'0'

[stop]
blueprint = collective.contact.importexport.stop
condition = python:True
""",  # noqa: E501
    )
