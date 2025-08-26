# encoding: utf-8
from BTrees.OOBTree import OOBTree  # noqa
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.documentviewer.convert import Converter
from collective.documentviewer.convert import saveFileToBlob
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.collectionwidget.utils import getCurrentCollection
from collective.querynextprev.interfaces import INextPrevNotNavigable
from datetime import date
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from ftw.labels.interfaces import ILabeling
from imio.dms.mail import _tr as _
from imio.dms.mail import ALL_SERVICE_FUNCTIONS
from imio.dms.mail import AUC_RECORD
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import MAIN_FOLDERS
from imio.dms.mail import PERIODS
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.interfaces import IProtectedItem
from imio.helpers.batching import batch_delete_files
from imio.helpers.batching import batch_get_keys
from imio.helpers.batching import batch_handle_key
from imio.helpers.batching import batch_hashed_filename
from imio.helpers.batching import batch_loop_else
from imio.helpers.batching import batch_skip_key
from imio.helpers.batching import can_delete_batch_files
from imio.helpers.cache import generate_key
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.cache import obj_modified
from imio.helpers.content import object_values
from imio.helpers.content import uuidToObject
from imio.helpers.security import check_zope_admin
from imio.helpers.workflow import do_transitions
from imio.helpers.xhtml import object_link
from interfaces import IIMDashboard
from natsort import natsorted
from operator import attrgetter
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from plone.api.exc import GroupNotFoundError
from plone.dexterity.utils import addContentToContainer
from plone.i18n.normalizer import IIDNormalizer
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from plone.z3cform.fieldsets.utils import add
from plone.z3cform.fieldsets.utils import remove
from Products.CMFPlone.interfaces import IHideFromBreadcrumbs
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import fileSize
from Products.CPUtils.Extensions.utils import log_list
from Products.Five import BrowserView
from unidecode import unidecode
from z3c.relationfield import RelationValue
from zc.relation.interfaces import ICatalog
from zExceptions import Redirect
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.interface import alsoProvides
from zope.intid import IIntIds
from zope.schema.interfaces import IVocabularyFactory

import logging
import os


cg_separator = " ___ "
PREVIEW_DIR = os.path.join(PRODUCT_DIR, "base_images")

# methods

logger = logging.getLogger("imio.dms.mail: utils")

"""
dms_config
----------
(not the default values! but possible values to illustrate)
# états précédant/suivant un autre et transitions pour y accéder. Utilisé dans can_do_transition et wf_adaptations
* ['wf_from_to']
    * ['dmsincomingmail', 'n_plus', 'from'] = [('created', 'back_to_creation'),
                                               ('proposed_to_manager', 'back_to_manager')]
    * ['dmsincomingmail', 'n_plus', 'to'], [('closed', 'close'), ('proposed_to_agent', 'propose_to_agent')])
    * ['dmsoutgoingmail', 'n_plus', 'from'], [('created', 'back_to_creation')])
    * ['dmsoutgoingmail', 'n_plus', 'to'], [('sent', 'mark_as_sent'), ('to_be_signed', 'propose_to_be_signed')])
* ['review_levels'] : sert à déterminer le niveau de validation d'un utilisateur suivant son groupe
    * ['dmsincomingmail'] = OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                         ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})])
    * ['task'] = OrderedDict([('_n_plus_1', {'st': ['to_assign', 'realized'], 'org': 'assigned_group'})])
    * ['dmsoutgoingmail'] = OrderedDict([('_n_plus_1', {'st': ['proposed_to_n_plus_1'],
                                                        'org': 'treating_groups'})])
* ['review_states'] : pour l'index state_group, lié à la validation
    * ['dmsincomingmail'] = OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),
                                         ('proposed_to_n_plus_1', {'group': ['_n_plus_1'], 'org': 'treating_groups'})])
    * ['task'] = OrderedDict([('to_assign', {'group': '_n_plus_1', 'org': 'assigned_group'}),
                                ('realized', {'group': '_n_plus_1', 'org': 'assigned_group'})])
    * ['dmsoutgoingmail'] = OrderedDict([('proposed_to_n_plus_1', {'group': '_n_plus_1', 'org': 'treating_groups'})])
* ['transitions_auc'] : indique si les transitions propose_to_agent ou propose_to_n_plus_x peuvent être effectuées en
                        fonction du paramètre assigned_user_check. (close toujours)
    * ['dmsincomingmail'][transition] = {'org1': True, 'org2': False}
* ['transitions_levels'] : indique les transitions valides (avant, arrière, n+_users) par état en fonction de la
                           présence des validateurs. (n+_users indique si le groupe a des utilisateurs pour cet état)
    * ['dmsincomingmail'][state] = {'org1': ('propose_to_n_plus_1', 'from_states', False), 'org2': (...) }
    ('from_states' est une valeur spéciale qui représente les transitions stockées dans from_states)
"""


def set_dms_config(keys=None, value="list", force=True):
    """
    Set initial value in 'imio.dms.mail' portal annotation.
    keys is the chain of annotation keys. First key 'imio.dms.mail' is implicitly added.
    Intermediate keys will contain PersistentDict.
    Last key will contain PersistentDict or PersistentList following 'value' parameter:
    'dict', 'list' or directly value
    """
    annot = IAnnotations(api.portal.get())
    if keys is None:
        keys = []
    keys.insert(0, "imio.dms.mail")
    last = len(keys) - 1
    for i, key in enumerate(keys):
        if i < last:
            annot = annot.setdefault(key, PersistentDict())
        else:
            if force or key not in annot:
                if value == "list":
                    annot[key] = PersistentList()
                elif value == "dict":
                    annot[key] = PersistentDict()
                else:
                    annot[key] = value
            return annot[key]


def get_dms_config(keys=None, missing_key_handling=False, missing_key_value=None):
    """
    Return annotation value from keys list.
    First key 'imio.dms.mail' is implicitly added.
    """
    annot = IAnnotations(api.portal.get())
    if keys is None:
        keys = []
    keys.insert(0, "imio.dms.mail")
    for key in keys:
        if missing_key_handling and key not in annot:
            return missing_key_value
        annot = annot[key]
    return annot


def ensure_set_field(obj, fieldname, value=None, replace_none=False):
    """Ensure a field is set on the object. Otherwise the defaut is used in getattr.

    :param obj: object
    :param fieldname: fieldname
    :param value: value
    :param replace_none: if True, replace value if it's None
    :return: bool indicating change
    """
    if fieldname not in obj.__dict__ or (replace_none and getattr(obj, fieldname) is None):
        setattr(obj, fieldname, value)
        return True
    return False


def group_has_user(groupname, action=None):
    """Check if group contains user

    :param groupname: group id
    :param action: None or group 'delete', group user 'add' or group user 'remove'
    :return: bool
    """
    try:
        # group is deleted
        if action == "delete":
            return False
        users_len = len(api.user.get_users(groupname=groupname))
        if action == "remove" and users_len == 1:
            return False
        elif action == "add" and users_len == 0:
            return True
        elif users_len:
            return True
    except GroupNotFoundError:
        return False
    return False


def update_transitions_levels_config(ptypes, action=None, group_id=None):
    """Set transitions_levels dms config following org group users:
    [ptype][state][org] = (valid_propose_to, valid_back_to, n_plus_users)

    :param ptypes: portal types
    :param action: useful on group assignment event. Can be 'add', 'remove', 'delete'
    :param group_id: new group assignment
    """
    orgs = get_registry_organizations()
    users_in_groups = {}  # boolean by groupname

    def check_group_users(g_n, u_in_g, g_id, act):
        if g_n not in u_in_g:
            u_in_g[g_n] = group_has_user(g_n, action=(g_n == g_id and act or None))
        return u_in_g[g_n]

    if "dmsincomingmail" in ptypes:  # i_e ok
        wf_from_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus"])  # i_e ok
        states = []
        max_level = 0
        for i, (st, tr) in enumerate(wf_from_to["to"], start=-1):  # 2 values before n+ (closed, proposed_to_agent)
            states.append((st, i))
            max_level = i
        # states: [('closed', -1), ('proposed_to_agent', 0), ('proposed_to_n_plus_1', 1)]
        states += [(st, 9) for (st, tr) in wf_from_to["from"]]
        states.reverse()
        # states: [('proposed_to_manager', 9), ('created', 9), ('proposed_to_n_plus_1', 1), ('proposed_to_agent', 0),
        #          ('closed', -1)]
        state9 = ""
        orgs_back = {}  # last valid back transition by org

        for state, level in states:
            start = level - 1
            if level == 9:  # from states
                start = max_level  # max n+ level from 1 to 5
            # for states before validation levels, we copy the first one
            if level == 9 and state9:
                set_dms_config(
                    ["transitions_levels", "dmsincomingmail", state],  # i_e ok
                    get_dms_config(["transitions_levels", "dmsincomingmail", state9]),
                )  # i_e ok
                continue
            config = {}
            for org in orgs:
                propose_to = "propose_to_agent"
                back_to = orgs_back.setdefault(org, "from_states")
                # check all lower levels to find first valid propose_to transition
                for lev in range(start, 0, -1):
                    # level 9: range(0, 0, -1) => [] ; range(1, 0, -1) => [1] ; etc.
                    # level 1: range(0, 0, -1) => [] ; level 2: range(1, 0, -1) => [1] ; etc.
                    # level 0, -1: range(-1, 0, -1) => []
                    if check_group_users("{}_n_plus_{}".format(org, lev), users_in_groups, group_id, action):
                        propose_to = "propose_to_n_plus_{}".format(lev)
                        break
                n_plus_users = None
                if state.startswith("proposed_to_n_plus_"):
                    n_plus_users = check_group_users(
                        "{}_n_plus_{}".format(org, level), users_in_groups, group_id, action
                    )
                config[org] = (propose_to, back_to, n_plus_users)
                if level != 9 and users_in_groups.get("{}_n_plus_{}".format(org, level), False):
                    orgs_back[org] = "back_to_n_plus_{}".format(level)

            set_dms_config(["transitions_levels", "dmsincomingmail", state], config)  # i_e ok
            if level == 9 and not state9:
                state9 = state

    if "dmsoutgoingmail" in ptypes:
        wf_from_to = get_dms_config(["wf_from_to", "dmsoutgoingmail", "n_plus"])
        states = [("created", 0)]
        for (st, tr) in wf_from_to["to"]:
            states.append((st, 1))
        # states: [('created', 0), ('sent', 1), ('to_be_signed', 1), ('validated', 1)]
        right_transitions = ("propose_to_n_plus_1", "back_to_n_plus_1", None)
        for st, way in states:
            config = {}
            for org in orgs:
                trs = ["", "", None]
                if check_group_users("{}_n_plus_1".format(org), users_in_groups, group_id, action):
                    trs[way] = right_transitions[way]
                config[org] = tuple(trs)
            set_dms_config(["transitions_levels", "dmsoutgoingmail", st], config)
        if "validated" in [tup[0] for tup in wf_from_to["to"]]:
            set_dms_config(
                ["transitions_levels", "dmsoutgoingmail", "proposed_to_n_plus_1"],
                {
                    org: (
                        "set_validated",
                        "",
                        check_group_users("{}_n_plus_1".format(org), users_in_groups, group_id, action),
                    )
                    for org in orgs
                },
            )

    if "task" in ptypes:
        states = (("created", 0), ("to_do", 1))
        right_transitions = ("do_to_assign", "back_in_to_assign")
        for state, way in states:
            config = {}
            for org in orgs:
                trs = {0: ["", ""], 1: ["", "back_in_created2"]}
                if check_group_users("{}_n_plus_1".format(org), users_in_groups, group_id, action):
                    trs[way][way] = right_transitions[way]
                config[org] = tuple(trs[way])
            set_dms_config(["transitions_levels", "task", state], config)


def update_transitions_auc_config(ptype, action=None, group_id=None):
    """
    Set transitions_auc dms config following assigned user check: [ptype][transition][org] = True
    :param ptype: portal type
    :param action: useful on group assignment event. Can be 'add', 'remove', 'delete'
    :param group_id: new group assignment
    """
    orgs = get_registry_organizations()
    if ptype == "dmsincomingmail":  # i_e ok
        auc = api.portal.get_registry_record(AUC_RECORD)
        wf_from_to = get_dms_config(["wf_from_to", "dmsincomingmail", "n_plus"])  # i_e ok
        transitions = [tr for (st, tr) in wf_from_to["to"]]
        previous_tr = ""
        global_config = {}
        for i, tr in enumerate(transitions, start=-1):  # -1 because close has been added in transitions
            config = {}
            for org in orgs:
                val = False
                if tr == "close":  # we can always close. assigned_user is set in subscriber
                    val = True
                elif auc == u"no_check":
                    val = True
                elif auc == u"mandatory":
                    # propose_to_agent: previous_tr is empty => val will be False
                    # propose_to_n_plus_x: lower level True => val is True
                    # propose_to_n_plus_x: lower level False and user at this level => val is True
                    groupname = "{}_n_plus_{}".format(org, i)
                    act = groupname == group_id and action or None
                    if previous_tr and (global_config[previous_tr][org] or group_has_user(groupname, action=act)):
                        val = True
                elif auc == u"n_plus_1":
                    # propose_to_agent: no n+1 level => val is True
                    # propose_to_n_plus_x: previous_tr => val is True
                    # propose_to_agent: n+1 level doesn't have user => val is True
                    groupname = "{}_n_plus_1".format(org)
                    act = groupname == group_id and action or None
                    if len(transitions) == 2 or previous_tr or not group_has_user(groupname, action=act):
                        val = True
                config[org] = val
            if tr != "close":
                previous_tr = tr
            global_config[tr] = config
            set_dms_config(["transitions_auc", "dmsincomingmail", tr], config)  # i_e ok


def highest_review_level(portal_type, group_ids):
    """Return the first review level"""
    review_levels = get_dms_config(["review_levels"])
    if portal_type not in review_levels:
        return None
    for keyg in review_levels[portal_type].keys():
        if keyg.startswith("_") and "%s'" % keyg in group_ids:
            return keyg
        elif "'%s'" % keyg in group_ids:
            return keyg
    return None


def list_wf_states_cache_key(function, context, portal_type):
    return get_cachekey_volatile("%s.%s" % (generate_key(function), portal_type))


@ram.cache(list_wf_states_cache_key)
def list_wf_states(context, portal_type):
    """
    list all portal_type wf states
    """
    ordered_states = {
        "dmsincomingmail": [
            "created",
            "proposed_to_pre_manager",
            "proposed_to_manager",  # i_e ok
            "proposed_to_n_plus_5",
            "proposed_to_n_plus_4",
            "proposed_to_n_plus_3",
            "proposed_to_n_plus_2",
            "proposed_to_n_plus_1",
            "proposed_to_agent",
            "in_treatment",
            "closed",
        ],
        "dmsincoming_email": [
            "created",
            "proposed_to_pre_manager",
            "proposed_to_manager",
            "proposed_to_n_plus_5",
            "proposed_to_n_plus_4",
            "proposed_to_n_plus_3",
            "proposed_to_n_plus_2",
            "proposed_to_n_plus_1",
            "proposed_to_agent",
            "in_treatment",
            "closed",
        ],
        "task": ["created", "to_assign", "to_do", "in_progress", "realized", "closed"],
        "dmsoutgoingmail": ["scanned", "created", "proposed_to_n_plus_1", "validated", "to_print", "to_be_signed",
                            "signed", "sent"],
        # "dmsoutgoing_email": ["scanned", "created", "proposed_to_n_plus_1", "validated", "to_print", "to_be_signed",
        #                       "signed", "sent"],
        "organization": ["active", "deactivated"],
        "person": ["active", "deactivated"],
        "held_position": ["active", "deactivated"],
        "contact_list": ["active", "deactivated"],
    }
    if portal_type not in ordered_states:
        return []
    pw = api.portal.get_tool("portal_workflow")
    ret = []
    # wf states
    states = []
    for workflow in pw.getWorkflowsFor(portal_type):
        states = {value.id: value.title for value in workflow.states.values()}
        break
    # keep ordered states
    for state in ordered_states[portal_type]:
        if state in states:
            ret.append((state, states[state]))
            del states[state]
    # add missing
    for missing in states:
        ret.append((missing, states[missing]))
    return ret


def back_or_again_state(obj, transitions=()):
    """
    p_transitions : list of back transitions
    """
    with api.env.adopt_roles(["Manager"]):
        history = obj.portal_workflow.getInfoFor(obj, "review_history")
    # action can be None if initial state or automatic transition
    # [{'action': None, 'review_state': 'created', 'comments': '', 'actor': 'admin', 'time': DateTime()}, ...]
    if transitions and history[-1]["action"] in transitions:
        return "back"
    if history[-1]["action"] and history[-1]["action"].startswith("back_"):
        return "back"
    i = 0
    last_state = history[-1]["review_state"]
    for event in history:
        if event["review_state"] == last_state:
            i = i + 1
            if i > 1:
                break
    else:
        return ""  # no break
    return "again"


def object_modified_cachekey(method, self, brain=False):
    """cachekey method for an object and his modification date."""
    return "/".join(self.getPhysicalPath()), obj_modified(self)


def get_scan_id(obj):
    """Return scan_id in multiple form"""
    sid = obj.scan_id and obj.scan_id.startswith("IMIO") and obj.scan_id[4:] or obj.scan_id
    sid_long, sid_short = "", ""
    if sid:
        sid_long = u"IMIO%s" % sid
        sid_short = len(sid) == 15 and sid[7:].lstrip("0") or sid
    return [sid, sid_long, sid_short]


def reimport_faceted_config(folder, xml, default_UID=None):  # noqa
    """Reimport faceted navigation config."""
    folder.unrestrictedTraverse("@@faceted_exportimport").import_xml(
        import_file=open(os.path.dirname(__file__) + "/faceted_conf/%s" % xml)
    )
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


def separate_fullname(user, fn_first=True, fullname=None):
    """Separate firstname and lastname from fullname"""
    if not fullname:
        fullname = safe_unicode(user.getProperty("fullname"))
    lastname = firstname = u""
    if fullname:
        parts = fullname.split()
        if len(parts) == 1:
            lastname = parts[0]
        elif len(parts) > 1:
            if fn_first:
                firstname = parts[0]
                lastname = " ".join(parts[1:])
            else:
                lastname = parts[0]
                firstname = " ".join(parts[1:])
    elif user:
        lastname = safe_unicode(user.id)
    return firstname, lastname


def dv_clean(portal, days_back="365", date_back=None):
    """Remove document viewer annotation on old mails.

    * days_back: default behavior: we take closed items not modified from this range
    * date_back: if present (YYYYMMDD), we take items not modified from this date (whatever the state)
    """
    if not check_zope_admin():
        return "You must be a zope manager to run this script"
    start = datetime.now()
    out = [
        "call the script followed by needed parameters:",
        "-> days_back=nb of days to keep (default '365') (not used if date_back is used)",
        "-> date_back=fixed date to consider (default None) (format YYYYMMDD)",
    ]
    # logger.info("Starting dv_clean at {}".format(start))
    log_list(out, "Starting dv_clean at {}".format(start), logger)
    from Products.CPUtils.Extensions.utils import dv_images_size

    normal_blob = saveFileToBlob(os.path.join(PREVIEW_DIR, "previsualisation_supprimee_normal.jpg"))
    blobs = {
        "large": normal_blob,
        "normal": normal_blob,
        "small": saveFileToBlob(os.path.join(PREVIEW_DIR, "previsualisation_supprimee_small.jpg")),
    }
    criterias = [
        {"portal_type": ["dmsincomingmail", "dmsincoming_email"]},
        {"portal_type": ["dmsoutgoingmail"]},
    ]
    state_criterias = [
        {"review_state": "closed"},
        {"review_state": "sent"},
    ]
    if date_back:
        if len(date_back) != 8:
            log_list(out, "Bad date_back length '{}'".format(date_back), logger)
            return
        mod_date = datetime.strptime(date_back, "%Y%m%d")
        # mod_date = add_timezone(mod_date, force=True)
    else:
        mod_date = start - timedelta(days=int(days_back))
    already_done = DateTime("2010/01/01").ISO8601()  # when using image saying preview has been deleted
    already_eml = DateTime("2011/01/01").ISO8601()  # when using image saying eml cannot be converted
    get_same_blob = True  # we will get previously blobs
    pc = portal.portal_catalog
    brains = []
    for j, criteria in enumerate(criterias):
        if not date_back:
            criteria.update(state_criterias[j])  # noqa
        criteria.update({"modified": {"query": mod_date, "range": "max"}, "sort_on": "created"})  # noqa
        brains.extend(pc(**criteria))

    bl = len(brains)
    pklfile = batch_hashed_filename('idm.dv_clean.pkl')
    batch_keys, batch_config = batch_get_keys(pklfile, loop_length=bl)
    total = {"obj": bl, "pages": 0, "files": 0, "size": 0}
    for brain in brains:
        if batch_skip_key(brain.UID, batch_keys, batch_config):
            continue
        mail = brain.getObject()
        for fobj in object_values(mail, ["DmsFile", "DmsAppendixFile", "ImioDmsFile"]):
            annot = IAnnotations(fobj).get("collective.documentviewer", "")
            if not annot or not annot.get("successfully_converted"):
                continue
            if annot["last_updated"] == already_done:
                if get_same_blob:
                    for name in ("large", "normal", "small"):
                        blobs[name] = annot["blob_files"]["{}/dump_1.jpg".format(name)]
                    get_same_blob = False
                continue
            if annot["last_updated"] == already_eml:
                continue
            get_same_blob = False
            total["files"] += 1
            sizes = dv_images_size(fobj)
            total["pages"] += sizes["pages"]
            total["size"] += sizes["large"] + sizes["normal"] + sizes["small"] + sizes["text"]
            # clean annotation
            files = OOBTree()
            for name in ["large", "normal", "small"]:
                files["{}/dump_1.jpg".format(name)] = blobs[name]
            annot["blob_files"] = files
            annot["num_pages"] = 1
            annot["pdf_image_format"] = "jpg"
            annot["last_updated"] = already_done
        if batch_handle_key(brain.UID, batch_keys, batch_config):
            break
    else:
        batch_loop_else(batch_keys, batch_config)

    end = datetime.now()
    delta = end - start
    # logger.info("Finishing dv_clean, duration {}".format(delta))
    log_list(out, "Finishing dv_clean, duration {}".format(delta), logger)
    total["deleted"] = total["pages"] * 4
    total["size"] = fileSize(total["size"])
    # logger.info("Objects: '{obj}', Files: '{files}', Pages: '{pages}', Deleted: '{deleted}', "
    #             "Size: '{size}'".format(**total))
    log_list(
        out,
        "Objects: '{obj}', Files: '{files}', Pages: '{pages}', Deleted: '{deleted}', " "Size: '{size}'".format(**total),
        logger
    )
    if can_delete_batch_files(batch_keys, batch_config):
        batch_delete_files(batch_keys, batch_config)
    return "\n".join(out)


def current_user_groups(user):
    """Return current user groups."""
    # no more used in code but kept if necessary
    return api.group.get_groups(user=user)


def current_user_groups_ids(user=None, userid=None):
    """Return current user groups ids."""
    return get_plone_groups_for_user(user_id=userid, user=user)


def user_is_admin(user=None):
    """Test if current user is admin."""
    if user is None:
        user = api.user.get_current()
    return user.has_role(["Manager", "Site Administrator"])


def is_in_user_groups(groups=(), admin=True, test="any", suffixes=(), org_uid="", user=None):
    """Test if one or all of a given group list is part of the current user groups.
    Test if one or all of a suffix list is part of the current user groups.
    """
    if user is None:
        user = api.user.get_current()
    # for admin, we bypass the check
    if admin and user_is_admin(user):
        return True
    u_groups = current_user_groups_ids(user)
    # u_suffixes = [sfx for sfx in suffixes for grp in u_groups if grp.endswith('_{}'.format(sfx))]
    u_suffixes = []
    for sfx in suffixes:
        for grp in u_groups:
            if org_uid:
                if grp == "{}_{}".format(org_uid, sfx):
                    u_suffixes.append(sfx)
            elif grp.endswith("_{}".format(sfx)):
                u_suffixes.append(sfx)
    if test == "any":
        return any(x in u_groups for x in groups) or any(sfx in u_suffixes for sfx in suffixes)
    elif test == "all":
        return all(x in u_groups for x in groups) and all(sfx in u_suffixes for sfx in suffixes)
    return False


def eml_preview(obj):
    """Adds jpeg documentviewer previews for eml file"""
    blobs = {}
    pc = api.portal.get_tool("portal_catalog")
    brains = pc.unrestrictedSearchResults(portal_type="dmsmainfile", markers="dvConvError")
    # search an existing main file with eml previews
    for brain in brains:
        o_annot = IAnnotations(brain._unrestrictedGetObject()).get("collective.documentviewer", "")
        if o_annot and "blob_files" in o_annot:
            for name in ("large", "normal", "small"):
                blobs[name] = o_annot["blob_files"]["{}/dump_1.jpg".format(name)]
            break
    # otherwise create previews
    if not blobs:
        normal_blob = saveFileToBlob(os.path.join(PREVIEW_DIR, "previsualisation_eml_normal.jpg"))
        blobs = {
            "large": normal_blob,
            "normal": normal_blob,
            "small": saveFileToBlob(os.path.join(PREVIEW_DIR, "previsualisation_eml_small.jpg")),
        }
    converter = Converter(obj)
    annot = IAnnotations(obj).get("collective.documentviewer", "")
    already_done = DateTime("2011/01/01").ISO8601()
    files = OOBTree()
    for name in ["large", "normal", "small"]:
        files["{}/dump_1.jpg".format(name)] = blobs[name]
    annot["blob_files"] = files
    annot["num_pages"] = 1
    annot["pdf_image_format"] = "jpg"
    annot["storage_type"] = converter.gsettings.storage_type
    annot["last_updated"] = already_done
    annot["catalog"] = None
    converter.initialize_filehash()  # get md5
    annot["filehash"] = converter.filehash
    annot["converting"] = False
    annot["successfully_converted"] = True


# views


class UtilsMethods(BrowserView):
    """Base view containing utils methods, not directly callable."""

    mainfile_type = "dmsmainfile"

    def get_object_from_relation(self, relation, attr="to", rel_object=True, from_path=False, iid=None):
        """Get object from relation or specific intid."""
        if attr not in ["to", "from"]:
            raise ValueError("attr parameter must be 'to' or 'from'")
        if rel_object:
            return getattr(relation, "{}_object".format(attr))
        if from_path:
            path = getattr(relation, "{}_path".format(attr))
            return api.portal.get().unrestrictedTraverse(path, None)
        if not iid:
            iid = getattr(relation, "{}_id".format(attr))
        intids = getUtility(IIntIds)
        try:
            return intids.getObject(iid)
        except KeyError:
            return None

    def highest_scan_id(self):
        """Return highest scan id."""
        pc = getToolByName(self.context, "portal_catalog")
        brains = pc.unrestrictedSearchResults(
            portal_type=self.mainfile_type, sort_on="scan_id", sort_order="descending"
        )
        if brains:
            return "dmsmainfiles: '%d', highest scan_id: '%s'" % (len(brains), brains[0].scan_id)
        else:  # pragma: no cover
            return "No scan id"

    def is_in_user_groups(self, groups=(), admin=True, test="any", suffixes=(), org_uid="", user=None):
        """Test if one or all of a given group list is part of the current user groups.
        Test if one or all of a suffix list is part of the current user groups.
        """
        return is_in_user_groups(groups=groups, admin=admin, test=test, suffixes=suffixes, org_uid=org_uid, user=user)

    def user_has_review_level(self, portal_type=None):
        """Test if the current user has a review level"""
        if portal_type is None:
            portal_type = self.context.portal_type
        return highest_review_level(portal_type, str(current_user_groups_ids(api.user.get_current()))) is not None

    def user_is_admin(self):
        """Test if current user is admin."""
        user = api.user.get_current()
        return user.has_role(["Manager", "Site Administrator"])


class VariousUtilsMethods(UtilsMethods):
    """View containing various utils methods. It can be used with `various-utils` name on all types."""

    def all_collection_uid(self, main_path="", subpath="mail-searches", col="all_mails"):
        portal = api.portal.get()
        return portal[main_path][subpath][col].UID()

    def check_scan_id(self, by="1000", sort="scan"):
        """Return a list of scan ids, one by 1000 items and by flow types"""
        if not self.user_is_admin() and not check_zope_admin():
            return
        import os

        res = {"0": {}, "1": {}, "2": {}, "Z": {}}
        flow_titles = {
            "0": u"Courrier entrant",
            "1": u"Courrier sortant",
            "2": u"Courrier sortant généré",
            "Z": u"Email entrant",
        }
        pc = getToolByName(self.context, "portal_catalog")
        brains = pc.unrestrictedSearchResults(portal_type=["dmsmainfile", "dmsommainfile"])
        divisor = int(by)
        out = []
        for brain in brains:
            if not brain.scan_id:
                continue
            try:
                nb = int(brain.scan_id[7:])
            except ValueError:
                out.append("Invalid scan_id '{}' for item {}".format(brain.scan_id, brain.getURL()))
                continue
            if (nb % divisor) == 0:
                ref = brain._unrestrictedGetObject().__parent__.internal_reference_no
                if sort == "scan":
                    res[brain.scan_id[2:3]][nb] = (os.path.dirname(brain.getURL()), ref)
                else:
                    res[brain.scan_id[2:3]][ref] = (os.path.dirname(brain.getURL()), nb)
        for flow in sorted(res):
            out.append("<h1>%s</h1>" % flow_titles[flow])
            for nb in natsorted(res[flow], reverse=True):
                out.append('<a href="%s" target="_blank">%s</a>, %s' % (res[flow][nb][0], nb, res[flow][nb][1]))
        return "<br/>\n".join(out)

    def cron_read_label_handling(self):
        """Cron task to handle read label"""
        logger.info("Running cron_read_label_handling")
        portal = self.context
        start = datetime(1973, 2, 12)
        catalog = portal.portal_catalog
        dic = get_dms_config(["read_label_cron"], missing_key_handling=True, missing_key_value={})
        count = 0
        for userid in dic.keys():
            if api.user.get(userid=userid) is None:
                continue
            for brain in catalog(
                    portal_type=["dmsincomingmail", "dmsincoming_email"],
                    recipient_groups=tuple(dic[userid]["orgs"]),
                    labels={"not": ["%s:lu" % userid]},
                    created={"query": (start, dic[userid]["end"]), "range": "min:max"},
            ):
                obj = brain.getObject()
                labeling = ILabeling(obj)
                user_ids = labeling.storage.setdefault("lu", PersistentList())  # _p_changed is managed
                user_ids.append(userid)  # _p_changed is managed
                obj.reindexObject(idxs=["labels"])
                count += 1
            del dic[userid]
        logger.info("End of cron_read_label_handling, %d items labeled" % count)

    def dv_conv_error(self):
        """When a conversion problem occurs, made the context no more convertible."""
        if not check_zope_admin():
            return "You must be zope admin to run this"
        if self.context.portal_type not in ("dmsmainfile", "dmsommainfile", "dmsappendixfile"):
            return "Portal type not considered: {}".format(self.context.portal_type)
        eml_preview(self.context)
        annot = IAnnotations(self.context)
        # so it cannot be converted anymore
        annot["collective.documentviewer"]["last_updated"] = DateTime("2050/01/01").ISO8601()
        if "exception_msg" in annot["collective.documentviewer"]:
            del annot["collective.documentviewer"]["exception_msg"]
        if "exception_traceback" in annot["collective.documentviewer"]:
            del annot["collective.documentviewer"]["exception_traceback"]
        self.context.reindexObject(idxs=["markers"])
        return self.context.REQUEST["RESPONSE"].redirect("{}/view".format(self.context.absolute_url()))

    def dv_images_clean(self):
        """Call dv_clean to remove old images following configuration"""
        # admin check is done in called dv_clean function
        params = {
            "days_back": api.portal.get_registry_record("imio.dms.mail.dv_clean_days", default=None),
            "date_back": api.portal.get_registry_record("imio.dms.mail.dv_clean_date", default=None),
        }
        for k, v in params.items():
            if not params[k]:
                del params[k]
        if not params:
            logger.error("No preservation parameters configured")
            return
        logger.info("Cleaning dv files with params {} on {}".format(params, self.context.absolute_url_path()))
        try:
            from datetime import datetime

            if params.get("date_back"):
                datetime.strftime(params["date_back"], "%Y%m%d")
        except Exception as msg:
            logger.error("Bad date value '{}': '{}'".format(params["date_back"], msg))
            return
        dv_clean(self.context, **params)

    def initialize_service_folder(self):
        """ """
        if not self.user_is_admin() and not check_zope_admin():
            return
        portal = api.portal.get()
        om_folder = portal["templates"]["om"]
        base_model = om_folder.get("main", None)
        if not base_model:
            return
        brains = portal.portal_catalog.unrestrictedSearchResults(
            portal_type="Folder", path={"query": "/".join(om_folder.getPhysicalPath()), "depth": 1}
        )
        for brain in brains:
            folder = brain._unrestrictedGetObject()
            contents = api.content.find(context=folder, depth=1)
            if not contents:
                logger.info("Copying %s in %s" % (base_model, brain.getPath()))
                api.content.copy(source=base_model, target=folder)
        return self.context.REQUEST["RESPONSE"].redirect(self.context.absolute_url())

    def is_unprotected(self):
        """Test if object is protected"""
        return not IProtectedItem.providedBy(self.context)

    def kofax_orgs(self):
        """Return a list of orgs formatted for Kofax"""
        if not self.user_is_admin():
            return

        def get_voc_values(voc_name):
            values = []
            factory = getUtility(IVocabularyFactory, voc_name)
            for term in factory(self.context):
                values.append("{}{}{}".format(term.title.encode("utf8"), cg_separator, term.value))
            return values

        ret = []  # noqa
        ret.append(_("Creating groups : to be used in kofax index").encode("utf8"))
        ret.append("")
        ret.append("\r\n".join(get_voc_values("imio.dms.mail.ActiveCreatingGroupVocabulary")))
        ret.append("")
        ret.append(_("Treating groups : to be used in kofax index").encode("utf8"))
        ret.append("")
        ret.append("\r\n".join(get_voc_values("collective.dms.basecontent.treating_groups")))
        return "\r\n".join(ret)

    def list_last_scan(self, typ="im", nb="100"):
        """List last scan of type."""
        if not check_zope_admin():
            return
        out = [
            u"<p>list_last_scan</h1>",
            u"-> typ='' : im, iem, om. Default=im",
            u"-> nb='' : get ... last. Default=100",
            u"ie. list_last_scan?typ=im",
            "",
        ]
        pc = self.context.portal_catalog
        limit = int(nb)
        criterias = {
            "portal_type": "dmsmainfile",
            "sort_on": "scan_id",
            "sort_order": "descending",
            "sort_limit": limit,
        }
        if typ == "im":
            criterias["id"] = {"not": "email.pdf"}
        elif typ == "iem":
            criterias["id"] = "email.pdf"
        elif typ == "om":
            criterias["portal_type"] = "dmsommainfile"
        brains = pc.unrestrictedSearchResults(**criterias)[:limit]
        for brain in brains:
            obj = brain._unrestrictedGetObject()
            mail = obj.getParentNode()
            out.append(
                u"{} ({}) in {} ({})".format(brain.scan_id, obj.version, mail.internal_reference_no, object_link(mail))
            )
        sep = u"\n<br />"
        return sep.join(out)

    def order_table_list(self, table=""):
        """Order table list in settings"""
        if not self.user_is_admin():
            return
        config = {"te": "mail_types", "ts": "omail_types", "fe": "omail_send_modes"}
        if table not in config:
            api.portal.show_message("Bad config name. Must be one of {}".format(", ".join(config.keys())), self.request)
            raise Redirect(self.context.absolute_url())
        rec_name = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(config.get(table, "mail_types"))
        lst = api.portal.get_registry_record(rec_name, default=[])
        if not lst:
            api.portal.show_message("Settings table '{}' empty".format(table), self.request)
            raise Redirect(self.context.absolute_url())
        lst.sort(key=lambda dic: unidecode(dic["dtitle"]))
        api.portal.set_registry_record(rec_name, lst)

    def pg_organizations(self, only_activated="1", output="csv", with_status=""):
        """Return a list of tuples with plonegroup organizations"""
        if not self.user_is_admin() and not check_zope_admin():
            return
        factory = getUtility(IVocabularyFactory, "collective.contact.plonegroup.organization_services")
        lst = []
        activated = get_registry_organizations()
        for term in factory(self.context):
            uid, title = term.value, term.title
            status = uid in activated and "a" or "na"
            if only_activated == "1" and status == "na":
                continue
            lst.append((uid, title.encode("utf8"), status))
        # sorted(lst, key=itemgetter(1))
        if output != "csv":
            return lst
        ret = []
        for uid, tit, stat in lst:
            if with_status:
                ret.append("%s;%s;%s" % (uid, tit, stat))
            else:
                ret.append("%s;%s" % (uid, tit))
        return "\n".join(ret)

    def template_infos(self):
        """Get from a generated document the original template."""
        annot = IAnnotations(self.context)
        if "documentgenerator" not in annot or "template_uid" not in annot["documentgenerator"]:
            return "No template"
        uid = annot["documentgenerator"]["template_uid"]
        doc = uuidToObject(uid, unrestricted=True)
        if doc:
            ret = [u"<p>Template: {}</p>".format(object_link(doc, target="_blank"))]
            merge = doc.get_templates_to_merge()
            if merge:
                ret.append(u"<ul>")
                for name in sorted(merge.keys()):
                    ret.append(u"<li>{} = {}</li>".format(name, object_link(merge[name][0], target="_blank")))
                else:
                    ret.append(u"</ul>")
            style = doc.get_style_template()
            if style:
                ret.append(u"<p>Style: {}</p>".format(object_link(style, target="_blank")))
            return u"".join(ret)
        else:
            return "No template found with uid '{}'".format(uid)

    def unread_criteria(self):
        """ """
        cc = getCurrentCollection(self.context)
        if not cc or cc.id != "in_copy_unread":
            return "FACET-EMPTY"
        user = api.user.get_current()
        return {"not": "%s:lu" % user.id}

    def user_usages(self, userid=""):
        """Checks user usages"""
        if not check_zope_admin():
            return "You must be a zope manager to run this script"
        if not userid:
            return "You must give a parameter named 'userid'"
        user = api.user.get(userid=userid)
        if user is None:
            return "Cannot find a user with userid='{}'".format(userid)
        out = [u"<h1>Usages of user name '{}'</h1>".format(userid)]
        portal = api.portal.getSite()
        log_list(
            out,
            u"<p>Fullname='{}'. Email='{}'</p>".format(
                object_link(
                    portal,
                    view="@@usergroup-userprefs?searchstring={}".format(userid),
                    content=safe_unicode(user.getProperty("fullname")),
                    target="_blank",
                ),
                safe_unicode(user.getProperty("email")),
            ),
        )
        # get groups
        log_list(out, u"<h2>In groups ?</h2>")
        groups = [group for group in get_plone_groups_for_user(user=user) if group != "AuthenticatedUsers"]
        if groups:
            log_list(
                out,
                u"<p>=> in {} {}.</p>".format(
                    len(groups),
                    object_link(
                        portal,
                        view="@@usergroup-usermembership?userid={}".format(userid),
                        content="groups",
                        target="_blank",
                    ),
                ),
            )
        else:
            log_list(out, u"<p>none</p>")

        config = {
            "dmsincomingmail": "{}/incoming-mail/mail-searches#c1={}&{{}}".format(
                portal.absolute_url(), self.all_collection_uid("incoming-mail")
            ),
            "dmsincoming_email": "{}/incoming-mail/mail-searches#c1={}&{{}}".format(
                portal.absolute_url(), self.all_collection_uid("incoming-mail")
            ),
            "dmsoutgoingmail": "{}/outgoing-mail/mail-searches#c1={}&{{}}".format(
                portal.absolute_url(), self.all_collection_uid("outgoing-mail")
            ),
            "task": "{}/tasks/task-searches#c1={}&{{}}".format(
                portal.absolute_url(), self.all_collection_uid("tasks", "task-searches", "all_tasks")
            ),
        }
        log_list(out, u"<h2>In personnel folder ?</h2>")
        intids = getUtility(IIntIds)
        catalog = getUtility(ICatalog)
        pc = portal.portal_catalog
        brains = pc.unrestrictedSearchResults(userid=userid, portal_type="held_position", sort_on="path")
        if brains:
            persons = {}
            for brain in brains:
                hp = brain._unrestrictedGetObject()
                hps = persons.setdefault(hp.__parent__, [])
                hps.append(hp)
            for person in persons:
                rels = list(catalog.findRelations({"to_id": intids.getId(person)}))
                log_list(
                    out,
                    u"<p>=> Found a person {}, with {} relations.</p>".format(
                        object_link(person, target="_blank"), len(rels)
                    ),
                )
                for hp in persons[person]:
                    rels = list(catalog.findRelations({"to_id": intids.getId(hp)}))
                    oms = pc.unrestrictedSearchResults(sender_index=hp.UID(), portal_type="dmsoutgoingmail")
                    oms_l = len(oms)
                    if oms_l:
                        oms_l = '<a href="{}" target="_blank">{}</a>'.format(
                            config["dmsoutgoingmail"].format("c7={}".format(hp.UID())), oms_l
                        )
                    log_list(
                        out,
                        u"<p>.. in HP {}, with {} relations and {} om sender.</p>".format(
                            object_link(hp, target="_blank"), len(rels), oms_l
                        ),
                    )
        else:
            log_list(out, u"<p>none</p>")

        log_list(out, u"<h2>Is an assigned user ?</h2>")
        brains = pc.unrestrictedSearchResults(assigned_user=userid, sort_on="path")
        if brains:
            tasks = {}
            for brain in brains:
                obj = brain._unrestrictedGetObject()
                lst = tasks.setdefault(brain.portal_type, [])
                lst.append(obj)
            crit = {"dmsincomingmail": "c6", "dmsincoming_email": "c6", "dmsoutgoingmail": "c13", "task": "c6"}
            for tp in tasks:
                tp_l = '<a href="{}" target="_blank">{}</a>'.format(
                    config[tp].format("{}={}".format(crit[tp], userid)), len(tasks[tp])
                )
                log_list(out, "<p>=> Found {} {}.</p>".format(tp_l, tp))
        else:
            log_list(out, u"<p>none</p>")

        log_list(out, u"<h2>Is a creator ?</h2>")
        brains = pc.unrestrictedSearchResults(Creator=userid, sort_on="path")
        if brains:
            log_list(out, "<p>=> Found {} items.</p>".format(len(brains)))
            for brain in brains:
                obj = brain._unrestrictedGetObject()
                log_list(out, u"<p>* {}</p>".format(object_link(obj, target="_blank")))
        else:
            log_list(out, u"<p>none</p>")
        return u"\n".join(out)


class IdmUtilsMethods(UtilsMethods):
    """View containing incoming mail utils methods"""

    def created_col_cond(self):
        """Condition for searchfor_created collection"""
        return self.is_in_user_groups(["encodeurs"], admin=False, suffixes=[CREATING_GROUP_SUFFIX])

    def get_im_folder(self):
        """Get the incoming-mail folder"""
        portal = getSite()
        return portal["incoming-mail"]

    def im_listing_url(self):
        col_folder = self.get_im_folder()["mail-searches"]
        url = col_folder.absolute_url()
        col_uid = col_folder["all_mails"].UID()
        from_date = date.today()
        to_date = from_date + timedelta(1)
        return "{}/#c3=20&b_start=0&c1={}&c10={}&c10={}".format(
            url, col_uid, from_date.strftime("%d/%m/%Y"), to_date.strftime("%d/%m/%Y")
        )

    def must_render_im_listing(self):
        return IIMDashboard.providedBy(self.context)

    def proposed_to_manager_col_cond(self):
        """Condition for searchfor_proposed_to_manager collection"""
        return self.is_in_user_groups(["encodeurs", "dir_general"], admin=False, suffixes=[CREATING_GROUP_SUFFIX])

    def proposed_to_n_plus_col_cond(self):
        """
        Condition for searchfor_proposed_to_n_plus collection
        """
        suffixes = []
        # a lower level search can be viewed by a higher level
        for i in range(int(self.context.id[-1:]), 6):
            suffixes.append("n_plus_{}".format(i))
        suffixes.append(CREATING_GROUP_SUFFIX)
        return self.is_in_user_groups(["encodeurs", "dir_general"], admin=False, suffixes=suffixes)

    def proposed_to_pre_manager_col_cond(self):
        """Condition for searchfor_proposed_to_pre_manager collection"""
        return self.is_in_user_groups(
            ["encodeurs", "dir_general", "pre_manager"], admin=False, suffixes=[CREATING_GROUP_SUFFIX]
        )


class OdmUtilsMethods(UtilsMethods):
    """View containing outgoing mail utils methods"""

    mainfile_type = "dmsommainfile"

    def get_om_folder(self):
        """Get the outgoing-mail folder"""
        portal = getSite()
        return portal["outgoing-mail"]

    def is_odt_activated(self):
        registry = getUtility(IRegistry)
        return registry["imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile"]

    def scanned_col_cond(self):
        """Condition for searchfor_scanned collection"""
        return self.is_in_user_groups(["encodeurs", "expedition"], admin=False, suffixes=[CREATING_GROUP_SUFFIX])


class Dummy(object):
    """dummy class that allows setting attributes"""

    def __init__(self, **kw):
        self.__dict__.update(kw)


class DummyView(object):
    def __init__(self, context=None, request=None):
        if context is not None:
            self.context = context
        else:
            self.context = Dummy()
        if request is not None:
            self.request = request
        else:
            self.request = {}


def create_period_folder_max(main_dir, dte, counter_dic, max_nb=1000):
    """Following date, get a period date string and create the subdirectory.
    If the children number is greater than max_nb, create another subfolder."""
    period = getattr(main_dir, "folder_period", u"week")
    dte_str = base_dte_str = dte.strftime(PERIODS.get(period, PERIODS["week"]))

    def folder_status(folder):
        if folder in counter_dic:  # known folder status
            pass
        elif folder in main_dir:  # folder already exists, count children
            counter_dic[folder] = len(main_dir[folder].objectIds())
        else:  # new folder
            counter_dic[folder] = 0
        return counter_dic[folder]

    # find the correct subfolder name following children count
    i = 0
    while folder_status(dte_str) > max_nb - 1:
        i += 1
        dte_str = "{}-{}".format(base_dte_str, i)

    counter_dic[dte_str] += 1
    return create_period_folder(main_dir, dte, subfolder=dte_str)


def create_period_folder(main_dir, dte, subfolder=""):
    """Following date, get a period date string and create the subdirectory.
    If subfolder is given, this subfolder name is used in place of dte."""
    if subfolder:
        dte_str = subfolder
    else:
        period = getattr(main_dir, "folder_period", u"week")
        dte_str = dte.strftime(PERIODS[period])
    if dte_str not in main_dir:
        with api.env.adopt_user(username="admin"):
            main_dir.setConstrainTypesMode(0)
            subfolder = api.content.create(main_dir, "Folder", dte_str, dte_str.decode())
            main_dir.setConstrainTypesMode(1)
            alsoProvides(subfolder, INextPrevNotNavigable)
            alsoProvides(subfolder, IHideFromBreadcrumbs)
            do_transitions(subfolder, ["show_internally"])
        return subfolder
    return main_dir[dte_str]


def create_personnel_content(
    userid, groups, functions=ALL_SERVICE_FUNCTIONS, primary=False, fn_first=None, assignment=True
):
    """Create or handle directory personnel content for a userid.

    :param userid: userid
    :param groups: groups to consider
    :param functions: functions to consider
    :param primary: set person primary_organization if only one org (to be used only when passing all user groups)
    :param fn_first: bool indicating firstname is starting fullname. When None, the value is taken from configuration
    :param assignment: bool indicating if we are doing an assignment
    """
    out = []  # used in portal_setup step context
    orgs = organizations_with_suffixes(groups, functions, group_as_str=True)
    if orgs:
        # or event.group_id in ('dir_general', 'encodeurs', 'expedition', 'lecteurs_globaux_ce', 'lecteurs_globaux_cs'):
        portal = api.portal.get()
        user = api.user.get(userid)
        user_groups = get_plone_groups_for_user(user=user)
        intids = getUtility(IIntIds)
        pf = portal["contacts"]["personnel-folder"]
        # exists already
        persons = portal.portal_catalog.unrestrictedSearchResults(userid=userid, portal_type="person")
        if persons:
            if len(persons) > 1:
                logger.warn(
                    "Found multiple personnel persons linked to userid '{}' : {}".format(
                        userid, "\n".join([br.getURL() for br in persons])
                    )
                )
            if userid in pf:
                pers = pf[userid]
            else:
                pers = persons[0]._unrestrictedGetObject()
        elif userid in pf:
            pers = pf[userid]
        elif assignment:
            if fn_first is None:
                start = api.portal.get_registry_record(
                    "imio.dms.mail.browser.settings.IImioDmsMailConfig." "omail_fullname_used_form", default="firstname"
                )
                fn_first = start == "firstname"
            firstname, lastname = separate_fullname(user, fn_first=fn_first)
            pers = api.content.create(
                container=pf,
                type="person",
                id=userid,
                userid=userid,
                lastname=lastname,
                firstname=firstname,
                use_parent_address=False,
            )
            out.append(u"person created for user %s, fn:'%s', ln:'%s'" % (userid, firstname, lastname))
        else:
            return out  # in unassignment, if pers doesn't exit, nothing more to do
        hps = [
            b._unrestrictedGetObject()
            for b in portal.portal_catalog.unrestrictedSearchResults(
                path="/".join(pers.getPhysicalPath()), portal_type="held_position"
            )
        ]
        hps_orgs = dict([(hp.get_organization(), hp) for hp in hps])
        if len(hps) != len(hps_orgs):
            logger.warn(
                u"Found multiple held positions for the same org in userid '{}' : {}".format(
                    userid, u" | ".join([hp.get_full_title() for hp in hps])
                )
            )
        elif primary and len(hps_orgs) == 1:
            pers.primary_organization = orgs[0]
        for uid in orgs:
            org = uuidToObject(uid, unrestricted=True)
            if not org:
                return
            if uid in pers:
                hp = pers[uid]
            elif org in hps_orgs:
                hp = hps_orgs[org]
            elif assignment:
                email = user.getProperty("email") or ""
                hp = api.content.create(
                    container=pers,
                    id=uid,
                    type="held_position",
                    email=safe_unicode(email.lower()),
                    position=RelationValue(intids.getId(org)),
                    use_parent_address=True,
                )
                out.append(u" -> hp created for userid '{}' with org '{}'".format(userid, org.get_full_title()))
            else:
                continue  # in unassignment, if hp doesn't exit, nothing more to do
            # activate hp only if the corresponding group has encodeur function (OM senders)
            if api.content.get_state(hp) == "active" and "{}_encodeur".format(uid) not in user_groups:
                api.content.transition(hp, "deactivate")
            if api.content.get_state(hp) == "deactivated" and "{}_encodeur".format(uid) in user_groups:
                api.content.transition(hp, "activate")
        # change person state following hps states: no otherwise the person is not more selectable in contacts
        # if portal.portal_catalog.unrestrictedSearchResults(path='/'.join(pers.getPhysicalPath()),
        #                                                    portal_type='held_position', review_state='active'):
        #     api.content.transition(pers, to_state='active')
        # else:
        #     api.content.transition(pers, to_state='deactivated')

        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMActiveSenderVocabulary")
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMSenderVocabulary")
    return out


def add_content_in_subfolder(view, obj, dte):
    """Add obj in period subfolder"""
    portal = api.portal.get()
    container = create_period_folder(portal[MAIN_FOLDERS[view.portal_type]], dte)
    new_object = addContentToContainer(container, obj)
    return container, new_object


def sub_create(main_folder, ptype, dte, oid, **params):
    container = create_period_folder(main_folder, dte)
    container.invokeFactory(ptype, id=oid, **params)  # i_e ok
    return container[oid]


def update_solr_config():
    """Update config following buildout var"""
    if api.portal.get_registry_record("collective.solr.port", default=None) is None:
        return
    for key, cast in (("host", u""), ("port", 0), ("base", u"")):
        full_key = "collective.solr.{}".format(key)
        value = api.portal.get_registry_record(full_key, default=None)
        new_value = type(cast)(os.getenv("COLLECTIVE_SOLR_{}".format(key.upper()), cast))
        if new_value and new_value != value:
            api.portal.set_registry_record(full_key, new_value)


def manage_fields(the_form, config_key, mode):
    """Remove, reorder and restrict fields.

    :param the_form: form displaying fields
    :param config_key: registry key field containiing the fields configuration
    :param mode: form mode ('view' or 'edit')
    """
    schema_config = api.portal.get_registry_record(
        "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(config_key)
    )
    if not schema_config:
        return
    to_input = []
    to_display = []

    # configured_fields = [e["field_name"] for e in schema_config]
    for fields_schema in reversed(schema_config):
        field_name = fields_schema["field_name"]
        read_condition = fields_schema.get("read_tal_condition") or ""
        write_condition = fields_schema.get("write_tal_condition") or ""
        if _evaluateExpression(the_form.context, expression=read_condition):
            to_display.append(field_name)
        if mode != "view" and _evaluateExpression(the_form.context, expression=write_condition):
            to_input.append(field_name)

        field = remove(the_form, field_name)
        if field is not None and field_name in to_display:
            if field_name.startswith("email_"):
                add(the_form, field, index=0, group="email")
            else:
                add(the_form, field, index=0)
            if mode != "view" and field_name not in to_input:
                field.mode = "display"

    # We remove fields not to display (not configured)
    for group in [the_form] + the_form.groups:
        for field_name in group.fields:
            if field_name not in to_display:
                group.fields = group.fields.omit(field_name)


def message_status(mid, older=None, to_state="inactive", transitions=["deactivate"], container="default"):
    site = api.portal.get()
    if container == "default":
        container = site["messages-config"]
    # We pass if id already exists
    if mid not in container:
        return False
    obj = container[mid]
    change = True
    if older is not None:
        with api.env.adopt_roles(["Manager"]):
            history = site.portal_workflow.getInfoFor(obj, "review_history")
        last_mod = history[-1]["time"].asdatetime().date()
        if datetime.now().date() - last_mod <= older:
            change = False
    if change and api.content.get_state(obj) != to_state:
        do_transitions(obj, transitions)
    return api.content.get_state(obj) == to_state


def is_n_plus_level_obsolete(mail, ptype, treating_group="", state=None, config=None, state_start="proposed_to_n_plus"):
    """Check if current treating_groups has validators on the state.

    :param mail: concerned object
    :param ptype: portal type
    :param treating_group: treating group
    :param state: current state
    :param config: transitions_levels dms config
    :param state_start: concerned state start check
    :return: obsolete bool, state, config
    """
    if treating_group == "":
        treating_group = mail.treating_groups
    if treating_group is None:
        return False, state, config
    if state is None:
        state = api.content.get_state(mail)
    if not state.startswith(state_start):
        return False, state, config
    if config is None:
        config = get_dms_config(["transitions_levels", ptype])
    if config[state][treating_group][2] is False:  # no user in the group
        return True, state, config
    return False, state, config


def do_next_transition(mail, ptype, treating_group="", state=None, config=None):
    """Do next transition following transition_levels"""
    if state is None:
        state = api.content.get_state(mail)
    if config is None:
        config = get_dms_config(["transitions_levels", ptype])
    if treating_group == "":
        treating_group = mail.treating_groups
    with api.env.adopt_roles(["Reviewer"]):
        api.content.transition(mail, config[state][treating_group][0])


def is_valid_identifier(identifier):
    idnormalizer = getUtility(IIDNormalizer)
    return idnormalizer.normalize(identifier) == identifier


def get_context_with_request(context):
    """When editing a dashboardcollection, the context is portal_registry.
    We must have the right context to get the labels jar definition."""
    # in case we have no REQUEST, it means that we are editing a DashboardCollection
    # for which when this vocabulary is used for the 'labels' queryField, the context
    # is portal_registry without a REQUEST...
    if not hasattr(context, "REQUEST"):
        # sometimes, the DashboardCollection is the first parent in the REQUEST.PARENTS...
        portal = getSite()
        published = portal.REQUEST.get("PUBLISHED", None)
        if base_hasattr(published, "getTagName"):  # plonemeeting specific ?
            context = published
        else:
            context = base_hasattr(published, "context") and published.context or None
        if not context or context == portal:
            # if not first parent, try to get it from HTTP_REFERER
            referer = portal.REQUEST["HTTP_REFERER"].replace(portal.absolute_url() + "/", "")
            referer = referer.replace("/edit", "")
            # referer = referer.split('?_authenticator=')[0]
            try:
                context = portal.unrestrictedTraverse(referer)
            except (KeyError, AttributeError):
                return None
            if not hasattr(context, "portal_type") or not context.portal_type == "DashboardCollection":
                return None
    return context


def invalidate_users_groups(portal=None, user=None, user_id=None, **kwargs):
    invalidate_cachekey_volatile_for("_users_groups_value", get_again=True)
    # for dmsmail tests only
    if getattr(portal or api.portal.get(), "_v_ready", False):
        if user is None:
            user = user_id and api.user.get(user_id) or api.user.get_current()
        # we ensure calling directly this method because if called elsewhere with current user (not refreshed),
        # the cached value is not correct
        # same reason as change_user method
        get_plone_groups_for_user(user=user, **kwargs)


def modifyFileInBlob(blob, filepath):
    with blob.open('w') as blob_file:
        with open(filepath, 'rb') as new_file:
            blob_file.write(new_file.read())


def create_read_label_cron_task(userid, orgs, end, portal=None):
    """Create cron task information that will be executed later to update read label.

    This is called after group assignment, thus by an admin user..."""
    if portal is None:
        portal = api.portal.get()
    cron_tasks = set_dms_config(["read_label_cron", userid], PersistentDict(), force=False)
    if "end" not in cron_tasks:
        cron_tasks["end"] = end
    orgs_set = cron_tasks.setdefault("orgs", set())
    orgs_set.update(orgs)


def vocabularyname_to_terms(vocabulary_name, context=None, sort_on=None):
    """Get terms from vocabulary name."""
    factory = getUtility(IVocabularyFactory, vocabulary_name)
    vocab = factory(context)
    if sort_on:
        return sorted([term for term in vocab], key=attrgetter(sort_on))
    return [term for term in vocab]
