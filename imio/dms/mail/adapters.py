# encoding: utf-8
from collections import OrderedDict
from AccessControl import getSecurityManager
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu

review_levels = {'dmsincomingmail': OrderedDict([('dir_general', {'st': 'proposed_to_manager'}),
                                                 ('_validateur', {'st': 'proposed_to_service_chief',
                                                                  'org': 'treating_groups'})])}


def highest_review_level(portal_type, group_ids):
    """ Return the first review level """
    if portal_type not in review_levels:
        return None
    for keyg in review_levels[portal_type].keys():
        if keyg.startswith('_') and "%s'" % keyg in group_ids:
            return keyg
        elif "'%s'" % keyg in group_ids:
            return keyg
    return None


class IncomingMailHighestValidationCriterion(object):

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        highest_level = highest_review_level('dmsincomingmail', str([g.id for g in groups]))
        if highest_level is None:
            return {}
        ret = {}
        criterias = review_levels['dmsincomingmail'][highest_level]
        if 'st' in criterias:
            ret['review_state'] = criterias['st']
        if 'org' in criterias:
            organizations = []
            for group in groups:
                if group.id.endswith(highest_level):
                    organizations.append(group.id[:-len(highest_level)])
            ret[criterias['org']] = organizations
        return ret


def organizations_with_suffixes(groups, suffixes):
    """ Return organization uid with suffixes """
    orgs = []
    for group in groups:
        parts = group.id.split('_')
        if len(parts) == 1:
            continue
        for suffix in suffixes:
            if suffix == parts[1] and parts[0] not in orgs:
                orgs.append(parts[0])
    return orgs


class IncomingMailInTreatingGroupCriterion(object):

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'treating_groups': orgs}


class IncomingMailInCopyGroupCriterion(object):

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': orgs}


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
