# encoding: utf-8

from AccessControl import getSecurityManager
from collective.classification.folder.interfaces import IServiceInCharge
from collective.classification.folder.interfaces import IServiceInCopy
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.indexers import contact_source
from collective.contact.core.interfaces import IContactContent
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.widget.interfaces import IContactAutocompleteWidget
from collective.dexteritytextindexer.interfaces import IDynamicTextIndexExtender
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.basecontent.dmsfile import IDmsAppendixFile
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.dms.mailcontent.indexers import add_parent_organizations
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task.interfaces import ITaskContent
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import OM_READER_SERVICE_FUNCTIONS
from imio.dms.mail.content.behaviors import IDmsMailCreatingGroup
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import logger
from imio.helpers import EMPTY_DATE
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_relations
from imio.helpers.content import object_values
from imio.helpers.content import uuidToObject
from imio.helpers.emailer import validate_email_address
from imio.pm.wsclient.interfaces import ISendableAnnexesToPM
from imio.prettylink.adapters import PrettyLinkAdapter
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu
from plone.app.contenttypes.indexers import _unicode_save_string_concat
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.ATContentTypes.interfaces.folder import IATFolder
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import sortable_title
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker as common_marker
from z3c.form.datamanager import AttributeField
from z3c.form.interfaces import IContextAware
from z3c.form.interfaces import IDataManager
from z3c.form.interfaces import NO_VALUE
from z3c.form.term import MissingChoiceTermsVocabulary
from z3c.form.term import MissingTermsMixin
from z3c.form.validator import SimpleFieldValidator
from zope.annotation import IAnnotations
from zope.component import adapter
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import implementer
from zope.interface import implements
from zope.interface import Interface
from zope.schema.interfaces import IField
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary

import datetime
import time


#######################
# Compound criterions #
#######################

default_criterias = {
    "dmsincomingmail": {
        "review_state": {
            "query": [
                "proposed_to_manager",  # i_e ok
                "proposed_to_pre_manager",
                "proposed_to_n_plus_5",
                "proposed_to_n_plus_4",
                "proposed_to_n_plus_3",
                "proposed_to_n_plus_2",
                "proposed_to_n_plus_1",
            ]
        }
    },
    "task": {"review_state": {"query": ["to_assign", "realized"]}},
}


def highest_validation_criterion(portal_type):
    """
    Return a query criterion corresponding to current user highest validation level
    NO MORE USED
    """
    if portal_type == "dmsincoming_email":
        portal_type = "dmsincomingmail"  # i_e ok
    groups = get_plone_groups_for_user(user=api.user.get_current())
    highest_level = highest_review_level(portal_type, str(groups))
    if highest_level is None:
        return default_criterias[portal_type]
    ret = {}
    review_levels = get_dms_config(["review_levels"])
    criterias = review_levels[portal_type][highest_level]
    if "st" in criterias:
        ret["review_state"] = {"query": criterias["st"]}
    if "org" in criterias:
        organizations = []
        for groupid in groups:
            if groupid.endswith(highest_level):
                organizations.append(groupid[: -len(highest_level)])
        ret[criterias["org"]] = {"query": organizations}
    return ret


class IncomingMailHighestValidationCriterion(object):
    """
    Return catalog criteria following highest validation group member
    NOT USED
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion("dmsincomingmail")  # i_e ok


class TaskHighestValidationCriterion(object):
    """
    Return catalog criteria following highest validation group member
    NOT USED
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion("task")


def validation_criterion(context, portal_type):
    """Return a query criterion corresponding to current user validation level"""
    if portal_type == "dmsincoming_email":
        portal_type = "dmsincomingmail"  # i_e ok
    groups = get_plone_groups_for_user(user=api.user.get_current())
    config = get_dms_config(["review_levels", portal_type])
    # set_dms_config(['review_levels', 'dmsincomingmail'],  # i_e ok
    #            OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
    #                         ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))
    ret = {"state_group": {"query": []}}
    for group_or_suffix in config:
        if not group_or_suffix.startswith("_"):
            if group_or_suffix in groups:
                for state in config[group_or_suffix]["st"]:
                    ret["state_group"]["query"].append(state)
        else:
            # get orgs of user groups with suffix
            orgs = organizations_with_suffixes(groups, [group_or_suffix[1:]], group_as_str=True)
            if orgs:
                for state in config[group_or_suffix]["st"]:
                    for org in orgs:
                        ret["state_group"]["query"].append("%s,%s" % (state, org))
    return ret


class IncomingMailValidationCriterion(object):
    """
    Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, "dmsincomingmail")  # i_e ok


class TaskValidationCriterion(object):
    """
    Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, "task")


class OutgoingMailValidationCriterion(object):
    """
    Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, "dmsoutgoingmail")


class IncomingMailInTreatingGroupCriterion(object):
    """
    Return catalog criteria following treating group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"treating_groups": {"query": orgs}}


class OutgoingMailInTreatingGroupCriterion(object):
    """
    Return catalog criteria following treating group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, OM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"treating_groups": {"query": orgs}}


class IncomingMailInCopyGroupCriterion(object):
    """
    Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"recipient_groups": {"query": orgs}}


class IncomingMailInCopyGroupUnreadCriterion(object):
    """
    Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        user = api.user.get_current()
        groups = get_plone_groups_for_user(user=user)
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"recipient_groups": {"query": orgs}, "labels": {"not": ["%s:lu" % user.id]}}


class IncomingMailFollowedCriterion(object):
    """
    Return catalog criteria for 'suivi' label
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return {"labels": {"query": "%s:suivi" % api.user.get_current().id}}


class OutgoingMailInCopyGroupCriterion(object):
    """
    Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, OM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"recipient_groups": {"query": orgs}}


class TaskInAssignedGroupCriterion(object):
    """
    Return catalog criteria following assigned group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"assigned_group": {"query": orgs}}


class TaskInProposingGroupCriterion(object):
    """
    Return catalog criteria following enquirer group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"mail_type": {"query": orgs}}


################
# GUI cleaning #
################


class ActionsSubMenuItem(OrigActionsSubMenuItem):
    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission("Manage portal", self.context):
            return False
        return super(ActionsSubMenuItem, self).available()


class FactoriesSubMenuItem(OrigFactoriesSubMenuItem):
    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission("Manage portal", self.context):
            return False
        return super(FactoriesSubMenuItem, self).available()


class WorkflowMenu(OrigWorkflowMenu):
    def getMenuItems(self, context, request):
        if not getSecurityManager().checkPermission("Manage portal", context):
            return []
        return super(WorkflowMenu, self).getMenuItems(context, request)


####################
# Various adapters #
####################


class IMPrettyLinkAdapter(PrettyLinkAdapter):
    def _leadingIcons(self):
        icons = []
        if self.context.task_description and self.context.task_description.raw:
            registry = getUtility(IRegistry)
            if api.content.get_state(self.context) in (
                registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states") or []
            ):
                icons.append(
                    (
                        "++resource++imio.dms.mail/remark.gif",
                        translate("Remark icon", domain="imio.dms.mail", context=self.request),
                    )
                )
        back_or_again_icon = self.context.get_back_or_again_icon()
        if back_or_again_icon:
            icons.append(
                (back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail", context=self.request))
            )
        annot = IAnnotations(self.context)
        if "hasResponse" in annot.get("dmsmail.markers", []):
            icons.append(
                (
                    "++resource++imio.dms.mail/replied_icon.png",
                    translate("Has response icon", domain="imio.dms.mail", context=self.request),
                )
            )
        return icons


class OMPrettyLinkAdapter(PrettyLinkAdapter):
    def _leadingIcons(self):
        icons = []
        if self.context.task_description and self.context.task_description.raw:
            registry = getUtility(IRegistry)
            if api.content.get_state(self.context) in (
                registry.get("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states") or []
            ):
                icons.append(
                    (
                        "++resource++imio.dms.mail/remark.gif",
                        translate("Remark icon", domain="imio.dms.mail", context=self.request),
                    )
                )
        back_or_again_icon = self.context.get_back_or_again_icon()
        if back_or_again_icon:
            icons.append(
                (back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail", context=self.request))
            )
        return icons


class TaskPrettyLinkAdapter(PrettyLinkAdapter):
    def _leadingIcons(self):
        icons = []
        back_or_again_icon = BACK_OR_AGAIN_ICONS[back_or_again_state(self.context)]
        if back_or_again_icon:
            icons.append(
                (back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail", context=self.request))
            )
        return icons


####################
# Indexes adapters #
####################


@indexer(IImioDmsOutgoingMail)
def approval_index(obj):
    """Indexer of 'approvings' for IImioDmsOutgoingMail.

    Stores userid:number for each approver.
    """
    annot = IAnnotations(obj)
    approval = annot.get("idm.approval", {"current": None})
    if approval["current"]:
        return [a["userid"] for a in approval["numbers"][approval["current"]]["users"]]
    return common_marker


@indexer(IDmsMailCreatingGroup)
def creating_group_index(obj):
    """Indexer of 'assigned_group' for IDmsMailCreatingGroup. Stores creating_group !"""
    if base_hasattr(obj, "creating_group") and obj.creating_group:
        return obj.creating_group
    return common_marker


@indexer(IImioDmsIncomingMail)
def im_sender_email_index(obj):
    """Indexer of 'email' for IImioDmsIncomingMail. Stores orig_sender_email !"""
    if obj.orig_sender_email:
        return validate_email_address(obj.orig_sender_email)[1]
    return common_marker


@indexer(IImioDmsOutgoingMail)
def om_sender_email_index(obj):
    """Indexer of 'email' for IImioDmsOutgoingMail. Stores orig_sender_email !"""
    return im_sender_email_index(obj)


@indexer(IImioDmsOutgoingMail)
def ready_for_email_index(obj):
    """Indexer of 'enabled' for IImioDmsOutgoingMail. Stores flag to know if email can be send (after be signed) !"""
    if not obj.is_email():  # if not email, we don't have to flag it
        return False
    # we check if a dms file is marked as signed...
    docs = []
    for doc in obj.values():
        if not IDmsFile.providedBy(doc):
            continue
        docs.append(doc)
        if doc.signed:
            return True
    if not docs:
        return True
    return False


@indexer(IATFolder)
def fancy_tree_folder_index(obj):
    if "/templates/om/" in "/".join(obj.getPhysicalPath()):
        return True
    return False


@indexer(IImioDmsIncomingMail)
def get_full_title_index(obj):
    """Metadata of 'get_full_title' for IImioDmsIncomingMail. Stores title !"""
    # No acquisition pb because get_full_title isn't an attr
    if obj.title:
        return obj.title.encode("utf8")
    return common_marker


# See getObjSize_file method from plone/app/contenttypes/indexers.py
# See Products/CMFPlone/skins/plone_scripts/getObjSize.py
def get_obj_size(obj):
    try:
        primary_field_info = IPrimaryFieldInfo(obj)
    except TypeError:
        logger.warn(u"Lookup of PrimaryField failed for %s" % obj.absolute_url())
        return
    const = {"KB": 1024, "MB": 1048576, "GB": 1073741824}
    order = ("GB", "MB", "KB")
    size = primary_field_info.value.size
    if size < 1024:
        return "1 KB"
    for c in order:
        if size / const[c] > 0:
            break
    return "%.1f %s" % (float(size / float(const[c])), c)  # noqa


@indexer(IDmsAppendixFile)
def get_obj_size_af_index(obj):
    return get_obj_size(obj)


@indexer(IDmsFile)
def get_obj_size_df_index(obj):
    return get_obj_size(obj)


@indexer(IImioDmsIncomingMail)
def in_out_date_index(obj):
    """Indexer of 'in_out_date' for IImioDmsIncomingMail. Stores reception_date !"""
    # No acquisition pb because in_out_date isn't an attr
    if obj.reception_date:
        return obj.reception_date
    return EMPTY_DATE


@indexer(IImioDmsOutgoingMail)
def om_in_out_date_index(obj):
    """Indexer of 'in_out_date' for IImioDmsOutgoingMail. Stores outgoing_date !"""
    # No acquisition pb because in_out_date isn't an attr
    if obj.outgoing_date:
        return obj.outgoing_date
    else:
        return EMPTY_DATE


@indexer(IImioDmsIncomingMail)
def im_irn_no_index(obj):
    """Indexer of 'internal_reference_no' for IImioDmsIncomingMail. Stores nothing !"""
    return common_marker


@indexer(IImioDmsOutgoingMail)
def om_irn_no_index(obj):
    """Indexer of 'internal_reference_no' for IImioDmsOutgoingMail. Stores nothing !"""
    return common_marker


@indexer(IImioDmsIncomingMail)
def mail_date_index(obj):
    """Indexer of 'mail_date' for IImioDmsIncomingMail. Stores original_mail_date !"""
    # No acquisition pb because mail_date isn't an attr but cannot store None
    if obj.original_mail_date:
        return obj.original_mail_date
    else:
        return EMPTY_DATE
    # return common_marker


@indexer(IImioDmsOutgoingMail)
def om_mail_date_index(obj):
    """Indexer of 'mail_date' for IImioDmsOutgoingMail."""
    if base_hasattr(obj, "mail_date"):
        if obj.mail_date:
            return obj.mail_date
        else:
            return EMPTY_DATE
    return common_marker


@indexer(IContentish)
def mail_type_index(obj):
    """Indexer of 'mail_type' for IContentish."""
    if base_hasattr(obj, "mail_type") and obj.mail_type:
        return obj.mail_type
    return common_marker


@indexer(IHeldPosition)
def heldposition_userid_index(obj):
    """Indexer of 'userid' for IHeldPosition. Stores parent userid !"""
    parent = obj.aq_parent
    if base_hasattr(parent, "userid") and parent.userid:
        return parent.userid
    return common_marker


@indexer(ITaskContent)
def task_enquirer_index(obj):
    """Indexer of 'mail_type' for ITaskContent. Stores enquirer !"""
    if base_hasattr(obj, "enquirer") and obj.enquirer:
        return obj.enquirer
    return common_marker


def im_markers(obj):
    """Calculates IImioDmsIncomingMail markers:

    * hasResponse
    """
    markers = []
    # Set hasResponse
    rels = get_relations(obj, "reply_to", backrefs=True)  # get only "normal" response
    for relation in rels:
        if not relation.isBroken() and relation.from_object.portal_type == "dmsoutgoingmail":
            markers.append("hasResponse")
            break
    # Stores on obj
    annot = IAnnotations(obj)
    annot["dmsmail.markers"] = markers
    return markers


@indexer(IImioDmsIncomingMail)
def markers_im_index(obj):
    """Indexer of various markers for IImioDmsIncomingMail"""
    return im_markers(obj)


def om_markers(obj):
    """Calculates IImioDmsOutgoingMail markers:

    * lastDmsFileIsOdt
    """
    markers = []
    # Set lastDmsFileIsOdt
    dfiles = object_values(obj, ["ImioDmsFile"])
    if dfiles and dfiles[-1].is_odt():
        markers.append("lastDmsFileIsOdt")
    # Stores on obj
    annot = IAnnotations(obj)
    annot["dmsmail.markers"] = markers
    return markers


@indexer(IImioDmsOutgoingMail)
def markers_om_index(obj):
    """Indexer of various markers for IImioDmsOutgoingMail"""
    return om_markers(obj)


def markers_conversion_error(obj):
    """Indexer of various markers for IDmsFile:

    * dvConvError
    """
    annot = IAnnotations(obj)
    markers = []
    if (obj.file and (obj.file.filename.endswith(".eml") or obj.file.contentType == "message/rfc822")) or \
            (annot.get("collective.documentviewer", {}).get("last_updated", "") == "2050-01-01T00:00:00"):
        markers.append("dvConvError")
    # Stores on obj
    annot["dmsmail.markers"] = markers
    return markers


@indexer(IDmsFile)
def markers_dmf_index(obj):
    return markers_conversion_error(obj)


@indexer(IDmsAppendixFile)
def markers_dmaf_index(obj):
    return markers_conversion_error(obj)


@indexer(IImioDmsIncomingMail)
def im_reception_date_index(obj):
    """Indexer of 'organization_type' for IImioDmsIncomingMail. Stores reception_date (in seconds) !"""
    # No acquisition pb because organization_type isn't an attr
    if obj.reception_date:
        return int(time.mktime(obj.reception_date.timetuple()))
    # there is by default a reception_date, but a user can empty it
    return 0


@indexer(IImioDmsOutgoingMail)
def om_outgoing_date_index(obj):
    """Indexer of 'organization_type' for IImioDmsOutgoingMail. Stores outgoing_date (in seconds) !"""
    # No acquisition pb because organization_type isn't an attr
    if obj.outgoing_date:
        return int(time.mktime(obj.outgoing_date.timetuple()))
    return 0


@indexer(IImioDmsOutgoingMail)
def sender_index(obj):
    """Indexer of 'sender_index' for IImioDmsOutgoingMail.

    Stores:
        * the sender UID
        * the organizations chain UIDs if the sender is held position, prefixed by 'l:'
    """
    if not obj.sender:
        return common_marker
    index = [obj.sender]
    sender = uuidToObject(obj.sender, unrestricted=True)
    # during a clear and rebuild, the sender is maybe not yet indexed...
    if sender:
        add_parent_organizations(sender.get_organization(), index)
    return index


@indexer(IOrganization)
def org_sortable_title_index(obj):
    """Indexer of 'sortable_title' for IOrganization. Stores organization chain concatenated by | !"""
    # sortable_title(org) returns <plone.indexer.delegate.DelegatingIndexer object> that must be called
    parts = [sortable_title(org)() for org in obj.get_organizations_chain() if org.title]
    parts and parts.append("")
    return "|".join(parts)


@indexer(IDmsDocument)
def state_group_index(obj):
    """Indexer of 'state_group' for IDmsDocument.

    Stores:
        * state,org_uid when validation is at org level
        * state only otherwise
    """
    # No acquisition pb because state_group isn't an attr
    state = api.content.get_state(obj=obj)
    portal_type = obj.portal_type
    if portal_type == "dmsincoming_email":
        portal_type = "dmsincomingmail"  # i_e ok
    # elif portal_type == 'dmsoutgoing_email':
    #     portal_type = 'dmsoutgoingmail'
    # set_dms_config(['review_states', 'dmsincomingmail'],  # i_e ok
    #                OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),
    #                             ('proposed_to_n_plus_1', {'group': '_n_plus_1', 'org': 'treating_groups'})]))
    config = get_dms_config(["review_states", portal_type])
    if state not in config or not config[state]["group"].startswith("_"):
        return state
    else:
        return "%s,%s" % (state, getattr(obj, config[state]["org"]))


@indexer(ITaskContent)
def task_state_group_index(obj):
    """Indexer of 'state_group' for ITaskContent."""
    return state_group_index(obj)


@indexer(IImioDmsOutgoingMail)
def send_modes_index(obj):
    """Indexer of 'Subject' for IImioDmsOutgoingMail. Stores send_modes !"""
    # No acquisition pb
    if obj.send_modes:
        return obj.send_modes
    return common_marker


@indexer(IContactContent)
def imio_contact_source(contact):
    """Metadata of 'contact_source' for IContactContent. Cleans value !"""
    # we get first a <plone.indexer.delegate.DelegatingIndexer object>
    value = contact_source(contact)().strip()
    return value.replace(", ,", "").replace("  ,", "").replace(",  ", "")


class ScanSearchableExtender(object):
    adapts(IScanFields)
    implements(IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def remove_extension(self, filename):
        if filename[-4:-3] == ".":
            return filename[:-4]
        return filename

    def searchable_text(self):
        items = [self.remove_extension(self.context.id)]
        if self.context.title:
            tit = self.remove_extension(self.context.title)
            if tit and tit not in items:
                items.append(tit)
        (sid, sid_long, sid_short) = get_scan_id(self.context)
        if sid:
            if sid != items[0]:
                items.append(sid)
            items.append(sid_long)
            if len(sid_short) >= 4:
                items.append(sid_short)
        if self.context.description:
            items.append(self.context.description)
        return u" ".join(items)

    def __call__(self):
        """Extend the searchable text with a custom string"""
        primary_field = IPrimaryFieldInfo(self.context)
        if primary_field.value is None:
            return self.searchable_text()
        mimetype = primary_field.value.contentType
        transforms = getToolByName(self.context, "portal_transforms")
        value = str(primary_field.value.data)
        filename = primary_field.value.filename
        try:
            transformed_value = transforms.convertTo("text/plain", value, mimetype=mimetype, filename=filename)
            if not transformed_value:
                return self.searchable_text()
            ret = _unicode_save_string_concat(self.searchable_text(), transformed_value.getData())
            if ret.startswith(" "):
                ret = ret[1:]
            return ret
        except:  # noqa
            return self.searchable_text()


class IdmSearchableExtender(object):
    """
    Extends SearchableText of scanned dms document.
    Concatenate the contained dmsmainfiles scan_id infos.
    """

    adapts(IImioDmsIncomingMail)
    implements(IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        # Dont use a catalog search to avoid bug in collective.indexing after optimize
        # brains = self.context.portal_catalog.unrestrictedSearchResults(object_provides='collective.dms.basecontent.'
        #                                                                'dmsfile.IDmsFile',
        #                                                                path={'query':
        #                                                                '/'.join(self.context.getPhysicalPath()),
        #                                                                'depth': 1})
        index = []
        for oid, obj in self.context.contentItems():
            if not IDmsFile.providedBy(obj):
                continue
            sid_infos = get_scan_id(obj)
            if sid_infos[0]:
                index += sid_infos
        if index:
            return u" ".join(index)


class OdmSearchableExtender(IdmSearchableExtender):
    """See IdmSearchableExtender"""

    adapts(IImioDmsOutgoingMail)


#########################
# vocabularies adapters #
#########################


class MissingTerms(MissingTermsMixin):

    complete_voc = NotImplemented
    field = NotImplemented
    widget = NotImplemented

    def getTerm(self, value):
        try:
            return super(MissingTermsMixin, self).getTerm(value)  # noqa
        except LookupError:
            try:
                return self.complete_voc().getTerm(value)
            except LookupError:
                pass
        if IContextAware.providedBy(self.widget) and not self.widget.ignoreContext:
            cur_value = getMultiAdapter((self.widget.context, self.field), IDataManager).query()
            if cur_value == value:
                return self._makeMissingTerm(value)
        raise

    def getTermByToken(self, token):
        try:
            return super(MissingTermsMixin, self).getTermByToken(token)  # noqa
        except LookupError:
            try:
                return self.complete_voc().getTermByToken(token)
            except LookupError:
                pass
        if IContextAware.providedBy(self.widget) and not self.widget.ignoreContext:
            value = getMultiAdapter((self.widget.context, self.field), IDataManager).query()
            term = self._makeMissingTerm(value)
            if term.token == token:
                return term
        raise LookupError(token)


class IMMCTV(MissingChoiceTermsVocabulary, MissingTerms):
    """Managing missing terms for IImioDmsIncomingMail."""

    def complete_voc(self):
        if self.field.getName() == "mail_type":
            return getUtility(IVocabularyFactory, "imio.dms.mail.IMMailTypesVocabulary")(self.context)
        elif self.field.getName() == "assigned_user":
            return getUtility(IVocabularyFactory, "plone.app.vocabularies.Users")(self.context)
        else:
            return SimpleVocabulary([])


class OMMCTV(MissingChoiceTermsVocabulary, MissingTerms):
    """Managing missing terms for IImioDmsOutgoingMail."""

    def complete_voc(self):
        if self.field.getName() == "mail_type":
            return getUtility(IVocabularyFactory, "imio.dms.mail.OMMailTypesVocabulary")(self.context)
        elif self.field.getName() == "sender":
            return getUtility(IVocabularyFactory, "imio.dms.mail.OMSenderVocabulary")(self.context)
        else:
            return SimpleVocabulary([])


#########################
# validation adapters #
#########################


class ContactAutocompleteValidator(SimpleFieldValidator):

    adapts(Interface, Interface, Interface, IField, IContactAutocompleteWidget)

    def validate(self, value, force=False):
        """
        Force validation when value is empty to force required validation.
        Because field is considered as not changed.
        """
        force = not value and True
        return super(ContactAutocompleteValidator, self).validate(value, force)


#########################
# DataManager adapters #
#########################


class DateDataManager(AttributeField):
    """DataManager for datetime widget"""

    def set(self, value):
        """The goal is to add seconds on dmsdocument and dmsfile datetime fields. For all fields ?"""
        if value is None:
            super(DateDataManager, self).set(value)
            return
        value_s = value.strftime("%Y%m%d%H%M")
        stored = self.query(default=None)
        stored_s = stored is not None and stored.strftime("%Y%m%d%H%M") or ""
        # store value if value is really changed
        if value_s != stored_s:
            # adding seconds
            if stored_s:
                value = value + datetime.timedelta(seconds=stored.second)
            super(DateDataManager, self).set(value)


class AssignedUserDataManager(AttributeField):
    """
    DataManager for assigned_user widget.
    To handle assigned_user default value as slave of MS.
    When request contains _default_assigned_user_ variable, this value is selected.
    """

    def query(self, default=NO_VALUE):
        """See z3c.form.interfaces.IDataManager"""
        if (
            self.field.__name__ == "assigned_user"
            and not getattr(self.adapted_context, "assigned_user")
            and "_default_assigned_user_" in self.context.REQUEST
        ):
            return self.context.REQUEST.get("_default_assigned_user_")
        return super(AssignedUserDataManager, self).query(default=default)


####################################
# Collective.classification adapters
####################################


@adapter(Interface)
@implementer(IServiceInCharge)
class ServiceInChargeAdapter(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        return getUtility(IVocabularyFactory, "collective.dms.basecontent.treating_groups")(self.context)


@adapter(Interface)
@implementer(IServiceInCopy)
class ServiceInCopyAdapter(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        return getUtility(IVocabularyFactory, "collective.dms.basecontent.recipient_groups")(self.context)


class ClassificationFolderInCopyGroupCriterion(object):
    """Return catalog criteria following recipient group member"""

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"recipient_groups": {"query": orgs}}


class ClassificationFolderInTreatingGroupCriterion(object):
    """Return catalog criteria following treating group member"""

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = get_plone_groups_for_user(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS, group_as_str=True)
        # if orgs is empty list, nothing is returned => ok
        return {"treating_groups": {"query": orgs}}


@implementer(ISendableAnnexesToPM)
class SendableAnnexesToPMAdapter(object):
    def __init__(self, context):
        self.context = context

    def get(self):
        for child in self.context.objectValues():
            if child.portal_type in ("dmsmainfile", "dmsappendixfile"):
                yield {
                    "title": child.title,
                    "UID": child.UID(),
                }
