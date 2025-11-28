# encoding: utf-8

from AccessControl import getSecurityManager
from borg.localrole.interfaces import ILocalRoleProvider
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
from collective.documentgenerator.utils import convert_and_save_odt
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import sort_categorized_elements
from collective.iconifiedcategory.utils import update_categorized_elements
from collective.task.interfaces import ITaskContent
from imio.dms.mail import _
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import OM_READER_SERVICE_FUNCTIONS
from imio.dms.mail.content.behaviors import IDmsMailCreatingGroup
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.interfaces import IOMApproval
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import is_dv_conv_in_error
from imio.dms.mail.utils import logger
from imio.esign.utils import add_files_to_session
from imio.helpers import EMPTY_DATE
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_relations
from imio.helpers.content import object_values
from imio.helpers.content import uuidToCatalogBrain
from imio.helpers.content import uuidToObject
from imio.helpers.emailer import validate_email_address
from imio.helpers.workflow import do_transitions
from imio.pm.wsclient.interfaces import ISendableAnnexesToPM
from imio.prettylink.adapters import PrettyLinkAdapter
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
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
from Products.CMFPlone.utils import safe_unicode
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
import os
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
def approvings_index(obj):
    """Indexer of 'approvings' for IImioDmsOutgoingMail.

    Stores userid:number for each approver.
    """
    approval = OMApprovalAdapter(obj)
    return approval.current_approvers


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
    # Set emailSent:
    if obj.email_status:
        markers.append("emailSent")
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
    if is_dv_conv_in_error(obj):
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


class ItemSignersAdapter(object):
    """Adapter to get signers of a given item.

    Not used for the moment because we use approval mechanism."""

    def __init__(self, context):
        self.context = context

    def get_signers(self):
        """Return the list of signers for the item."""
        # make sure signers are sorted by signature number
        for signer in self.context.signers:
            if signer["signer"] == "_empty_":
                continue
            hp = uuidToObject(signer["signer"], unrestricted=True)
            if hp:
                yield {
                    "held_position": hp,
                    "name": hp.get_person().get_title(include_person_title=False),
                    "function": hp.label or u"",
                }

    def get_files_uids(self):
        """List of file uids.

        :return: list of uid of files
        """
        # must get here already converted file in pdf format...
        return []
        # for sub_content in self.context.values():
        #     if sub_content.portal_type in ("dmsommainfile", "dmsappendixfile"):
        #         yield sub_content.UID()


@implementer(ILocalRoleProvider)
class ApprovalRoleAdapter(object):
    """borg.localrole adapter to set localrole for signing approvers and signers"""

    def __init__(self, context):
        self.context = context

    def getRoles(self, principal):
        """Returns an iterable of roles granted to the specified user object"""
        return self.config.get(principal, ())

    def getAllRoles(self):
        """Returns an iterable consisting of tuples of the form: (principal_id, sequence_of_roles)"""
        config = self.config
        if not config:
            yield "", ("",)
            return
        for principal, roles in config.items():
            yield principal, roles

    @property
    def config(self):
        approval = OMApprovalAdapter(self.context)
        return approval.roles


@implementer(IOMApproval)
class OMApprovalAdapter(object):
    """Adapter for outgoing mail approval.

    Annotation structure: metadata + 2D matrix with n signers and m files

    ### Metadata
    self.annot["session_id"] = str
        The unique id of the internal approval session
    self.annot["signers"] = list[n] (userid, name, label)
        The list of signers for the approval process
    self.annot["approvers"] = list[n] tuple(userids)
        The list of approvers for the approval process, one tuple for each signer
    self.annot["editors"] = list[n] bool
        The list of editor flags for the approval process, one bool for each signer
    self.annot["files"] = list[m] file_uids
        The list of files to be approved
    self.annot["pdf_files"] = list[m] pdf_file_uids
        The list of pdf files generated for external signature

    ### Matrix
    self.annot["approval"][n][m] = {
        'status': 'w' | 'p' | 'a'  # Waiting | Proposed | Approved
        "approved_on": datetime,
        "approved_by": userid,
    }
    """

    def __init__(self, context):
        self.context = context
        self.annot = IAnnotations(self.context).setdefault(
            "idm.approval",
            PersistentMapping(
                {
                    # Metadata
                    "session_id": None,
                    "signers": PersistentList(),
                    "editors": PersistentList(),
                    "approvers": PersistentList(),
                    "files": PersistentList(),
                    "pdf_files": PersistentList(),
                    # Matrix
                    "approval": PersistentList(),
                }
            ),
        )

    def reset(self):
        """Reset approval annotation."""
        # Metadata
        self.annot["session_id"] = None
        self.annot["signers"] = PersistentList()
        self.annot["editors"] = PersistentList()
        self.annot["approvers"] = PersistentList()
        self.annot["files"] = PersistentList()
        self.annot["pdf_files"] = PersistentList()
        # Matrix
        self.annot["approval"] = PersistentList()

    @property
    def session_id(self):
        """Return the unique session id of the approval process."""
        return self.annot["session_id"]

    @property
    def files_uids(self):
        """Return the UIDs of the files to be approved."""
        return self.annot["files"]

    @property
    def pdf_files_uids(self):
        """Return the UIDs of the pdf files to be signed externally, or None if the pdf files doesn't exist."""
        return self.annot["pdf_files"]

    @property
    def signers(self):
        """Return the list of users ids who are signers, in order."""
        return [x[0] for x in self.annot["signers"]]

    @property
    def signers_details(self):
        """Return a list of tuple (position, name, function) containing signers."""
        signers_details = []
        for nb, signer in enumerate(self.annot["signers"]):
            signers_details.append((nb, signer[1], signer[2]))
        return signers_details

    @property
    def approvers(self):
        """Return the list of users ids who are approvers, flattened."""
        approvers = set()
        for i_approvers in self.annot["approvers"]:
            approvers = approvers.union(set(i_approvers))
        return list(approvers)

    @property
    def current_nb(self):
        """
        Return the index of the approval to be approved.
        -1 if all approved
        None if no approval in progress
        """
        if len(self.files_uids) == 0:
            return None
        # TODO pourquoi recalculer tout le temps une valeur qui pourrait etre stockée à chaque changement ?
        for nb in range(len(self.annot["approval"])):
            waiting_statuses = [d["status"] == "w" for d in self.annot["approval"][nb]]
            if not all(waiting_statuses):
                break
        else:
            return None

        for nb in range(len(self.annot["approval"])):
            approved_statuses = [d["status"] == "a" for d in self.annot["approval"][nb]]
            # Checks if any file pending approval at this nb
            if not all(approved_statuses):
                return nb

        return -1  # all approved

    @property
    def current_approvers(self):
        """Return the list of user ids who are approvers in this numbered step."""
        current_nb = self.current_nb
        if current_nb is not None and current_nb >= 0:
            return self.annot["approvers"][current_nb]
        return []

    def get_approver_nb(self, userid):
        """Return the approval number (index) for a given approver userid."""
        for nb, nb_approvers in enumerate(self.annot["approvers"]):
            if userid in nb_approvers:
                return nb
        return None

    @property
    def roles(self):
        roles = {}
        current_nb = self.current_nb
        state = api.content.get_state(self.context)
        if current_nb is None or state not in ("to_approve", "to_print", "to_be_signed", "signed", "sent"):
            return roles
        for nb, nb_approvers in enumerate(self.annot["approvers"]):
            if 0 <= current_nb < nb:
                continue  # only users that can approve have visibility
            userid, __, __ = self.annot["signers"][nb]
            roles[userid] = ("Reader",)
            for approver in nb_approvers:
                def_roles = ["Reader"]
                # TODO add a specific role and permission to manage approval ?
                if self.annot["editors"][nb] and current_nb == nb:  # only current approvers are editors
                    def_roles.append("Editor")
                # normally we don't overwrite existing userid because an approver cannot be signer
                roles[approver] = tuple(def_roles)
        return roles

    def start_approval_process(self):
        """Update the annotation to start the approval process."""
        orig_nb = self.current_nb
        if self.approvers:
            # first time transition, set the first level to "proposed"
            if orig_nb is None:
                for i_fuid in range(len(self.files_uids)):
                    self.annot["approval"][0][i_fuid]["status"] = "p"
            # approve again after a back... maybe some approvals are already done
            else:
                c_a = None
                for i_fuid, fuid in enumerate(self.files_uids):
                    # If file approved, check if modified since approval
                    brain = uuidToCatalogBrain(fuid, unrestricted=True)
                    last_mod = brain.modified
                    last_mod = datetime.datetime(
                        last_mod.year(),
                        last_mod.month(),
                        last_mod.day(),
                        last_mod.hour(),
                        last_mod.minute(),
                        int(last_mod.second()),
                        int(last_mod.micros() % 1000000),
                    )
                    for nb in range(len(self.annot["approval"])):
                        # If file not approved, save current approval nb
                        if self.annot["approval"][nb][i_fuid]["status"] != "a":
                            if c_a is None or nb < c_a:
                                c_a = nb
                            continue
                        if last_mod > self.annot["approval"][nb][i_fuid]["approved_on"]:
                            self.annot["approval"][nb][i_fuid]["approved_on"] = None
                            self.annot["approval"][nb][i_fuid]["approved_by"] = None
                            if c_a is None or nb < c_a:
                                c_a = nb
                            self.annot["approval"][nb][i_fuid]["status"] = "p"
                # set next approvals to "waiting"
                if c_a is not None:
                    for nb in range(c_a, len(self.annot["approval"])):
                        for i_fuid in range(len(self.files_uids)):
                            if c_a == nb and self.annot["approval"][nb][i_fuid]["status"] != "a":
                                self.annot["approval"][nb][i_fuid]["status"] = "p"
                            elif self.annot["approval"][nb][i_fuid]["status"] == "p":
                                self.annot["approval"][nb][i_fuid]["status"] = "w"
        if orig_nb != self.current_nb:
            self.context.portal_catalog.reindexObject(self.context, idxs=("approvings",), update_metadata=0)

    def update_signers(self):
        """Update the annotation with the current signers from the mail context."""
        # Create approvals backup to restore after update
        backup_files_uids = []
        backup_approvals = []
        for fuid_index, fuid in enumerate(self.files_uids):
            backup_files_uids.append(fuid)
            backup_approvals.append([])
            for nb in range(len(self.annot["approval"])):
                if self.annot["approval"][nb][fuid_index]["status"] == "a":
                    backup_approval = self.annot["approval"][nb][fuid_index]
                    backup_approval["signer"] = self.signers[nb]
                    backup_approvals[fuid_index].append(backup_approval)
        self.reset()

        signer_emails = set()
        signers = sorted(self.context.signers, key=lambda s: s["number"])
        for signer in signers:
            if signer["signer"] == "_empty_":
                continue
            signer_hp = uuidToObject(signer["signer"], unrestricted=True)
            if signer_hp is None:
                raise ValueError(
                    _(
                        u"The signer held position with UID ${uid} does not exist !",
                        mapping={"uid": signer["signer"]},
                    )
                )
            signer_person = signer_hp.get_person()
            user_email = api.user.get(signer_person.userid).getProperty("email")
            if user_email in signer_emails:
                raise ValueError(
                    _(
                        u"You cannot have the same email (${email}) for multiple signers !",
                        mapping={"email": user_email},
                    )
                )
            signer_emails.add(user_email)

            approvers = []
            for approving in signer["approvings"] or []:
                if approving == "_empty_":
                    continue
                if approving == "_themself_":
                    person = signer_person
                else:
                    person = uuidToObject(approving, unrestricted=True)
                userid = person.userid
                if userid in self.approvers:
                    raise ValueError(
                        _(
                            "The ${userid} already exists in the approvings with another order ${o} <=> ${c}",
                            mapping={
                                "userid": userid,
                                "o": next(
                                    nb
                                    for nb, nb_approvers in enumerate(self.annot["approvers"])
                                    if userid in nb_approvers
                                )
                                + 1,
                                "c": len(self.annot["approvers"]) + 1,
                            },
                        )
                    )
                approvers.append(userid)

            # Add signer in annotation
            signer_name = signer_person.get_title(include_person_title=False)
            signer_label = signer_hp.label or u""
            self.annot["signers"].append((signer_person.userid, signer_name, signer_label))
            self.annot["approvers"].append(approvers)
            self.annot["editors"].append(signer["editor"])
            self.annot["approval"].append(PersistentList())
            for f_uid in self.files_uids:
                self.annot["approval"][-1].append(
                    PersistentMapping(
                        {
                            "status": "w",
                            "approved_on": None,
                            "approved_by": None,
                        }
                    )
                )

        for fuid in backup_files_uids:
            self.add_file_to_approval(fuid)
        if api.content.get_state(self.context) == "to_approve":
            self.start_approval_process()

        # Restore backups
        for fuid_index, fuid in enumerate(backup_files_uids):
            for backup_approval in backup_approvals[fuid_index]:
                if backup_approval["signer"] not in self.signers:
                    continue  # signer removed
                signer_index = self.signers.index(backup_approval["signer"])
                self.approve_file(
                    uuidToObject(fuid, unrestricted=True),
                    backup_approval["approved_by"],
                    transition="propose_to_be_signed",
                    c_a=signer_index,
                )
                approved_on = backup_approval["approved_on"]
                self.annot["approval"][signer_index][fuid_index]["approved_on"] = approved_on

    def add_file_to_approval(self, f_uid):
        """Add a file to approval annotation."""
        if f_uid in self.files_uids:
            return
        self.annot["files"].append(f_uid)
        self.annot["pdf_files"].append(None)
        for nb in range(len(self.annot["approval"])):
            self.annot["approval"][nb].append(
                PersistentMapping(
                    {
                        "status": "w",
                        "approved_on": None,
                        "approved_by": None,
                    }
                )
            )

    def remove_file_from_approval(self, f_uid):
        """Remove a file from approval annotation."""
        if f_uid not in self.files_uids:
            return
        file_index = self.files_uids.index(f_uid)
        self.annot["files"].remove(f_uid)
        self.annot["pdf_files"].remove(self.annot["pdf_files"][file_index])
        for nb in range(len(self.annot["approval"])):
            self.annot["approval"][nb].pop(file_index)

    def is_file_approved(self, f_uid, userid=None, nb=None, totally=True):
        """Check if file is approved.

        :param f_uid: file uid
        :param userid: if set, check only for this approver's userid, and ignores 'totally' and 'nb' param if set.
        :param nb: if set, check only for this approval number, and ignores 'totally' param if set.
        :param totally: if True, return True if at least one approval number is approved
                        if False, return True if all approval numbers are approved
        :return: bool
        """
        if f_uid not in self.files_uids:
            return False
        file_index = self.files_uids.index(f_uid)

        if userid is not None:
            if userid not in self.approvers:
                return False
            approver_index = next(
                nb for nb, nb_approvers in enumerate(self.annot["approvers"]) if userid in nb_approvers
            )
            return self.annot["approval"][approver_index][file_index]["status"] == "a"

        if nb is not None:
            if 0 <= nb < len(self.annot["approval"]):
                return self.annot["approval"][nb][file_index]["status"] == "a"
            return False

        if totally:
            return all(
                self.annot["approval"][nb][file_index]["status"] == "a" for nb in range(len(self.annot["approval"]))
            )
        else:
            return any(
                self.annot["approval"][nb][file_index]["status"] == "a" for nb in range(len(self.annot["approval"]))
            )

    def can_approve(self, userid, f_uid, editable=True):
        """Check if user can approve the file.

        :param userid: user id
        :param f_uid: file uid
        :param editable: is file editable
        :return: bool
        """
        c_a = self.current_nb  # current approval
        if c_a is None:  # to early
            return False
        if userid not in self.approvers:  # not an approver
            return False
        if f_uid not in self.files_uids:  # file not in approval
            return False
        if not editable:
            return False
        approver_index = next(nb for nb, nb_approvers in enumerate(self.annot["approvers"]) if userid in nb_approvers)
        if approver_index != c_a:  # cannot approve now
            return False
        return True

    def approve_file(self, afile, userid, values=None, transition=None, c_a=None):
        """Approve the current file.

        :param afile: file to approve
        :param userid: current user id
        :param values: optional dict to update
        :param transition: optional transition to do after approval
        :param c_a: overrides current approval number to mark approval, if None uses current_nb
        :return: approval status bool (True=ok), reload bool (True=reload page)
        """
        request = afile.REQUEST
        if c_a is None:
            c_a = self.current_nb  # current approval
        if c_a is None:
            raise ValueError("There is no approval in progress !")
        f_uid = afile.UID()
        if f_uid not in self.files_uids:
            raise ValueError("The file '%s' is not in the approval list !" % f_uid)
        f_index = self.annot["files"].index(f_uid)
        # approve
        self.annot["approval"][c_a][f_index]["status"] = "a"
        self.annot["approval"][c_a][f_index]["approved_on"] = datetime.datetime.now()
        self.annot["approval"][c_a][f_index]["approved_by"] = userid
        pc = getToolByName(self.context, "portal_catalog")
        if self.is_file_approved(f_uid):
            afile.approved = True
            if values is not None:
                values["approved"] = True
        yet_to_approve = [fuid for fuid in self.files_uids if not self.is_file_approved(fuid, userid=userid)]
        if yet_to_approve:
            user = api.user.get(userid)
            if user is None:
                raise ValueError("The user '%s' does not exist !" % userid)
            fullname = user.getProperty("fullname") or userid
            api.portal.show_message(
                message=_(
                    u"The file '${file}' has been approved by ${user}. However, there is/are yet ${nb} files "
                    u"to approve on this mail.",
                    mapping={"file": safe_unicode(afile.Title()), "user": fullname, "nb": len(yet_to_approve)},
                ),
                request=request,
                type="info",
            )
            return True, True
        message = u"The file '${file}' has been approved by ${user}. "
        max_number = len(self.annot["approval"])
        c_a = self.current_nb  # current approval
        if c_a is not None and 0 <= c_a < max_number:
            for i in range(len(self.files_uids)):
                if self.annot["approval"][c_a][i]["status"] != "a":
                    self.annot["approval"][c_a][i]["status"] = "p"
            pc.reindexObject(self.context, idxs=("approvings",), update_metadata=0)
            self.context.reindexObjectSecurity()  # to update local roles from adapter
            message += u"Next approval number is ${nb}."
            api.portal.show_message(
                message=_(message, mapping={"file": safe_unicode(afile.Title()), "user": userid, "nb": c_a + 1}),
                request=request,
                type="info",
            )
            return True, True
        else:
            pc.reindexObject(self.context, idxs=("approvings",), update_metadata=0)
            message += u"All approvals have been done for this file."
            api.portal.show_message(
                message=_(message, mapping={"file": safe_unicode(afile.Title()), "user": userid}),
                request=request,
                type="info",
            )
            # we create a signing session if needed
            if self.context.esign:
                with api.env.adopt_roles(["Manager"]):
                    ret, msg = self.add_mail_files_to_session()
                    if not ret:
                        api.portal.show_message(
                            message=_(
                                u"There was an error while creating the signing session: ${msg} !", mapping={"msg": msg}
                            ),
                            request=request,
                            type="error",
                        )
                        return False, True
                    else:
                        api.portal.show_message(
                            message=_(u"A signing session has been created: ${msg}.", mapping={"msg": msg}),
                            request=request,
                            type="info",
                        )
            if transition:
                # must use the following ?
                # do_next_transition(self.context, self.context.portal_type, state="to_approve")
                with api.env.adopt_roles(["Reviewer"]):
                    do_transitions(self.context, [transition])
                    # api.portal.show_message(
                    #     message=_(u"The mail has been automatically transitioned to state '${state}'.",
                    #               mapping={"state": self.context.portal_workflow.getInfoFor(self.context,
                    #               "review_state")}),
                    #     request=request,
                    #     type="info",
                    # )
            return True, True
        return True, False

    def unapprove_file(self, afile, signer_userid):
        """Unapprove the current file.

        :param afile: file to unapprove
        :param signer_userid: userid of the signer to remove approval for
        """
        f_uid = afile.UID()
        if f_uid not in self.files_uids:
            raise ValueError("The file '%s' is not in the approval list !" % afile.Title())
        f_index = self.annot["files"].index(f_uid)

        if signer_userid not in self.signers:
            raise ValueError("The user '%s' is not a signer !" % signer_userid)

        orig_nb = self.current_nb
        nb = self.signers.index(signer_userid)

        self.annot["approval"][nb][f_index]["status"] = "w"
        self.annot["approval"][nb][f_index]["approved_on"] = None
        self.annot["approval"][nb][f_index]["approved_by"] = None

        afile.approved = False

        if orig_nb != self.current_nb:
            pc = getToolByName(self.context, "portal_catalog")
            pc.reindexObject(self.context, idxs=("approvings",), update_metadata=0)
            self.context.reindexObjectSecurity()  # to update local roles from adapter

        self.start_approval_process()

    def add_mail_files_to_session(self):
        """Add mail files to sign session."""
        if not self.files_uids:
            return False, "No files"
        not_approved = [fuid for fuid in self.files_uids if not self.is_file_approved(fuid)]
        if not_approved:
            return False, "Not all files approved"
        file_uids = []
        for i, f_uid in enumerate(self.files_uids):
            fobj = uuidToObject(f_uid)
            if not fobj:
                continue
            if self.pdf_files_uids[i]:  # already done ??
                continue
            if not fobj.scan_id or len(fobj.scan_id) != 15:
                api.portal.show_message(
                    message=_(
                        "File '${file}' has no or a wrong scan id, it cannot be added to sign session.",
                        mapping={"file": fobj.absolute_url()},
                    ),
                    request=self.context.REQUEST,
                    type="error",
                )
                return False, "Bad scan_id for file uid {}".format(f_uid)
                # return False, "File without scan id"
            # new_filename like u'Modele de base avec sceau S0013 Test sceau 4.odt (limited to 120 chars)
            f_title = os.path.splitext(fobj.file.filename)[0]
            new_filename = u"{}.pdf".format(f_title)
            # TODO which pdf format to choose ?
            pdf_file = convert_and_save_odt(
                fobj.file,
                self.context,
                "dmsommainfile",
                new_filename,
                fmt="pdf",
                from_uid=f_uid,
                attributes={
                    "to_sign": True,
                    "content_category": fobj.content_category,
                    "to_approve": False,
                    "approved": fobj.approved,
                    "scan_id": fobj.scan_id,
                    "scan_user": fobj.scan_user,
                },
            )
            # TODO is to_sign attribute set from content_category
            pdf_uid = pdf_file.UID()
            self.pdf_files_uids[i] = pdf_uid
            # we rename the pdf filename to include pdf uid. So after the file is later consumed, we can retrieve object
            pdf_file.file.filename = u"{}__{}.pdf".format(f_title, pdf_uid)
            # check if special attributes must be updated (when to_approve and approved False, event set default values)
            if pdf_file.to_approve or pdf_file.approved != fobj.approved:
                pdf_file.to_approve = False
                pdf_file.approved = fobj.approved
                self.remove_file_from_approval(pdf_uid)
                update_categorized_elements(
                    self.context,
                    pdf_file,
                    get_category_object(self.context, pdf_file.content_category),
                    limited=True,
                    sort=False,
                    logging=True,
                )
            file_uids.append(pdf_uid)
        sort_categorized_elements(self.context)
        signers = []
        for signer, (nb, name, label) in zip(self.signers, self.signers_details):
            user = api.user.get(signer)
            email = user.getProperty("email")
            signers.append((signer, email, name, label))
        watcher_users = api.user.get_users(groupname="esign_watchers")
        watcher_emails = [user.getProperty("email") for user in watcher_users]
        session_id, session = add_files_to_session(signers, file_uids, bool(self.context.seal), watchers=watcher_emails)
        self.annot["session_id"] = session_id
        return True, "{} files added to session number {}".format(len(file_uids), session_id)
