# encoding: utf-8
from zope.component import adapts, getMultiAdapter, getUtility
from zope.interface import implements
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from z3c.form.term import MissingChoiceTermsVocabulary, MissingTermsMixin
from z3c.form.interfaces import IContextAware, IDataManager

from AccessControl import getSecurityManager
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import sortable_title
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker as common_marker
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu
from plone.app.contenttypes.indexers import _unicode_save_string_concat
from plone.app.uuid.utils import uuidToObject
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from plone.rfc822.interfaces import IPrimaryFieldInfo

from collective import dexteritytextindexer
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.content.organization import IOrganization
from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.mailcontent.indexers import add_parent_organizations
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task.interfaces import ITaskContent
from imio.prettylink.adapters import PrettyLinkAdapter

from dmsmail import IImioDmsIncomingMail, IImioDmsOutgoingMail
from .overrides import IDmsPerson

from utils import review_levels, highest_review_level, organizations_with_suffixes, get_scan_id, list_wf_states

from . import EMPTY_DATE

#######################
# Compound criterions #
#######################

default_criterias = {'dmsincomingmail': {'review_state': {'query': ['proposed_to_manager',
                                                                    'proposed_to_service_chief']}},
                     'task': {'review_state': {'query': ['to_assign', 'realized']}}}
no_group_validation_states = {
    'dmsincomingmail': ['created', 'proposed_to_manager', 'proposed_to_agent', 'in_treatment', 'closed'],
    'task': ['created', 'to_do', 'in_progress', 'closed'],
    'dmsoutgoingmail': ['created', 'to_be_signed', 'scanned', 'sent']}


def highest_validation_criterion(portal_type):
    """ Return a query criterion corresponding to current user highest validation level """
    groups = api.group.get_groups(user=api.user.get_current())
    highest_level = highest_review_level(portal_type, str([g.id for g in groups]))
    if highest_level is None:
        return default_criterias[portal_type]
    ret = {}
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
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion('dmsincomingmail')


class TaskHighestValidationCriterion(object):
    """
        Return catalog criteria following highest validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion('task')


def validation_criterion(context, portal_type):
    """ Return a query criterion corresponding to current user validation level """
    groups = api.group.get_groups(user=api.user.get_current())
    orgs = organizations_with_suffixes(groups, ['validateur'])
    ret = {'state_group': {'query': []}}
    if portal_type == 'dmsincomingmail' and 'dir_general' in [g.id for g in groups]:
        ret['state_group']['query'].append('proposed_to_manager')
    if orgs:
        # we get group validation states
        states = [st.id for st in list_wf_states(context, portal_type)
                  if st.id not in no_group_validation_states[portal_type]]
        for state in states:
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
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
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
        orgs = organizations_with_suffixes(groups, ['encodeur', 'validateur', 'editeur', 'lecteur'])
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
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': {'query': orgs}}


class OutgoingMailInCopyGroupCriterion(object):
    """
        Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['encodeur', 'validateur', 'editeur', 'lecteur'])
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
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'assigned_group': {'query': orgs}}


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
            if api.content.get_state(self.context) in registry.get(
                    'imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states') or []:
                icons.append(("++resource++imio.dms.mail/remark.gif", translate("Remark icon", domain="imio.dms.mail",
                                                                                context=self.request)))
        return icons


class OMPrettyLinkAdapter(PrettyLinkAdapter):

    def _leadingIcons(self):
        icons = []
        if self.context.task_description and self.context.task_description.raw:
            registry = getUtility(IRegistry)
            if api.content.get_state(self.context) in registry.get(
                    'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states') or []:
                icons.append(("++resource++imio.dms.mail/remark.gif", translate("Remark icon", domain="imio.dms.mail",
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
def userid_person_index(obj):
    """ Index method escaping acquisition. We use an existing index to store person userid """
    if base_hasattr(obj, 'userid') and obj.userid:
        return obj.userid
    return common_marker


@indexer(IHeldPosition)
def userid_heldposition_index(obj):
    """ Index method escaping acquisition. We use an existing index to store heldposition userid """
    parent = obj.aq_parent
    if base_hasattr(parent, 'userid') and parent.userid:
        return parent.userid
    return common_marker


@indexer(IImioDmsIncomingMail)
def mail_date_index(obj):
    # No acquisition pb because mail_date isn't an attr but cannot store None
    if obj.original_mail_date:
        return obj.original_mail_date
    else:
        return EMPTY_DATE
    return common_marker


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


@indexer(IImioDmsOutgoingMail)
def om_in_out_date_index(obj):
    # No acquisition pb because in_out_date isn't an attr
    if obj.outgoing_date:
        return obj.outgoing_date
    else:
        return EMPTY_DATE
    return common_marker


@indexer(IDmsDocument)
def state_group_index(obj):
    # No acquisition pb because state_group isn't an attr
    state = api.content.get_state(obj=obj)
    if state in no_group_validation_states[obj.portal_type]:
        return state
    else:
        return "%s,%s" % (state, obj.treating_groups)


@indexer(ITaskContent)
def task_state_group_index(obj):
    # No acquisition pb because state_group isn't an attr
    state = api.content.get_state(obj=obj)
    return "%s,%s" % (state, obj.assigned_group)


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


class ScanSearchableExtender(object):
    adapts(IScanFields)
    implements(dexteritytextindexer.IDynamicTextIndexExtender)

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
        except:
            return self.searchable_text()


class IdmSearchableExtender(object):
    """
        Extends SearchableText of dms document.
        Concatenate the contained dmsmainfiles scan_id infos.
    """
    adapts(IDmsDocument)
    implements(dexteritytextindexer.IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        brains = self.context.portal_catalog.unrestrictedSearchResults(portal_type='dmsmainfile',
                                                                       path={'query':
                                                                       '/'.join(self.context.getPhysicalPath()),
                                                                       'depth': 1})
        index = []
        for brain in brains:
            sid_infos = get_scan_id(brain)
            if sid_infos[0]:
                index += sid_infos
        if index:
            return u' '.join(index)

#########################
# vocabularies adapters #
#########################


class MissingTerms(MissingTermsMixin):

    def getTerm(self, value):
        try:
            return super(MissingTermsMixin, self).getTerm(value)
        except LookupError:
            try:
                return self.complete_voc().getTerm(value)
            except LookupError:
                pass
        if (IContextAware.providedBy(self.widget) and not self.widget.ignoreContext):
            curValue = getMultiAdapter((self.widget.context, self.field), IDataManager).query()
            if curValue == value:
                return self._makeMissingTerm(value)
        raise

    def getTermByToken(self, token):
        try:
            return super(MissingTermsMixin, self).getTermByToken(token)
        except LookupError:
            try:
                return self.complete_voc().getTermByToken(token)
            except LookupError:
                pass
        if (IContextAware.providedBy(self.widget) and not self.widget.ignoreContext):
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
