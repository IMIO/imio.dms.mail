# encoding: utf-8

from AccessControl import getSecurityManager
from collective.dexteritytextindexer.interfaces import IDynamicTextIndexExtender
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.indexers import contact_source
from collective.contact.core.interfaces import IContactContent
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.widget.interfaces import IContactAutocompleteWidget
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.basecontent.dmsfile import IDmsAppendixFile
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.dms.mailcontent.indexers import add_parent_organizations
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task.interfaces import ITaskContent
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import EMPTY_DATE
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import OM_READER_SERVICE_FUNCTIONS
from imio.dms.mail.dmsmail import IImioDmsIncomingMail
from imio.dms.mail.dmsmail import IImioDmsOutgoingMail
from imio.dms.mail.overrides import IDmsPerson
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import get_scan_id
from imio.dms.mail.utils import highest_review_level
from imio.dms.mail.utils import logger
from imio.prettylink.adapters import PrettyLinkAdapter
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu
from plone.app.contenttypes.indexers import _unicode_save_string_concat
from plone.app.uuid.utils import uuidToObject
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import sortable_title
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker as common_marker
from z3c.form.datamanager import AttributeField
from z3c.form.interfaces import IContextAware
from z3c.form.interfaces import IDataManager
from z3c.form.term import MissingChoiceTermsVocabulary
from z3c.form.term import MissingTermsMixin
from z3c.form.validator import SimpleFieldValidator
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
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

default_criterias = {'dmsincomingmail': {'review_state': {'query': ['proposed_to_manager', 'proposed_to_pre_manager',
                                                                    'proposed_to_service_chief']}},
                     'task': {'review_state': {'query': ['to_assign', 'realized']}}}


def highest_validation_criterion(portal_type):
    """
        Return a query criterion corresponding to current user highest validation level
        NO MORE USED
    """
    if portal_type == 'dmsincoming_email':
        portal_type = 'dmsincomingmail'
    groups = api.group.get_groups(user=api.user.get_current())
    highest_level = highest_review_level(portal_type, str([g.id for g in groups]))
    if highest_level is None:
        return default_criterias[portal_type]
    ret = {}
    review_levels = get_dms_config(['review_levels'])
    criterias = review_levels[portal_type][highest_level]
    if 'st' in criterias:
        ret['review_state'] = {'query': criterias['st']}
    if 'org' in criterias:
        organizations = []
        for group in groups:
            if group.id.endswith(highest_level):
                organizations.append(group.id[:-len(highest_level)])
        ret[criterias['org']] = {'query': organizations}
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
        return highest_validation_criterion('dmsincomingmail')


class TaskHighestValidationCriterion(object):
    """
        Return catalog criteria following highest validation group member
        NOT USED
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion('task')


def validation_criterion(context, portal_type):
    """ Return a query criterion corresponding to current user validation level """
    if portal_type == 'dmsincoming_email':
        portal_type = 'dmsincomingmail'
    groups = api.group.get_groups(user=api.user.get_current())
    groups_ids = [g.id for g in groups]
    config = get_dms_config(['review_levels', portal_type])
    # set_dms_config(['review_levels', 'dmsincomingmail'],
    #            OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
    #                         ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})]))

    ret = {'state_group': {'query': []}}
    for group_or_suffix in config:
        if not group_or_suffix.startswith('_'):
            if group_or_suffix in groups_ids:
                for state in config[group_or_suffix]['st']:
                    ret['state_group']['query'].append(state)
        else:
            # get orgs of user groups with suffix
            orgs = organizations_with_suffixes(groups, [group_or_suffix[1:]])
            if orgs:
                for state in config[group_or_suffix]['st']:
                    for org in orgs:
                        ret['state_group']['query'].append('%s,%s' % (state, org))
    return ret


class IncomingMailValidationCriterion(object):
    """
        Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, 'dmsincomingmail')


class TaskValidationCriterion(object):
    """
        Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, 'task')


class OutgoingMailValidationCriterion(object):
    """
        Return catalog criteria following validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return validation_criterion(self.context, 'dmsoutgoingmail')


class IncomingMailInTreatingGroupCriterion(object):
    """
        Return catalog criteria following treating group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'treating_groups': {'query': orgs}}


class OutgoingMailInTreatingGroupCriterion(object):
    """
        Return catalog criteria following treating group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, OM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'treating_groups': {'query': orgs}}


class IncomingMailInCopyGroupCriterion(object):
    """
        Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': {'query': orgs}}


class IncomingMailInCopyGroupUnreadCriterion(object):
    """
        Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        user = api.user.get_current()
        groups = api.group.get_groups(user=user)
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': {'query': orgs}, 'labels': {'not': ['%s:lu' % user.id]}}


class IncomingMailFollowedCriterion(object):
    """
        Return catalog criteria for 'suivi' label
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return {'labels': {'query': '%s:suivi' % api.user.get_current().id}}


class OutgoingMailInCopyGroupCriterion(object):
    """
        Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, OM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': {'query': orgs}}


class TaskInAssignedGroupCriterion(object):
    """
        Return catalog criteria following assigned group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'assigned_group': {'query': orgs}}


class TaskInProposingGroupCriterion(object):
    """
        Return catalog criteria following enquirer group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, IM_READER_SERVICE_FUNCTIONS)
        # if orgs is empty list, nothing is returned => ok
        return {'mail_type': {'query': orgs}}


################
# GUI cleaning #
################

class ActionsSubMenuItem(OrigActionsSubMenuItem):

    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission('Manage portal', self.context):
            return False
        return super(ActionsSubMenuItem, self).available()


class FactoriesSubMenuItem(OrigFactoriesSubMenuItem):

    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission('Manage portal', self.context):
            return False
        return super(FactoriesSubMenuItem, self).available()


class WorkflowMenu(OrigWorkflowMenu):

    def getMenuItems(self, context, request):
        if not getSecurityManager().checkPermission('Manage portal', context):
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
            if api.content.get_state(self.context) in (registry.get(
                    'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states') or []):
                icons.append(("++resource++imio.dms.mail/remark.gif", translate("Remark icon", domain="imio.dms.mail",
                                                                                context=self.request)))
        back_or_again_icon = self.context.get_back_or_again_icon()
        if back_or_again_icon:
            icons.append((back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail",
                                                        context=self.request)))
        return icons


class OMPrettyLinkAdapter(PrettyLinkAdapter):

    def _leadingIcons(self):
        icons = []
        if self.context.task_description and self.context.task_description.raw:
            registry = getUtility(IRegistry)
            if api.content.get_state(self.context) in (registry.get(
                    'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states') or []):
                icons.append(("++resource++imio.dms.mail/remark.gif", translate("Remark icon", domain="imio.dms.mail",
                                                                                context=self.request)))
        back_or_again_icon = self.context.get_back_or_again_icon()
        if back_or_again_icon:
            icons.append((back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail",
                                                        context=self.request)))
        return icons


class TaskPrettyLinkAdapter(PrettyLinkAdapter):

    def _leadingIcons(self):
        icons = []
        back_or_again_icon = BACK_OR_AGAIN_ICONS[back_or_again_state(self.context)]
        if back_or_again_icon:
            icons.append((back_or_again_icon, translate(back_or_again_icon, domain="imio.dms.mail",
                                                        context=self.request)))
        return icons


####################
# Indexes adapters #
####################

@indexer(IContentish)
def mail_type_index(obj):
    """ Index method escaping acquisition """
    if base_hasattr(obj, 'mail_type') and obj.mail_type:
        return obj.mail_type
    return common_marker


@indexer(IDmsPerson)
def person_userid_index(obj):
    """ Index method escaping acquisition. We use an existing index 'mail_type' to store person userid """
    if base_hasattr(obj, 'userid') and obj.userid:
        return obj.userid
    return common_marker


@indexer(IHeldPosition)
def heldposition_userid_index(obj):
    """ Index method escaping acquisition. We use an existing index 'mail_type' to store heldposition userid """
    parent = obj.aq_parent
    if base_hasattr(parent, 'userid') and parent.userid:
        return parent.userid
    return common_marker


@indexer(ITaskContent)
def task_enquirer_index(obj):
    """ Index method escaping acquisition. We use an existing index 'mail_type' to store task enquirer """
    if base_hasattr(obj, 'enquirer') and obj.enquirer:
        return obj.enquirer
    return common_marker


@indexer(IImioDmsIncomingMail)
def mail_date_index(obj):
    # No acquisition pb because mail_date isn't an attr but cannot store None
    if obj.original_mail_date:
        return obj.original_mail_date
    else:
        return EMPTY_DATE
    # return common_marker


@indexer(IImioDmsOutgoingMail)
def om_mail_date_index(obj):
    if base_hasattr(obj, 'mail_date'):
        if obj.mail_date:
            return obj.mail_date
        else:
            return EMPTY_DATE
    return common_marker


@indexer(IImioDmsIncomingMail)
def in_out_date_index(obj):
    # No acquisition pb because in_out_date isn't an attr
    if obj.reception_date:
        return obj.reception_date
    return EMPTY_DATE


@indexer(IImioDmsOutgoingMail)
def om_in_out_date_index(obj):
    # No acquisition pb because in_out_date isn't an attr
    if obj.outgoing_date:
        return obj.outgoing_date
    else:
        return EMPTY_DATE


@indexer(IImioDmsIncomingMail)
def im_reception_date_index(obj):
    # No acquisition pb because organization_type isn't an attr
    if obj.reception_date:
        return int(time.mktime(obj.reception_date.timetuple()))
    # there is by default a reception_date, but a user can empty it
    return 0


@indexer(IImioDmsOutgoingMail)
def om_outgoing_date_index(obj):
    # No acquisition pb because organization_type isn't an attr
    if obj.outgoing_date:
        return int(time.mktime(obj.outgoing_date.timetuple()))
    return 0


@indexer(IDmsDocument)
def state_group_index(obj):
    # Index contains state,org when validation is at org level, or state only otherwise
    # No acquisition pb because state_group isn't an attr
    # set_dms_config(['review_states', 'dmsincomingmail'],
    #                OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),
    #                             ('proposed_to_n_plus_1', {'group': '_n_plus_1', 'org': 'treating_groups'})]))
    state = api.content.get_state(obj=obj)
    if obj.portal_type == 'dmsincoming_email':
        portal_type = 'dmsincomingmail'
    elif obj.portal_type == 'dmsoutgoing_email':
        portal_type = 'dmsoutgoingmail'
    else:
        portal_type = obj.portal_type
    config = get_dms_config(['review_states', portal_type])
    if state not in config or not config[state]['group'].startswith('_'):
        return state
    else:
        return "%s,%s" % (state, getattr(obj, config[state]['org']))


@indexer(ITaskContent)
def task_state_group_index(obj):
    return state_group_index(obj)


@indexer(IOrganization)
def org_sortable_title_index(obj):
    """ Return organization chain concatenated by | """
    # sortable_title(org) returns <plone.indexer.delegate.DelegatingIndexer object> that must be called
    parts = [sortable_title(org)() for org in obj.get_organizations_chain() if org.title]
    parts and parts.append('')
    return '|'.join(parts)


@indexer(IImioDmsOutgoingMail)
def sender_index(obj):
    """
        return an index containing:
        * the sender UID
        * the organizations chain UIDs if the sender is held position, prefixed by 'l:'
    """
    if not obj.sender:
        return common_marker
    index = [obj.sender]

    add_parent_organizations(uuidToObject(obj.sender).get_organization(), index)
    return index


@indexer(IImioDmsIncomingMail)
def get_full_title_index(obj):
    # No acquisition pb because get_full_title isn't an attr
    if obj.title:
        return obj.title.encode('utf8')
    return common_marker


@indexer(IDmsDocument)
def creating_group_index(obj):
    if base_hasattr(obj, 'creating_group') and obj.creating_group:
        return obj.creating_group
    return common_marker


@indexer(IContactContent)
def contact_creating_group_index(obj):
    if base_hasattr(obj, 'creating_group') and obj.creating_group:
        return obj.creating_group
    return common_marker


@indexer(IContactContent)
def imio_contact_source(contact):
    # we get first a <plone.indexer.delegate.DelegatingIndexer object>
    value = contact_source(contact)().strip()
    return value.replace(', ,', '').replace('  ,', '').replace(',  ', '')


# See getObjSize_file method from plone/app/contenttypes/indexers.py
# See Products/CMFPlone/skins/plone_scripts/getObjSize.py
def get_obj_size(obj):
    try:
        primary_field_info = IPrimaryFieldInfo(obj)
    except TypeError:
        logger.warn(u'Lookup of PrimaryField failed for %s' % obj.absolute_url())
        return
    const = {'KB': 1024, 'MB': 1048576, 'GB': 1073741824}
    order = ('GB', 'MB', 'KB')
    size = primary_field_info.value.size
    if size < 1024:
        return '1 KB'
    for c in order:
        if size / const[c] > 0:
            break
    return '%.1f %s' % (float(size / float(const[c])), c)  # noqa


@indexer(IDmsAppendixFile)
def get_obj_size_af_index(obj):
    return get_obj_size(obj)


@indexer(IDmsFile)
def get_obj_size_df_index(obj):
    return get_obj_size(obj)


class ScanSearchableExtender(object):
    adapts(IScanFields)
    implements(IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def searchable_text(self):
        items = [self.context.id.endswith('.pdf') and self.context.id[0:-4] or self.context.id]
        tit = (self.context.title and self.context.title != self.context.id and
               (self.context.title.endswith('.pdf') and self.context.title[0:-4] or self.context.title) or u"")
        if tit:
            items.append(tit)
        (sid, sid_long, sid_short) = get_scan_id(self.context)
        if sid:
            if sid != items[0]:
                items.append(sid)
            items.append(sid_long)
            items.append(sid_short)
        if self.context.description:
            items.append(self.context.description)
        return u" ".join(items)

    def __call__(self):
        """ Extend the searchable text with a custom string """
        primary_field = IPrimaryFieldInfo(self.context)
        if primary_field.value is None:
            return self.searchable_text()
        mimetype = primary_field.value.contentType
        transforms = getToolByName(self.context, 'portal_transforms')
        value = str(primary_field.value.data)
        filename = primary_field.value.filename
        try:
            transformed_value = transforms.convertTo('text/plain', value,
                                                     mimetype=mimetype,
                                                     filename=filename)
            if not transformed_value:
                return self.searchable_text()
            ret = _unicode_save_string_concat(self.searchable_text(),
                                              transformed_value.getData())
            if ret.startswith(' '):
                ret = ret[1:]
            return ret
        except:  # noqa
            return self.searchable_text()


class IdmSearchableExtender(object):
    """
        Extends SearchableText of dms document.
        Concatenate the contained dmsmainfiles scan_id infos.
    """
    adapts(IDmsDocument)
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
            return u' '.join(index)

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
    """ Managing missing terms for IImioDmsIncomingMail. """

    def complete_voc(self):
        if self.field.getName() == 'mail_type':
            return getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')(self.context)
        elif self.field.getName() == 'assigned_user':
            return getUtility(IVocabularyFactory, 'plone.app.vocabularies.Users')(self.context)
        else:
            return SimpleVocabulary([])


class OMMCTV(MissingChoiceTermsVocabulary, MissingTerms):
    """ Managing missing terms for IImioDmsOutgoingMail. """

    def complete_voc(self):
        if self.field.getName() == 'mail_type':
            return getUtility(IVocabularyFactory, 'imio.dms.mail.OMMailTypesVocabulary')(self.context)
        else:
            return SimpleVocabulary([])


#########################
# validation adapters #
#########################

class ContactAutocompleteValidator(SimpleFieldValidator):

    adapts(
        Interface,
        Interface,
        Interface,
        IField,
        IContactAutocompleteWidget)

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
    """ DataManager for datetime widget """

    def set(self, value):
        value_s = value.strftime("%Y%m%d%H%M")
        stored = self.query(default=None)
        stored_s = stored is not None and stored.strftime("%Y%m%d%H%M") or ''
        # store value if value is really changed
        if value_s != stored_s:
            # adding seconds
            if stored_s:
                value = value + datetime.timedelta(seconds=stored.second)
            super(DateDataManager, self).set(value)
