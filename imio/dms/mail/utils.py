# encoding: utf-8
from operator import methodcaller
from collections import OrderedDict

from zope.component.hooks import getSite
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.component import getUtility

from plone import api
from plone.app.textfield.value import RichTextValue
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import getToolByName
from Products.Five import BrowserView

from browser.settings import IImioDmsMailConfig


# methods

review_levels = {'dmsincomingmail': OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                                 ('_validateur', {'st': ['proposed_to_service_chief'],
                                                                  'org': 'treating_groups'})]),
                 'task': OrderedDict([('_validateur', {'st': ['to_assign', 'realized'],
                                                       'org': 'assigned_group'})])}


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


def get_selected_org_suffix_users(org_uid, suffixes):
    """
        Get users that belongs to suffixed groups related to selected organization.
    """
    org_members = []
    # only add to vocabulary users with these functions in the organization
    for function_id in suffixes:
        groupname = "{}_{}".format(org_uid, function_id)
        members = api.user.get_users(groupname=groupname)
        for member in members:
            if member not in org_members:
                org_members.append(member)
    return org_members


def voc_selected_org_suffix_users(org_uid, suffixes):
    """
        Return users vocabulary that belongs to suffixed groups related to selected organization.
    """
    if not org_uid or org_uid == u'--NOVALUE--':
        return SimpleVocabulary([])
    terms = []
    # only add to vocabulary users with these functions in the organization
    for member in sorted(get_selected_org_suffix_users(org_uid, suffixes), key=methodcaller('getUserName')):
            terms.append(SimpleTerm(
                value=member.getUserName(),  # login
                token=member.getId(),  # id
                title=member.getUser().getProperty('fullname') or member.getUserName()))  # title
    return SimpleVocabulary(terms)


def list_wf_states(context, portal_type):
    """
        list all portal_type wf states
    """
    ordered_states = {
        'dmsincomingmail': ['created', 'proposed_to_manager', 'proposed_to_service_chief',
                            'proposed_to_agent', 'in_treatment', 'closed'],
        'task': ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed']
    }
    if portal_type not in ordered_states:
        return []
    pw = getToolByName(context, 'portal_workflow')
    ret = []
    # wf states
    for workflow in pw.getWorkflowsFor(portal_type):
        state_ids = [value.id for value in workflow.states.values()]
        break
    # keep ordered states
    for state in ordered_states[portal_type]:
        if state in state_ids:
            ret.append(state)
            state_ids.remove(state)
    # add missing
    for missing in state_ids:
        ret.append(missing)
    return ret


# May be moved to imio.helpers ?
def create_richtextval(text):
    """ Return a RichTextValue """
    if not isinstance(text, unicode):
        text = text.decode('utf8')
    return RichTextValue(raw=text, mimeType='text/html', outputMimeType='text/html', encoding='utf-8')


# views

class UtilsMethods(BrowserView):
    """ View containing utils methods """

    def user_is_admin(self):
        """ Test if current user is admin """
        user = api.user.get_current()
        if user.has_role('Manager') or user.has_role('Site Administrator'):
            return True
        return False

    def current_user_groups(self):
        """ Return current user groups """
        return api.group.get_groups(user=api.user.get_current())

    def current_user_groups_ids(self):
        """ Return current user groups ids """
        return [g.id for g in api.group.get_groups(user=api.user.get_current())]

    def highest_scan_id(self):
        """ Return highest scan id """
        pc = getToolByName(self.context, 'portal_catalog')
        brains = pc(portal_type='dmsmainfile', sort_on='scan_id', sort_order='descending', sort_limit=1)
        if brains:
            return brains[0].scan_id
        else:
            return 'No scan id'


class IdmUtilsMethods(UtilsMethods):
    """ View containing incoming mail utils methods """

    def get_im_folder(self):
        """ Get the incoming-mail folder """
        portal = getSite()
        return portal['incoming-mail']

    def user_has_review_level(self, portal_type=None):
        """ Test if the current user has a review level """
        groups = self.current_user_groups()
        if portal_type is None:
            portal_type = self.context.portal_type
        if highest_review_level(portal_type, str([g.id for g in groups])) is not None:
            return True
        else:
            return False

    def idm_has_assigned_user(self):
        """ Test if assigned_user is set or if the test is required or if the user is admin """
        if self.context.assigned_user is not None:
            return True
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if not settings.assigned_user_check:
            return True
        if self.user_is_admin():
            return True
        return False

    def created_col_cond(self):
        """ Condition for searchfor_created collection """
        if 'encodeurs' in self.current_user_groups_ids():
            return True
        return False

    def proposed_to_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_manager collection """
        if 'dir_general' in self.current_user_groups_ids():
            return True
        return False

    def proposed_to_serv_chief_col_cond(self):
        """ Condition for searchfor_proposed_to_service_chief collection """
        if organizations_with_suffixes(self.current_user_groups(), ['validateur']):
            return True
        return False
