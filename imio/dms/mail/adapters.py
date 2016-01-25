# encoding: utf-8
from zope.component import adapts
from zope.interface import implements
from collective import dexteritytextindexer
from AccessControl import getSecurityManager
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu
from plone.app.contenttypes.indexers import _unicode_save_string_concat
from plone.indexer import indexer
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker as common_marker
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from dmsmail import IDmsIncomingMail
from utils import review_levels, highest_review_level, organizations_with_suffixes, get_scan_id

#######################
# Compound criterions #
#######################

default_criterias = {'dmsincomingmail': {'review_state': {'query': ['proposed_to_manager',
                                                                    'proposed_to_service_chief']}},
                     'task': {'review_state': {'query': ['to_assign', 'realized']}}}


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
# Indexes adapters #
####################

@indexer(IContentish)
def mail_type_index(obj):
    """ Index method escaping acquisition """
    if base_hasattr(obj, 'mail_type') and obj.mail_type:
        return obj.mail_type
    return common_marker


@indexer(IDmsIncomingMail)
def mail_date_index(obj):
    # No acquisition pb because mail_date isn't an attr but cannot store None
    if obj.original_mail_date:
        return obj.original_mail_date
    return common_marker


@indexer(IDmsIncomingMail)
def in_out_date_index(obj):
    # No acquisition pb because in_out_date isn't an attr
    return obj.reception_date


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
